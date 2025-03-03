"""Tests for the process.started event handler."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from pythmata.core.config import Settings
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.core.utils import handle_process_started
from pythmata.models.process import ActivityLog, ProcessDefinition, ProcessInstance
from tests.core.engine.base import BaseEngineTest


@pytest.mark.asyncio
class TestProcessStartedHandler(BaseEngineTest):
    """Test suite for the process.started event handler."""

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

    async def test_process_started_creates_instance_if_not_exists(self):
        """
        Test that handle_process_started creates a process instance in the database
        if it doesn't already exist.

        This test verifies the fix for the foreign key violation issue.
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

        # Only mock Settings and execute_process
        with (
            patch(
                "pythmata.core.utils.service_utils.Settings",
                return_value=self.test_settings,
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

            # Verify that activity logs can be created for this instance
            activity_log = ActivityLog(
                instance_id=uuid.UUID(instance_id),
                activity_type="NODE_ENTERED",
                node_id="StartEvent_1",
                timestamp=instance.start_time,
            )
            self.session.add(activity_log)

            # This commit would fail with a foreign key violation if the instance doesn't exist
            await self.session.commit()

            # Verify that the activity log was created
            result = await self.session.execute(
                select(ActivityLog).where(
                    ActivityLog.instance_id == uuid.UUID(instance_id)
                )
            )
            logs = result.scalars().all()
            assert len(logs) == 1
            assert logs[0].node_id == "StartEvent_1"

    async def test_process_started_uses_existing_instance(self):
        """
        Test that handle_process_started uses an existing process instance
        if one already exists in the database.
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

        # Create a process instance in the database
        from datetime import UTC, datetime

        from pythmata.models.process import ProcessStatus

        instance_id = str(uuid.uuid4())
        instance = ProcessInstance(
            id=uuid.UUID(instance_id),
            definition_id=uuid.UUID(definition_id),
            status=ProcessStatus.RUNNING,
            start_time=datetime.now(UTC),
        )
        self.session.add(instance)
        await self.session.commit()

        # Only mock Settings and execute_process
        with (
            patch(
                "pythmata.core.utils.service_utils.Settings",
                return_value=self.test_settings,
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
                    "definition_id": definition_id,
                    "variables": {},
                    "source": "test",
                    "timestamp": "2025-03-02T12:00:00Z",
                }
            )

            # Verify that execute_process was called
            mock_execute.assert_called_once()

            # Verify that the process instance still exists in the database
            result = await self.session.execute(
                select(ProcessInstance).where(
                    ProcessInstance.id == uuid.UUID(instance_id)
                )
            )
            db_instance = result.scalar_one_or_none()
            assert db_instance is not None
            assert str(db_instance.definition_id) == definition_id

            # Verify that the instance in the database is the same one we created
            assert db_instance.id == instance.id
            assert db_instance.start_time == instance.start_time
