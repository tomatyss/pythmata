import pytest

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestSubprocessVariables:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_subprocess_variable_isolation(self):
        """Test subprocess variables are isolated from parent scope."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-subprocess-vars-1"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"

        # Create initial token and set parent variable
        token = await executor.create_initial_token(instance_id, parent_process_id)
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="count",
            variable=ProcessVariableValue(type="integer", value=1),
        )

        # Enter subprocess and set subprocess variable
        subprocess_token = await executor.enter_subprocess(token, subprocess_id)
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="count",
            variable=ProcessVariableValue(type="integer", value=2),
            scope_id=subprocess_id,
        )

        # Verify parent and subprocess variables are isolated
        parent_value = await self.state_manager.get_variable(instance_id, "count")
        subprocess_value = await self.state_manager.get_variable(
            instance_id, "count", scope_id=subprocess_id
        )

        assert parent_value.value == 1
        assert subprocess_value.value == 2

    async def test_subprocess_variable_inheritance(self):
        """Test subprocess inherits parent process variables."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-subprocess-vars-2"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"

        # Create initial token and set parent variables
        token = await executor.create_initial_token(instance_id, parent_process_id)
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="user",
            variable=ProcessVariableValue(type="string", value="John"),
        )
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="role",
            variable=ProcessVariableValue(type="string", value="admin"),
        )

        # Enter subprocess
        subprocess_token = await executor.enter_subprocess(token, subprocess_id)

        # Verify subprocess can read parent variables
        subprocess_user = await self.state_manager.get_variable(
            instance_id, "user", scope_id=subprocess_id
        )
        subprocess_role = await self.state_manager.get_variable(
            instance_id, "role", scope_id=subprocess_id
        )

        # Variables should be inherited from parent if not found in subprocess scope
        assert subprocess_user.value == "John"
        assert subprocess_role.value == "admin"

    async def test_subprocess_variable_output(self):
        """Test subprocess can output variables to parent."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-subprocess-vars-3"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"
        next_task_id = "Task_1"

        # Create initial token
        token = await executor.create_initial_token(instance_id, parent_process_id)

        # Enter subprocess and set subprocess variables
        subprocess_token = await executor.enter_subprocess(token, subprocess_id)
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="result",
            variable=ProcessVariableValue(type="string", value="success"),
            scope_id=subprocess_id,
        )

        # Complete subprocess with output mapping
        output_vars = {"result": "result"}  # Map subprocess result to parent result
        parent_token = await executor.complete_subprocess(
            subprocess_token, next_task_id, output_vars
        )

        # Verify variable was copied to parent scope
        parent_result = await self.state_manager.get_variable(instance_id, "result")
        assert parent_result.value == "success"

        # Verify subprocess scope was cleaned up
        subprocess_result = await self.state_manager.get_variable(
            instance_id, "result", scope_id=subprocess_id, check_parent=False
        )
        assert subprocess_result is None
