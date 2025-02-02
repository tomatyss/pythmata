from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from pythmata.core.engine.events.signal import SignalEvent
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager


class MockStateManager:
    """Mock state manager with signal subscription methods"""

    async def set_signal_subscription(self, *args, **kwargs):
        pass

    async def wait_for_signal(self, *args, **kwargs):
        pass

    async def remove_signal_subscription(self, *args, **kwargs):
        pass


@pytest.fixture
def state_manager():
    mock = Mock(spec=MockStateManager)
    mock.set_signal_subscription = AsyncMock()
    mock.wait_for_signal = AsyncMock()
    mock.remove_signal_subscription = AsyncMock()
    return mock


@pytest.fixture
def token():
    return Token(
        instance_id="instance1",
        node_id="node1",
        data={},
        token_id=UUID("12345678-1234-5678-1234-567812345678"),
    )


async def test_basic_signal_event(state_manager, token):
    """Test basic signal event creation and execution"""
    # Arrange
    signal_event = SignalEvent(
        event_id="signal1", signal_name="test_signal", state_manager=state_manager
    )

    # Mock state manager methods
    state_manager.wait_for_signal.return_value = {"payload": {"data": "test"}}

    # Act
    result_token = await signal_event.execute(token)

    # Assert
    assert result_token.data.get("signal_payload") == {"data": "test"}
    state_manager.set_signal_subscription.assert_called_once_with(
        "test_signal", token.instance_id, token.node_id
    )
    state_manager.wait_for_signal.assert_called_once_with(
        "test_signal", token.instance_id, token.node_id
    )
    state_manager.remove_signal_subscription.assert_called_once_with(
        "test_signal", token.instance_id, token.node_id
    )


async def test_multiple_signal_receivers(state_manager):
    """Test signal broadcast to multiple process instances"""
    # Arrange
    tokens = [
        Token(
            instance_id=f"instance{i}",
            node_id=f"node{i}",
            data={},
            token_id=UUID(f"12345678-1234-5678-1234-56781234567{i}"),
        )
        for i in range(3)
    ]

    signal_events = [
        SignalEvent(
            event_id=f"signal{i}",
            signal_name="test_signal",
            state_manager=state_manager,
        )
        for i in range(3)
    ]

    # Mock state manager methods with same payload for all receivers
    signal_payload = {"payload": {"broadcast_data": "test"}}
    state_manager.wait_for_signal.return_value = signal_payload

    # Act
    results = []
    for token, event in zip(tokens, signal_events):
        results.append(await event.execute(token))

    # Assert
    # Verify each token received the signal
    for result_token in results:
        assert result_token.data.get("signal_payload") == signal_payload["payload"]

    # Verify subscriptions were managed for each instance
    assert state_manager.set_signal_subscription.call_count == 3
    assert state_manager.wait_for_signal.call_count == 3
    assert state_manager.remove_signal_subscription.call_count == 3

    # Verify correct subscription management for each instance
    for i, token in enumerate(tokens):
        state_manager.set_signal_subscription.assert_any_call(
            "test_signal", token.instance_id, token.node_id
        )
        state_manager.wait_for_signal.assert_any_call(
            "test_signal", token.instance_id, token.node_id
        )
        state_manager.remove_signal_subscription.assert_any_call(
            "test_signal", token.instance_id, token.node_id
        )


async def test_subscription_cleanup_on_error(state_manager, token):
    """Test subscription cleanup when an unexpected error occurs"""
    # Arrange
    signal_event = SignalEvent(
        event_id="signal1", signal_name="test_signal", state_manager=state_manager
    )

    # Mock error behavior
    error_message = "Unexpected error during signal handling"
    state_manager.wait_for_signal.side_effect = Exception(error_message)

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await signal_event.execute(token)

    assert str(exc_info.value) == error_message

    # Verify subscription was set and cleaned up despite error
    state_manager.set_signal_subscription.assert_called_once_with(
        "test_signal", token.instance_id, token.node_id
    )
    state_manager.wait_for_signal.assert_called_once_with(
        "test_signal", token.instance_id, token.node_id
    )
    state_manager.remove_signal_subscription.assert_called_once_with(
        "test_signal", token.instance_id, token.node_id
    )


async def test_signal_payload_types(state_manager, token):
    """Test handling of different signal payload data types"""
    # Arrange
    signal_event = SignalEvent(
        event_id="signal1", signal_name="test_signal", state_manager=state_manager
    )

    # Test different payload data types
    test_payloads = [
        # String
        {"payload": {"data": "test string"}},
        # Number
        {"payload": {"data": 42}},
        # Boolean
        {"payload": {"data": True}},
        # List
        {"payload": {"data": [1, "two", False]}},
        # Nested dictionary
        {"payload": {"data": {"nested": {"value": 123}}}},
        # Mixed types
        {
            "payload": {
                "string_data": "test",
                "number_data": 42,
                "boolean_data": True,
                "list_data": [1, 2, 3],
                "dict_data": {"key": "value"},
            }
        },
    ]

    # Act & Assert
    for payload in test_payloads:
        # Set mock return value for this iteration
        state_manager.wait_for_signal.return_value = payload

        # Execute signal event
        result_token = await signal_event.execute(token)

        # Verify payload was correctly stored in token
        assert result_token.data.get("signal_payload") == payload["payload"]


async def test_invalid_signal_payload(state_manager, token):
    """Test handling of invalid signal payload format"""
    # Arrange
    signal_event = SignalEvent(
        event_id="signal1", signal_name="test_signal", state_manager=state_manager
    )

    # Test cases with invalid payload formats
    invalid_payloads = [
        None,  # Missing payload
        {},  # Empty payload
        {"wrong_key": "data"},  # Missing payload key
        {"payload": None},  # None payload
    ]

    # Act & Assert
    for invalid_payload in invalid_payloads:
        state_manager.wait_for_signal.return_value = invalid_payload

        with pytest.raises(ValueError) as exc_info:
            await signal_event.execute(token)

        assert "Invalid signal payload format" in str(exc_info.value)

        # Verify cleanup still occurs
        state_manager.remove_signal_subscription.assert_called_with(
            "test_signal", token.instance_id, token.node_id
        )
