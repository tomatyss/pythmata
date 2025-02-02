from unittest.mock import AsyncMock, Mock

import pytest

from pythmata.core.engine.events import MessageBoundaryEvent
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager


class MockStateManager:
    """Mock state manager with message subscription methods"""

    async def set_message_subscription(self, *args, **kwargs):
        pass

    async def wait_for_message(self, *args, **kwargs):
        pass

    async def remove_message_subscription(self, *args, **kwargs):
        pass


class TestMessageBoundaryEvents:
    @pytest.fixture
    def state_manager(self):
        mock = Mock(spec=MockStateManager)
        mock.set_message_subscription = AsyncMock()
        mock.wait_for_message = AsyncMock()
        mock.remove_message_subscription = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_basic_message_boundary_event(self, state_manager):
        """Test basic message boundary event functionality"""
        # Setup
        task_id = "task_1"
        event_id = "message_boundary_1"
        message_name = "test_message"
        instance_id = "test_instance"

        # Create token representing active task
        task_token = Token(
            instance_id=instance_id, node_id=task_id, state=TokenState.ACTIVE, data={}
        )

        # Create message boundary event
        message_boundary = MessageBoundaryEvent(
            event_id=event_id,
            attached_to_id=task_id,
            message_name=message_name,
            state_manager=state_manager,
        )

        # Setup mock response
        message_data = {"key": "value"}
        state_manager.wait_for_message.return_value = {"payload": message_data}

        # Execute boundary event
        result_token = await message_boundary.execute(task_token)

        # Verify results
        assert result_token.instance_id == instance_id
        assert result_token.node_id == event_id
        assert result_token.state == TokenState.ACTIVE
        assert result_token.data["message_payload"] == message_data

        # Verify state manager interactions
        state_manager.set_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=None
        )
        state_manager.wait_for_message.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=None
        )
        state_manager.remove_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id
        )

    @pytest.mark.asyncio
    async def test_interrupting_message_boundary_event(self, state_manager):
        """Test interrupting message boundary event behavior"""
        task_id = "task_1"
        event_id = "message_boundary_1"
        message_name = "test_message"
        instance_id = "test_instance"

        task_token = Token(
            instance_id=instance_id,
            node_id=task_id,
            state=TokenState.ACTIVE,
            data={"task_data": "important"},
        )

        message_boundary = MessageBoundaryEvent(
            event_id=event_id,
            attached_to_id=task_id,
            message_name=message_name,
            state_manager=state_manager,
            is_interrupting=True,
        )

        # Setup mock response
        message_data = {"interrupt": "true"}
        state_manager.wait_for_message.return_value = {"payload": message_data}

        # Execute boundary event
        result_token = await message_boundary.execute(task_token)

        # Verify results
        assert result_token.instance_id == instance_id
        assert result_token.node_id == event_id
        assert result_token.state == TokenState.ACTIVE
        # Verify original task data is preserved
        assert result_token.data["task_data"] == "important"
        assert result_token.data["message_payload"] == message_data
        assert (
            task_token.state == TokenState.COMPLETED
        )  # Task should be completed for interrupting events

        # Verify state manager interactions
        state_manager.set_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=None
        )
        state_manager.wait_for_message.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=None
        )
        state_manager.remove_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id
        )

    @pytest.mark.asyncio
    async def test_non_interrupting_message_boundary_event(self, state_manager):
        """Test non-interrupting message boundary event behavior"""
        task_id = "task_1"
        event_id = "message_boundary_1"
        message_name = "test_message"
        instance_id = "test_instance"

        task_token = Token(
            instance_id=instance_id,
            node_id=task_id,
            state=TokenState.ACTIVE,
            data={"task_data": "continues"},
        )

        message_boundary = MessageBoundaryEvent(
            event_id=event_id,
            attached_to_id=task_id,
            message_name=message_name,
            state_manager=state_manager,
            is_interrupting=False,
        )

        # Setup mock response
        message_data = {"notify": "true"}
        state_manager.wait_for_message.return_value = {"payload": message_data}

        # Execute boundary event
        result_token = await message_boundary.execute(task_token)

        # Verify results
        assert result_token.instance_id == instance_id
        assert result_token.node_id == event_id
        assert result_token.state == TokenState.ACTIVE
        # Verify original task data is preserved
        assert result_token.data["task_data"] == "continues"
        assert result_token.data["message_payload"] == message_data
        # Original task token should still be active
        assert task_token.state == TokenState.ACTIVE

        # Verify state manager interactions
        state_manager.set_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=None
        )
        state_manager.wait_for_message.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=None
        )
        state_manager.remove_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id
        )

    @pytest.mark.asyncio
    async def test_message_boundary_event_with_correlation(self, state_manager):
        """Test message boundary event with correlation key"""
        task_id = "task_1"
        event_id = "message_boundary_1"
        message_name = "test_message"
        instance_id = "test_instance"
        correlation_key = "order_id"
        correlation_value = "12345"

        task_token = Token(
            instance_id=instance_id,
            node_id=task_id,
            state=TokenState.ACTIVE,
            data={correlation_key: correlation_value},
        )

        message_boundary = MessageBoundaryEvent(
            event_id=event_id,
            attached_to_id=task_id,
            message_name=message_name,
            state_manager=state_manager,
            correlation_key=correlation_key,
        )

        # Setup mock response
        message_data = {"status": "completed"}
        state_manager.wait_for_message.return_value = {"payload": message_data}

        # Execute boundary event
        result_token = await message_boundary.execute(task_token)

        # Verify results
        assert result_token.instance_id == instance_id
        assert result_token.node_id == event_id
        assert result_token.state == TokenState.ACTIVE
        assert result_token.data["message_payload"] == message_data

        # Verify state manager interactions
        state_manager.set_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=correlation_value
        )
        state_manager.wait_for_message.assert_called_once_with(
            message_name, instance_id, task_id, correlation_value=correlation_value
        )
        state_manager.remove_message_subscription.assert_called_once_with(
            message_name, instance_id, task_id
        )
