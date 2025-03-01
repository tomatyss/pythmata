"""Registry for service tasks."""

from typing import Dict, List, Optional, Type

from pythmata.core.services.base import ServiceTask
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceTaskRegistry:
    """
    Registry for service tasks.

    Maintains a collection of available service tasks that can be used in BPMN processes.
    Provides methods for registering, retrieving, and listing service tasks.
    """

    _instance = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ServiceTaskRegistry, cls).__new__(cls)
            cls._instance._tasks = {}
        return cls._instance

    def register(self, task_class: Type[ServiceTask]) -> None:
        """
        Register a service task.

        Args:
            task_class: Service task class to register
        """
        task = task_class()
        self._tasks[task.name] = task
        logger.info(f"Registered service task: {task.name}")

    def get_task(self, name: str) -> Optional[ServiceTask]:
        """
        Get a service task by name.

        Args:
            name: Name of the service task

        Returns:
            Optional[ServiceTask]: The service task if found, None otherwise
        """
        return self._tasks.get(name)

    def list_tasks(self) -> List[Dict[str, any]]:
        """
        List all registered service tasks.

        Returns:
            List[Dict[str, any]]: List of service task information
        """
        return [
            {
                "name": task.name,
                "description": task.description,
                "properties": task.properties,
            }
            for task in self._tasks.values()
        ]


# Global registry instance
_registry = ServiceTaskRegistry()


def get_service_task_registry() -> ServiceTaskRegistry:
    """
    Get the global service task registry.

    Returns:
        ServiceTaskRegistry: The global service task registry
    """
    return _registry
