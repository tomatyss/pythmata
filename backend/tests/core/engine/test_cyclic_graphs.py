"""Tests for cyclic graph detection and handling."""

import pytest

from pythmata.core.engine.executor import ProcessExecutionLimitError
from pythmata.core.engine.validator import ProcessGraphValidationError
from pythmata.core.types import Event, EventType, Task
from tests.core.engine.base import BaseEngineTest


@pytest.mark.asyncio
class TestCyclicGraphs(BaseEngineTest):
    """Test detection and handling of cyclic process flows."""

    def create_cyclic_flow(self) -> dict:
        """Create a process graph with a simple cycle."""
        return {
            "nodes": [
                Event(
                    id="Start_1",
                    type="event",
                    event_type=EventType.START,
                    outgoing=["Flow_1"],
                ),
                Task(
                    id="Task_1", type="task", incoming=["Flow_1"], outgoing=["Flow_2"]
                ),
                Task(
                    id="Task_2", type="task", incoming=["Flow_2"], outgoing=["Flow_3"]
                ),
                Task(
                    id="Task_3",
                    type="task",
                    incoming=["Flow_3"],
                    outgoing=["Flow_2"],  # Creates cycle back to Task_2
                ),
                Event(
                    id="End_1",
                    type="event",
                    event_type=EventType.END,
                    incoming=[],  # No incoming flow since we have a cycle
                ),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Task_1"},
                {"id": "Flow_2", "source_ref": "Task_1", "target_ref": "Task_2"},
                {"id": "Flow_3", "source_ref": "Task_2", "target_ref": "Task_3"},
                {
                    "id": "Flow_2",
                    "source_ref": "Task_3",
                    "target_ref": "Task_2",
                },  # Cycle back to Task_2
            ],
        }

    def create_complex_cyclic_flow(self) -> dict:
        """Create a process graph with multiple cycles."""
        return {
            "nodes": [
                Event(
                    id="Start_1",
                    type="event",
                    event_type=EventType.START,
                    outgoing=["Flow_1"],
                ),
                Task(
                    id="Task_1",
                    type="task",
                    incoming=["Flow_1", "Flow_6"],  # Cycle entry point
                    outgoing=["Flow_2"],
                ),
                Task(
                    id="Task_2",
                    type="task",
                    incoming=["Flow_2"],
                    outgoing=["Flow_3", "Flow_4"],  # Branch point
                ),
                Task(
                    id="Task_3", type="task", incoming=["Flow_3"], outgoing=["Flow_5"]
                ),
                Task(
                    id="Task_4",
                    type="task",
                    incoming=["Flow_4"],
                    outgoing=["Flow_6"],  # Cycles back to Task_1
                ),
                Event(
                    id="End_1",
                    type="event",
                    event_type=EventType.END,
                    incoming=["Flow_5"],
                ),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Task_1"},
                {"id": "Flow_2", "source_ref": "Task_1", "target_ref": "Task_2"},
                {"id": "Flow_3", "source_ref": "Task_2", "target_ref": "Task_3"},
                {"id": "Flow_4", "source_ref": "Task_2", "target_ref": "Task_4"},
                {"id": "Flow_5", "source_ref": "Task_3", "target_ref": "End_1"},
                {"id": "Flow_6", "source_ref": "Task_4", "target_ref": "Task_1"},
            ],
        }

    def create_nested_cyclic_flow(self) -> dict:
        """Create a process graph with nested cycles."""
        return {
            "nodes": [
                Event(
                    id="Start_1",
                    type="event",
                    event_type=EventType.START,
                    outgoing=["Flow_1"],
                ),
                Task(
                    id="Task_1",
                    type="task",
                    incoming=["Flow_1", "Flow_7"],  # Outer cycle entry
                    outgoing=["Flow_2"],
                ),
                Task(
                    id="Task_2",
                    type="task",
                    incoming=["Flow_2", "Flow_5"],  # Inner cycle entry
                    outgoing=["Flow_3"],
                ),
                Task(
                    id="Task_3",
                    type="task",
                    incoming=["Flow_3"],
                    outgoing=["Flow_4", "Flow_5"],  # Inner cycle
                ),
                Task(
                    id="Task_4",
                    type="task",
                    incoming=["Flow_4"],
                    outgoing=["Flow_6", "Flow_7"],  # Outer cycle
                ),
                Event(
                    id="End_1",
                    type="event",
                    event_type=EventType.END,
                    incoming=["Flow_6"],
                ),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Task_1"},
                {"id": "Flow_2", "source_ref": "Task_1", "target_ref": "Task_2"},
                {"id": "Flow_3", "source_ref": "Task_2", "target_ref": "Task_3"},
                {"id": "Flow_4", "source_ref": "Task_3", "target_ref": "Task_4"},
                {"id": "Flow_5", "source_ref": "Task_3", "target_ref": "Task_2"},
                {"id": "Flow_6", "source_ref": "Task_4", "target_ref": "End_1"},
                {"id": "Flow_7", "source_ref": "Task_4", "target_ref": "Task_1"},
            ],
        }

    async def test_simple_cycle_detection(self):
        """Test detection of simple cycles in process graph."""
        instance_id = "test-cycle-1"
        graph = self.create_cyclic_flow()

        # Create initial token at start event
        await self.executor.create_initial_token(instance_id, "Start_1")

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process(instance_id, graph)
        assert "Cycle detected" in str(exc.value)

    async def test_complex_cycle_detection(self):
        """Test detection of complex cycles with branches."""
        instance_id = "test-cycle-2"
        graph = self.create_complex_cyclic_flow()

        # Create initial token at start event
        await self.executor.create_initial_token(instance_id, "Start_1")

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process(instance_id, graph)
        assert "Cycle detected" in str(exc.value)

    async def test_nested_cycle_detection(self):
        """Test detection of nested cycles."""
        instance_id = "test-cycle-3"
        graph = self.create_nested_cyclic_flow()

        # Create initial token at start event
        await self.executor.create_initial_token(instance_id, "Start_1")

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process(instance_id, graph)
        assert "Cycle detected" in str(exc.value)

    async def test_iteration_limit(self):
        """Test iteration limit prevents infinite execution."""
        instance_id = "test-limit"
        # Create a graph with a self-loop that can eventually reach the end
        graph = {
            "nodes": [
                Event(
                    id="Start_1",
                    type="event",
                    event_type=EventType.START,
                    outgoing=["Flow_1"],
                ),
                Task(
                    id="Task_1",
                    type="task",
                    incoming=["Flow_1", "Flow_2"],  # Self-loop
                    outgoing=["Flow_2", "Flow_3"],  # Self-loop and path to end
                ),
                Event(
                    id="End_1",
                    type="event",
                    event_type=EventType.END,
                    incoming=["Flow_3"],
                ),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Task_1"},
                {
                    "id": "Flow_2",
                    "source_ref": "Task_1",
                    "target_ref": "Task_1",
                },  # Self-loop
                {
                    "id": "Flow_3",
                    "source_ref": "Task_1",
                    "target_ref": "End_1",
                },  # Path to end
            ],
        }

        # Create initial token at start event
        await self.executor.create_initial_token(instance_id, "Start_1")

        # Override MAX_ITERATIONS to force limit
        self.executor.MAX_ITERATIONS = 2

        with pytest.raises(ProcessExecutionLimitError) as exc:
            await self.executor.execute_process(instance_id, graph)
        assert "exceeded" in str(exc.value)
