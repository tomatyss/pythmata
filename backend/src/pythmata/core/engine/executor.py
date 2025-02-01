from typing import Dict, List, Optional
from uuid import UUID

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

class ProcessExecutor:
    """
    Executes BPMN processes by managing token movement through nodes.
    
    The executor is responsible for:
    - Creating initial tokens at process start
    - Moving tokens between nodes
    - Splitting tokens at gateways
    - Consuming tokens at end events
    - Managing token state persistence
    """
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    async def create_initial_token(self, instance_id: str, start_event_id: str) -> Token:
        """
        Create a new token at a start event.
        
        Args:
            instance_id: Process instance ID
            start_event_id: ID of the start event node
            
        Returns:
            The created token
        """
        token = Token(instance_id=instance_id, node_id=start_event_id)
        await self.state_manager.add_token(
            instance_id=instance_id,
            node_id=start_event_id,
            data=token.to_dict()
        )
        return token

    async def move_token(self, token: Token, target_node_id: str) -> Token:
        """
        Move a token to a new node.
        
        Args:
            token: The token to move
            target_node_id: ID of the target node
            
        Returns:
            The moved token
        """
        # Remove token from current node
        # Remove token from current node
        await self.state_manager.remove_token(
            instance_id=token.instance_id,
            node_id=token.node_id
        )
        # Clear Redis cache for this instance
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")
        
        # Create new token at target node
        new_token = token.copy(node_id=target_node_id)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict()
        )
        
        return new_token

    async def consume_token(self, token: Token) -> None:
        """
        Consume a token (remove it from the process).
        
        Args:
            token: The token to consume
        """
        # Remove token and clear cache
        await self.state_manager.remove_token(
            instance_id=token.instance_id,
            node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

    async def split_token(self, token: Token, target_node_ids: List[str]) -> List[Token]:
        """
        Split a token into multiple tokens (e.g., at a parallel gateway).
        
        Args:
            token: The token to split
            target_node_ids: IDs of the target nodes
            
        Returns:
            List of new tokens
        """
        # Remove original token and clear cache
        await self.state_manager.remove_token(
            instance_id=token.instance_id,
            node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")
        
        # Create new tokens
        new_tokens = []
        for node_id in target_node_ids:
            new_token = token.copy(node_id=node_id)
            await self.state_manager.add_token(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                data=new_token.to_dict()
            )
            new_tokens.append(new_token)
            
        return new_tokens
