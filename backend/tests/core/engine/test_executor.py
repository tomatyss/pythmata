from uuid import UUID

import pytest

from pythmata.api.schemas.process.variables import ProcessVariableValue
from pythmata.core.engine.token import TokenState
from tests.core.engine.base import BaseEngineTest
from tests.core.testing import assert_token_state


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

    async def test_variable_passing_between_nodes(self):
        """Test passing variables between nodes in a process."""
        # Create a simple process with a few nodes
        process_graph = self.create_sequence_flow(
            start_id="Start_1", task_id="Task_1", end_id="End_1"
        )

        # Create a unique instance ID for this test
        instance_id = "test-variables-1"

        # Create initial token and set variables
        token = await self.executor.create_initial_token(instance_id, "Start_1")

        # Set initial variables
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="value",
            variable=ProcessVariableValue(type="integer", value=5),
        )
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="message",
            variable=ProcessVariableValue(type="string", value="Initial message"),
        )

        # Move token to task and modify variables
        token = await self.executor.move_token(token, "Task_1")

        # Simulate task execution - double the value
        current_value = (
            await self.state_manager.get_variable(instance_id, "value")
        ).value
        new_value = current_value * 2
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="value",
            variable=ProcessVariableValue(type="integer", value=new_value),
        )
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="path_taken",
            variable=ProcessVariableValue(type="string", value="low"),
        )

        # Move token to end event
        token = await self.executor.move_token(token, "End_1")

        # Create summary variable
        final_value = (
            await self.state_manager.get_variable(instance_id, "value")
        ).value
        path_taken = (
            await self.state_manager.get_variable(instance_id, "path_taken")
        ).value
        message = (await self.state_manager.get_variable(instance_id, "message")).value

        summary = f"Final value: {final_value}, Path taken: {path_taken}, Original message: {message}"
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="summary",
            variable=ProcessVariableValue(type="string", value=summary),
        )

        # Consume token at end event
        await self.executor.consume_token(token)

        # Verify process completed (no active tokens)
        tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(tokens) == 0

        # Get the variables to verify they were passed correctly
        variables = await self.state_manager.get_variables(instance_id)

        # The initial value was 5, which was doubled to 10
        assert variables["value"].value == 10
        assert variables["path_taken"].value == "low"
        assert variables["message"].value == "Initial message"

        # Verify the summary variable was created
        expected_summary = (
            "Final value: 10, Path taken: low, Original message: Initial message"
        )
        assert variables["summary"].value == expected_summary

    async def test_variable_passing_alternate_path(self):
        """Test passing variables between nodes using an alternate path."""
        # Create a simple process with a few nodes
        process_graph = self.create_sequence_flow(
            start_id="Start_1", task_id="Task_1", end_id="End_1"
        )

        # Create a unique instance ID for this test
        instance_id = "test-variables-high-path"

        # Create initial token and set variables
        token = await self.executor.create_initial_token(instance_id, "Start_1")

        # Set initial variables
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="value",
            variable=ProcessVariableValue(type="integer", value=15),
        )
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="message",
            variable=ProcessVariableValue(type="string", value="Initial message"),
        )

        # Move token to task and modify variables
        token = await self.executor.move_token(token, "Task_1")

        # Simulate task execution - increment the value by 10
        current_value = (
            await self.state_manager.get_variable(instance_id, "value")
        ).value
        new_value = current_value + 10
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="value",
            variable=ProcessVariableValue(type="integer", value=new_value),
        )
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="path_taken",
            variable=ProcessVariableValue(type="string", value="high"),
        )

        # Move token to end event
        token = await self.executor.move_token(token, "End_1")

        # Create summary variable
        final_value = (
            await self.state_manager.get_variable(instance_id, "value")
        ).value
        path_taken = (
            await self.state_manager.get_variable(instance_id, "path_taken")
        ).value
        message = (await self.state_manager.get_variable(instance_id, "message")).value

        summary = f"Final value: {final_value}, Path taken: {path_taken}, Original message: {message}"
        await self.state_manager.set_variable(
            instance_id=instance_id,
            name="summary",
            variable=ProcessVariableValue(type="string", value=summary),
        )

        # Consume token at end event
        await self.executor.consume_token(token)

        # Verify process completed (no active tokens)
        tokens = await self.state_manager.get_token_positions(instance_id)
        assert len(tokens) == 0

        # Get the variables to verify they were passed correctly
        variables = await self.state_manager.get_variables(instance_id)

        # The initial value was 15, which was incremented by 10 to 25
        assert variables["value"].value == 25
        assert variables["path_taken"].value == "high"
        assert variables["message"].value == "Initial message"

        # Verify the summary variable was created
        expected_summary = (
            "Final value: 25, Path taken: high, Original message: Initial message"
        )
        assert variables["summary"].value == expected_summary
