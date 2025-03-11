import time

import pytest

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestComplexMultiInstance:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_nested_multi_instance(self):
        """Test nested multi-instance activities (parallel within sequential)."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-nested-mi-1"
        outer_activity_id = "OuterActivity_1"
        inner_activity_id = "InnerActivity_1"
        next_task_id = "Task_1"

        # Outer sequential multi-instance data
        departments = ["HR", "IT", "Finance"]
        # Inner parallel multi-instance data per department
        employees = {
            "HR": ["Alice", "Bob"],
            "IT": ["Charlie", "Dave", "Eve"],
            "Finance": ["Frank", "Grace"],
        }

        # Create initial token for outer sequential activity
        outer_token = await executor.create_initial_token(
            instance_id, outer_activity_id
        )
        outer_token.data["collection"] = departments
        outer_token.data["is_parallel"] = False

        # Start first sequential instance
        current_token = await executor.create_sequential_instance(outer_token, 0)

        # Process each department sequentially
        for i, dept in enumerate(departments):
            # Set up inner parallel multi-instance
            current_token.node_id = inner_activity_id
            current_token.data["collection"] = employees[dept]
            current_token.data["is_parallel"] = True

            # Create parallel instances for employees
            inner_tokens = await executor.create_parallel_instances(current_token)
            assert len(inner_tokens) == len(employees[dept])

            # Complete all employee instances
            for inner_token in inner_tokens:
                result = await executor.complete_parallel_instance(
                    inner_token, len(employees[dept])
                )
                if result:  # Last parallel instance completed
                    # Clean up completed parallel instance tokens
                    await self.state_manager.clear_scope_tokens(
                        instance_id, inner_activity_id
                    )
                    # Clean up task tokens
                    stored_tokens = await self.state_manager.get_token_positions(
                        instance_id
                    )
                    for token in stored_tokens:
                        if token["node_id"] == "Task_1":
                            await self.state_manager.remove_token(
                                instance_id, token["node_id"]
                            )
                    # Move to next department if not last
                    if i < len(departments) - 1:
                        current_token = await executor.complete_sequential_instance(
                            current_token, len(departments)
                        )

        # Complete final department and clean up
        final_token = await executor.complete_sequential_instance(
            current_token, len(departments)
        )

        # Clean up outer activity token
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        for token in stored_tokens:
            if token["node_id"] == outer_activity_id:
                await self.state_manager.remove_token(instance_id, token["node_id"])

        # Verify process completed correctly
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE
        assert final_token.scope_id is None

        # Verify only one token remains
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id

    async def test_multi_instance_variable_isolation(self):
        """Test variable scope isolation between multi-instance activities."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-mi-vars-1"
        activity_id = "Activity_1"

        # Create parallel instances with their own variables
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = ["A", "B", "C"]
        token.data["is_parallel"] = True

        instance_tokens = await executor.create_parallel_instances(token)

        # Set different variables in each instance scope
        for i, instance_token in enumerate(instance_tokens):
            await self.state_manager.set_variable(
                instance_id=instance_id,
                name="local_var",
                variable=ProcessVariableValue(type="string", value=f"value_{i}"),
                scope_id=instance_token.scope_id,
            )

        # Verify variable isolation
        for i, instance_token in enumerate(instance_tokens):
            value = await self.state_manager.get_variable(
                instance_id, "local_var", scope_id=instance_token.scope_id
            )
            assert value.value == f"value_{i}"

    async def test_multi_instance_performance(self):
        """Test multi-instance creation performance meets requirements."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-mi-perf-1"
        activity_id = "Activity_1"

        # Test with different collection sizes
        collection_sizes = [10, 50, 100]
        max_time_per_instance = 0.050  # 50ms requirement

        for size in collection_sizes:
            # Create token with collection
            token = await executor.create_initial_token(instance_id, activity_id)
            token.data["collection"] = [f"item_{i}" for i in range(size)]
            token.data["is_parallel"] = True

            # Measure parallel instance creation time
            start_time = time.time()
            instance_tokens = await executor.create_parallel_instances(token)
            end_time = time.time()

            total_time = end_time - start_time
            time_per_instance = total_time / size

            # Verify performance requirement
            assert time_per_instance <= max_time_per_instance, (
                f"Instance creation took {time_per_instance:.3f}s per instance "
                f"(required: {max_time_per_instance:.3f}s)"
            )

            # Cleanup for next iteration
            await self.state_manager.redis.flushdb()

    async def test_collection_type_variations(self):
        """Test multi-instance handling of different collection types."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-mi-collections-1"
        activity_id = "Activity_1"

        # Test different collection types
        collections = [
            # List of strings
            ["item1", "item2", "item3"],
            # List of dictionaries
            [{"id": 1, "name": "First"}, {"id": 2, "name": "Second"}],
            # List of mixed types
            [1, "two", {"three": 3}, ["four"]],
        ]

        for collection in collections:
            # Create token with collection
            token = await executor.create_initial_token(instance_id, activity_id)
            token.data["collection"] = collection
            token.data["is_parallel"] = True

            # Create instances
            instance_tokens = await executor.create_parallel_instances(token)

            # Verify correct number of instances
            assert len(instance_tokens) == len(collection)

            # Verify each instance has correct item data
            for i, instance_token in enumerate(instance_tokens):
                assert instance_token.data["item"] == collection[i]

            # Cleanup for next collection
            await self.state_manager.redis.flushdb()

    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery in multi-instance activities."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-mi-error-1"
        activity_id = "Activity_1"
        collection = ["A", "B", "C", "D"]

        # Create parallel instances
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection
        token.data["is_parallel"] = True

        instance_tokens = await executor.create_parallel_instances(token)

        # Simulate error in one instance
        error_token = instance_tokens[1]
        error_token.state = TokenState.ERROR
        await self.state_manager.update_token_state(
            instance_id,
            error_token.node_id,
            TokenState.ERROR,
            scope_id=error_token.scope_id,
        )

        # Complete instances before error
        await executor.complete_parallel_instance(instance_tokens[0], len(collection))

        # Verify activity remains incomplete due to error
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        error_tokens = [
            t for t in stored_tokens if t["state"] == TokenState.ERROR.value
        ]
        completed_tokens = [
            t for t in stored_tokens if t["state"] == TokenState.COMPLETED.value
        ]
        assert len(error_tokens) == 1
        assert len(completed_tokens) == 1  # Only instance[0] completed

        # Recover error token and complete
        error_token.state = TokenState.ACTIVE
        await self.state_manager.update_token_state(
            instance_id,
            error_token.node_id,
            TokenState.ACTIVE,
            scope_id=error_token.scope_id,
        )
        await executor.complete_parallel_instance(error_token, len(collection))

        # Complete remaining instances in order
        await executor.complete_parallel_instance(
            instance_tokens[2], len(collection)  # Complete instance C
        )
        final_token = await executor.complete_parallel_instance(
            instance_tokens[3], len(collection)  # Complete instance D
        )

        # Verify activity completed after recovery
        assert final_token.node_id == "Task_1"
        assert final_token.state == TokenState.ACTIVE
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == "Task_1"
