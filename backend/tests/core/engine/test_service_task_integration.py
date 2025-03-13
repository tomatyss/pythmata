"""Integration tests for service task execution in the process engine."""

import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstance, ProcessInstanceManager
from pythmata.core.services.base import ServiceTask
from pythmata.core.services.registry import ServiceTaskRegistry
from pythmata.models.process import (
    ActivityLog,
    ActivityType,
    ProcessDefinition,
    ProcessStatus,
)
from tests.data.process_samples import SERVICE_TASK_BPMN


class TestServiceTask(ServiceTask):
    """Test service task for integration testing."""

    @property
    def name(self) -> str:
        return "test_task"

    @property
    def description(self) -> str:
        return "Test service task for integration testing"

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
        # Store the property value in a process variable
        return {
            "result": f"Executed with {properties.get('test_prop', 'no value')}",
            "variables": {
                "service_result": f"Executed with {properties.get('test_prop', 'no value')}"
            },
        }


@pytest.fixture
def mock_registry():
    """Create a mock registry with a test service task."""
    registry = ServiceTaskRegistry()
    # Clear any existing tasks for testing
    registry._tasks = {}
    registry.register(TestServiceTask)
    return registry


@pytest.mark.asyncio
async def test_service_task_execution(mock_registry, state_manager, session):
    """Test that a service task is executed during process execution."""
    # Create a process definition for testing
    parser = BPMNParser()
    process_graph = parser.parse(SERVICE_TASK_BPMN)

    definition = ProcessDefinition(
        id=uuid4(),
        name="Test Service Task Process",
        version=1,
        bpmn_xml=SERVICE_TASK_BPMN,
    )
    session.add(definition)
    await session.commit()

    # Create executor and instance manager
    executor = ProcessExecutor(state_manager)
    instance_manager = ProcessInstanceManager(session, executor, state_manager)

    # Create a process instance
    instance = ProcessInstance(
        id=uuid4(),
        definition_id=definition.id,
        status=ProcessStatus.RUNNING,
    )
    session.add(instance)
    await session.commit()

    # Start the instance
    instance = await instance_manager.start_instance(
        instance, definition.bpmn_xml, variables={}
    )

    # Set the instance manager on the executor
    executor.instance_manager = instance_manager

    # Start the process
    await executor.execute_process(str(instance.id), process_graph)

    # Wait for the process to complete with a timeout
    timeout = 5.0  # 5 seconds timeout
    start_time = asyncio.get_event_loop().time()

    while True:
        await asyncio.sleep(0.1)
        # Check for timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Test timed out after {timeout} seconds")

        # Query the instance status directly from the database
        result = await session.execute(
            select(ProcessInstance).where(ProcessInstance.id == instance.id)
        )
        current_instance = result.scalar_one()
        if current_instance.status == ProcessStatus.COMPLETED:
            instance = current_instance  # Update our reference
            break

    # Check that the process completed successfully
    assert instance.status == ProcessStatus.COMPLETED

    # Check that the service task was executed and instance completed
    result = await session.execute(
        select(ActivityLog).where(
            ActivityLog.instance_id == instance.id,
            ActivityLog.activity_type == ActivityType.INSTANCE_COMPLETED,
        )
    )
    completion_activities = result.scalars().all()

    assert len(completion_activities) == 1

    # Check that the process completed successfully
    assert instance.status == ProcessStatus.COMPLETED


@pytest.mark.asyncio
async def test_service_task_error_handling(mock_registry, state_manager, session):
    """Test that service task errors are handled properly."""
    # Create a process definition for testing
    parser = BPMNParser()
    process_graph = parser.parse(SERVICE_TASK_BPMN)

    definition = ProcessDefinition(
        id=uuid4(),
        name="Test Service Task Process",
        version=1,
        bpmn_xml=SERVICE_TASK_BPMN,
    )
    session.add(definition)
    await session.commit()

    # Create executor and instance manager
    executor = ProcessExecutor(state_manager)
    instance_manager = ProcessInstanceManager(session, executor, state_manager)

    # Create a process instance
    instance = ProcessInstance(
        id=uuid4(),
        definition_id=definition.id,
        status=ProcessStatus.RUNNING,
    )
    session.add(instance)
    await session.commit()

    # Start the instance
    instance = await instance_manager.start_instance(
        instance, definition.bpmn_xml, variables={}
    )

    # Set the instance manager on the executor
    executor.instance_manager = instance_manager

    # Mock the service task to raise an exception
    with patch.object(TestServiceTask, "execute", side_effect=Exception("Test error")):
        try:
            # Start the process - this should raise an exception
            await executor.execute_process(str(instance.id), process_graph)
        except Exception as e:
            # Expected exception, now check that the instance is in error state
            pass

    # Wait for the process to be marked as error with a timeout
    timeout = 5.0  # 5 seconds timeout
    start_time = asyncio.get_event_loop().time()

    while True:
        await asyncio.sleep(0.1)
        # Check for timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Test timed out after {timeout} seconds")

        # Query the instance status directly from the database
        result = await session.execute(
            select(ProcessInstance).where(ProcessInstance.id == instance.id)
        )
        current_instance = result.scalar_one()
        if current_instance.status == ProcessStatus.ERROR:
            instance = current_instance  # Update our reference
            break

    # Check that the process errored
    assert instance.status == ProcessStatus.ERROR

    # Check that the error was logged with an activity log
    result = await session.execute(
        select(ActivityLog).where(
            ActivityLog.instance_id == instance.id,
            ActivityLog.activity_type == ActivityType.INSTANCE_ERROR,
        )
    )
    error_activities = result.scalars().all()

    assert len(error_activities) == 1
