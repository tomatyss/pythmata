"""Tests for process graph validation functionality."""

import pytest

from pythmata.core.engine.validator import ProcessGraphValidationError
from pythmata.core.types import Event, EventType, Task
from tests.core.engine.base import BaseEngineTest


@pytest.mark.asyncio
class TestProcessGraphValidation(BaseEngineTest):
    """Test process graph validation functionality."""

    async def test_invalid_graph_missing_flows(self):
        """Test validation fails when graph is missing flows."""
        invalid_graph = {
            "nodes": [
                Event(
                    id="Start_1", type="event", event_type=EventType.START, outgoing=[]
                )
            ]
        }

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process("test-instance", invalid_graph)
        assert "Missing flows section" in str(exc.value)

    async def test_invalid_node_references(self):
        """Test validation fails when flow references nonexistent node."""
        # Use create_sequence_flow() as base but modify to create invalid reference
        graph = self.create_sequence_flow()
        graph["flows"][0]["target_ref"] = "nonexistent_node"

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process("test-instance", graph)
        assert "Invalid node reference" in str(exc.value)

    async def test_disconnected_nodes(self):
        """Test validation fails when nodes are not properly connected."""
        graph = {
            "nodes": [
                Event(
                    id="Start_1", type="event", event_type=EventType.START, outgoing=[]
                ),
                Event(id="End_1", type="event", event_type=EventType.END, incoming=[]),
            ],
            "flows": [],
        }

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process("test-instance", graph)
        assert "Disconnected nodes detected" in str(exc.value)

    async def test_missing_start_event(self):
        """Test validation fails when no start event is present."""
        graph = {
            "nodes": [
                Task(id="Task_1", type="task", incoming=[], outgoing=["Flow_1"]),
                Event(
                    id="End_1",
                    type="event",
                    event_type=EventType.END,
                    incoming=["Flow_1"],
                ),
            ],
            "flows": [{"id": "Flow_1", "source_ref": "Task_1", "target_ref": "End_1"}],
        }

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process("test-instance", graph)
        assert "No start event found" in str(exc.value)

    async def test_missing_end_event(self):
        """Test validation fails when no end event is present."""
        graph = {
            "nodes": [
                Event(
                    id="Start_1",
                    type="event",
                    event_type=EventType.START,
                    outgoing=["Flow_1"],
                ),
                Task(id="Task_1", type="task", incoming=["Flow_1"], outgoing=[]),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "Task_1"}
            ],
        }

        with pytest.raises(ProcessGraphValidationError) as exc:
            await self.executor.execute_process("test-instance", graph)
        assert "No end event found" in str(exc.value)

    async def test_valid_process_graph(self):
        """Test validation passes for valid process graph."""
        graph = self.create_sequence_flow()
        # Should not raise any exceptions
        await self.executor.execute_process("test-instance", graph)
