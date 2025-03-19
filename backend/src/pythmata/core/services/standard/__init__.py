"""Standard service tasks."""

# Import service tasks to register them
# Register standard service tasks
from pythmata.core.services.registry import get_service_task_registry
from pythmata.core.services.standard.http import HttpServiceTask
from pythmata.core.services.standard.logger import LoggerServiceTask


class StandardServiceRegistry:
    """Registry for standard service tasks."""

    def __init__(self):
        """Initialize the standard service registry."""
        self.registry = get_service_task_registry()
        self.http = HttpServiceTask
        self.logger = LoggerServiceTask


# Register the standard service tasks
registry = get_service_task_registry()
registry.register(HttpServiceTask)
registry.register(LoggerServiceTask)
