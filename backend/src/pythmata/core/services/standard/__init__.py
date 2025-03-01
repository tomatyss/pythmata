"""Standard service tasks."""

# Import service tasks to register them
# Register standard service tasks
from pythmata.core.services.registry import get_service_task_registry
from pythmata.core.services.standard.http import HttpServiceTask
from pythmata.core.services.standard.logger import LoggerServiceTask

registry = get_service_task_registry()
registry.register(HttpServiceTask)
registry.register(LoggerServiceTask)
