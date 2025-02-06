import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessInstance, ProcessStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pythmata.core.engine.instance import ProcessInstanceManager


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

    def __init__(
        self,
        state_manager: StateManager,
        instance_manager: Optional["ProcessInstanceManager"] = None,
    ):
        self.state_manager = state_manager
        self.instance_manager = instance_manager

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
        # Handle transaction boundaries
        if self.instance_manager:
            # Check if moving to Transaction_End (complete transaction and move to End_1)
            if target_node_id == "Transaction_End":
                # First complete the transaction
                await self.instance_manager.complete_transaction(
                    UUID(token.instance_id)
                )
                # Then move token directly to End_1 and complete process
                await self.state_manager.remove_token(
                    instance_id=token.instance_id, node_id=token.node_id
                )
                await self.state_manager.redis.delete(f"tokens:{token.instance_id}")
                new_token = token.copy(node_id="End_1")
                await self.state_manager.add_token(
                    instance_id=new_token.instance_id,
                    node_id=new_token.node_id,
                    data=new_token.to_dict(),
                )
                # Mark process as completed
                instance = await self.instance_manager.session.get(
                    ProcessInstance, UUID(token.instance_id)
                )
                if instance:
                    instance.status = ProcessStatus.COMPLETED
                    instance.end_time = datetime.now(UTC)
                    await self.instance_manager.session.commit()
                return new_token
            # Check if moving into a transaction (but not to internal transaction nodes)
            elif target_node_id.startswith("Transaction_") and target_node_id not in [
                "Transaction_Start",
                "Transaction_End",
            ]:
                await self.instance_manager.start_transaction(
                    UUID(token.instance_id), target_node_id
                )
                # Move token to transaction's start event
                target_node_id = "Transaction_Start"

        # Remove token from current node
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        # Clear Redis cache for this instance
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create new token at target node
        new_token = token.copy(node_id=target_node_id)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        # Handle end events
        if target_node_id == "End_1" and self.instance_manager:
            # Mark process as completed with end time
            instance = await self.instance_manager.session.get(
                ProcessInstance, UUID(token.instance_id)
            )
            if instance:
                instance.status = ProcessStatus.COMPLETED
                instance.end_time = datetime.now(UTC)
                await self.instance_manager.session.commit()

        return new_token

    async def consume_token(self, token: Token) -> None:
        """
        Consume a token (remove it from the process).

        Args:
            token: The token to consume
        """
        # Remove token and clear cache
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
            new_tokens.append(new_token)

        return new_tokens

    async def enter_subprocess(self, token: Token, subprocess_id: str) -> Token:
        """
        Move a token into a subprocess and create a new scope.

        Args:
            token: The token to move into subprocess
            subprocess_id: ID of the subprocess node

        Returns:
            The new token in subprocess scope
        """
        # Remove token from current node and clear cache
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create new token in subprocess scope
        new_token = token.copy(node_id=subprocess_id, scope_id=subprocess_id)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token

    async def exit_subprocess(self, token: Token, next_task_id: str) -> Token:
        """
        Move a token out of a subprocess back to parent process.

        Args:
            token: The token to move out of subprocess
            next_task_id: ID of the next task in parent process

        Returns:
            The new token in parent scope
        """
        # Remove token from subprocess and clear cache
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create new token in parent scope
        new_token = token.copy(node_id=next_task_id, scope_id=None)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token

    async def create_call_activity(self, token: Token) -> Token:
        """
        Create a new process instance for a call activity.

        Args:
            token: Token at the call activity node

        Returns:
            New token in the called process instance
        """
        # Get called process ID from token data
        called_process_id = token.data.get("called_process_id")
        if not called_process_id:
            raise ValueError("Called process ID not specified in token data")

        # Create new instance ID for called process
        new_instance_id = str(uuid4())

        # Set parent token to waiting state
        await self.state_manager.update_token_state(
            instance_id=token.instance_id,
            node_id=token.node_id,
            state=TokenState.WAITING,
        )

        # Map input variables if specified
        input_vars = token.data.get("input_vars", {})
        for subprocess_var, parent_var in input_vars.items():
            value = await self.state_manager.get_variable(
                instance_id=token.instance_id, name=parent_var
            )
            if value is not None:
                await self.state_manager.set_variable(
                    instance_id=new_instance_id, name=subprocess_var, value=value
                )

        # Create new token in called process
        new_token = Token(
            instance_id=new_instance_id,
            node_id="Start_1",
            parent_instance_id=token.instance_id,
            parent_activity_id=token.node_id,
        )
        await self.state_manager.add_token(
            instance_id=new_instance_id, node_id="Start_1", data=new_token.to_dict()
        )

        return new_token

    async def complete_call_activity(
        self,
        token: Token,
        next_task_id: str,
        output_vars: Optional[Dict[str, str]] = None,
    ) -> Token:
        """
        Complete a call activity and return to parent process.

        Args:
            token: Token at the called process end event
            next_task_id: ID of the next task in parent process
            output_vars: Optional mapping of subprocess variables to parent variables
                        Format: {"parent_var": "subprocess_var"}

        Returns:
            New token in parent process
        """
        if not token.parent_instance_id or not token.parent_activity_id:
            raise ValueError("Token is not from a call activity")

        # Map output variables to parent process if specified
        if output_vars:
            for parent_var, subprocess_var in output_vars.items():
                value = await self.state_manager.get_variable(
                    instance_id=token.instance_id, name=subprocess_var
                )
                if value is not None:
                    await self.state_manager.set_variable(
                        instance_id=token.parent_instance_id,
                        name=parent_var,
                        value=value,
                    )

        # Remove token from subprocess end event
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Clean up any remaining tokens in subprocess
        await self.state_manager.clear_scope_tokens(
            instance_id=token.instance_id,
            scope_id=None,  # Clear all tokens in subprocess
        )

        # Create new token in parent process
        new_token = Token(instance_id=token.parent_instance_id, node_id=next_task_id)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token

    async def propagate_call_activity_error(
        self, token: Token, error_boundary_id: str
    ) -> Token:
        """
        Propagate an error from called process to parent error boundary event.

        Args:
            token: Token at the error event in called process
            error_boundary_id: ID of the error boundary event in parent process

        Returns:
            New token at parent error boundary event
        """
        if not token.parent_instance_id or not token.parent_activity_id:
            raise ValueError("Token is not from a call activity")

        # Remove token from subprocess error event
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Clean up any remaining tokens in subprocess
        await self.state_manager.clear_scope_tokens(
            instance_id=token.instance_id,
            scope_id=None,  # Clear all tokens in subprocess
        )

        # Create new token at parent error boundary event
        new_token = Token(
            instance_id=token.parent_instance_id,
            node_id=error_boundary_id,
            data={"error_code": token.data.get("error_code")},
        )
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token

    async def trigger_event_subprocess(
        self, token: Token, event_subprocess_id: str, event_data: Dict
    ) -> Token:
        """
        Trigger an event subprocess when a matching event occurs.

        Args:
            token: Token from the parent process
            event_subprocess_id: ID of the event subprocess to trigger
            event_data: Event data including type, name, and interrupting flag

        Returns:
            New token in the event subprocess scope
        """
        # Create new token in event subprocess scope
        start_event_id = f"StartEvent_{event_subprocess_id.split('_')[-1]}"
        new_token = token.copy(
            node_id=start_event_id,
            scope_id=event_subprocess_id,
            data={"event_data": event_data},
        )

        # If interrupting event, cancel the parent token
        if event_data.get("interrupting", False):
            await self.state_manager.update_token_state(
                instance_id=token.instance_id,
                node_id=token.node_id,
                state=TokenState.CANCELLED,
            )
            # Remove the cancelled token
            await self.state_manager.remove_token(
                instance_id=token.instance_id, node_id=token.node_id
            )
            await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Add the new token
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token

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
            scope_id=token.scope_id  # Only remove token with matching scope
        )

        # Create instance tokens
        parent_scope = token.scope_id or ""
        logger.debug(f"Creating {len(collection)} instances with parent scope: {parent_scope}")
        
        for i, item in enumerate(collection):
            # Create hierarchical scope ID
            instance_scope = f"{parent_scope}/{token.node_id}_instance_{i}".lstrip("/")
            logger.debug(f"Creating instance {i} with scope: {instance_scope}")
            
            # Preserve original token data and update with instance-specific data
            instance_data = token.data.copy()
            instance_data.update({
                "item": item,
                "index": i,
                "collection": collection,
                "is_parallel": True,
                "parent_scope": parent_scope,  # Store parent scope for reference
            })
            
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
        instance_data.update({
            "item": collection[index],
            "index": index,
            "collection": collection,
            "is_parallel": False,
        })

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
        logger.debug(f"\nCompleting parallel instance - node_id: {token.node_id}, scope_id: {token.scope_id}")
        
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
            logger.debug(f"Token - node_id: {t['node_id']}, scope_id: {t.get('scope_id')}, state: {t.get('state')}")

        # Get all tokens for this activity by node_id
        activity_tokens = [t for t in stored_tokens if t["node_id"] == token.node_id]

        # Count completed tokens from fresh state
        completed_tokens = [
            t for t in activity_tokens if t.get("state") == TokenState.COMPLETED.value
        ]

        # Check completion condition if specified
        completion_condition = token.data.get("completion_condition")
        should_complete = False
        
        if completion_condition:
            # Create context for condition evaluation
            context = {"count": len(completed_tokens)}
            try:
                should_complete = eval(completion_condition, {"__builtins__": {}}, context)
            except Exception as e:
                logger.error(f"Error evaluating completion condition: {e}")
                should_complete = False
        else:
            # Default behavior: complete when all instances are done
            should_complete = len(completed_tokens) == total_instances

        if should_complete:
            # Completion condition met, create new token
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
                    t for t in activity_tokens 
                    if t.get("scope_id", "").startswith(parent_scope)
                ]
                
                # Remove tokens for this activity's scope
                for t in activity_scope_tokens:
                    await self.state_manager.remove_token(
                        instance_id=token.instance_id,
                        node_id=t["node_id"],
                        scope_id=t.get("scope_id")
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
                        scope_id=t.get("scope_id")
                    )

                # Clear any remaining Task_1 tokens
                task_tokens = [t for t in all_tokens if t["node_id"] == next_task_id]
                for t in task_tokens:
                    await self.state_manager.remove_token(
                        instance_id=token.instance_id,
                        node_id=t["node_id"],
                        scope_id=t.get("scope_id")
                    )

                # Add single final token
                await self.state_manager.add_token(
                    instance_id=new_token.instance_id,
                    node_id=new_token.node_id,
                    data=new_token.to_dict(),
                )
            return new_token

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

    async def complete_subprocess(
        self,
        token: Token,
        next_task_id: str,
        output_vars: Optional[Dict[str, str]] = None,
    ) -> Token:
        """
        Complete a subprocess and move token to next task in parent process.

        Args:
            token: The token at subprocess end event
            next_task_id: ID of the next task in parent process
            output_vars: Optional mapping of subprocess variables to parent variables
                        Format: {"parent_var": "subprocess_var"}

        Returns:
            The new token in parent scope
        """
        # Copy output variables to parent scope if specified
        if output_vars:
            for parent_var, subprocess_var in output_vars.items():
                # Get value from subprocess scope
                value = await self.state_manager.get_variable(
                    instance_id=token.instance_id,
                    name=subprocess_var,
                    scope_id=token.scope_id,
                )
                # Set value in parent scope
                if value is not None:
                    await self.state_manager.set_variable(
                        instance_id=token.instance_id, name=parent_var, value=value
                    )

        # Remove token from subprocess end event
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Clean up any remaining tokens in subprocess scope
        await self.state_manager.clear_scope_tokens(
            instance_id=token.instance_id, scope_id=token.scope_id
        )

        # Create new token in parent scope
        new_token = token.copy(node_id=next_task_id, scope_id=None)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token
