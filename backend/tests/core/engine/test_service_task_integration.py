"""Integration tests for service task execution in the process engine."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstance
from pythmata.core.services.base import ServiceTask
from pythmata.core.services.registry import ServiceTaskRegistry

# Sample BPMN XML with a service task
SERVICE_TASK_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="ServiceTask_1" />
    <bpmn:serviceTask id="ServiceTask_1" name="Test Service Task">
      <bpmn:extensionElements>
        <pythmata:ServiceTaskConfig taskName="test_task">
          <pythmata:Properties>
            <pythmata:Property name="test_prop" value="test_value" />
          </pythmata:Properties>
        </pythmata:ServiceTaskConfig>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="ServiceTask_1" targetRef="EndEvent_1" />
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
  </bpmn:process>
</bpmn:definitions>"""


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

    async def execute(self, properties: dict, variables: dict) -> dict:
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
async def test_service_task_execution(mock_registry, state_manager):
    """Test that a service task is executed during process execution."""
    # Create a process executor
    executor = ProcessExecutor(state_manager)

    # Create a process instance
    instance = await executor.create_instance(
        process_xml=SERVICE_TASK_BPMN, variables={}
    )

    # Start the process
    await executor.start_instance(instance.id)

    # Wait for the process to complete
    while instance.status != "COMPLETED":
        await asyncio.sleep(0.1)

    # Check that the process completed successfully
    assert instance.status == "COMPLETED"

    # Check that the service task was executed
    activities = await executor.get_instance_activities(instance.id)
    service_activities = [
        a for a in activities if a.activity_type == "SERVICE_TASK_EXECUTED"
    ]

    assert len(service_activities) == 1
    assert service_activities[0].node_id == "ServiceTask_1"

    # Check that the service task result was stored in the process variables
    variables = await executor.get_instance_variables(instance.id)
    assert any(v.name == "service_result" for v in variables)
    service_result_var = next(v for v in variables if v.name == "service_result")
    assert service_result_var.value_data == "Executed with test_value"


@pytest.mark.asyncio
async def test_service_task_error_handling(mock_registry, state_manager):
    """Test that service task errors are handled properly."""
    # Create a process executor
    executor = ProcessExecutor(state_manager)

    # Create a process instance
    instance = await executor.create_instance(
        process_xml=SERVICE_TASK_BPMN, variables={}
    )

    # Mock the service task to raise an exception
    with patch.object(TestServiceTask, "execute", side_effect=Exception("Test error")):
        # Start the process
        await executor.start_instance(instance.id)

        # Wait for the process to complete or error
        while instance.status not in ["COMPLETED", "ERROR"]:
            await asyncio.sleep(0.1)

        # Check that the process errored
        assert instance.status == "ERROR"

        # Check that the service task error was logged
        activities = await executor.get_instance_activities(instance.id)
        service_activities = [
            a for a in activities if a.activity_type == "SERVICE_TASK_EXECUTED"
        ]

        assert len(service_activities) == 1
        assert service_activities[0].node_id == "ServiceTask_1"
        assert service_activities[0].details.get("status") == "ERROR"
        assert "Test error" in service_activities[0].details.get("error", "")
