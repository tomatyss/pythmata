from uuid import UUID

import pytest

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestEventSubprocess:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_event_subprocess_triggering(self):
        """Test event subprocess is triggered correctly by events."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-event-subprocess-1"
        parent_process_id = "Process_1"
        event_subprocess_id = "EventSubprocess_1"
        start_event_id = "StartEvent_1"

        # Create initial token in parent process
        token = await executor.create_initial_token(instance_id, parent_process_id)

        # Simulate event trigger
        event_data = {"type": "message", "name": "test_event"}
        event_token = await executor.trigger_event_subprocess(
            token, event_subprocess_id, event_data
        )

        # Verify event subprocess token was created
        assert event_token is not None
        assert isinstance(event_token.id, UUID)
        assert event_token.instance_id == instance_id
        assert event_token.node_id == start_event_id
        assert event_token.state == TokenState.ACTIVE
        assert event_token.scope_id == event_subprocess_id
        assert event_token.data.get("event_data") == event_data

        # Verify both tokens exist (parent process and event subprocess)
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 2
        assert any(t["node_id"] == token.node_id for t in stored_tokens)
        assert any(t["node_id"] == start_event_id for t in stored_tokens)

    async def test_interrupting_event_subprocess(self):
        """Test interrupting event subprocess behavior."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-event-subprocess-2"
        parent_process_id = "Process_1"
        event_subprocess_id = "EventSubprocess_2"
        start_event_id = "StartEvent_2"

        # Create initial token in parent process
        token = await executor.create_initial_token(instance_id, parent_process_id)

        # Simulate interrupting event trigger
        event_data = {"type": "error", "name": "test_error", "interrupting": True}
        event_token = await executor.trigger_event_subprocess(
            token, event_subprocess_id, event_data
        )

        # Verify event subprocess token was created
        assert event_token is not None
        assert event_token.node_id == start_event_id
        assert event_token.state == TokenState.ACTIVE
        assert event_token.scope_id == event_subprocess_id

        # Verify parent process token was cancelled
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1  # Only event subprocess token remains
        assert stored_tokens[0]["node_id"] == start_event_id

    async def test_non_interrupting_event_subprocess(self):
        """Test non-interrupting event subprocess behavior."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-event-subprocess-3"
        parent_process_id = "Process_1"
        event_subprocess_id = "EventSubprocess_3"
        start_event_id = "StartEvent_3"

        # Create initial token in parent process
        token = await executor.create_initial_token(instance_id, parent_process_id)

        # Simulate non-interrupting event trigger
        event_data = {"type": "message", "name": "test_message", "interrupting": False}
        event_token = await executor.trigger_event_subprocess(
            token, event_subprocess_id, event_data
        )

        # Verify event subprocess token was created
        assert event_token is not None
        assert event_token.node_id == start_event_id
        assert event_token.state == TokenState.ACTIVE
        assert event_token.scope_id == event_subprocess_id

        # Verify both tokens exist and are active
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 2  # Both tokens remain active
        assert any(
            t["node_id"] == token.node_id and t["state"] == TokenState.ACTIVE.value
            for t in stored_tokens
        )
        assert any(
            t["node_id"] == start_event_id and t["state"] == TokenState.ACTIVE.value
            for t in stored_tokens
        )

    async def test_concurrent_event_subprocesses(self):
        """Test multiple event subprocesses can run concurrently."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-event-subprocess-4"
        parent_process_id = "Process_1"
        event_subprocess_1_id = "EventSubprocess_4a"
        event_subprocess_2_id = "EventSubprocess_4b"
        start_event_1_id = "StartEvent_4a"
        start_event_2_id = "StartEvent_4b"

        # Create initial token in parent process
        token = await executor.create_initial_token(instance_id, parent_process_id)

        # Trigger first event subprocess
        event_1_data = {
            "type": "message",
            "name": "test_message_1",
            "interrupting": False,
        }
        event_token_1 = await executor.trigger_event_subprocess(
            token, event_subprocess_1_id, event_1_data
        )

        # Trigger second event subprocess
        event_2_data = {
            "type": "message",
            "name": "test_message_2",
            "interrupting": False,
        }
        event_token_2 = await executor.trigger_event_subprocess(
            token, event_subprocess_2_id, event_2_data
        )

        # Verify all tokens exist and are active
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 3  # Parent + 2 event subprocesses
        assert any(t["node_id"] == token.node_id for t in stored_tokens)
        assert any(t["node_id"] == start_event_1_id for t in stored_tokens)
        assert any(t["node_id"] == start_event_2_id for t in stored_tokens)

        # Verify each token has correct scope
        scopes = {t["scope_id"] for t in stored_tokens}
        assert None in scopes  # Parent process scope
        assert event_subprocess_1_id in scopes
        assert event_subprocess_2_id in scopes
