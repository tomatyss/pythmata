import logging
from typing import Dict, Optional
from uuid import uuid4

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

logger = logging.getLogger(__name__)


class CallActivityManager:
    """
    Manages call activity operations including creation, completion, and error handling.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

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
        await self._map_input_variables(token.instance_id, new_instance_id, input_vars)

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
            await self._map_output_variables(token, output_vars)

        # Remove token from subprocess end event with scope
        await self.state_manager.remove_token(
            instance_id=token.instance_id,
            node_id=token.node_id,
            scope_id=token.scope_id,
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

    async def _map_input_variables(
        self,
        parent_instance_id: str,
        child_instance_id: str,
        input_vars: Dict[str, str],
    ) -> None:
        """Map variables from parent to child process."""
        for subprocess_var, parent_var in input_vars.items():
            value = await self.state_manager.get_variable(
                instance_id=parent_instance_id, name=parent_var
            )
            if value is not None:
                await self.state_manager.set_variable(
                    instance_id=child_instance_id,
                    name=subprocess_var,
                    variable=ProcessVariableValue(type=value.type, value=value.value),
                )

    async def _map_output_variables(
        self, token: Token, output_vars: Dict[str, str]
    ) -> None:
        """Map variables from child to parent process."""
        for parent_var, subprocess_var in output_vars.items():
            value = await self.state_manager.get_variable(
                instance_id=token.instance_id, name=subprocess_var
            )
            if value is not None:
                await self.state_manager.set_variable(
                    instance_id=token.parent_instance_id,
                    name=parent_var,
                    variable=ProcessVariableValue(type=value.type, value=value.value),
                )
