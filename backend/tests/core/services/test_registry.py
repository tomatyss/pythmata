"""Tests for the service task registry."""

import pytest

from pythmata.core.services.base import ServiceTask
from pythmata.core.services.registry import (
    ServiceTaskRegistry,
    get_service_task_registry,
)


class MockServiceTask(ServiceTask):
    """Mock service task for testing."""

    @property
    def name(self) -> str:
        return "mock_task"

    @property
    def description(self) -> str:
        return "Mock service task for testing"

    @property
    def properties(self) -> list:
        return [
            {
                "name": "test_prop",
                "label": "Test Property",
                "type": "string",
                "required": True,
                "description": "A test property",
            }
        ]

    async def execute(self, properties: dict, variables: dict) -> dict:
        return {"result": f"Executed with {properties.get('test_prop', 'no value')}"}


def test_registry_singleton():
    """Test that the registry is a singleton."""
    registry1 = ServiceTaskRegistry()
    registry2 = ServiceTaskRegistry()

    assert registry1 is registry2
    assert get_service_task_registry() is registry1


def test_register_task():
    """Test registering a service task."""
    registry = ServiceTaskRegistry()
    # Clear any existing tasks for testing
    registry._tasks = {}

    registry.register(MockServiceTask)

    assert "mock_task" in registry._tasks
    assert isinstance(registry._tasks["mock_task"], MockServiceTask)


def test_get_task():
    """Test getting a service task."""
    registry = ServiceTaskRegistry()
    # Clear any existing tasks for testing
    registry._tasks = {}

    registry.register(MockServiceTask)

    task = registry.get_task("mock_task")
    assert task is not None
    assert task.name == "mock_task"

    # Test getting a non-existent task
    assert registry.get_task("non_existent") is None


def test_list_tasks():
    """Test listing service tasks."""
    registry = ServiceTaskRegistry()
    # Clear any existing tasks for testing
    registry._tasks = {}

    registry.register(MockServiceTask)

    tasks = registry.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "mock_task"
    assert tasks[0]["description"] == "Mock service task for testing"
    assert len(tasks[0]["properties"]) == 1
    assert tasks[0]["properties"][0]["name"] == "test_prop"
