import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import LockError

from pythmata.core.config import Settings

logger = logging.getLogger(__name__)


class StateManager:
    """Manages process state and variables using Redis."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis: Optional[Redis] = None
        self.lock_timeout = 30  # seconds

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self.redis = redis.from_url(
                str(self.settings.redis.url),
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.settings.redis.pool_size,
            )
            # Test connection
            await self.redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    async def get_process_state(self, instance_id: str) -> Dict[str, Any]:
        """Get the current state of a process instance.

        Args:
            instance_id: The process instance ID

        Returns:
            Dict containing the process state
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

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
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:state"
        await self.redis.set(key, json.dumps(state), ex=ttl)

    async def get_variable(
        self,
        instance_id: str,
        name: str,
        scope_id: Optional[str] = None,
        check_parent: bool = True,
    ) -> Any:
        """Get a process variable.

        Args:
            instance_id: The process instance ID
            name: Variable name
            scope_id: Optional scope ID (e.g., subprocess ID)
            check_parent: Whether to check parent scope if not found in specified scope

        Returns:
            The variable value from specified scope, or parent scope if check_parent is True
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:vars"

        # First try to get from specified scope
        if scope_id:
            scope_key = f"{scope_id}:{name}"
            value = await self.redis.hget(key, scope_key)
            if value:
                return json.loads(value)

            # If not found in subprocess scope and check_parent is True, try parent scope
            if check_parent:
                value = await self.redis.hget(key, name)
                return json.loads(value) if value else None
            return None
        else:
            # Direct access to parent scope
            value = await self.redis.hget(key, name)
            return json.loads(value) if value else None

    async def set_variable(
        self, instance_id: str, name: str, value: Any, scope_id: Optional[str] = None
    ) -> None:
        """Set a process variable.

        Args:
            instance_id: The process instance ID
            name: Variable name
            value: Variable value
            scope_id: Optional scope ID (e.g., subprocess ID)
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:vars"
        scope_key = f"{scope_id}:{name}" if scope_id else name
        await self.redis.hset(key, scope_key, json.dumps(value))

    async def get_token_positions(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get current token positions for a process instance.

        Args:
            instance_id: The process instance ID

        Returns:
            List of token positions
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:tokens"
        tokens = await self.redis.lrange(key, 0, -1)
        return [json.loads(token) for token in tokens]

    async def add_token(
        self, instance_id: str, node_id: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a token to a node.

        Args:
            instance_id: The process instance ID
            node_id: The node ID where the token is placed
            data: Optional token data
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:tokens"
        token = {
            "instance_id": instance_id,
            "node_id": node_id,
            "state": "ACTIVE",
            "data": data or {},
            "id": str(uuid4()),
            "scope_id": data.get("scope_id") if data else None,
        }
        await self.redis.rpush(key, json.dumps(token))

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
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

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
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

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

    async def remove_token(self, instance_id: str, node_id: str) -> None:
        """Remove a token from a node.

        Args:
            instance_id: The process instance ID
            node_id: The node ID to remove the token from
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:tokens"
        tokens = await self.get_token_positions(instance_id)

        # Filter out the token to remove
        new_tokens = [token for token in tokens if token["node_id"] != node_id]

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
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        lock_key = f"lock:process:{instance_id}"
        return await self.redis.set(
            lock_key, "1", ex=timeout or self.lock_timeout, nx=True
        )

    async def release_lock(self, instance_id: str) -> None:
        """Release a process instance lock.

        Args:
            instance_id: The process instance ID
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

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
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

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
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:timer:{timer_id}"
        state = await self.redis.get(key)
        return json.loads(state) if state else None

    async def delete_timer_state(self, instance_id: str, timer_id: str) -> None:
        """Delete timer state.

        Args:
            instance_id: The process instance ID
            timer_id: The timer event ID
        """
        if not self.redis:
            raise RuntimeError("Not connected to Redis")

        key = f"process:{instance_id}:timer:{timer_id}"
        await self.redis.delete(key)
