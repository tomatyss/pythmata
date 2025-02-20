from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessInstance, ProcessStatus
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


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
        logger.info(
            f"[TokenVerification] Verifying token state for {token.id}")
        logger.debug(f"[TokenVerification] Token details: {token.to_dict()}")

        # Get current token state from storage
        stored_token = await self.state_manager.get_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        logger.debug(
            f"[TokenVerification] Retrieved stored token state: {stored_token}")

        if not stored_token:
            logger.error(
                f"[TokenVerification] Token {token.id} not found in storage")
            raise TokenStateError(f"Token not found: {token.id}")

        current_state = stored_token.get("state")
        logger.info(
            f"[TokenVerification] Token {token.id} current state: {current_state}")

        if current_state != TokenState.ACTIVE.value:
            logger.error(
                f"[TokenVerification] Token {token.id} is in invalid state: {current_state}")
            raise TokenStateError(
                f"Token {token.id} is not active (state: {current_state})"
            )

        logger.info(
            f"[TokenVerification] Token {token.id} verification successful")

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
        logger.info(
            f"[TokenCreation] Starting creation of initial token for instance {instance_id} at node {start_event_id}"
        )

        # Log all existing tokens for this instance
        all_tokens = await self.state_manager.get_token_positions(instance_id)
        logger.info(
            f"[TokenState] Current tokens for instance {instance_id}: {len(all_tokens)} tokens"
        )
        for t in all_tokens:
            logger.info(f"[TokenState] Existing token: {t}")

        # Log Redis keys for this instance
        keys = await self.state_manager.redis.keys(f"process:{instance_id}:*")
        logger.info(
            f"[RedisState] Current Redis keys for instance {instance_id}: {keys}")

        token = Token(instance_id=instance_id, node_id=start_event_id)
        logger.info(
            f"[TokenCreation] Created new token object: {token.to_dict()}")

        # Check if token already exists
        logger.info(f"[TokenIdempotency] Checking for existing token at {start_event_id}")
        existing_token = await self.state_manager.get_token(
            instance_id=instance_id, node_id=start_event_id
        )
        if existing_token:
            logger.info(
                f"[TokenIdempotency] Token already exists at {start_event_id} for instance {instance_id}, returning existing token"
            )
            logger.debug(f"[TokenIdempotency] Existing token details: {existing_token}")
            # Return existing token instead of raising an error for idempotency
            return Token(
                instance_id=instance_id,
                node_id=start_event_id,
                token_id=UUID(existing_token["id"]) if existing_token.get("id") else None,
                data=existing_token.get("data", {}),
                state=TokenState(existing_token.get("state", "ACTIVE"))
            )
        logger.info(f"[TokenIdempotency] No existing token found, proceeding with creation")

        try:
            # Create token atomically
            async with self.state_manager.redis.pipeline(transaction=True) as pipe:
                logger.info(
                    f"[RedisTransaction] Starting atomic token creation for {token.id}")

                # Check for any locks
                lock_key = f"lock:process:{instance_id}"
                lock_exists = await self.state_manager.redis.exists(lock_key)
                logger.info(
                    f"[LockState] Lock status for instance {instance_id}: exists={lock_exists}")

                await self.state_manager.add_token(
                    instance_id=instance_id,
                    node_id=start_event_id,
                    data=token.to_dict(),
                )
                await pipe.execute()

                # Verify token was created
                created_token = await self.state_manager.get_token(
                    instance_id=instance_id, node_id=start_event_id
                )
                logger.info(
                    f"[TokenVerification] Token creation verification: {created_token is not None}"
                )
                if created_token:
                    logger.info(
                        f"[TokenVerification] Created token state: {created_token}")

            logger.info(
                f"[TokenCreation] Initial token {token.id} created successfully")
            return token
        except Exception as e:
            logger.error(f"Failed to create initial token: {str(e)}")
            raise

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
            TokenStateError: If token state is invalid or lock cannot be acquired
        """
        logger.info(
            f"Moving token {token.id} from {token.node_id} to {target_node_id}")

        # Acquire instance lock first
        if not await self.state_manager.acquire_lock(token.instance_id):
            logger.error(
                f"Failed to acquire lock for instance {token.instance_id}")
            raise TokenStateError("Failed to acquire instance lock")

        try:
            # Verify token state
            await self._verify_token_state(token)

            # Handle transaction boundaries if instance manager is provided
            if instance_manager:
                if target_node_id == "Transaction_End":
                    logger.info(
                        f"Handling transaction end for token {token.id}")
                    return await self._handle_transaction_end(token, instance_manager)
                elif target_node_id.startswith("Transaction_") and target_node_id not in [
                    "Transaction_Start",
                    "Transaction_End",
                ]:
                    logger.info(f"Starting transaction for token {token.id}")
                    await instance_manager.start_transaction(
                        UUID(token.instance_id), target_node_id
                    )
                    target_node_id = "Transaction_Start"

            # Use Redis transaction for atomic move
            logger.info(
                f"[RedisTransaction] Starting atomic token move operation for {token.id}")
            logger.debug(
                f"[RedisTransaction] Moving from {token.node_id} to {target_node_id}")

            async with self.state_manager.redis.pipeline(transaction=True) as pipe:
                # Create new token at target node first
                new_token = token.copy(
                    node_id=target_node_id, scope_id=token.scope_id)
                logger.info(
                    f"[TokenCreation] Creating new token {new_token.id} at {target_node_id}")
                logger.debug(
                    f"[TokenState] New token data: {new_token.to_dict()}")
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

                # Then remove old token
                logger.info(f"Removing token {token.id} from {token.node_id}")
                await self.state_manager.remove_token(
                    instance_id=token.instance_id, node_id=token.node_id
                )
                await pipe.delete(f"tokens:{token.instance_id}")

                # Execute transaction
                logger.info(
                    f"[RedisTransaction] Executing Redis pipeline for token movement")
                await pipe.execute()
                logger.info(
                    f"[TokenMovement] Token {token.id} moved to {target_node_id} successfully")
                logger.debug(
                    f"[TokenMovement] Final token state: {new_token.to_dict()}")

            # Handle process completion if moving to end event
            if target_node_id == "End_1" and instance_manager:
                logger.info(
                    f"[ProcessCompletion] Token {token.id} reached end event, handling completion")
                logger.debug(
                    f"[ProcessCompletion] Instance ID: {token.instance_id}")
                await self._handle_process_completion(token, instance_manager)

            return new_token
        except Exception as e:
            logger.error(f"Failed to move token: {str(e)}")
            raise
        finally:
            # Always release the lock
            await self.state_manager.release_lock(token.instance_id)

    async def consume_token(self, token: Token) -> None:
        """
        Consume a token (remove it from the process).

        Args:
            token: The token to consume

        Raises:
            TokenStateError: If token state is invalid or lock cannot be acquired
        """
        logger.info(f"Consuming token {token.id} at {token.node_id}")

        # Acquire instance lock first
        if not await self.state_manager.acquire_lock(token.instance_id):
            logger.error(
                f"Failed to acquire lock for instance {token.instance_id}")
            raise TokenStateError("Failed to acquire instance lock")

        try:
            # Get token state
            stored_token = await self.state_manager.get_token(
                instance_id=token.instance_id, node_id=token.node_id
            )

            if not stored_token:
                logger.error(f"Token {token.id} not found for consumption")
                raise TokenStateError(f"Token not found: {token.id}")

            if stored_token.get("state") != TokenState.ACTIVE.value:
                logger.error(
                    f"Cannot consume inactive token {token.id} (state: {stored_token.get('state')})"
                )
                raise TokenStateError(
                    f"Token {token.id} is not active (state: {stored_token.get('state')})"
                )

            # Use Redis transaction for atomic consumption
            async with self.state_manager.redis.pipeline(transaction=True) as pipe:
                # Remove token atomically
                await self.state_manager.remove_token(
                    instance_id=token.instance_id, node_id=token.node_id
                )
                await pipe.delete(f"tokens:{token.instance_id}")
                await pipe.execute()
                logger.info(f"Token {token.id} consumed successfully")
        except Exception as e:
            logger.error(f"Failed to consume token: {str(e)}")
            raise
        finally:
            # Always release the lock
            await self.state_manager.release_lock(token.instance_id)

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
        logger.info(
            f"Splitting token {token.id} into {len(target_node_ids)} new tokens"
        )

        try:
            # Verify token state before operation
            await self._verify_token_state(token)

            # Use Redis transaction for atomic split
            async with self.state_manager.redis.pipeline(transaction=True) as pipe:
                logger.info(
                    f"Removing original token {token.id} from {token.node_id}")
                # Remove original token
                await self.state_manager.remove_token(
                    instance_id=token.instance_id, node_id=token.node_id
                )
                await pipe.delete(f"tokens:{token.instance_id}")

                # Create new tokens
                new_tokens = []
                for node_id in target_node_ids:
                    new_token = token.copy(node_id=node_id)
                    logger.info(
                        f"Creating new token {new_token.id} at {node_id}")
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
                logger.info(
                    f"Token split completed successfully, created {len(new_tokens)} new tokens"
                )

            return new_tokens
        except Exception as e:
            logger.error(f"Failed to split token: {str(e)}")
            raise

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
        logger.info(f"Updating token {token.id} state to {state.value}")
        try:
            # Verify token exists before update
            stored_token = await self.state_manager.get_token(
                instance_id=token.instance_id, node_id=token.node_id
            )
            if not stored_token:
                logger.error(f"Token {token.id} not found for state update")
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
                logger.info(
                    f"Token {token.id} state updated successfully to {state.value}"
                )
        except Exception as e:
            logger.error(f"Failed to update token state: {str(e)}")
            raise

    async def _handle_transaction_end(self, token: Token, instance_manager) -> Token:
        """Handle moving token to transaction end."""
        logger.info(f"Handling transaction end for token {token.id}")
        try:
            # Complete the transaction
            logger.info(
                f"Completing transaction for instance {token.instance_id}")
            await instance_manager.complete_transaction(UUID(token.instance_id))

            # Use Redis transaction for atomic operation
            async with self.state_manager.redis.pipeline(transaction=True) as pipe:
                logger.info(f"Removing token {token.id} from {token.node_id}")
                # Remove current token
                await self.state_manager.remove_token(
                    instance_id=token.instance_id, node_id=token.node_id
                )
                await pipe.delete(f"tokens:{token.instance_id}")

                # Create new token at End_1
                new_token = token.copy(node_id="End_1")
                logger.info(f"Creating new token {new_token.id} at End_1")
                await self.state_manager.add_token(
                    instance_id=new_token.instance_id,
                    node_id=new_token.node_id,
                    data=new_token.to_dict(),
                )

                # Execute transaction
                await pipe.execute()
                logger.info(f"Transaction end handling completed successfully")

            # Mark process as completed
            await self._handle_process_completion(token, instance_manager)

            return new_token
        except Exception as e:
            logger.error(f"Failed to handle transaction end: {str(e)}")
            raise

    async def _handle_process_completion(self, token: Token, instance_manager) -> None:
        """Handle process completion when token reaches end event."""
        logger.info(
            f"Handling process completion for instance {token.instance_id}")
        try:
            instance = await instance_manager.session.get(
                ProcessInstance, UUID(token.instance_id)
            )
            if instance:
                logger.info(
                    f"Updating instance {token.instance_id} status to COMPLETED"
                )
                instance.status = ProcessStatus.COMPLETED
                instance.end_time = datetime.now(UTC)
                await instance_manager.session.commit()
                logger.info(
                    f"Process instance {token.instance_id} completed successfully"
                )
            else:
                logger.warning(
                    f"Process instance {token.instance_id} not found for completion"
                )
        except Exception as e:
            logger.error(f"Failed to handle process completion: {str(e)}")
            raise
