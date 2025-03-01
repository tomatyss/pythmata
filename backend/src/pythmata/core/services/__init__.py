"""Service task module."""

# Import standard service tasks to register them
from pythmata.core.services.registry import get_service_task_registry

# Import standard service tasks module to register them
import pythmata.core.services.standard

__all__ = ["get_service_task_registry", "pythmata.core.services.standard"]
