"""Tests for event handler utility functions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from pythmata.core.config import Settings
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.core.utils.event_handlers import handle_process_started
from pythmata.models.process import ProcessDefinition, ProcessInstance
from tests.core.engine.base import BaseEngineTest


@pytest.mark.asyncio
class TestEventHandlers(BaseEngineTest):
    """Test suite for event handler utility functions."""

    @pytest.fixture(autouse=True)
    async def setup_handler_test(
        self,
        state_manager: StateManager,
        event_bus: EventBus,
        session,
        test_settings: Settings,
    ):
        """Setup test environment with state manager, event bus, and session.

        Args:
            state_manager: The state manager fixture
            event_bus: The event bus fixture
            session: The database session fixture
            test_settings: The test settings fixture
        """
        self.event_bus = event_bus
        self.session = session
        self.test_settings = test_settings

    async def test_handle_process_started(self):
        """
        Test process.started event handler following BPMN lifecycle.

        This test verifies:
        1. Process definition loading
        2. BPMN parsing and validation
        3. Process instance initialization
        4. Process execution
        """
        # Create a process definition in the database
        definition_id = str(uuid.uuid4())
        definition = ProcessDefinition(
            id=uuid.UUID(definition_id),
            name="Test Process",
            bpmn_xml="""<?xml version="1.0" encoding="UTF-8"?>
            <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" 
                             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" 
                             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                             id="Definitions_1"
                             targetNamespace="http://bpmn.io/schema/bpmn"
                             exporter="Pythmata"
                             exporterVersion="1.0">
              <bpmn:process id="Process_1" isExecutable="true">
                <bpmn:startEvent id="StartEvent_1">
                  <bpmn:outgoing>Flow_1</bpmn:outgoing>
                </bpmn:startEvent>
                <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="EndEvent_1" />
                <bpmn:endEvent id="EndEvent_1">
                  <bpmn:incoming>Flow_1</bpmn:incoming>
                </bpmn:endEvent>
              </bpmn:process>
            </bpmn:definitions>""",
            version=1,
        )
        self.session.add(definition)
        await self.session.commit()

        # Generate a unique instance ID
        instance_id = str(uuid.uuid4())

        # Mock Settings and execute_process
        with (
            patch(
                "pythmata.core.utils.service_utils.Settings",
                new=MagicMock(return_value=self.test_settings),
            ),
            patch(
                "pythmata.core.engine.executor.ProcessExecutor.execute_process",
                new_callable=AsyncMock,
            ) as mock_execute
        ):
            # Call the handle_process_started function with our test data
            await handle_process_started(
                {
                    "instance_id": instance_id,
                    "definition_id": definition_id,
                    "variables": {},
                    "source": "test",
                    "timestamp": "2025-03-02T12:00:00Z",
                }
            )

            # Verify that execute_process was called
            mock_execute.assert_called_once()

            # Verify that the process instance was created in the database
            result = await self.session.execute(
                select(ProcessInstance).where(
                    ProcessInstance.id == uuid.UUID(instance_id)
                )
            )
            instance = result.scalar_one_or_none()
            assert instance is not None
            assert str(instance.definition_id) == definition_id

    async def test_handle_process_started_error_cases(self):
        """
        Test error handling in process.started event handler.

        Tests the following error cases:
        1. Process definition not found
        2. Invalid BPMN XML
        3. Missing start event
        """
        # Test Case 1: Process definition not found
        non_existent_definition_id = str(uuid.uuid4())
        instance_id = str(uuid.uuid4())

        # Mock Settings and execute_process
        with (
            patch(
                "pythmata.core.utils.service_utils.Settings",
                new=MagicMock(return_value=self.test_settings),
            ),
            patch(
                "pythmata.core.engine.executor.ProcessExecutor.execute_process",
                new_callable=AsyncMock,
            ) as mock_execute,
        ):
            # Call the handle_process_started function with our test data
            await handle_process_started(
                {
                    "instance_id": instance_id,
                    "definition_id": non_existent_definition_id,
                    "variables": {},
                    "source": "test",
                    "timestamp": "2025-03-02T12:00:00Z",
                }
            )

            # Verify that execute_process was not called
            mock_execute.assert_not_called()

        # Test Case 2: Invalid BPMN XML
        definition_id = str(uuid.uuid4())
        definition = ProcessDefinition(
            id=uuid.UUID(definition_id),
            name="Invalid Process",
            bpmn_xml="<invalid>xml</invalid>",  # Invalid BPMN XML
            version=1,
        )
        self.session.add(definition)
        await self.session.commit()

        instance_id = str(uuid.uuid4())

        # Mock Settings, parse_bpmn, and execute_process
        with (
            patch(
                "pythmata.core.utils.service_utils.Settings",
                new=MagicMock(return_value=self.test_settings),
            ),
            patch(
                "pythmata.core.utils.process_utils.parse_bpmn",
                side_effect=ValueError("Invalid BPMN XML"),
            ),
            patch(
                "pythmata.core.engine.executor.ProcessExecutor.execute_process",
                new_callable=AsyncMock,
            ) as mock_execute
        ):
            # Call the handle_process_started function with our test data
            await handle_process_started(
                {
                    "instance_id": instance_id,
                    "definition_id": definition_id,
                    "variables": {},
                    "source": "test",
                    "timestamp": "2025-03-02T12:00:00Z",
                }
            )

            # Verify that execute_process was not called
            mock_execute.assert_not_called()

        # Test Case 3: Missing start event
        definition_id = str(uuid.uuid4())
        definition = ProcessDefinition(
            id=uuid.UUID(definition_id),
            name="No Start Event Process",
            bpmn_xml="""<?xml version="1.0" encoding="UTF-8"?>
            <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" 
                             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" 
                             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                             id="Definitions_1"
                             targetNamespace="http://bpmn.io/schema/bpmn"
                             exporter="Pythmata"
                             exporterVersion="1.0">
              <bpmn:process id="Process_1" isExecutable="true">
                <bpmn:endEvent id="EndEvent_1" />
              </bpmn:process>
            </bpmn:definitions>""",  # BPMN XML without a start event
            version=1,
        )
        self.session.add(definition)
        await self.session.commit()

        instance_id = str(uuid.uuid4())

        # Mock Settings, validate_start_event, and execute_process
        with (
            patch(
                "pythmata.core.utils.service_utils.Settings",
                new=MagicMock(return_value=self.test_settings),
            ),
            patch(
                "pythmata.core.utils.process_utils.validate_start_event",
                side_effect=ValueError("No start event found in process definition"),
            ),
            patch(
                "pythmata.core.engine.executor.ProcessExecutor.execute_process",
                new_callable=AsyncMock,
            ) as mock_execute
        ):
            # Call the handle_process_started function with our test data
            await handle_process_started(
                {
                    "instance_id": instance_id,
                    "definition_id": definition_id,
                    "variables": {},
                    "source": "test",
                    "timestamp": "2025-03-02T12:00:00Z",
                }
            )

            # Verify that execute_process was not called
            mock_execute.assert_not_called()
