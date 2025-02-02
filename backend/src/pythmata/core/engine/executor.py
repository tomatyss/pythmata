from datetime import UTC, datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessInstance, ProcessStatus

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

    async def complete_subprocess(
        self, token: Token, next_task_id: str, output_vars: Optional[Dict[str, str]] = None
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
                    scope_id=token.scope_id
                )
                # Set value in parent scope
                if value is not None:
                    await self.state_manager.set_variable(
                        instance_id=token.instance_id,
                        name=parent_var,
                        value=value
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
