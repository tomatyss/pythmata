import pytest
from uuid import UUID

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

@pytest.mark.asyncio
class TestProcessExecutor:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()
        
        yield
        
        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_create_initial_token(self):
        """Test creation of initial token at process start."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-create-1"
        start_event_id = "Start_1"

        # Create initial token
        token = await executor.create_initial_token(instance_id, start_event_id)

        # Verify token was created
        assert token is not None
        assert isinstance(token.id, UUID)
        assert token.instance_id == instance_id
        assert token.node_id == start_event_id
        assert token.state == TokenState.ACTIVE

        # Verify token was stored
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == start_event_id

    async def test_move_token(self):
        """Test moving a token from one node to another."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-move-1"
        start_event_id = "Start_1"
        task_id = "Task_1"

        # Create and move token
        token = await executor.create_initial_token(instance_id, start_event_id)
        moved_token = await executor.move_token(token, task_id)

        # Verify token was moved
        assert moved_token.node_id == task_id
        assert moved_token.state == TokenState.ACTIVE

        # Verify token position was updated in storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == task_id

    async def test_consume_token(self):
        """Test consuming a token at an end event."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-consume-1"
        end_event_id = "End_1"

        # Create token at end event
        token = await executor.create_initial_token(instance_id, end_event_id)
        
        # Consume token
        await executor.consume_token(token)

        # Verify token was removed from storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 0

    async def test_split_token(self):
        """Test splitting a token at a parallel gateway."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-split-1"
        gateway_id = "Gateway_1"
        target_ids = ["Task_1", "Task_2"]

        # Create token at gateway
        token = await executor.create_initial_token(instance_id, gateway_id)
        
        # Split token
        new_tokens = await executor.split_token(token, target_ids)

        # Verify new tokens were created
        assert len(new_tokens) == 2
        assert {t.node_id for t in new_tokens} == set(target_ids)
        assert all(t.state == TokenState.ACTIVE for t in new_tokens)

        # Verify tokens in storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 2
        assert {t["node_id"] for t in stored_tokens} == set(target_ids)
