from uuid import UUID

import pytest

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestBasicSubprocess:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_enter_subprocess(self):
        """Test token enters subprocess and creates new subprocess scope."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-subprocess-1"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"

        # Create initial token in parent process
        token = await executor.create_initial_token(instance_id, parent_process_id)

        # Move token to subprocess
        subprocess_token = await executor.enter_subprocess(token, subprocess_id)

        # Verify subprocess token was created
        assert subprocess_token is not None
        assert isinstance(subprocess_token.id, UUID)
        assert subprocess_token.instance_id == instance_id
        assert subprocess_token.node_id == subprocess_id
        assert subprocess_token.state == TokenState.ACTIVE
        assert subprocess_token.scope_id == subprocess_id  # New scope for subprocess

        # Verify token position in storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == subprocess_id
        assert stored_tokens[0]["scope_id"] == subprocess_id

    async def test_exit_subprocess(self):
        """Test token exits subprocess and returns to parent process."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-subprocess-2"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"
        next_task_id = "Task_1"

        # Create and move token to subprocess
        token = await executor.create_initial_token(instance_id, parent_process_id)
        subprocess_token = await executor.enter_subprocess(token, subprocess_id)

        # Exit subprocess
        parent_token = await executor.exit_subprocess(subprocess_token, next_task_id)

        # Verify token returned to parent scope
        assert parent_token is not None
        assert parent_token.instance_id == instance_id
        assert parent_token.node_id == next_task_id
        assert parent_token.state == TokenState.ACTIVE
        assert parent_token.scope_id is None  # Back to parent scope

        # Verify token position in storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id
        assert stored_tokens[0]["scope_id"] is None

    async def test_subprocess_completion(self):
        """Test subprocess completion and continuation of parent process."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-subprocess-3"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"
        subprocess_end_id = "SubprocessEnd_1"
        next_task_id = "Task_1"

        # Create and move token to subprocess
        token = await executor.create_initial_token(instance_id, parent_process_id)
        subprocess_token = await executor.enter_subprocess(token, subprocess_id)

        # Move to subprocess end event
        end_token = await executor.move_token(subprocess_token, subprocess_end_id)

        # Complete subprocess
        parent_token = await executor.complete_subprocess(end_token, next_task_id)

        # Verify subprocess completion
        assert parent_token is not None
        assert parent_token.instance_id == instance_id
        assert parent_token.node_id == next_task_id
        assert parent_token.state == TokenState.ACTIVE
        assert parent_token.scope_id is None

        # Verify token position in storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id
        assert stored_tokens[0]["scope_id"] is None

        # Verify subprocess scope is cleaned up
        subprocess_tokens = await self.state_manager.get_scope_tokens(
            instance_id, subprocess_id
        )
        assert len(subprocess_tokens) == 0
