from uuid import UUID

import pytest

from pythmata.core.engine.token import TokenState
from pythmata.core.types import Event, EventType
from tests.core.engine.base import BaseEngineTest


@pytest.mark.asyncio
class TestBasicSubprocess(BaseEngineTest):
    async def test_enter_subprocess(self):
        """Test token enters subprocess and creates new subprocess scope."""
        instance_id = "test-subprocess-1"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"

        # Create initial token in parent process
        token = await self.executor.create_initial_token(instance_id, parent_process_id)

        # Move token to subprocess
        subprocess_token = await self.executor.enter_subprocess(token, subprocess_id)

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
        instance_id = "test-subprocess-2"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"
        next_task_id = "Task_1"

        # Create and move token to subprocess
        token = await self.executor.create_initial_token(instance_id, parent_process_id)
        subprocess_token = await self.executor.enter_subprocess(token, subprocess_id)

        # Exit subprocess
        parent_token = await self.executor.exit_subprocess(
            subprocess_token, next_task_id
        )

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
        instance_id = "test-subprocess-3"
        parent_process_id = "Process_1"
        subprocess_id = "Subprocess_1"
        subprocess_end_id = "SubprocessEnd_1"
        next_task_id = "Task_1"

        # Create and move token to subprocess
        token = await self.executor.create_initial_token(instance_id, parent_process_id)
        subprocess_token = await self.executor.enter_subprocess(token, subprocess_id)

        # Create end event in subprocess scope and set up token
        end_event = Event(id=subprocess_end_id, type="event", event_type=EventType.END)
        
        # Create token at end event with proper scope
        async with self.state_manager.redis.pipeline(transaction=True) as pipe:
            # Remove old token
            await self.state_manager.remove_token(
                instance_id=subprocess_token.instance_id,
                node_id=subprocess_token.node_id
            )
            await pipe.delete(f"tokens:{subprocess_token.instance_id}")
            
            # Create new token at end event
            end_token = subprocess_token.copy(node_id=subprocess_end_id)
            await self.state_manager.add_token(
                instance_id=end_token.instance_id,
                node_id=end_token.node_id,
                data=end_token.to_dict()
            )
            await self.state_manager.update_token_state(
                instance_id=end_token.instance_id,
                node_id=end_token.node_id,
                state=TokenState.ACTIVE,
                scope_id=subprocess_id
            )
            await pipe.execute()

        # Complete subprocess
        parent_token = await self.executor.complete_subprocess(end_token, next_task_id)

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
