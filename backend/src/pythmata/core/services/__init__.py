"""Service task module."""

# Import standard service tasks to register them
# Import standard service tasks module to register them
from pythmata.core.services.registry import get_service_task_registry

__all__ = ["get_service_task_registry", "pythmata.core.services.standard"]
