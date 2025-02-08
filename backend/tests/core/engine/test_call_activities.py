import pytest

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestCallActivities:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_basic_call_activity_creation(self):
        """Test creating a call activity and initializing called process."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-call-1"
        call_activity_id = "CallActivity_1"
        called_process_id = "subprocess-1"

        # Create token at call activity
        token = await executor.create_initial_token(instance_id, call_activity_id)
        token.data["called_process_id"] = called_process_id

        # Create and initialize call activity
        new_token = await executor.create_call_activity(token)

        # Verify call activity was created
        assert new_token is not None
        assert new_token.instance_id != instance_id  # Should be new instance
        assert new_token.node_id == "Start_1"  # Should start at start event
        assert new_token.state == TokenState.ACTIVE
        assert new_token.parent_instance_id == instance_id
        assert new_token.parent_activity_id == call_activity_id

        # Verify tokens in storage
        parent_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(parent_tokens) == 1
        assert parent_tokens[0]["node_id"] == call_activity_id
        assert parent_tokens[0]["state"] == TokenState.WAITING.value

        child_tokens = await self.state_manager.get_token_positions(
            new_token.instance_id
        )
        assert len(child_tokens) == 1
        assert child_tokens[0]["node_id"] == "Start_1"

    async def test_call_activity_variable_mapping(self):
        """Test variable mapping between parent and called process."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-call-2"
        call_activity_id = "CallActivity_1"
        called_process_id = "subprocess-1"

        # Create token with variables
        token = await executor.create_initial_token(instance_id, call_activity_id)
        token.data.update(
            {
                "called_process_id": called_process_id,
                "input_vars": {"subprocess_var": "parent_var"},
                "parent_var": "test_value",
            }
        )

        # Set variable in parent scope
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="parent_var",
            variable=ProcessVariableValue(type="string", value="test_value"),
        )

        # Create call activity
        new_token = await executor.create_call_activity(token)

        # Verify variable was mapped to subprocess
        subprocess_var = await self.state_manager.get_variable(
            instance_id=new_token.instance_id, name="subprocess_var"
        )
        assert subprocess_var.value == "test_value"

    async def test_call_activity_completion(self):
        """Test completion of called process and return to parent."""
        executor = ProcessExecutor(self.state_manager)
        parent_instance_id = "test-call-3"
        call_activity_id = "CallActivity_1"
        next_task_id = "Task_1"
        subprocess_instance_id = "subprocess-instance-1"

        # Create parent token
        parent_token = await executor.create_initial_token(
            parent_instance_id, call_activity_id
        )

        # Create subprocess token at end event
        subprocess_token = Token(
            instance_id=subprocess_instance_id,
            node_id="End_1",
            parent_instance_id=parent_instance_id,
            parent_activity_id=call_activity_id,
        )

        # Set output variable in subprocess
        await self.state_manager.set_variable(
            instance_id=subprocess_instance_id,
            name="result",
            variable=ProcessVariableValue(type="string", value="success"),
        )

        # Complete call activity
        output_vars = {"parent_result": "result"}
        new_token = await executor.complete_call_activity(
            subprocess_token, next_task_id, output_vars
        )

        # Verify token returned to parent process
        assert new_token.instance_id == parent_instance_id
        assert new_token.node_id == next_task_id
        assert new_token.state == TokenState.ACTIVE

        # Verify variable mapping
        parent_result = await self.state_manager.get_variable(
            instance_id=parent_instance_id, name="parent_result"
        )
        assert parent_result.value == "success"

        # Verify subprocess tokens were cleaned up
        subprocess_tokens = await self.state_manager.get_token_positions(
            subprocess_instance_id
        )
        assert len(subprocess_tokens) == 0

    async def test_call_activity_error_propagation(self):
        """Test error propagation from called process to parent."""
        executor = ProcessExecutor(self.state_manager)
        parent_instance_id = "test-call-4"
        call_activity_id = "CallActivity_1"
        error_boundary_id = "ErrorBoundary_1"
        subprocess_instance_id = "subprocess-instance-2"

        # Create parent token
        parent_token = await executor.create_initial_token(
            parent_instance_id, call_activity_id
        )

        # Create subprocess token at error event
        subprocess_token = Token(
            instance_id=subprocess_instance_id,
            node_id="Error_1",
            parent_instance_id=parent_instance_id,
            parent_activity_id=call_activity_id,
            data={"error_code": "test_error"},
        )

        # Propagate error to parent
        new_token = await executor.propagate_call_activity_error(
            subprocess_token, error_boundary_id
        )

        # Verify token moved to error boundary event
        assert new_token.instance_id == parent_instance_id
        assert new_token.node_id == error_boundary_id
        assert new_token.state == TokenState.ACTIVE
        assert new_token.data.get("error_code") == "test_error"

        # Verify subprocess tokens were cleaned up
        subprocess_tokens = await self.state_manager.get_token_positions(
            subprocess_instance_id
        )
        assert len(subprocess_tokens) == 0
