"""Base class and utilities for service tasks."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ServiceTask(ABC):
    """
    Base class for all service tasks.

    Service tasks are executable components that can be configured in BPMN diagrams
    to perform specific actions when a token reaches them, such as making HTTP requests,
    sending emails, or logging information.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the unique name of the service task.

        Returns:
            str: Unique identifier for this service task type
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Get a human-readable description of what the service task does.

        Returns:
            str: Description of the service task's purpose and behavior
        """

    @property
    @abstractmethod
    def properties(self) -> List[Dict[str, Any]]:
        """
        Get the list of configurable properties for this service task.

        Each property is defined as a dictionary with the following keys:
        - name: Unique property identifier
        - label: Human-readable label
        - type: Data type (string, number, boolean, etc.)
        - required: Whether the property is required
        - default: Default value (optional)
        - description: Property description (optional)

        Returns:
            List[Dict[str, Any]]: List of property definitions
        """

    @abstractmethod
    async def execute(
        self, context: Dict[str, Any], properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the service task with the given context and properties.

        Args:
            context: Execution context containing token, variables, etc.
            properties: Configuration properties for this execution

        Returns:
            Dict[str, Any]: Result of the execution

        Raises:
            Exception: If execution fails
        """
