import logging
from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessInstance, ProcessStatus

logger = logging.getLogger(__name__)


class TokenStateError(Exception):
    """Raised when token state is invalid for requested operation."""



class TokenManager:
    """
    Manages token operations including creation, movement, and state changes.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    async def _verify_token_state(self, token: Token) -> None:
        """
        Verify token is in valid state for operations.

        Args:
            token: Token to verify

        Raises:
            TokenStateError: If token state is invalid
        """
        # Get current token state from storage
        stored_token = await self.state_manager.get_token(
            instance_id=token.instance_id, node_id=token.node_id
        )

        if not stored_token:
            raise TokenStateError(f"Token not found: {token.id}")

        if stored_token.get("state") != TokenState.ACTIVE.value:
            raise TokenStateError(
                f"Token {token.id} is not active (state: {stored_token.get('state')})"
            )

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

        # Check if token already exists
        existing_token = await self.state_manager.get_token(
            instance_id=instance_id, node_id=start_event_id
        )
        if existing_token:
            raise TokenStateError(
                f"Token already exists at {start_event_id} for instance {instance_id}"
            )

        # Create token atomically
        async with self.state_manager.redis.pipeline(transaction=True) as pipe:
            await self.state_manager.add_token(
                instance_id=instance_id, node_id=start_event_id, data=token.to_dict()
            )
            await pipe.execute()

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

        Raises:
            TokenStateError: If token state is invalid
        """
        # Verify token state before operation
        await self._verify_token_state(token)

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

        # Use Redis transaction for atomic move
        async with self.state_manager.redis.pipeline(transaction=True) as pipe:
            # Remove token from current node
            await self.state_manager.remove_token(
                instance_id=token.instance_id, node_id=token.node_id
            )
            await pipe.delete(f"tokens:{token.instance_id}")

            # Create new token at target node
            new_token = token.copy(node_id=target_node_id, scope_id=token.scope_id)
            await self.state_manager.add_token(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                data=new_token.to_dict(),
            )
            await self.state_manager.update_token_state(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                state=TokenState.ACTIVE,
                scope_id=new_token.scope_id,
            )

            # Execute transaction
            await pipe.execute()

        # Handle process completion if moving to end event
        if target_node_id == "End_1" and instance_manager:
            await self._handle_process_completion(token, instance_manager)

        return new_token

    async def consume_token(self, token: Token) -> None:
        """
        Consume a token (remove it from the process).

        Args:
            token: The token to consume

        Raises:
            TokenStateError: If token state is invalid
        """
        # Use Redis transaction for atomic consumption
        async with self.state_manager.redis.pipeline(transaction=True) as pipe:
            # Get token state within transaction
            stored_token = await self.state_manager.get_token(
                instance_id=token.instance_id, node_id=token.node_id
            )

            if not stored_token:
                raise TokenStateError(f"Token not found: {token.id}")

            if stored_token.get("state") != TokenState.ACTIVE.value:
                raise TokenStateError(
                    f"Token {token.id} is not active (state: {stored_token.get('state')})"
                )

            # Remove token atomically
            await self.state_manager.remove_token(
                instance_id=token.instance_id, node_id=token.node_id
            )
            await pipe.delete(f"tokens:{token.instance_id}")
            await pipe.execute()

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

        Raises:
            TokenStateError: If token state is invalid
        """
        # Verify token state before operation
        await self._verify_token_state(token)

        # Use Redis transaction for atomic split
        async with self.state_manager.redis.pipeline(transaction=True) as pipe:
            # Remove original token
            await self.state_manager.remove_token(
                instance_id=token.instance_id, node_id=token.node_id
            )
            await pipe.delete(f"tokens:{token.instance_id}")

            # Create new tokens
            new_tokens = []
            for node_id in target_node_ids:
                new_token = token.copy(node_id=node_id)
                await self.state_manager.add_token(
                    instance_id=new_token.instance_id,
                    node_id=new_token.node_id,
                    data=new_token.to_dict(),
                )
                await self.state_manager.update_token_state(
                    instance_id=new_token.instance_id,
                    node_id=new_token.node_id,
                    state=TokenState.ACTIVE,
                )
                new_tokens.append(new_token)

            # Execute transaction
            await pipe.execute()

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

        Raises:
            TokenStateError: If token state is invalid
        """
        # Verify token exists before update
        stored_token = await self.state_manager.get_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        if not stored_token:
            raise TokenStateError(f"Token not found: {token.id}")

        # Use Redis transaction for atomic update
        async with self.state_manager.redis.pipeline(transaction=True) as pipe:
            await self.state_manager.update_token_state(
                instance_id=token.instance_id,
                node_id=token.node_id,
                state=state,
                scope_id=scope_id or token.scope_id,
            )
            await pipe.execute()

    async def _handle_transaction_end(self, token: Token, instance_manager) -> Token:
        """Handle moving token to transaction end."""
        # Complete the transaction
        await instance_manager.complete_transaction(UUID(token.instance_id))

        # Use Redis transaction for atomic operation
        async with self.state_manager.redis.pipeline(transaction=True) as pipe:
            # Remove current token
            await self.state_manager.remove_token(
                instance_id=token.instance_id, node_id=token.node_id
            )
            await pipe.delete(f"tokens:{token.instance_id}")

            # Create new token at End_1
            new_token = token.copy(node_id="End_1")
            await self.state_manager.add_token(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                data=new_token.to_dict(),
            )

            # Execute transaction
            await pipe.execute()

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
