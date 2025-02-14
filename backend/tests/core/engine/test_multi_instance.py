from uuid import UUID

import pytest

from pythmata.core.engine.token import TokenState
from tests.core.engine.base import BaseEngineTest
from tests.core.testing import assert_token_state


@pytest.mark.asyncio
class TestMultiInstance(BaseEngineTest):
    async def test_parallel_instance_creation(self):
        """Test creation of parallel multi-instance activity."""
        instance_id = "test-multi-instance-1"
        activity_id = "Activity_1"
        collection_data = ["item1", "item2", "item3"]

        # Create process graph and initial token
        process_graph = self.create_multi_instance_flow(activity_id)
        token = await self.setup_multi_instance_token(
            instance_id, activity_id, collection_data, is_parallel=True
        )

        # Create parallel instances
        instance_tokens = await self.executor.create_parallel_instances(token)

        # Verify instance tokens
        assert len(instance_tokens) == len(collection_data)
        for i, instance_token in enumerate(instance_tokens):
            assert instance_token.instance_id == instance_id
            assert instance_token.node_id == activity_id
            assert instance_token.state == TokenState.ACTIVE
            assert instance_token.scope_id.startswith(f"{activity_id}_instance_")
            assert instance_token.data["item"] == collection_data[i]
            assert instance_token.data["index"] == i

        # Verify tokens in storage
        await assert_token_state(
            self.state_manager,
            instance_id,
            len(collection_data),
            [activity_id] * len(collection_data),
        )

    async def test_sequential_instance_creation(self):
        """Test creation of sequential multi-instance activity."""
        instance_id = "test-multi-instance-2"
        activity_id = "Activity_2"
        collection_data = ["item1", "item2", "item3"]

        # Create process graph and initial token
        process_graph = self.create_multi_instance_flow(activity_id)
        token = await self.setup_multi_instance_token(
            instance_id, activity_id, collection_data, is_parallel=False
        )

        # Create first sequential instance
        instance_token = await self.executor.create_sequential_instance(token, 0)

        # Verify instance token
        assert instance_token.instance_id == instance_id
        assert instance_token.node_id == activity_id
        assert instance_token.state == TokenState.ACTIVE
        assert instance_token.scope_id == f"{activity_id}_instance_0"
        assert instance_token.data["item"] == collection_data[0]
        assert instance_token.data["index"] == 0

        # Verify only one token exists
        await assert_token_state(self.state_manager, instance_id, 1, [activity_id])

    async def test_sequential_instance_completion(self):
        """Test completion of sequential multi-instance activity."""
        instance_id = "test-multi-instance-3"
        activity_id = "Activity_3"
        next_task_id = "Task_1"
        collection_data = ["item1", "item2"]

        # Create process graph and initial token
        process_graph = self.create_multi_instance_flow(activity_id, next_task_id)
        token = await self.setup_multi_instance_token(
            instance_id, activity_id, collection_data, is_parallel=False
        )

        # Create and complete first instance
        first_instance = await self.executor.create_sequential_instance(token, 0)
        second_instance = await self.executor.complete_sequential_instance(
            first_instance, len(collection_data)
        )

        # Verify second instance
        assert second_instance is not None
        assert second_instance.instance_id == instance_id
        assert second_instance.node_id == activity_id
        assert second_instance.state == TokenState.ACTIVE
        assert second_instance.scope_id == f"{activity_id}_instance_1"
        assert second_instance.data["item"] == collection_data[1]
        assert second_instance.data["index"] == 1

        # Complete second (final) instance
        final_token = await self.executor.complete_sequential_instance(
            second_instance, len(collection_data)
        )

        # Verify activity completion
        assert final_token.instance_id == instance_id
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE
        assert final_token.scope_id is None

        # Verify token moved to next task
        await assert_token_state(self.state_manager, instance_id, 1, [next_task_id])

    async def test_parallel_instance_completion(self):
        """Test completion of parallel multi-instance activity."""
        instance_id = "test-multi-instance-4"
        activity_id = "Activity_4"
        next_task_id = "Task_1"
        collection_data = ["item1", "item2"]

        # Create process graph and initial token
        process_graph = self.create_multi_instance_flow(activity_id, next_task_id)
        token = await self.setup_multi_instance_token(
            instance_id, activity_id, collection_data, is_parallel=True
        )

        # Create parallel instances
        instance_tokens = await self.executor.create_parallel_instances(token)

        # Complete first instance
        await self.executor.complete_parallel_instance(
            instance_tokens[0], len(collection_data)
        )

        # Verify first instance completed but activity not complete
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        completed = [
            t for t in stored_tokens if t["state"] == TokenState.COMPLETED.value
        ]
        active = [t for t in stored_tokens if t["state"] == TokenState.ACTIVE.value]
        assert len(completed) == 1
        assert len(active) == 1

        # Complete second instance
        final_token = await self.executor.complete_parallel_instance(
            instance_tokens[1], len(collection_data)
        )

        # Verify activity completion
        assert final_token.instance_id == instance_id
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE
        assert final_token.scope_id is None

        # Verify token moved to next task
        await assert_token_state(self.state_manager, instance_id, 1, [next_task_id])

    async def test_empty_collection_handling(self):
        """Test handling of empty collection for multi-instance activity."""
        instance_id = "test-multi-instance-5"
        activity_id = "Activity_5"
        next_task_id = "Task_1"
        collection_data = []

        # Create process graph and initial token
        process_graph = self.create_multi_instance_flow(activity_id, next_task_id)
        token = await self.setup_multi_instance_token(
            instance_id, activity_id, collection_data, is_parallel=True
        )

        # Attempt to create instances with empty collection
        token = await self.executor.handle_empty_collection(token, next_task_id)

        # Verify token moved directly to next task
        assert token.instance_id == instance_id
        assert token.node_id == next_task_id
        assert token.state == TokenState.ACTIVE
        assert token.scope_id is None

        # Verify token in storage
        await assert_token_state(self.state_manager, instance_id, 1, [next_task_id])
