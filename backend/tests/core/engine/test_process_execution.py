"""Tests for process execution functionality."""

import pytest
from uuid import uuid4

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType, Gateway, GatewayType, Task


@pytest.mark.asyncio
class TestProcessExecution:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_basic_sequence_flow(self):
        """Test execution of a simple sequence flow: Start -> Task -> End."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = str(uuid4())

        # Create process graph
        process_graph = {
            "nodes": [
                Event(id="Start_1", type="event", event_type=EventType.START, outgoing=["Flow_1"]),
                Task(id="Task_1", type="task", incoming=["Flow_1"], outgoing=["Flow_2"]),
                Event(id="End_1", type="event", event_type=EventType.END, incoming=["Flow_2"]),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Task_1"},
                {"id": "Flow_2", "source_ref": "Task_1", "target_ref": "End_1"},
            ],
        }

        # Create initial token
        token = await executor.create_initial_token(instance_id, "Start_1")
        assert token.node_id == "Start_1"

        # Execute process
        await executor.execute_process(instance_id, process_graph)

        # Verify final state
        tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(tokens) == 0  # All tokens should be consumed

    async def test_exclusive_gateway_flow(self):
        """Test execution with exclusive gateway."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = str(uuid4())

        # Create process graph
        process_graph = {
            "nodes": [
                Event(id="Start_1", type="event", event_type=EventType.START, outgoing=["Flow_1"]),
                Gateway(
                    id="Gateway_1",
                    type="gateway",
                    gateway_type=GatewayType.EXCLUSIVE,
                    incoming=["Flow_1"],
                    outgoing=["Flow_2", "Flow_3"],
                ),
                Task(id="Task_1", type="task", incoming=["Flow_2"], outgoing=["Flow_4"]),
                Task(id="Task_2", type="task", incoming=["Flow_3"], outgoing=["Flow_5"]),
                Event(id="End_1", type="event", event_type=EventType.END, incoming=["Flow_4", "Flow_5"]),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Gateway_1"},
                {
                    "id": "Flow_2",
                    "source_ref": "Gateway_1",
                    "target_ref": "Task_1",
                    "condition_expression": "true",
                },
                {
                    "id": "Flow_3",
                    "source_ref": "Gateway_1",
                    "target_ref": "Task_2",
                },
                {"id": "Flow_4", "source_ref": "Task_1", "target_ref": "End_1"},
                {"id": "Flow_5", "source_ref": "Task_2", "target_ref": "End_1"},
            ],
        }

        # Create initial token
        token = await executor.create_initial_token(instance_id, "Start_1")
        assert token.node_id == "Start_1"

        # Execute process
        await executor.execute_process(instance_id, process_graph)

        # Verify final state
        tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(tokens) == 0  # All tokens should be consumed

    async def test_parallel_gateway_flow(self):
        """Test execution with parallel gateway."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = str(uuid4())

        # Create process graph
        process_graph = {
            "nodes": [
                Event(id="Start_1", type="event", event_type=EventType.START, outgoing=["Flow_1"]),
                Gateway(
                    id="Gateway_1",
                    type="gateway",
                    gateway_type=GatewayType.PARALLEL,
                    incoming=["Flow_1"],
                    outgoing=["Flow_2", "Flow_3"],
                ),
                Task(id="Task_1", type="task", incoming=["Flow_2"], outgoing=["Flow_4"]),
                Task(id="Task_2", type="task", incoming=["Flow_3"], outgoing=["Flow_5"]),
                Gateway(
                    id="Gateway_2",
                    type="gateway",
                    gateway_type=GatewayType.PARALLEL,
                    incoming=["Flow_4", "Flow_5"],
                    outgoing=["Flow_6"],
                ),
                Event(id="End_1", type="event", event_type=EventType.END, incoming=["Flow_6"]),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Gateway_1"},
                {"id": "Flow_2", "source_ref": "Gateway_1", "target_ref": "Task_1"},
                {"id": "Flow_3", "source_ref": "Gateway_1", "target_ref": "Task_2"},
                {"id": "Flow_4", "source_ref": "Task_1", "target_ref": "Gateway_2"},
                {"id": "Flow_5", "source_ref": "Task_2", "target_ref": "Gateway_2"},
                {"id": "Flow_6", "source_ref": "Gateway_2", "target_ref": "End_1"},
            ],
        }

        # Create initial token
        token = await executor.create_initial_token(instance_id, "Start_1")
        assert token.node_id == "Start_1"

        # Execute process
        await executor.execute_process(instance_id, process_graph)

        # Verify final state
        tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(tokens) == 0  # All tokens should be consumed

    async def test_inclusive_gateway_flow(self):
        """Test execution with inclusive gateway."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = str(uuid4())

        # Set up test variables
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="amount",
            variable=ProcessVariableValue(type="float", value=150.0),
        )

        # Create process graph with inclusive gateway
        process_graph = {
            "nodes": [
                Event(id="Start_1", type="event", event_type=EventType.START, outgoing=["Flow_1"]),
                Gateway(
                    id="Gateway_1",
                    type="gateway",
                    gateway_type=GatewayType.INCLUSIVE,
                    incoming=["Flow_1"],
                    outgoing=["Flow_2", "Flow_3", "Flow_4"],
                ),
                Task(id="Task_1", type="task", incoming=["Flow_2"], outgoing=["Flow_5"]),  # High priority
                Task(id="Task_2", type="task", incoming=["Flow_3"], outgoing=["Flow_6"]),  # Medium priority
                Task(id="Task_3", type="task", incoming=["Flow_4"], outgoing=["Flow_7"]),  # Low priority
                Gateway(
                    id="Gateway_2",
                    type="gateway",
                    gateway_type=GatewayType.INCLUSIVE,
                    incoming=["Flow_5", "Flow_6", "Flow_7"],
                    outgoing=["Flow_8"],
                ),
                Event(id="End_1", type="event", event_type=EventType.END, incoming=["Flow_8"]),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Gateway_1"},
                {
                    "id": "Flow_2",
                    "source_ref": "Gateway_1",
                    "target_ref": "Task_1",
                    "condition_expression": "variables.get('amount', 0) >= 100",
                },
                {
                    "id": "Flow_3",
                    "source_ref": "Gateway_1",
                    "target_ref": "Task_2",
                    "condition_expression": "variables.get('amount', 0) >= 50",
                },
                {
                    "id": "Flow_4",
                    "source_ref": "Gateway_1",
                    "target_ref": "Task_3",
                    "condition_expression": "variables.get('amount', 0) >= 0",
                },
                {"id": "Flow_5", "source_ref": "Task_1", "target_ref": "Gateway_2"},
                {"id": "Flow_6", "source_ref": "Task_2", "target_ref": "Gateway_2"},
                {"id": "Flow_7", "source_ref": "Task_3", "target_ref": "Gateway_2"},
                {"id": "Flow_8", "source_ref": "Gateway_2", "target_ref": "End_1"},
            ],
        }

        # Create initial token
        token = await executor.create_initial_token(instance_id, "Start_1")
        assert token.node_id == "Start_1"

        # Execute process
        await executor.execute_process(instance_id, process_graph)

        # Verify final state
        tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(tokens) == 0  # All tokens should be consumed
