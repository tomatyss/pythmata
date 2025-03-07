"""
Example plugin for Pythmata.

This plugin demonstrates how to create and register custom service tasks
using the Pythmata plugin system.
"""

from pythmata.core.services.registry import get_service_task_registry
from .notification_task import NotificationServiceTask

# Register the service task
registry = get_service_task_registry()
registry.register(NotificationServiceTask)

# You can register multiple service tasks if needed
