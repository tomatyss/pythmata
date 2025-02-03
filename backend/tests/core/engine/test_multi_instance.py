from uuid import UUID

import pytest

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestMultiInstance:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_parallel_instance_creation(self):
        """Test creation of parallel multi-instance activity."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-multi-instance-1"
        activity_id = "Activity_1"
        collection_data = ["item1", "item2", "item3"]

        # Create initial token at multi-instance activity
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection_data
        token.data["is_parallel"] = True

        # Create parallel instances
        instance_tokens = await executor.create_parallel_instances(token)

        # Verify correct number of instances created
        assert len(instance_tokens) == len(collection_data)
        
        # Verify each instance token properties
        for i, instance_token in enumerate(instance_tokens):
            assert instance_token.instance_id == instance_id
            assert instance_token.node_id == activity_id
            assert instance_token.state == TokenState.ACTIVE
            assert instance_token.scope_id.startswith(f"{activity_id}_instance_")
            assert instance_token.data["item"] == collection_data[i]
            assert instance_token.data["index"] == i

        # Verify tokens in storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == len(collection_data)
        for token in stored_tokens:
            assert token["state"] == TokenState.ACTIVE.value
            assert token["node_id"] == activity_id

    async def test_sequential_instance_creation(self):
        """Test creation of sequential multi-instance activity."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-multi-instance-2"
        activity_id = "Activity_2"
        collection_data = ["item1", "item2", "item3"]

        # Create initial token at multi-instance activity
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection_data
        token.data["is_parallel"] = False

        # Create first sequential instance
        instance_token = await executor.create_sequential_instance(token, 0)

        # Verify first instance properties
        assert instance_token.instance_id == instance_id
        assert instance_token.node_id == activity_id
        assert instance_token.state == TokenState.ACTIVE
        assert instance_token.scope_id == f"{activity_id}_instance_0"
        assert instance_token.data["item"] == collection_data[0]
        assert instance_token.data["index"] == 0

        # Verify only one token exists
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["state"] == TokenState.ACTIVE.value
        assert stored_tokens[0]["node_id"] == activity_id

    async def test_sequential_instance_completion(self):
        """Test completion of sequential multi-instance activity."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-multi-instance-3"
        activity_id = "Activity_3"
        next_task_id = "Task_1"
        collection_data = ["item1", "item2"]

        # Create initial token at multi-instance activity
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection_data
        token.data["is_parallel"] = False

        # Create and complete first instance
        first_instance = await executor.create_sequential_instance(token, 0)
        second_instance = await executor.complete_sequential_instance(
            first_instance, len(collection_data)
        )

        # Verify second instance created
        assert second_instance is not None
        assert second_instance.instance_id == instance_id
        assert second_instance.node_id == activity_id
        assert second_instance.state == TokenState.ACTIVE
        assert second_instance.scope_id == f"{activity_id}_instance_1"
        assert second_instance.data["item"] == collection_data[1]
        assert second_instance.data["index"] == 1

        # Complete second (final) instance
        final_token = await executor.complete_sequential_instance(
            second_instance, len(collection_data)
        )

        # Verify activity completion
        assert final_token.instance_id == instance_id
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE
        assert final_token.scope_id is None

        # Verify no remaining instance tokens
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id

    async def test_parallel_instance_completion(self):
        """Test completion of parallel multi-instance activity."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-multi-instance-4"
        activity_id = "Activity_4"
        next_task_id = "Task_1"
        collection_data = ["item1", "item2"]

        # Create initial token at multi-instance activity
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection_data
        token.data["is_parallel"] = True

        # Create parallel instances
        instance_tokens = await executor.create_parallel_instances(token)

        # Complete first instance
        await executor.complete_parallel_instance(
            instance_tokens[0], len(collection_data)
        )

        # Verify first instance completed but activity not complete
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 2
        completed = [t for t in stored_tokens if t["state"] == TokenState.COMPLETED.value]
        active = [t for t in stored_tokens if t["state"] == TokenState.ACTIVE.value]
        assert len(completed) == 1
        assert len(active) == 1

        # Complete second instance
        final_token = await executor.complete_parallel_instance(
            instance_tokens[1], len(collection_data)
        )

        # Verify activity completion
        assert final_token.instance_id == instance_id
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE
        assert final_token.scope_id is None

        # Verify no remaining instance tokens
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id

    async def test_empty_collection_handling(self):
        """Test handling of empty collection for multi-instance activity."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-multi-instance-5"
        activity_id = "Activity_5"
        next_task_id = "Task_1"
        collection_data = []

        # Create initial token at multi-instance activity
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection_data
        token.data["is_parallel"] = True

        # Attempt to create instances with empty collection
        token = await executor.handle_empty_collection(token, next_task_id)

        # Verify token moved directly to next task
        assert token.instance_id == instance_id
        assert token.node_id == next_task_id
        assert token.state == TokenState.ACTIVE
        assert token.scope_id is None

        # Verify token in storage
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id
