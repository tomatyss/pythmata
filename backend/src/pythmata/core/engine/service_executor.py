"""Service task executor implementation."""

from typing import Dict, Optional
from uuid import UUID

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.token import Token
from pythmata.core.services.registry import get_service_task_registry
from pythmata.core.state import StateManager
from pythmata.core.types import Task, PYTHON_TYPES_NAMES_TO_BPMN
from pythmata.models.process import ActivityType
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceTaskExecutor:
    """
    Executes service tasks in a controlled environment.

    Features:
    - Service task lookup and execution
    - Process variable access and modification
    - Result capture and storage
    - Activity logging
    """

    def __init__(self, state_manager: StateManager):
        """
        Initialize service task executor.

        Args:
            state_manager: Manager for process state and variables
        """
        self.state_manager = state_manager
        self.registry = get_service_task_registry()

    async def execute_service_task(
        self, token: Token, task: Task, instance_manager=None
    ) -> None:
        """
        Execute a service task.

        Args:
            token: Current process token
            task: Service task to execute
            instance_manager: Optional instance manager for activity logging

        Raises:
            Exception: If service task execution fails
        """
        # Get service task configuration from task extensions
        service_task_config = self._extract_service_task_config(task)
        if not service_task_config:
            logger.warning(f"No service task configuration found for task {task.id}")
            return

        # Get service task implementation
        service_task = self.registry.get_task(service_task_config.get("task_name"))
        if not service_task:
            error_msg = f"Service task {service_task_config.get('task_name')} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Build execution context
        variables = await self.state_manager.get_variables(
            instance_id=token.instance_id, scope_id=token.scope_id
        )

        context = {
            "token": token,
            "variables": variables,
            "task_id": task.id,
            "instance_id": token.instance_id,
        }

        # Execute service task
        try:
            logger.info(
                f"Executing service task {service_task_config.get('task_name')} for task {task.id}"
            )
            result = await service_task.execute(
                context, service_task_config.get("properties", {})
            )

            # Create activity log
            if instance_manager:
                await instance_manager._create_activity_log(
                    UUID(token.instance_id),
                    ActivityType.SERVICE_TASK_EXECUTED,
                    task.id,
                    {
                        "service_task": service_task_config.get("task_name"),
                        "status": "COMPLETED",
                        "result": result,
                    },
                )

            # Store result in process variables if output mapping is defined
            output_mapping = service_task_config.get("properties", {}).get(
                "output_mapping"
            )
            if output_mapping:
                if isinstance(output_mapping, str):
                    try:
                        output_mapping = eval(output_mapping)
                    except:
                        logger.warning(
                            f"Failed to parse output mapping: {output_mapping}"
                        )
                        output_mapping = {}

                for var_name, result_path in output_mapping.items():
                    value = self._extract_value(result, result_path)
                    if value is not None:
                        await self.state_manager.set_variable(
                            instance_id=token.instance_id,
                            name=var_name,
                            variable=ProcessVariableValue(
                                type=PYTHON_TYPES_NAMES_TO_BPMN.get(type(value).__name__, 'none'), value=value
                            ),
                            scope_id=token.scope_id,
                        )

        except Exception as e:
            logger.error(f"Service task execution failed for task {task.id}: {str(e)}")

            # Create activity log for error
            if instance_manager:
                await instance_manager._create_activity_log(
                    UUID(token.instance_id),
                    ActivityType.SERVICE_TASK_EXECUTED,
                    task.id,
                    {
                        "service_task": service_task_config.get("task_name"),
                        "status": "ERROR",
                        "error": str(e),
                    },
                )
            raise

    def _extract_service_task_config(self, task: Task) -> Optional[Dict]:
        """
        Extract service task configuration from task extensions.

        Args:
            task: Task to extract configuration from

        Returns:
            Optional[Dict]: Service task configuration if found, None otherwise
        """
        if not task.extensions:
            return None

        # Look for service task configuration in extensions
        service_config = task.extensions.get("serviceTaskConfig")
        if not service_config:
            return None

        return service_config

    def _extract_value(self, data: Dict, path: str) -> any:
        """
        Extract a value from a nested dictionary using a dot-notation path.

        Args:
            data: Dictionary to extract value from
            path: Dot-notation path (e.g., "response.data.items[0].id")

        Returns:
            any: Extracted value or None if not found
        """
        if not path or not data:
            return None

        parts = path.split(".")
        current = data

        try:
            for part in parts:
                # Handle array indexing
                if "[" in part and part.endswith("]"):
                    name, index_str = part.split("[", 1)
                    index = int(index_str[:-1])
                    current = current.get(name, [])[index]
                else:
                    current = current.get(part)

                if current is None:
                    return None
        except (KeyError, IndexError, TypeError):
            return None

        return current
