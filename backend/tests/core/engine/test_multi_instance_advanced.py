import asyncio
import logging

import pytest

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.asyncio
class TestAdvancedMultiInstance:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_nested_parallel_multi_instance(self):
        """Test parallel multi-instance activities nested within another parallel multi-instance."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-nested-parallel-mi"
        outer_activity_id = "OuterActivity"
        inner_activity_id = "InnerActivity"
        next_task_id = "Task_1"

        # Outer parallel multi-instance data (departments)
        departments = ["HR", "IT", "Finance"]
        # Inner parallel multi-instance data per department (employees)
        employees = {
            "HR": ["Alice", "Bob"],
            "IT": ["Charlie", "Dave", "Eve"],
            "Finance": ["Frank", "Grace"],
        }

        # Create initial token for outer parallel activity
        outer_token = await executor.create_initial_token(
            instance_id, outer_activity_id
        )
        outer_token.data["collection"] = departments
        outer_token.data["is_parallel"] = True

        # Create parallel instances for departments
        department_tokens = await executor.create_parallel_instances(outer_token)
        assert len(department_tokens) == len(departments)

        logger.debug("Created department tokens:")
        for token in department_tokens:
            logger.debug(
                f"Department token - node_id: {token.node_id}, scope_id: {token.scope_id}"
            )

        # Track all inner instance tokens
        all_inner_tokens = []

        # Create inner parallel instances for each department
        for i, dept_token in enumerate(department_tokens):
            # Create a copy of the department token for inner instances
            inner_token = Token(
                instance_id=dept_token.instance_id,
                node_id=inner_activity_id,
                scope_id=dept_token.scope_id,
                data=dept_token.data.copy(),
            )
            inner_token.data["collection"] = employees[departments[i]]
            inner_token.data["is_parallel"] = True

            inner_tokens = await executor.create_parallel_instances(inner_token)
            assert len(inner_tokens) == len(employees[departments[i]])
            logger.debug(f"\nCreated inner tokens for department {departments[i]}:")
            for token in inner_tokens:
                logger.debug(
                    f"Inner token - node_id: {token.node_id}, scope_id: {token.scope_id}, parent_scope: {token.data.get('parent_scope')}"
                )
            all_inner_tokens.extend(inner_tokens)

        # Complete all inner instances
        logger.debug("\nStarting inner instance completion:")
        for inner_token in all_inner_tokens:
            # Find parent token by matching scope hierarchy
            parent_scope = inner_token.data.get("parent_scope", "")
            dept = departments[
                department_tokens.index(
                    next(t for t in department_tokens if t.scope_id == parent_scope)
                )
            ]
            logger.debug(
                f"\nCompleting inner token - node_id: {inner_token.node_id}, scope_id: {inner_token.scope_id}"
            )
            stored_tokens = await self.state_manager.get_token_positions(instance_id)
            logger.debug("Current tokens in state:")
            for token in stored_tokens:
                logger.debug(
                    f"Token - node_id: {token['node_id']}, scope_id: {token.get('scope_id')}, state: {token.get('state')}"
                )

            await executor.complete_parallel_instance(inner_token, len(employees[dept]))

        # Complete outer instances
        final_token = None
        for dept_token in department_tokens:
            result = await executor.complete_parallel_instance(
                dept_token, len(departments)
            )
            if result:
                final_token = result

        # Verify final state
        assert final_token is not None
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE
        assert final_token.scope_id is None

        # Verify only one token remains
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id

    async def test_conditional_completion(self):
        """Test multi-instance completion based on conditions."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-conditional-mi"
        activity_id = "Activity_1"
        next_task_id = "Task_1"

        # Create initial token
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = ["item1", "item2", "item3", "item4"]
        token.data["is_parallel"] = True
        token.data["completion_condition"] = (
            "count >= 2"  # Complete when 2 instances finish
        )

        # Create parallel instances
        instance_tokens = await executor.create_parallel_instances(token)
        assert len(instance_tokens) == 4

        # Complete first two instances
        completed_count = 0
        final_token = None
        for instance_token in instance_tokens[:2]:
            instance_token.data["count"] = completed_count + 1
            result = await executor.complete_parallel_instance(
                instance_token, len(token.data["collection"])
            )
            completed_count += 1
            if result:
                final_token = result

        # Verify early completion
        assert final_token is not None
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE

        # Verify remaining instances were cleaned up
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(stored_tokens) == 1
        assert stored_tokens[0]["node_id"] == next_task_id

    async def test_dynamic_collection_modification(self):
        """Test handling of dynamic modifications to the collection during execution."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-dynamic-mi"
        activity_id = "Activity_1"
        next_task_id = "Task_1"

        # Initial collection
        collection = ["item1", "item2", "item3"]

        # Create initial token
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection
        token.data["is_parallel"] = False  # Use sequential for dynamic modification

        # Create first sequential instance
        current_token = await executor.create_sequential_instance(token, 0)
        assert current_token.data["item"] == "item1"

        # Add new items to collection
        collection.extend(["item4", "item5"])
        current_token.data["collection"] = collection

        # Complete current instance and create next
        next_token = await executor.complete_sequential_instance(
            current_token, len(collection)
        )
        assert next_token.data["item"] == "item2"
        assert len(next_token.data["collection"]) == 5

        # Complete remaining instances
        while next_token.node_id == activity_id:
            next_token = await executor.complete_sequential_instance(
                next_token, len(collection)
            )

        # Verify final state
        assert next_token.node_id == next_task_id
        assert next_token.state == TokenState.ACTIVE

    async def test_large_collection_performance(self):
        """Test performance with large collections."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-large-mi"
        activity_id = "Activity_1"

        # Test with 500 items
        collection_size = 500
        max_time_per_instance = 0.050  # 50ms requirement

        # Create token with large collection
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = [f"item_{i}" for i in range(collection_size)]
        token.data["is_parallel"] = True

        # Measure instance creation time
        start_time = asyncio.get_event_loop().time()
        instance_tokens = await executor.create_parallel_instances(token)
        end_time = asyncio.get_event_loop().time()

        # Verify performance
        total_time = end_time - start_time
        time_per_instance = total_time / collection_size

        assert time_per_instance <= max_time_per_instance, (
            f"Instance creation took {time_per_instance:.3f}s per instance "
            f"(required: {max_time_per_instance:.3f}s)"
        )
        assert len(instance_tokens) == collection_size

    async def test_concurrent_instance_modifications(self):
        """Test concurrent modifications to different instances."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-concurrent-mi"
        activity_id = "Activity_1"

        # Create initial token
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = ["item1", "item2", "item3"]
        token.data["is_parallel"] = True

        # Create parallel instances
        instance_tokens = await executor.create_parallel_instances(token)

        # Simulate concurrent modifications
        async def modify_instance(token: Token, value: str):
            await self.state_manager.set_variable(
                instance_id=instance_id,
                name="test_var",
                variable=ProcessVariableValue(type="string", value=value),
                scope_id=token.scope_id,
            )

        # Create concurrent tasks
        tasks = [
            modify_instance(instance_tokens[0], "value1"),
            modify_instance(instance_tokens[1], "value2"),
            modify_instance(instance_tokens[2], "value3"),
        ]

        # Run modifications concurrently
        await asyncio.gather(*tasks)

        # Verify each instance has correct value
        for i, token in enumerate(instance_tokens):
            value = await self.state_manager.get_variable(
                instance_id, "test_var", scope_id=token.scope_id
            )
            assert value.value == f"value{i+1}"

    async def test_instance_failure_recovery(self):
        """Test recovery from failed instances."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-failure-mi"
        activity_id = "Activity_1"
        next_task_id = "Task_1"

        # Create initial token
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = ["item1", "item2", "item3"]
        token.data["is_parallel"] = True

        # Create parallel instances
        instance_tokens = await executor.create_parallel_instances(token)

        # Simulate failure in second instance
        failed_token = instance_tokens[1]
        failed_token.state = TokenState.ERROR
        await self.state_manager.update_token_state(
            instance_id,
            failed_token.node_id,
            TokenState.ERROR,
            scope_id=failed_token.scope_id,
        )

        # Complete first instance
        await executor.complete_parallel_instance(
            instance_tokens[0], len(token.data["collection"])
        )

        # Verify activity remains incomplete
        stored_tokens = await self.state_manager.get_token_positions(instance_id)
        error_tokens = [
            t for t in stored_tokens if t["state"] == TokenState.ERROR.value
        ]
        assert len(error_tokens) == 1

        # Recover failed instance
        failed_token.state = TokenState.ACTIVE
        await self.state_manager.update_token_state(
            instance_id,
            failed_token.node_id,
            TokenState.ACTIVE,
            scope_id=failed_token.scope_id,
        )

        # Complete remaining instances
        for instance_token in instance_tokens[1:]:
            result = await executor.complete_parallel_instance(
                instance_token, len(token.data["collection"])
            )
            if result:
                final_token = result

        # Verify successful completion
        assert final_token.node_id == next_task_id
        assert final_token.state == TokenState.ACTIVE

    async def test_complex_variable_scoping(self):
        """Test complex variable scoping in nested multi-instance activities."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-scoping-mi"
        outer_activity_id = "OuterActivity"
        inner_activity_id = "InnerActivity"

        # Create outer token
        outer_token = await executor.create_initial_token(
            instance_id, outer_activity_id
        )
        outer_token.data["collection"] = ["A", "B"]
        outer_token.data["is_parallel"] = True

        # Create outer instances
        outer_tokens = await executor.create_parallel_instances(outer_token)

        # Set variables at different scopes
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="root_var",
            variable=ProcessVariableValue(type="string", value="root"),
        )

        for i, outer_token in enumerate(outer_tokens):
            # Set outer scope variables
            await self.state_manager.set_variable(
                instance_id=instance_id,
                name="outer_var",
                variable=ProcessVariableValue(type="string", value=f"outer_{i}"),
                scope_id=outer_token.scope_id,
            )

            # Create inner instances
            outer_token.node_id = inner_activity_id
            outer_token.data["collection"] = [1, 2]
            outer_token.data["is_parallel"] = True
            inner_tokens = await executor.create_parallel_instances(outer_token)

            # Set inner scope variables
            for j, inner_token in enumerate(inner_tokens):
                await self.state_manager.set_variable(
                    instance_id=instance_id,
                    name="inner_var",
                    variable=ProcessVariableValue(
                        type="string", value=f"inner_{i}_{j}"
                    ),
                    scope_id=inner_token.scope_id,
                )

                # Verify variable access
                root_val = await self.state_manager.get_variable(
                    instance_id, "root_var", scope_id=inner_token.scope_id
                )
                outer_val = await self.state_manager.get_variable(
                    instance_id, "outer_var", scope_id=inner_token.scope_id
                )
                inner_val = await self.state_manager.get_variable(
                    instance_id, "inner_var", scope_id=inner_token.scope_id
                )

                assert root_val.value == "root"
                assert outer_val.value == f"outer_{i}"
                assert inner_val.value == f"inner_{i}_{j}"

    async def test_collection_variable_updates(self):
        """Test updating collection variables during execution."""
        executor = ProcessExecutor(self.state_manager)
        instance_id = "test-collection-vars-mi"
        activity_id = "Activity_1"

        # Initial collection with objects
        collection = [
            {"id": 1, "status": "pending"},
            {"id": 2, "status": "pending"},
            {"id": 3, "status": "pending"},
        ]

        # Create initial token
        token = await executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection
        token.data["is_parallel"] = True

        # Create parallel instances
        instance_tokens = await executor.create_parallel_instances(token)

        # Update collection items in different instances
        for i, instance_token in enumerate(instance_tokens):
            # Store updated item in instance scope
            collection[i]["status"] = "completed"
            await self.state_manager.set_variable(
                instance_id=instance_id,
                name="item",
                variable=ProcessVariableValue(type="json", value=collection[i]),
                scope_id=instance_token.scope_id,
            )

        # Verify updates in each instance scope
        for i, instance_token in enumerate(instance_tokens):
            item = await self.state_manager.get_variable(
                instance_id, "item", scope_id=instance_token.scope_id
            )
            assert item.value["status"] == "completed"
            assert item.value["id"] == i + 1
