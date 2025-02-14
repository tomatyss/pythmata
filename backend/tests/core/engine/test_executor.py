from uuid import UUID

import pytest

from pythmata.core.engine.token import TokenState
from tests.core.engine.base import BaseEngineTest
from tests.core.testing import assert_token_state
from tests.data.process_samples import create_test_bpmn_xml


@pytest.mark.asyncio
class TestProcessExecutor(BaseEngineTest):
    async def test_create_initial_token(self):
        """Test creation of initial token at process start."""
        instance_id = "test-create-1"
        start_event_id = "StartEvent_1"

        # Create initial token
        token = await self.executor.create_initial_token(instance_id, start_event_id)

        # Verify token was created
        assert token is not None
        assert isinstance(token.id, UUID)
        assert token.instance_id == instance_id
        assert token.node_id == start_event_id
        assert token.state == TokenState.ACTIVE

        # Verify token was stored
        await assert_token_state(self.state_manager, instance_id, 1, [start_event_id])

    async def test_move_token(self):
        """Test moving a token from one node to another."""
        instance_id = "test-move-1"
        start_event_id = "StartEvent_1"
        task_id = "Task_1"

        # Create and move token
        token = await self.executor.create_initial_token(instance_id, start_event_id)
        moved_token = await self.executor.move_token(token, task_id)

        # Verify token was moved
        assert moved_token.node_id == task_id
        assert moved_token.state == TokenState.ACTIVE

        # Verify token position was updated in storage
        await assert_token_state(self.state_manager, instance_id, 1, [task_id])

    async def test_consume_token(self):
        """Test consuming a token at an end event."""
        instance_id = "test-consume-1"
        end_event_id = "End_1"

        # Create token at end event
        token = await self.executor.create_initial_token(instance_id, end_event_id)

        # Consume token
        await self.executor.consume_token(token)

        # Verify token was removed from storage
        await assert_token_state(self.state_manager, instance_id, 0)

    async def test_split_token(self):
        """Test splitting a token at a parallel gateway."""
        instance_id = "test-split-1"
        gateway_id = "Gateway_1"
        target_ids = ["Task_1", "Task_2"]

        # Create token at gateway
        token = await self.executor.create_initial_token(instance_id, gateway_id)

        # Split token
        new_tokens = await self.executor.split_token(token, target_ids)

        # Verify new tokens were created
        assert len(new_tokens) == 2
        assert {t.node_id for t in new_tokens} == set(target_ids)
        assert all(t.state == TokenState.ACTIVE for t in new_tokens)

        # Verify tokens in storage
        await assert_token_state(self.state_manager, instance_id, 2, target_ids)
