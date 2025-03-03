"""Service task module."""

# Import standard service tasks to register them
# Import standard service tasks module to register them
from pythmata.core.services.registry import get_service_task_registry
from pythmata.core.services.standard.http import HttpServiceTask
from pythmata.core.services.standard.logger import LoggerServiceTask

registry = get_service_task_registry()
registry.register(HttpServiceTask)
registry.register(LoggerServiceTask)

__all__ = ["get_service_task_registry", "HttpServiceTask", "LoggerServiceTask"]
