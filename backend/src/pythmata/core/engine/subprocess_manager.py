import logging
from typing import Dict, Optional
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.api.schemas import ProcessVariableValue

logger = logging.getLogger(__name__)

class SubprocessManager:
    """
    Manages subprocess operations including entering, exiting, and variable handling.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

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
            await self._map_subprocess_variables(token, output_vars)

        # Mark token as completed before removing
        await self.state_manager.update_token_state(
            instance_id=token.instance_id,
            node_id=token.node_id,
            state=TokenState.COMPLETED,
            scope_id=token.scope_id,
        )

        # Remove token from subprocess end event with scope
        await self.state_manager.remove_token(
            instance_id=token.instance_id,
            node_id=token.node_id,
            scope_id=token.scope_id,
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

    async def _map_subprocess_variables(
        self, token: Token, output_vars: Dict[str, str]
    ) -> None:
        """Map subprocess variables to parent scope."""
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
                    instance_id=token.instance_id,
                    name=parent_var,
                    variable=ProcessVariableValue(
                        type=value.type, value=value.value
                    ),
                )
