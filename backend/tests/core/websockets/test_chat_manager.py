"""Tests for WebSocket chat manager."""

import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket
from pydantic import BaseModel

from pythmata.core.websockets.chat_manager import (
    ChatConnectionManager,
    ChatWebSocketMessage,
)


@pytest.fixture
def chat_manager():
    """Create a new chat manager for each test."""
    return ChatConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.send_json = AsyncMock()
    return websocket


@pytest.mark.asyncio
async def test_connect(chat_manager, mock_websocket):
    """Test connecting a client."""
    client_id = "test-client"

    # Connect the client
    await chat_manager.connect(mock_websocket, client_id)

    # Verify the client is connected
    assert client_id in chat_manager.active_connections
    assert chat_manager.active_connections[client_id] == mock_websocket

    # Verify the WebSocket was accepted
    mock_websocket.accept.assert_called_once()


def test_disconnect(chat_manager, mock_websocket):
    """Test disconnecting a client."""
    client_id = "test-client"
    session_id = uuid.uuid4()

    # Setup: Connect the client and associate with a session
    chat_manager.active_connections[client_id] = mock_websocket
    chat_manager.session_clients[session_id] = {client_id}
    chat_manager.client_sessions[client_id] = session_id

    # Disconnect the client
    chat_manager.disconnect(client_id)

    # Verify the client is disconnected
    assert client_id not in chat_manager.active_connections
    assert client_id not in chat_manager.client_sessions
    assert session_id not in chat_manager.session_clients


@pytest.mark.asyncio
async def test_join_session(chat_manager, mock_websocket):
    """Test joining a session."""
    client_id = "test-client"
    session_id = uuid.uuid4()

    # Setup: Connect the client
    chat_manager.active_connections[client_id] = mock_websocket

    # Join the session
    with patch.object(
        chat_manager, "broadcast_to_session", AsyncMock()
    ) as mock_broadcast:
        await chat_manager.join_session(client_id, session_id)

        # Verify the client is associated with the session
        assert session_id in chat_manager.session_clients
        assert client_id in chat_manager.session_clients[session_id]
        assert chat_manager.client_sessions[client_id] == session_id

        # Verify broadcast was called
        mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_leave_session(chat_manager, mock_websocket):
    """Test leaving a session."""
    client_id = "test-client"
    session_id = uuid.uuid4()

    # Setup: Connect the client and associate with a session
    chat_manager.active_connections[client_id] = mock_websocket
    chat_manager.session_clients[session_id] = {client_id}
    chat_manager.client_sessions[client_id] = session_id

    # Leave the session
    with patch.object(
        chat_manager, "broadcast_to_session", AsyncMock()
    ) as mock_broadcast:
        await chat_manager.leave_session(client_id)

        # Verify the client is no longer associated with the session
        assert client_id not in chat_manager.client_sessions
        assert session_id not in chat_manager.session_clients

        # Verify broadcast was called
        mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_send_personal_message(chat_manager, mock_websocket):
    """Test sending a personal message."""
    client_id = "test-client"

    # Setup: Connect the client
    chat_manager.active_connections[client_id] = mock_websocket

    # Send a personal message
    message_type = "test_type"
    content = {"key": "value"}
    await chat_manager.send_personal_message(client_id, message_type, content)

    # Verify the message was sent
    mock_websocket.send_json.assert_called_once()

    # Verify the message format
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == message_type
    assert call_args["content"] == content


@pytest.mark.asyncio
async def test_send_personal_message_client_not_found(chat_manager, mock_websocket):
    """Test sending a personal message to a non-existent client."""
    client_id = "test-client"

    # Send a personal message to a non-existent client
    with patch("pythmata.core.websockets.chat_manager.logger.warning") as mock_warning:
        await chat_manager.send_personal_message(client_id, "test_type", {})

        # Verify warning was logged
        mock_warning.assert_called_once()

        # Verify the message was not sent
        mock_websocket.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_send_personal_message_exception(chat_manager, mock_websocket):
    """Test handling an exception when sending a personal message."""
    client_id = "test-client"

    # Setup: Connect the client
    chat_manager.active_connections[client_id] = mock_websocket

    # Setup: Mock send_json to raise an exception
    mock_websocket.send_json.side_effect = Exception("Test exception")

    # Send a personal message
    with (
        patch("pythmata.core.websockets.chat_manager.logger.error") as mock_error,
        patch.object(chat_manager, "disconnect") as mock_disconnect,
    ):
        await chat_manager.send_personal_message(client_id, "test_type", {})

        # Verify error was logged
        mock_error.assert_called_once()

        # Verify the client was disconnected
        mock_disconnect.assert_called_once_with(client_id)


