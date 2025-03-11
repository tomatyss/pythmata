"""Tests for LLM service streaming functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythmata.core.llm.service import LlmService
from pythmata.core.websockets.chat_manager import chat_manager


@pytest.fixture
def mock_aisuite_client():
    """Create a mock AISuite client."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client


@pytest.fixture
def llm_service(mock_aisuite_client):
    """Create an LLM service with a mock client."""
    with patch("aisuite.Client", return_value=mock_aisuite_client):
        service = LlmService()
        service.client = mock_aisuite_client
        return service


@pytest.mark.asyncio
async def test_stream_chat_completion(llm_service, mock_aisuite_client):
    """Test streaming chat completion."""
    # Setup mock response chunks
    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [MagicMock()]
    mock_chunk1.choices[0].delta.content = "Hello"

    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [MagicMock()]
    mock_chunk2.choices[0].delta.content = " world"

    mock_chunk3 = MagicMock()
    mock_chunk3.choices = [MagicMock()]
    mock_chunk3.choices[0].delta.content = "!"

    # Configure mock to return chunks
    mock_aisuite_client.chat.completions.create.return_value = [
        mock_chunk1,
        mock_chunk2,
        mock_chunk3,
    ]

    # Mock chat_manager.send_personal_message
    with patch.object(chat_manager, "send_personal_message", AsyncMock()) as mock_send:
        # Call the method
        client_id = "test-client"
        messages = [{"role": "user", "content": "Test message"}]
        result = await llm_service.stream_chat_completion(messages, client_id)

        # Verify the result
        assert result == "Hello world!"

        # Verify chat_manager.send_personal_message was called for each chunk
        assert mock_send.call_count == 3

        # Verify the first call
        mock_send.assert_any_call(client_id, "token", {"content": "Hello"})

        # Verify the second call
        mock_send.assert_any_call(client_id, "token", {"content": " world"})

        # Verify the third call
        mock_send.assert_any_call(client_id, "token", {"content": "!"})


@pytest.mark.asyncio
async def test_stream_chat_completion_error(llm_service, mock_aisuite_client):
    """Test error handling in streaming chat completion."""
    # Configure mock to raise an exception
    mock_aisuite_client.chat.completions.create.side_effect = Exception("Test error")

    # Call the method and expect an exception
    client_id = "test-client"
    messages = [{"role": "user", "content": "Test message"}]

    with pytest.raises(Exception):
        await llm_service.stream_chat_completion(messages, client_id)


@pytest.mark.asyncio
async def test_stream_chat_completion_empty_response(llm_service, mock_aisuite_client):
    """Test streaming chat completion with empty response."""
    # Setup mock response chunks with empty content
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = None

    # Configure mock to return chunks
    mock_aisuite_client.chat.completions.create.return_value = [mock_chunk]

    # Mock chat_manager.send_personal_message
    with patch.object(chat_manager, "send_personal_message", AsyncMock()) as mock_send:
        # Call the method
        client_id = "test-client"
        messages = [{"role": "user", "content": "Test message"}]
        result = await llm_service.stream_chat_completion(messages, client_id)

        # Verify the result
        assert result == ""

        # Verify chat_manager.send_personal_message was not called
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_stream_chat_completion_model_format(llm_service, mock_aisuite_client):
    """Test model format conversion in streaming chat completion."""
    # Setup mock response chunk
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "Hello"

    # Configure mock to return chunks
    mock_aisuite_client.chat.completions.create.return_value = [mock_chunk]

    # Mock chat_manager.send_personal_message
    with patch.object(chat_manager, "send_personal_message", AsyncMock()):
        # Call the method with a model name containing '/'
        client_id = "test-client"
        messages = [{"role": "user", "content": "Test message"}]
        await llm_service.stream_chat_completion(
            messages, client_id, model="anthropic/claude-3-7-sonnet-latest"
        )

        # Verify the model format was converted
        mock_aisuite_client.chat.completions.create.assert_called_once()
        call_args = mock_aisuite_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "anthropic:claude-3-7-sonnet-latest"
