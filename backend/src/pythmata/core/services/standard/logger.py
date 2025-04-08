"""Logger service task implementation."""

from typing import Any, Dict, List

from pythmata.core.services.base import ServiceTask
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class LoggerServiceTask(ServiceTask):
    """
    Service task for logging information during process execution.

    Allows processes to log messages at different levels (info, warning, error)
    with configurable content derived from process variables.
    """

    @property
    def name(self) -> str:
        """
        Get the unique name of the service task.

        Returns:
            str: Unique identifier for this service task type
        """
        return "logger"

    @property
    def description(self) -> str:
        """
        Get a human-readable description of what the service task does.

        Returns:
            str: Description of the service task's purpose and behavior
        """
        return "Log messages during process execution"

    @property
    def properties(self) -> List[Dict[str, Any]]:
        """
        Get the list of configurable properties for this service task.

        Returns:
            List[Dict[str, Any]]: List of property definitions
        """
        return [
            {
                "name": "level",
                "label": "Log Level",
                "type": "string",
                "required": True,
                "default": "info",
                "options": ["info", "warning", "error", "debug"],
                "description": "Logging level",
            },
            {
                "name": "message",
                "label": "Message",
                "type": "string",
                "required": True,
                "description": "Message to log",
            },
            {
                "name": "include_variables",
                "label": "Include Variables",
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Whether to include process variables in the log",
            },
            {
                "name": "variable_filter",
                "label": "Variable Filter",
                "type": "string",
                "required": False,
                "description": "Comma-separated list of variable names to include (if include_variables is true)",
            },
        ]

    async def execute(
        self, context: Dict[str, Any], properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the logging task.

        Args:
            context: Execution context containing token, variables, etc.
            properties: Configuration properties for this execution

        Returns:
            Dict[str, Any]: Result of the execution

        Raises:
            Exception: If logging fails
        """
        level = properties.get("level", "info").lower()
        message = properties.get("message", "")
        include_variables = properties.get("include_variables", False)
        variable_filter = properties.get("variable_filter", "")

        # Get variables if needed
        variables = {}
        if include_variables and context.get("variables"):
            if variable_filter:
                # Filter variables by name
                filter_list = [name.strip() for name in variable_filter.split(",")]
                variables = {
                    name: value
                    for name, value in context["variables"].items()
                    if name in filter_list
                }
            else:
                # Include all variables
                variables = context["variables"]

        # Format log message
        log_data = {
            "message": message,
            "process_instance_id": context["token"].instance_id,
            "task_id": context["task_id"],
        }

        if variables:
            log_data["variables"] = {k: v.model_dump_json() for k, v in variables.items()}

        log_message = f"{message} [Process: {context['token'].instance_id}, Task: {context['task_id']}, Data: {log_data}]"

        # Log at appropriate level
        if level == "info":
            logger.info(log_message)
        elif level == "warning":
            logger.warning(log_message)
        elif level == "error":
            logger.error(log_message)
        elif level == "debug":
            logger.debug(log_message)
        else:
            logger.info(log_message)

        return {
            "level": level,
            "message": message,
            "variables_included": include_variables,
            "log_data": log_data,
        }