@pytest.mark.asyncio
async def test_broadcast_to_session(chat_manager, mock_websocket):
    """Test broadcasting to a session."""
    client_id = "test-client"
    session_id = uuid.uuid4()

    # Setup: Connect the client and associate with a session
    chat_manager.active_connections[client_id] = mock_websocket
    chat_manager.session_clients[session_id] = {client_id}
    chat_manager.client_sessions[client_id] = session_id

    # Broadcast to the session
    message_type = "test_type"
    content = {"key": "value"}
    await chat_manager.broadcast_to_session(session_id, message_type, content)

    # Verify the message was sent
    mock_websocket.send_json.assert_called_once()

    # Verify the message format
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == message_type
    assert call_args["content"] == content


@pytest.mark.asyncio
async def test_broadcast_to_session_exclude_client(chat_manager, mock_websocket):
    """Test broadcasting to a session with client exclusion."""
    client_id1 = "test-client-1"
    client_id2 = "test-client-2"
    session_id = uuid.uuid4()

    # Setup: Connect two clients and associate with a session
    mock_websocket1 = AsyncMock(spec=WebSocket)
    mock_websocket2 = AsyncMock(spec=WebSocket)

    chat_manager.active_connections[client_id1] = mock_websocket1
    chat_manager.active_connections[client_id2] = mock_websocket2
    chat_manager.session_clients[session_id] = {client_id1, client_id2}
    chat_manager.client_sessions[client_id1] = session_id
    chat_manager.client_sessions[client_id2] = session_id

    # Broadcast to the session, excluding client1
    await chat_manager.broadcast_to_session(
        session_id, "test_type", {}, exclude_client=client_id1
    )

    # Verify the message was not sent to client1
    mock_websocket1.send_json.assert_not_called()

    # Verify the message was sent to client2
    mock_websocket2.send_json.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_to_session_not_found(chat_manager, mock_websocket):
    """Test broadcasting to a non-existent session."""
    session_id = uuid.uuid4()

    # Broadcast to a non-existent session
    with patch("pythmata.core.websockets.chat_manager.logger.warning") as mock_warning:
        await chat_manager.broadcast_to_session(session_id, "test_type", {})

        # Verify warning was logged
        mock_warning.assert_called_once()

        # Verify no messages were sent
        mock_websocket.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_to_session_exception(chat_manager, mock_websocket):
    """Test handling an exception when broadcasting to a session."""
    client_id = "test-client"
    session_id = uuid.uuid4()

    # Setup: Connect the client and associate with a session
    chat_manager.active_connections[client_id] = mock_websocket
    chat_manager.session_clients[session_id] = {client_id}
    chat_manager.client_sessions[client_id] = session_id

    # Setup: Mock send_json to raise an exception
    mock_websocket.send_json.side_effect = Exception("Test exception")

    # Broadcast to the session
    with (
        patch("pythmata.core.websockets.chat_manager.logger.error") as mock_error,
        patch.object(chat_manager, "disconnect") as mock_disconnect,
    ):
        await chat_manager.broadcast_to_session(session_id, "test_type", {})

        # Verify error was logged
        mock_error.assert_called_once()

        # Verify the client was disconnected
        mock_disconnect.assert_called_once_with(client_id)


def test_chat_websocket_message():
    """Test ChatWebSocketMessage model."""
    message_type = "test_type"
    content = {"key": "value"}

    # Create a message
    message = ChatWebSocketMessage(type=message_type, content=content)

    # Verify the message attributes
    assert message.type == message_type
    assert message.content == content

    # Verify the message can be serialized
    serialized = message.model_dump()
    assert serialized["type"] == message_type
    assert serialized["content"] == content
