from asyncio import TimeoutError
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from pythmata.core.engine.events.message import MessageEvent, MessageTimeoutError
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


@pytest.fixture
def state_manager():
    mock = Mock(spec=MockStateManager)
    mock.set_message_subscription = AsyncMock()
    mock.wait_for_message = AsyncMock()
    mock.remove_message_subscription = AsyncMock()
    return mock


@pytest.fixture
def token():
    return Token(
        instance_id="instance1",
        node_id="node1",
        data={},
        token_id=UUID("12345678-1234-5678-1234-567812345678"),
    )


async def test_basic_message_event(state_manager, token):
    """Test basic message event creation and execution"""
    # Arrange
    message_event = MessageEvent(
        event_id="message1", message_name="test_message", state_manager=state_manager
    )

    # Mock state manager methods
    state_manager.wait_for_message.return_value = {"payload": {"data": "test"}}

    # Act
    result_token = await message_event.execute(token)

    # Assert
    assert result_token.data.get("message_payload") == {"data": "test"}
    state_manager.set_message_subscription.assert_called_once_with(
        "test_message", token.instance_id, token.node_id, correlation_value=None
    )
    state_manager.wait_for_message.assert_called_once_with(
        "test_message", token.instance_id, token.node_id, correlation_value=None
    )
    state_manager.remove_message_subscription.assert_called_once_with(
        "test_message", token.instance_id, token.node_id
    )


async def test_message_correlation(state_manager):
    """Test message correlation with process variables"""
    # Arrange
    token = Token(
        instance_id="instance1",
        node_id="node1",
        data={"order_id": "12345"},
        token_id=UUID("12345678-1234-5678-1234-567812345678"),
    )

    message_event = MessageEvent(
        event_id="message1",
        message_name="order_response",
        state_manager=state_manager,
        correlation_key="order_id",
    )

    # Mock state manager methods
    state_manager.wait_for_message.return_value = {
        "payload": {"status": "approved"},
        "correlation_key": "12345",
    }

    # Act
    result_token = await message_event.execute(token)

    # Assert
    assert result_token.data.get("message_payload") == {"status": "approved"}
    state_manager.set_message_subscription.assert_called_once_with(
        "order_response", token.instance_id, token.node_id, correlation_value="12345"
    )
    state_manager.wait_for_message.assert_called_once_with(
        "order_response", token.instance_id, token.node_id, correlation_value="12345"
    )
    state_manager.remove_message_subscription.assert_called_once_with(
        "order_response", token.instance_id, token.node_id
    )


async def test_missing_correlation_key(state_manager, token):
    """Test error handling when correlation key is missing from token data"""
    # Arrange
    message_event = MessageEvent(
        event_id="message1",
        message_name="order_response",
        state_manager=state_manager,
        correlation_key="order_id",  # Key not present in token data
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await message_event.execute(token)

    assert str(exc_info.value) == "Correlation key 'order_id' not found in token data"
    state_manager.set_message_subscription.assert_not_called()
    state_manager.wait_for_message.assert_not_called()
    state_manager.remove_message_subscription.assert_not_called()


async def test_message_timeout(state_manager, token):
    """Test handling of message timeout"""
    # Arrange
    message_event = MessageEvent(
        event_id="message1",
        message_name="test_message",
        state_manager=state_manager,
        timeout=5,  # 5 second timeout
    )

    # Mock timeout behavior
    state_manager.wait_for_message.side_effect = TimeoutError()

    # Act & Assert
    with pytest.raises(MessageTimeoutError) as exc_info:
        await message_event.execute(token)

    assert str(exc_info.value) == "Message 'test_message' not received within 5 seconds"
    state_manager.set_message_subscription.assert_called_once_with(
        "test_message", token.instance_id, token.node_id, correlation_value=None
    )
    state_manager.wait_for_message.assert_called_once_with(
        "test_message", token.instance_id, token.node_id, correlation_value=None
    )
    state_manager.remove_message_subscription.assert_called_once_with(
        "test_message", token.instance_id, token.node_id
    )


async def test_subscription_cleanup_on_error(state_manager, token):
    """Test subscription cleanup when an unexpected error occurs"""
    # Arrange
    message_event = MessageEvent(
        event_id="message1", message_name="test_message", state_manager=state_manager
    )

    # Mock error behavior
    error_message = "Unexpected database error"
    state_manager.wait_for_message.side_effect = Exception(error_message)

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await message_event.execute(token)

    assert str(exc_info.value) == error_message
    state_manager.set_message_subscription.assert_called_once_with(
        "test_message", token.instance_id, token.node_id, correlation_value=None
    )
    state_manager.wait_for_message.assert_called_once_with(
        "test_message", token.instance_id, token.node_id, correlation_value=None
    )
    state_manager.remove_message_subscription.assert_called_once_with(
        "test_message", token.instance_id, token.node_id
    )
