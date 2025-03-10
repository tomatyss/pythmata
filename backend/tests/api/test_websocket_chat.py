"""Tests for WebSocket chat functionality."""

import asyncio
import json
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.routes.websockets import chat_websocket, process_chat_message
from pythmata.core.websockets.chat_manager import chat_manager
from pythmata.models.chat import ChatMessage, ChatSession


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_json = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_chat_websocket_connect(mock_websocket, mock_db):
    """Test WebSocket connection."""
    # Mock chat_manager.connect
    with patch.object(chat_manager, 'connect', AsyncMock()) as mock_connect:
        # Simulate WebSocketDisconnect to exit the loop
        mock_websocket.receive_json.side_effect = WebSocketDisconnect()
        
        # Call the WebSocket endpoint
        client_id = str(uuid.uuid4())
        await chat_websocket(mock_websocket, client_id, mock_db)
        
        # Verify chat_manager.connect was called
        mock_connect.assert_called_once_with(mock_websocket, client_id)


@pytest.mark.asyncio
async def test_chat_websocket_disconnect(mock_websocket, mock_db):
    """Test WebSocket disconnection."""
    # Mock chat_manager methods
    with patch.object(chat_manager, 'connect', AsyncMock()) as mock_connect, \
         patch.object(chat_manager, 'disconnect') as mock_disconnect:
        # Simulate WebSocketDisconnect to exit the loop
        mock_websocket.receive_json.side_effect = WebSocketDisconnect()
        
        # Call the WebSocket endpoint
        client_id = str(uuid.uuid4())
        await chat_websocket(mock_websocket, client_id, mock_db)
        
        # Verify chat_manager.disconnect was called
        mock_disconnect.assert_called_once_with(client_id)


@pytest.mark.asyncio
async def test_process_chat_message_unknown_type(mock_db):
    """Test processing a message with unknown type."""
    # Mock logger.warning
    with patch('pythmata.api.routes.websockets.logger.warning') as mock_warning:
        # Call process_chat_message with unknown message type
        client_id = str(uuid.uuid4())
        data = {"type": "unknown_type", "content": {}}
        await process_chat_message(client_id, data, mock_db)
        
        # Verify logger.warning was called
        mock_warning.assert_called_once()


@pytest.mark.asyncio
async def test_handle_chat_message(mock_db):
    """Test handling a chat message."""
    # Mock LlmService and chat_manager methods
    with patch('pythmata.api.routes.websockets.LlmService') as MockLlmService, \
         patch.object(chat_manager, 'send_personal_message', AsyncMock()) as mock_send, \
         patch.object(chat_manager, 'join_session', AsyncMock()) as mock_join:
        # Setup mock LLM service
        mock_llm = AsyncMock()
        mock_llm.stream_chat_completion = AsyncMock(return_value="Test response")
        MockLlmService.return_value = mock_llm
        
        # Mock db.execute result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Call handle_chat_message
        from pythmata.api.routes.websockets import handle_chat_message
        client_id = str(uuid.uuid4())
        process_id = str(uuid.uuid4())
        data = {
            "content": "Test message",
            "processId": process_id,
            "currentXml": "<xml></xml>"
        }
        await handle_chat_message(client_id, data, mock_db)
        
        # Verify LLM service was called
        mock_llm.stream_chat_completion.assert_called_once()
        
        # Verify chat_manager.send_personal_message was called
        assert mock_send.call_count >= 2  # At least message_received and message_complete
        
        # Verify db.commit was called (for storing messages)
        assert mock_db.commit.call_count >= 2  # For user message and assistant message


@pytest.mark.asyncio
async def test_handle_join_session(mock_db):
    """Test handling a join session message."""
    # Mock chat_manager.join_session
    with patch.object(chat_manager, 'join_session', AsyncMock()) as mock_join:
        # Call handle_join_session
        from pythmata.api.routes.websockets import handle_join_session
        client_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        data = {"sessionId": session_id}
        await handle_join_session(client_id, data)
        
        # Verify chat_manager.join_session was called
        mock_join.assert_called_once()


@pytest.mark.asyncio
async def test_handle_typing_indicator(mock_db):
    """Test handling a typing indicator message."""
    # Mock chat_manager.broadcast_to_session
    with patch.object(chat_manager, 'broadcast_to_session', AsyncMock()) as mock_broadcast:
        # Call handle_typing_indicator
        from pythmata.api.routes.websockets import handle_typing_indicator
        client_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        data = {"sessionId": session_id, "isTyping": True}
        await handle_typing_indicator(client_id, data)
        
        # Verify chat_manager.broadcast_to_session was called
        mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_handle_leave_session(mock_db):
    """Test handling a leave session message."""
    # Mock chat_manager.leave_session
    with patch.object(chat_manager, 'leave_session', AsyncMock()) as mock_leave:
        # Call handle_leave_session
        from pythmata.api.routes.websockets import handle_leave_session
        client_id = str(uuid.uuid4())
        await handle_leave_session(client_id)
        
        # Verify chat_manager.leave_session was called
        mock_leave.assert_called_once_with(client_id)
