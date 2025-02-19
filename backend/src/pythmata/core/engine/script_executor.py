from typing import Dict, Optional

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager
from pythmata.core.types import Task
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionContextBuilder:
    """
    Builds safe execution contexts for script tasks.
    
    Provides:
    - Controlled access to built-in functions
    - Process variables and token access
    - Safe variable modification methods
    """

    def build_context(
        self, token: Token, variables: Dict, state_manager: StateManager
    ) -> Dict:
        """
        Build a safe execution context for script tasks.

        Args:
            token: Current process token
            variables: Process variables
            state_manager: State manager for variable updates

        Returns:
            Dict containing the safe execution context
        """
        return {
            "token": token,
            "variables": variables,
            "result": None,  # For script output
            "set_variable": lambda name, value: state_manager.set_variable(
                instance_id=token.instance_id,
                name=name,
                variable=ProcessVariableValue(
                    type=type(value).__name__, value=value
                ),
                scope_id=token.scope_id,
            ),
            # Safe built-ins
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "sum": sum,
            "min": min,
            "max": max,
        }


class ScriptExecutor:
    """
    Handles execution of script tasks in a controlled environment.
    
    Features:
    - Safe execution context with limited built-ins
    - Process variable access and modification
    - Result capture and storage
    """

    def __init__(self, state_manager: StateManager):
        """
        Initialize script executor.

        Args:
            state_manager: Manager for process state and variables
        """
        self.state_manager = state_manager
        self.context_builder = ExecutionContextBuilder()

    async def execute_script(self, token: Token, task: Task) -> None:
        """
        Execute a script task safely.

        Args:
            token: Current process token
            task: Script task to execute

        Raises:
            Exception: If script execution fails
        """
        if not task.script:
            logger.warning(f"No script defined for task {task.id}")
            return

        # Get process variables for script context
        variables = await self.state_manager.get_variables(
            instance_id=token.instance_id,
            scope_id=token.scope_id
        )

        # Create safe execution context
        context = self.context_builder.build_context(
            token, variables, self.state_manager
        )

        try:
            # Execute script in restricted environment
            exec(
                task.script,
                {"__builtins__": {}},  # No built-ins
                context,  # Our safe context
            )

            # Store script result if any
            if context["result"] is not None:
                await self.state_manager.set_variable(
                    instance_id=token.instance_id,
                    name=f"{task.id}_result",
                    variable=ProcessVariableValue(
                        type=type(context["result"]).__name__,
                        value=context["result"],
                    ),
                    scope_id=token.scope_id,
                )
        except Exception as e:
            logger.error(f"Script execution failed for task {task.id}: {str(e)}")
            raise
