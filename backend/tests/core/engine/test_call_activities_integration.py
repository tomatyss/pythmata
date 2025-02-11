import asyncio
import time
from uuid import uuid4

import pytest

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestCallActivitiesIntegration:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_end_to_end_call_activity(self):
        """Test complete end-to-end execution of a call activity."""
        executor = ProcessExecutor(self.state_manager)
        parent_instance_id = str(uuid4())
        call_activity_id = "CallActivity_1"
        called_process_id = "subprocess-1"

        # 1. Create and initialize call activity
        start_time = time.perf_counter()  # Start measuring only call activity overhead
        parent_token = await executor.create_initial_token(
            parent_instance_id, call_activity_id
        )
        parent_token.data.update(
            {
                "called_process_id": called_process_id,
                "input_vars": {"subprocess_var": "parent_var"},
                "parent_var": "test_value",
            }
        )

        # Set variable in parent scope
        await self.state_manager.set_variable(
            instance_id=parent_instance_id,
            name="parent_var",
            variable=ProcessVariableValue(type="string", value="test_value"),
        )

        # Create call activity
        subprocess_token = await executor.create_call_activity(parent_token)

        # Verify subprocess initialization
        assert subprocess_token.parent_instance_id == parent_instance_id
        assert subprocess_token.parent_activity_id == call_activity_id
        assert subprocess_token.node_id == "Start_1"

        # Verify variable mapping
        subprocess_var = await self.state_manager.get_variable(
            instance_id=subprocess_token.instance_id, name="subprocess_var"
        )
        assert subprocess_var.value == "test_value"

        # Stop measuring call activity creation overhead
        creation_time = time.perf_counter()
        creation_overhead = (creation_time - start_time) * 1000
        assert (
            creation_overhead < 50
        ), f"Call activity creation overhead too high: {creation_overhead}ms"

        # 2. Execute subprocess tasks (simulated)
        task_token = await executor.move_token(subprocess_token, "Task_1")
        await asyncio.sleep(0.1)  # Simulate task execution
        end_token = await executor.move_token(task_token, "End_1")

        # 3. Complete call activity
        completion_start = time.perf_counter()  # Start measuring completion overhead
        output_vars = {"parent_result": "result"}
        await self.state_manager.set_variable(
            instance_id=subprocess_token.instance_id,
            name="result",
            variable=ProcessVariableValue(type="string", value="success"),
        )

        final_token = await executor.complete_call_activity(
            end_token, "Task_2", output_vars
        )

        # Verify final state
        assert final_token.instance_id == parent_instance_id
        assert final_token.node_id == "Task_2"
        assert final_token.state == TokenState.ACTIVE

        # Verify variable mapping back to parent
        parent_result = await self.state_manager.get_variable(
            instance_id=parent_instance_id, name="parent_result"
        )
        assert parent_result.value == "success"

        # Verify subprocess cleanup
        subprocess_tokens = await self.state_manager.get_token_positions(
            subprocess_token.instance_id
        )
        assert len(subprocess_tokens) == 0

        # Check completion performance
        completion_time = time.perf_counter()
        completion_overhead = (completion_time - completion_start) * 1000
        assert (
            completion_overhead < 50
        ), f"Call activity completion overhead too high: {completion_overhead}ms"

        # Total overhead should be less than 100ms (excluding task execution time)
        total_overhead = creation_overhead + completion_overhead
        assert (
            total_overhead < 100
        ), f"Total call activity overhead too high: {total_overhead}ms"

    async def test_error_propagation_with_compensation(self):
        """Test error propagation and compensation handling in call activities."""
        executor = ProcessExecutor(self.state_manager)
        parent_instance_id = str(uuid4())
        call_activity_id = "CallActivity_1"
        error_boundary_id = "ErrorBoundary_1"
        compensation_handler_id = "CompensationHandler_1"
        called_process_id = "subprocess-1"

        # 1. Setup and start call activity
        parent_token = await executor.create_initial_token(
            parent_instance_id, call_activity_id
        )
        parent_token.data["called_process_id"] = called_process_id

        subprocess_token = await executor.create_call_activity(parent_token)

        # 2. Execute subprocess until error (simulated)
        task_token = await executor.move_token(subprocess_token, "Task_1")
        await self.state_manager.set_variable(
            instance_id=subprocess_token.instance_id,
            name="task_1_result",
            variable=ProcessVariableValue(type="string", value="completed"),
        )

        # Move to error event
        error_token = await executor.move_token(task_token, "Error_1")
        error_token.data["error_code"] = "business_error"

        # 3. Propagate error and trigger compensation
        boundary_token = await executor.propagate_call_activity_error(
            error_token, error_boundary_id
        )

        # Verify error handling
        assert boundary_token.instance_id == parent_instance_id
        assert boundary_token.node_id == error_boundary_id
        assert boundary_token.state == TokenState.ACTIVE
        assert boundary_token.data.get("error_code") == "business_error"

        # 4. Execute compensation handler (simulated)
        compensation_token = await executor.move_token(
            boundary_token, compensation_handler_id
        )
        await asyncio.sleep(0.1)  # Simulate compensation handling

        # 5. Complete compensation
        final_token = await executor.move_token(compensation_token, "End_1")

        # Verify final state
        assert final_token.instance_id == parent_instance_id
        assert final_token.node_id == "End_1"
        assert final_token.state == TokenState.ACTIVE

        # Verify subprocess cleanup
        subprocess_tokens = await self.state_manager.get_token_positions(
            subprocess_token.instance_id
        )
        assert len(subprocess_tokens) == 0
