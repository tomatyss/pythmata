"""Tests for the service task executor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythmata.core.engine.service_executor import ServiceTaskExecutor
from pythmata.core.services.base import ServiceTask
from pythmata.core.services.registry import ServiceTaskRegistry


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

    async def execute(self, context: dict, properties: dict) -> dict:
        return {"result": f"Executed with {properties.get('test_prop', 'no value')}"}


@pytest.fixture
def mock_registry():
    """Create a mock registry with a test service task."""
    registry = ServiceTaskRegistry()
    # Clear any existing tasks for testing
    registry._tasks = {}
    registry.register(MockServiceTask)
    return registry


@pytest.mark.asyncio
async def test_execute_service_task(mock_registry, state_manager):
    """Test executing a service task."""
    executor = ServiceTaskExecutor(state_manager)

    # Create a mock token and task
    token = MagicMock()
    token.instance_id = "12345678-1234-5678-1234-567812345678"  # Valid UUID format
    token.scope_id = None

    task = MagicMock()
    task.id = "test-task"
    task.extensions = {
        "serviceTaskConfig": {
            "task_name": "mock_task",
            "properties": {"test_prop": "test value"},
        }
    }

    # Mock the state_manager.get_variables method to return our test variables
    async def mock_get_variables(*args, **kwargs):
        return {"var1": "value1"}

    state_manager.get_variables = mock_get_variables

    # Create a mock instance manager
    instance_manager = MagicMock()
    instance_manager._create_activity_log = AsyncMock()

    # Execute the service task
    await executor.execute_service_task(token, task, instance_manager)

    # Check that the activity log was created
    instance_manager._create_activity_log.assert_called_once()
    args = instance_manager._create_activity_log.call_args[0]

    # Extract the details from the activity log
    details = args[3]

    # Check the result
    assert details["status"] == "COMPLETED"
    assert "result" in details
    assert details["result"]["result"] == "Executed with test value"


@pytest.mark.asyncio
async def test_execute_nonexistent_task(mock_registry, state_manager):
    """Test executing a non-existent service task."""
    executor = ServiceTaskExecutor(state_manager)

    # Create a mock token and task
    token = MagicMock()
    token.instance_id = "12345678-1234-5678-1234-567812345678"  # Valid UUID format
    token.scope_id = None

    task = MagicMock()
    task.id = "test-task"
    task.extensions = {
        "serviceTaskConfig": {
            "task_name": "non_existent_task",
            "properties": {"test_prop": "test value"},
        }
    }

    # Mock the state_manager.get_variables method to return our test variables
    async def mock_get_variables(*args, **kwargs):
        return {"var1": "value1"}

    state_manager.get_variables = mock_get_variables

    # Create a mock instance manager
    instance_manager = MagicMock()
    instance_manager._create_activity_log = AsyncMock()

    # Execute the service task and expect an error
    with pytest.raises(ValueError) as excinfo:
        await executor.execute_service_task(token, task, instance_manager)

    # Check the error message
    assert "not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_execute_task_with_error(mock_registry, state_manager):
    """Test executing a service task that raises an error."""
    executor = ServiceTaskExecutor(state_manager)

    # Create a mock token and task
    token = MagicMock()
    token.instance_id = "12345678-1234-5678-1234-567812345678"  # Valid UUID format
    token.scope_id = None

    task = MagicMock()
    task.id = "test-task"
    task.extensions = {
        "serviceTaskConfig": {
            "task_name": "mock_task",
            "properties": {"test_prop": "test value"},
        }
    }

    # Mock the state_manager.get_variables method to return our test variables
    async def mock_get_variables(*args, **kwargs):
        return {"var1": "value1"}

    state_manager.get_variables = mock_get_variables

    # Create a mock instance manager
    instance_manager = MagicMock()
    instance_manager._create_activity_log = AsyncMock()

    # Mock the execute method to raise an exception
    with patch.object(MockServiceTask, "execute", side_effect=Exception("Test error")):
        # Execute the service task and expect an error
        with pytest.raises(Exception) as excinfo:
            await executor.execute_service_task(token, task, instance_manager)

        # Check the error message
        assert "Test error" in str(excinfo.value)

        # Check that the activity log was created with error status
        instance_manager._create_activity_log.assert_called_once()
        args = instance_manager._create_activity_log.call_args[0]

        # Extract the details from the activity log
        details = args[3]

        # Check the result
        assert details["status"] == "ERROR"
        assert "error" in details
        assert "Test error" in details["error"]


@pytest.mark.asyncio
async def test_execute_task_with_missing_required_property(
    mock_registry, state_manager
):
    """Test executing a service task with missing required property."""
    executor = ServiceTaskExecutor(state_manager)

    # Create a mock token and task
    token = MagicMock()
    token.instance_id = "12345678-1234-5678-1234-567812345678"  # Valid UUID format
    token.scope_id = None

    task = MagicMock()
    task.id = "test-task"
    task.extensions = {
        "serviceTaskConfig": {
            "task_name": "mock_task",
            "properties": {},  # Missing test_prop
        }
    }

    # Mock the state_manager.get_variables method to return our test variables
    async def mock_get_variables(*args, **kwargs):
        return {"var1": "value1"}

    state_manager.get_variables = mock_get_variables

    # Create a mock instance manager
    instance_manager = MagicMock()
    instance_manager._create_activity_log = AsyncMock()

    # Execute the service task
    await executor.execute_service_task(token, task, instance_manager)

    # Check that the activity log was created
    instance_manager._create_activity_log.assert_called_once()
    args = instance_manager._create_activity_log.call_args[0]

    # Extract the details from the activity log
    details = args[3]

    # Check the result
    assert details["status"] == "COMPLETED"
    assert "result" in details
    assert details["result"]["result"] == "Executed with no value"
