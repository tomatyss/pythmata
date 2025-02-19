import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
from redis.asyncio import Redis

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.config import Settings
from pythmata.core.types import TokenState
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class StateManager:
    """Manages process state and variables using Redis."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._redis: Optional[Redis] = None
        self.lock_timeout = 30  # seconds

    @property
    def redis(self) -> Redis:
        """Get Redis connection, raising error if not connected."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")
        return self._redis

    async def connect(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Establish connection to Redis with retries.

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds

        Raises:
            RuntimeError: If connection fails after all retries
        """
        import asyncio

        last_error = None

        for attempt in range(max_retries):
            try:
                self._redis = redis.from_url(
                    str(self.settings.redis.url),
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=self.settings.redis.pool_size,
                )
                # Test connection
                await self._redis.ping()
                logger.info("Successfully connected to Redis")
                return
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:  # Don't sleep on last attempt
                    logger.warning(
                        f"Failed to connect to Redis (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(
                        f"Failed to connect to Redis after {max_retries} attempts: {e}"
                    )

        # If we get here, all retries failed
        raise RuntimeError(
            f"Failed to connect to Redis after {max_retries} attempts"
        ) from last_error

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def get_process_state(self, instance_id: str) -> Dict[str, Any]:
        """Get the current state of a process instance.

        Args:
            instance_id: The process instance ID

        Returns:
            Dict containing the process state
        """
        key = f"process:{instance_id}:state"
        state = await self.redis.get(key)
        return json.loads(state) if state else {}

    async def set_process_state(
        self, instance_id: str, state: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Set the state of a process instance.

        Args:
            instance_id: The process instance ID
            state: The state to store
            ttl: Optional TTL in seconds
        """
        key = f"process:{instance_id}:state"
        await self.redis.set(key, json.dumps(state), ex=ttl)

    async def get_variable(
        self,
        instance_id: str,
        name: str,
        scope_id: Optional[str] = None,
        check_parent: bool = True,
    ) -> Optional[ProcessVariableValue]:
        """Get a process variable.

        Args:
            instance_id: The process instance ID
            name: Variable name
            scope_id: Optional scope ID (e.g., subprocess ID)
            check_parent: Whether to check parent scope if not found in specified scope

        Returns:
            The variable value from specified scope, or parent scope if check_parent is True
        """
        key = f"process:{instance_id}:vars"

        # First try to get from specified scope
        if scope_id:
            scope_key = f"{scope_id}:{name}"
            value = await self.redis.hget(key, scope_key)
            if value:
                data = json.loads(value)
                return ProcessVariableValue.from_storage_format(data)

            # If not found and check_parent is True, traverse up the scope hierarchy
            if check_parent:
                # Split scope path into parts
                scope_parts = scope_id.split("/")
                while scope_parts:
                    # Remove last part to get parent scope
                    scope_parts.pop()
                    parent_scope = "/".join(scope_parts)

                    # Try to get variable from parent scope
                    parent_key = f"{parent_scope}:{name}" if parent_scope else name
                    value = await self.redis.hget(key, parent_key)
                    if value:
                        data = json.loads(value)
                        return ProcessVariableValue.from_storage_format(data)

                # If still not found, try root scope
                value = await self.redis.hget(key, name)
                if value:
                    data = json.loads(value)
                    return ProcessVariableValue.from_storage_format(data)
            return None
        else:
            # Direct access to root scope
            value = await self.redis.hget(key, name)
            if value:
                data = json.loads(value)
                return ProcessVariableValue.from_storage_format(data)
            return None

    async def set_variable(
        self,
        instance_id: str,
        name: str,
        variable: ProcessVariableValue,
        scope_id: Optional[str] = None,
    ) -> None:
        """Set a process variable.

        Args:
            instance_id: The process instance ID
            name: Variable name
            variable: Variable value and type
            scope_id: Optional scope ID (e.g., subprocess ID)
        """
        key = f"process:{instance_id}:vars"
        scope_key = f"{scope_id}:{name}" if scope_id else name
        storage_format = variable.to_storage_format()
        await self.redis.hset(key, scope_key, json.dumps(storage_format))

    async def get_token(
        self, instance_id: str, node_id: str, scope_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a specific token from a node.

        Args:
            instance_id: The process instance ID
            node_id: The node ID where the token is located
            scope_id: Optional scope ID to match specific token

        Returns:
            Token data if found, None otherwise
        """
        tokens = await self.get_token_positions(instance_id)
        for token in tokens:
            if token["node_id"] == node_id and token.get("scope_id") == scope_id:
                return token
        return None

    async def get_token_positions(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get current token positions for a process instance.

        Args:
            instance_id: The process instance ID

        Returns:
            List of token positions with duplicates removed
        """
        key = f"process:{instance_id}:tokens"
        tokens = await self.redis.lrange(key, 0, -1)

        # Parse tokens and remove duplicates by node_id and scope_id
        seen = set()
        unique_tokens = []
        for token in tokens:
            data = json.loads(token)
            key = (data["node_id"], data.get("scope_id"))
            if key not in seen:
                seen.add(key)
                unique_tokens.append(data)

        return unique_tokens

    async def add_token(
        self, instance_id: str, node_id: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a token to a node.

        Args:
            instance_id: The process instance ID
            node_id: The node ID where the token is placed
            data: Optional token data
        """
        key = f"process:{instance_id}:tokens"
        scope_id = data.get("scope_id") if data else None

        # Use Redis transaction to ensure atomic operation
        async with self.redis.pipeline(transaction=True) as pipe:
            # Get existing tokens
            tokens = await self.get_token_positions(instance_id)

            # Remove any existing token at the same node and scope
            new_tokens = [
                token
                for token in tokens
                if token["node_id"] != node_id or token.get("scope_id") != scope_id
            ]

            # Create new token
            new_token = {
                "instance_id": instance_id,
                "node_id": node_id,
                "state": "ACTIVE",
                "data": data or {},
                "id": str(uuid4()),
                "scope_id": scope_id,
            }
            new_tokens.append(new_token)

            # Replace token list atomically
            await pipe.delete(key)
            if new_tokens:
                await pipe.rpush(key, *[json.dumps(token) for token in new_tokens])
            await pipe.execute()

    async def get_scope_tokens(
        self, instance_id: str, scope_id: str
    ) -> List[Dict[str, Any]]:
        """Get tokens within a specific scope.

        Args:
            instance_id: The process instance ID
            scope_id: The scope ID (e.g., subprocess ID)

        Returns:
            List of tokens in the scope
        """
        key = f"process:{instance_id}:tokens"
        tokens = await self.redis.lrange(key, 0, -1)
        return [
            json.loads(token)
            for token in tokens
            if json.loads(token).get("scope_id") == scope_id
        ]

    async def clear_scope_tokens(self, instance_id: str, scope_id: str) -> None:
        """Remove all tokens and variables within a specific scope.

        Args:
            instance_id: The process instance ID
            scope_id: The scope ID to clear (e.g., subprocess ID)
        """
        # Clear tokens
        key = f"process:{instance_id}:tokens"
        tokens = await self.get_token_positions(instance_id)

        # Filter out tokens in the specified scope
        new_tokens = [token for token in tokens if token.get("scope_id") != scope_id]

        # Replace the token list
        await self.redis.delete(key)
        if new_tokens:
            await self.redis.rpush(key, *[json.dumps(token) for token in new_tokens])

        # Clear variables in scope
        vars_key = f"process:{instance_id}:vars"
        all_vars = await self.redis.hgetall(vars_key)

        # Remove variables in this scope
        for var_key in list(all_vars.keys()):
            if var_key.startswith(f"{scope_id}:"):
                await self.redis.hdel(vars_key, var_key)

    async def remove_token(
        self, instance_id: str, node_id: str, scope_id: Optional[str] = None
    ) -> None:
        """Remove a token from a node.

        Args:
            instance_id: The process instance ID
            node_id: The node ID to remove the token from
            scope_id: Optional scope ID to match specific token
        """
        key = f"process:{instance_id}:tokens"
        tokens = await self.get_token_positions(instance_id)

        # Filter out the token to remove, matching both node_id and scope_id if provided
        new_tokens = [
            token
            for token in tokens
            if token["node_id"] != node_id
            or (scope_id is not None and token.get("scope_id") != scope_id)
        ]

        # Replace the token list
        await self.redis.delete(key)
        if new_tokens:
            await self.redis.rpush(key, *[json.dumps(token) for token in new_tokens])

    async def acquire_lock(
        self, instance_id: str, timeout: Optional[int] = None
    ) -> bool:
        """Acquire a lock for a process instance.

        Args:
            instance_id: The process instance ID
            timeout: Lock timeout in seconds

        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = f"lock:process:{instance_id}"
        return await self.redis.set(
            lock_key, "1", ex=timeout or self.lock_timeout, nx=True
        )

    async def release_lock(self, instance_id: str) -> None:
        """Release a process instance lock.

        Args:
            instance_id: The process instance ID
        """
        lock_key = f"lock:process:{instance_id}"
        await self.redis.delete(lock_key)

    async def save_timer_state(
        self, instance_id: str, timer_id: str, state: Dict[str, Any]
    ) -> None:
        """Save timer state.

        Args:
            instance_id: The process instance ID
            timer_id: The timer event ID
            state: Timer state to save
        """
        key = f"process:{instance_id}:timer:{timer_id}"
        await self.redis.set(key, json.dumps(state))

    async def get_timer_state(
        self, instance_id: str, timer_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get timer state.

        Args:
            instance_id: The process instance ID
            timer_id: The timer event ID

        Returns:
            Timer state if exists, None otherwise
        """
        key = f"process:{instance_id}:timer:{timer_id}"
        state = await self.redis.get(key)
        return json.loads(state) if state else None

    async def delete_timer_state(self, instance_id: str, timer_id: str) -> None:
        """Delete timer state.

        Args:
            instance_id: The process instance ID
            timer_id: The timer event ID
        """
        key = f"process:{instance_id}:timer:{timer_id}"
        await self.redis.delete(key)

    async def update_token_state(
        self,
        instance_id: str,
        node_id: str,
        state: TokenState,
        scope_id: Optional[str] = None,
    ) -> None:
        """Update the state of a token at a specific node.

        Args:
            instance_id: The process instance ID
            node_id: The node ID where the token is located
            state: The new token state
            scope_id: Optional scope ID to match specific token
        """
        key = f"process:{instance_id}:tokens"
        tokens = await self.get_token_positions(instance_id)

        # Find and update the token state
        updated = False
        for token in tokens:
            if token["node_id"] == node_id and token.get("scope_id") == scope_id:
                token["state"] = state.value
                token["data"]["state"] = state.value  # Update state in data too
                updated = True
                break

        if not updated:
            raise ValueError(f"No token found at node {node_id} with scope {scope_id}")
        # Replace the token list
        await self.redis.delete(key)
        await self.redis.rpush(key, *[json.dumps(token) for token in tokens])
