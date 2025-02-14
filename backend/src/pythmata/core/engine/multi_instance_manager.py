import logging
from typing import Dict, List, Optional

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

logger = logging.getLogger(__name__)


class MultiInstanceManager:
    """
    Manages multi-instance activities including parallel and sequential instances.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    async def create_parallel_instances(self, token: Token) -> List[Token]:
        """
        Create parallel instances for a multi-instance activity.

        Args:
            token: Token at the multi-instance activity node

        Returns:
            List of tokens for parallel instances
        """
        logger.debug(f"\nCreating parallel instances for token at {token.node_id}")
        logger.debug(f"Parent scope: {token.scope_id}")

        collection = token.data.get("collection", [])
        instance_tokens = []

        # Remove the original token first to avoid conflicts
        logger.debug("Removing original token")
        await self.state_manager.remove_token(
            instance_id=token.instance_id,
            node_id=token.node_id,
            scope_id=token.scope_id,  # Only remove token with matching scope
        )

        # Create instance tokens
        parent_scope = token.scope_id or ""
        logger.debug(
            f"Creating {len(collection)} instances with parent scope: {parent_scope}"
        )

        for i, item in enumerate(collection):
            # Create hierarchical scope ID
            instance_scope = f"{parent_scope}/{token.node_id}_instance_{i}".lstrip("/")
            logger.debug(f"Creating instance {i} with scope: {instance_scope}")

            # Preserve original token data and update with instance-specific data
            instance_data = token.data.copy()
            instance_data.update(
                {
                    "item": item,
                    "index": i,
                    "collection": collection,
                    "is_parallel": True,
                    "parent_scope": parent_scope,  # Store parent scope for reference
                }
            )

            # Use target_node_id if specified, otherwise keep original node_id
            target_node = instance_data.pop("target_node_id", token.node_id)
            instance_token = token.copy(
                scope_id=instance_scope,
                node_id=target_node,
                data=instance_data,
            )
            await self.state_manager.add_token(
                instance_id=instance_token.instance_id,
                node_id=instance_token.node_id,
                data=instance_token.to_dict(),
            )
            instance_tokens.append(instance_token)

        return instance_tokens

    async def create_sequential_instance(self, token: Token, index: int) -> Token:
        """
        Create a sequential instance for a multi-instance activity.

        Args:
            token: Token at the multi-instance activity node
            index: Index in the collection for this instance

        Returns:
            Token for the sequential instance
        """
        collection = token.data.get("collection", [])
        if index >= len(collection):
            raise ValueError(
                f"Index {index} out of range for collection size {len(collection)}"
            )

        # Preserve original token data and update with instance-specific data
        instance_data = token.data.copy()
        instance_data.update(
            {
                "item": collection[index],
                "index": index,
                "collection": collection,
                "is_parallel": False,
            }
        )

        instance_token = token.copy(
            scope_id=f"{token.node_id}_instance_{index}",
            data=instance_data,
        )

        # For first instance, remove the original token
        if index == 0:
            await self.state_manager.remove_token(
                instance_id=token.instance_id, node_id=token.node_id
            )
            await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        await self.state_manager.add_token(
            instance_id=instance_token.instance_id,
            node_id=instance_token.node_id,
            data=instance_token.to_dict(),
        )

        return instance_token

    async def complete_parallel_instance(
        self, token: Token, total_instances: int
    ) -> Optional[Token]:
        """
        Complete a parallel instance and check if all instances are complete.

        Args:
            token: Token of the completed instance
            total_instances: Total number of instances

        Returns:
            Token at next task if all instances complete, None otherwise
        """
        logger.debug(
            f"\nCompleting parallel instance - node_id: {token.node_id}, scope_id: {token.scope_id}"
        )

        # Update token state with scope
        token.state = TokenState.COMPLETED
        logger.debug("Updating token state to COMPLETED")
        await self.state_manager.update_token_state(
            instance_id=token.instance_id,
            node_id=token.node_id,
            state=TokenState.COMPLETED,
            scope_id=token.scope_id,
        )

        # Get fresh token list AFTER the update
        stored_tokens = await self.state_manager.get_token_positions(token.instance_id)
        logger.debug("\nStored tokens after update:")
        for t in stored_tokens:
            logger.debug(
                f"Token - node_id: {t['node_id']}, scope_id: {t.get('scope_id')}, state: {t.get('state')}"
            )

        # Get all tokens for this activity by node_id
        activity_tokens = [t for t in stored_tokens if t["node_id"] == token.node_id]

        # Count completed tokens from fresh state
        completed_tokens = [
            t for t in activity_tokens if t.get("state") == TokenState.COMPLETED.value
        ]

        # Check completion condition if specified
        completion_condition = token.data.get("completion_condition")
        should_complete = await self._evaluate_completion_condition(
            completion_condition, len(completed_tokens), total_instances
        )

        if should_complete:
            return await self._handle_completion(token, activity_tokens)

        return None

    async def complete_sequential_instance(
        self, token: Token, total_instances: int
    ) -> Token:
        """
        Complete a sequential instance and create next instance or complete activity.

        Args:
            token: Token of the completed instance
            total_instances: Total number of instances

        Returns:
            Token for next instance or at next task if all complete
        """
        current_index = token.data.get("index", 0)
        next_index = current_index + 1

        # Remove current instance token
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        if next_index < total_instances:
            # Create next sequential instance
            return await self.create_sequential_instance(token, next_index)
        else:
            # All instances completed, move to next task
            next_task_id = "Task_1"  # This should come from process definition
            new_token = token.copy(node_id=next_task_id, scope_id=None)
            await self.state_manager.add_token(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                data=new_token.to_dict(),
            )
            return new_token

    async def handle_empty_collection(self, token: Token, next_task_id: str) -> Token:
        """
        Handle case when multi-instance activity has empty collection.

        Args:
            token: Token at the multi-instance activity
            next_task_id: ID of the next task

        Returns:
            Token moved to next task
        """
        # Remove token from current node
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create token at next task
        new_token = token.copy(node_id=next_task_id, scope_id=None)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token

    async def _evaluate_completion_condition(
        self, condition: Optional[str], completed_count: int, total_instances: int
    ) -> bool:
        """Evaluate completion condition for parallel instances."""
        if condition:
            # Create context for condition evaluation
            context = {"count": completed_count}
            try:
                return eval(condition, {"__builtins__": {}}, context)
            except Exception as e:
                logger.error(f"Error evaluating completion condition: {e}")
                return False
        else:
            # Default behavior: complete when all instances are done
            return completed_count == total_instances

    async def _handle_completion(
        self, token: Token, activity_tokens: List[Dict]
    ) -> Token:
        """Handle completion of all instances."""
        next_task_id = "Task_1"  # This should come from process definition

        # Preserve original token data except instance-specific fields
        token_data = token.data.copy()
        token_data.pop("item", None)
        token_data.pop("index", None)
        token_data.pop("scope_id", None)

        new_token = Token(
            instance_id=token.instance_id, node_id=next_task_id, data=token_data
        )

        # For inner activities, only remove tokens in the current scope level
        if "/" in token.scope_id:  # This is an inner activity
            parent_scope = token.data.get("parent_scope", "")
            activity_scope_tokens = [
                t
                for t in activity_tokens
                if t.get("scope_id", "").startswith(parent_scope)
            ]

            # Remove tokens for this activity's scope
            for t in activity_scope_tokens:
                await self.state_manager.remove_token(
                    instance_id=token.instance_id,
                    node_id=t["node_id"],
                    scope_id=t.get("scope_id"),
                )

            # Add new token for inner activity completion
            await self.state_manager.add_token(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                data=new_token.to_dict(),
            )
        else:  # This is an outer activity
            # Check if all inner activities are complete
            all_tokens = await self.state_manager.get_token_positions(token.instance_id)
            inner_tokens = [t for t in all_tokens if t["node_id"] == "InnerActivity"]
            if inner_tokens:
                # Still have inner activities, just mark this one complete
                return None

            # All inner activities are done, remove outer tokens and create final token
            outer_tokens = [t for t in all_tokens if t["node_id"] == token.node_id]
            for t in outer_tokens:
                await self.state_manager.remove_token(
                    instance_id=token.instance_id,
                    node_id=t["node_id"],
                    scope_id=t.get("scope_id"),
                )

            # Clear any remaining Task_1 tokens
            task_tokens = [t for t in all_tokens if t["node_id"] == next_task_id]
            for t in task_tokens:
                await self.state_manager.remove_token(
                    instance_id=token.instance_id,
                    node_id=t["node_id"],
                    scope_id=t.get("scope_id"),
                )

            # Add single final token
            await self.state_manager.add_token(
                instance_id=new_token.instance_id,
                node_id=new_token.node_id,
                data=new_token.to_dict(),
            )
        return new_token
