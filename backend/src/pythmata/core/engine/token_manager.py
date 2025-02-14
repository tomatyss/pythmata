import logging
from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessInstance, ProcessStatus

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages token operations including creation, movement, and state changes.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    async def create_initial_token(
        self, instance_id: str, start_event_id: str
    ) -> Token:
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
            instance_id=instance_id, node_id=start_event_id, data=token.to_dict()
        )
        # Set initial token state to active
        await self.state_manager.update_token_state(
            instance_id=instance_id, node_id=start_event_id, state=TokenState.ACTIVE
        )
        return token

    async def move_token(
        self,
        token: Token,
        target_node_id: str,
        instance_manager=None,  # Optional instance manager for handling process completion
    ) -> Token:
        """
        Move a token to a new node.

        Args:
            token: The token to move
            target_node_id: ID of the target node
            instance_manager: Optional instance manager for process completion handling

        Returns:
            The moved token
        """
        # Handle transaction boundaries if instance manager is provided
        if instance_manager:
            if target_node_id == "Transaction_End":
                return await self._handle_transaction_end(token, instance_manager)
            elif target_node_id.startswith("Transaction_") and target_node_id not in [
                "Transaction_Start",
                "Transaction_End",
            ]:
                await instance_manager.start_transaction(
                    UUID(token.instance_id), target_node_id
                )
                target_node_id = "Transaction_Start"

        # Remove token from current node
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create new token at target node, preserving scope
        new_token = token.copy(node_id=target_node_id, scope_id=token.scope_id)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )
        # Set new token state to active, preserving scope
        await self.state_manager.update_token_state(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            state=TokenState.ACTIVE,
            scope_id=new_token.scope_id,
        )

        # Handle process completion if moving to end event
        if target_node_id == "End_1" and instance_manager:
            await self._handle_process_completion(token, instance_manager)

        return new_token

    async def _handle_transaction_end(self, token: Token, instance_manager) -> Token:
        """Handle moving token to transaction end."""
        # Complete the transaction
        await instance_manager.complete_transaction(UUID(token.instance_id))

        # Remove current token
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create new token at End_1
        new_token = token.copy(node_id="End_1")
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        # Mark process as completed
        await self._handle_process_completion(token, instance_manager)

        return new_token

    async def _handle_process_completion(self, token: Token, instance_manager) -> None:
        """Handle process completion when token reaches end event."""
        instance = await instance_manager.session.get(
            ProcessInstance, UUID(token.instance_id)
        )
        if instance:
            instance.status = ProcessStatus.COMPLETED
            instance.end_time = datetime.now(UTC)
            await instance_manager.session.commit()

    async def consume_token(self, token: Token) -> None:
        """
        Consume a token (remove it from the process).

        Args:
            token: The token to consume
        """
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

    async def split_token(
        self, token: Token, target_node_ids: List[str]
    ) -> List[Token]:
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
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create new tokens
        new_tokens = []
        for node_id in target_node_ids:
            new_token = token.copy(node_id=node_id)
            await self.state_manager.add_token(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                data=new_token.to_dict(),
            )
            # Set new token state to active
            await self.state_manager.update_token_state(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                state=TokenState.ACTIVE,
            )
            new_tokens.append(new_token)

        return new_tokens

    async def update_token_state(
        self, token: Token, state: TokenState, scope_id: Optional[str] = None
    ) -> None:
        """
        Update a token's state.

        Args:
            token: The token to update
            state: New state to set
            scope_id: Optional scope ID
        """
        await self.state_manager.update_token_state(
            instance_id=token.instance_id,
            node_id=token.node_id,
            state=state,
            scope_id=scope_id or token.scope_id,
        )
