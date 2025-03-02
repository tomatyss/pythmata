"""Tests for the LLM service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pythmata.core.llm.service import LlmService
from pythmata.core.llm.prompts import BPMN_SYSTEM_PROMPT, XML_GENERATION_PROMPT, XML_MODIFICATION_PROMPT


@pytest.fixture
def llm_service():
    """Create an LLM service instance for testing."""
    with patch("aisuite.Client") as mock_client:
        # Setup mock client
        service = LlmService()
        yield service


@pytest.fixture
def mock_chat_response():
    """Create a mock chat completion response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content="This is a test response"),
            finish_reason="stop"
        )
    ]
    mock_response.usage = MagicMock(
        input_tokens=100,
        output_tokens=50
    )
    return mock_response


@pytest.fixture
def mock_chat_response_with_xml():
    """Create a mock chat completion response with XML."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""Here's the BPMN XML:

```xml
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:task id="Task_1" name="Review Application" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
```

This XML defines a simple process with a start event, a task, and an end event."""
            ),
            finish_reason="stop"
        )
    ]
    mock_response.usage = MagicMock(
        input_tokens=150,
        output_tokens=100
    )
    return mock_response


@pytest.mark.asyncio
async def test_chat_completion(llm_service, mock_chat_response):
    """Test the chat completion method."""
    # Setup mock to return the mock_chat_response directly
    mock_create = MagicMock()
    mock_create.return_value = mock_chat_response
    llm_service.client.chat.completions.create = mock_create
    
    # Test with default parameters
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, world!"}
    ]
    
    result = await llm_service.chat_completion(messages)
    
    # Verify result
    assert result["content"] == "This is a test response"
    assert result["finish_reason"] == "stop"
    assert result["usage"]["prompt_tokens"] == 100
    assert result["usage"]["completion_tokens"] == 50
    assert result["usage"]["total_tokens"] == 150
    
    # Verify client was called with correct parameters
    llm_service.client.chat.completions.create.assert_called_once()
    args, kwargs = llm_service.client.chat.completions.create.call_args
    assert kwargs["messages"] == messages
    assert kwargs["model"] == "anthropic:claude-3-7-sonnet-latest"
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_tokens"] == 1000


@pytest.mark.asyncio
async def test_chat_completion_model_format_conversion(llm_service, mock_chat_response):
    """Test model format conversion in chat completion."""
    # Setup mock
    mock_create = MagicMock()
    mock_create.return_value = mock_chat_response
    llm_service.client.chat.completions.create = mock_create
    
    # Test with model format using slash
    messages = [{"role": "user", "content": "Hello"}]
    await llm_service.chat_completion(messages, model="anthropic/claude-3-7-sonnet-latest")
    
    # Verify model format was converted
    args, kwargs = llm_service.client.chat.completions.create.call_args
    assert kwargs["model"] == "anthropic:claude-3-7-sonnet-latest"


@pytest.mark.asyncio
async def test_chat_completion_error_handling(llm_service):
    """Test error handling in chat completion."""
    # Setup mock to raise exception
    mock_create = MagicMock()
    mock_create.side_effect = Exception("API error")
    llm_service.client.chat.completions.create = mock_create
    
    # Test error handling
    messages = [{"role": "user", "content": "Hello"}]
    with pytest.raises(Exception) as exc_info:
        await llm_service.chat_completion(messages)
    
    assert "API error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_xml(llm_service):
    """Test XML generation."""
    # Setup mock
    mock_response = {
        "content": """Here's the BPMN XML for your process:

```xml
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:task id="Task_1" name="Review Application" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
```

This XML defines a simple process with a start event, a task for reviewing applications, and an end event.""",
        "model": "anthropic:claude-3-7-sonnet-latest",
        "finish_reason": "stop",
        "usage": {"total_tokens": 250}
    }
    
    # Mock the chat_completion method
    llm_service.chat_completion = AsyncMock(return_value=mock_response)
    
    # Test XML generation
    result = await llm_service.generate_xml("Create a process for reviewing applications")
    
    # Verify result
    assert "<bpmn:task id=\"Task_1\" name=\"Review Application\" />" in result["xml"]
    assert "Here's the BPMN XML for your process:" in result["explanation"]
    
    # Verify chat_completion was called with correct parameters
    llm_service.chat_completion.assert_called_once()
    args, kwargs = llm_service.chat_completion.call_args
    
    # Check that system prompt and generation prompt were used
    messages = kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert BPMN_SYSTEM_PROMPT in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Create a process for reviewing applications" in messages[1]["content"]


@pytest.mark.asyncio
async def test_generate_xml_without_language_specifier(llm_service):
    """Test XML generation with code block without language specifier."""
    # Setup mock with code block without language specifier
    mock_response = {
        "content": """Here's the BPMN XML for your process:

```
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:task id="Task_1" name="Review Application" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
```

This XML defines a simple process with a start event, a task for reviewing applications, and an end event.""",
        "model": "anthropic:claude-3-7-sonnet-latest",
        "finish_reason": "stop",
        "usage": {"total_tokens": 250}
    }
    
    # Mock the chat_completion method
    llm_service.chat_completion = AsyncMock(return_value=mock_response)
    
    # Test XML generation
    result = await llm_service.generate_xml("Create a process for reviewing applications")
    
    # Verify result
    assert "<bpmn:task id=\"Task_1\" name=\"Review Application\" />" in result["xml"]
    assert "Here's the BPMN XML for your process:" in result["explanation"]


@pytest.mark.asyncio
async def test_generate_xml_no_code_block(llm_service):
    """Test XML generation when no code block is present."""
    # Setup mock with no code block
    mock_response = {
        "content": "I'm sorry, I can't generate XML for this request.",
        "model": "anthropic:claude-3-7-sonnet-latest",
        "finish_reason": "stop",
        "usage": {"total_tokens": 50}
    }
    
    # Mock the chat_completion method
    llm_service.chat_completion = AsyncMock(return_value=mock_response)
    
    # Test XML generation
    result = await llm_service.generate_xml("Invalid request")
    
    # Verify result
    assert result["xml"] == ""
    assert result["explanation"] == "I'm sorry, I can't generate XML for this request."


@pytest.mark.asyncio
async def test_modify_xml(llm_service):
    """Test XML modification."""
    # Setup mock
    mock_response = {
        "content": """I've modified the XML to add a service task:

```xml
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:serviceTask id="ServiceTask_1" name="Process Payment" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
```

I've added a service task named "Process Payment" between the start and end events.""",
        "model": "anthropic:claude-3-7-sonnet-latest",
        "finish_reason": "stop",
        "usage": {"total_tokens": 250}
    }
    
    # Mock the chat_completion method
    llm_service.chat_completion = AsyncMock(return_value=mock_response)
    
    # Original XML
    original_xml = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""
    
    # Test XML modification
    result = await llm_service.modify_xml(
        current_xml=original_xml,
        request="Add a service task for payment processing"
    )
    
    # Verify result
    assert "<bpmn:serviceTask id=\"ServiceTask_1\" name=\"Process Payment\" />" in result["xml"]
    assert "I've modified the XML to add a service task:" in result["explanation"]
    
    # Verify chat_completion was called with correct parameters
    llm_service.chat_completion.assert_called_once()
    args, kwargs = llm_service.chat_completion.call_args
    
    # Check that system prompt and modification prompt were used
    messages = kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert BPMN_SYSTEM_PROMPT in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Add a service task for payment processing" in messages[1]["content"]
    assert original_xml in messages[1]["content"]


@pytest.mark.asyncio
async def test_modify_xml_fallback_to_original(llm_service):
    """Test XML modification fallback when no XML is extracted."""
    # Setup mock with no code block
    mock_response = {
        "content": "I'm sorry, I can't modify this XML.",
        "model": "anthropic:claude-3-7-sonnet-latest",
        "finish_reason": "stop",
        "usage": {"total_tokens": 50}
    }
    
    # Mock the chat_completion method
    llm_service.chat_completion = AsyncMock(return_value=mock_response)
    
    # Original XML
    original_xml = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""
    
    # Test XML modification
    result = await llm_service.modify_xml(
        current_xml=original_xml,
        request="Invalid request"
    )
    
    # Verify result falls back to original XML
    assert result["xml"] == original_xml
    assert result["explanation"] == "I'm sorry, I can't modify this XML."


@pytest.mark.asyncio
async def test_usage_extraction_openai_format(llm_service):
    """Test usage extraction with OpenAI format."""
    # Setup mock with OpenAI-style usage
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content="Test response"),
            finish_reason="stop"
        )
    ]
    mock_response.usage = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    }
    
    mock_create = MagicMock()
    mock_create.return_value = mock_response
    llm_service.client.chat.completions.create = mock_create
    
    # Test chat completion
    result = await llm_service.chat_completion([{"role": "user", "content": "Hello"}])
    
    # Verify usage extraction
    assert result["usage"]["prompt_tokens"] == 100
    assert result["usage"]["completion_tokens"] == 50
    assert result["usage"]["total_tokens"] == 150


@pytest.mark.asyncio
async def test_usage_extraction_error_handling(llm_service, mock_chat_response):
    """Test error handling in usage extraction."""
    # Setup mock to raise exception during usage extraction
    mock_chat_response.usage = None  # This will cause an exception in usage extraction
    
    mock_create = MagicMock()
    mock_create.return_value = mock_chat_response
    llm_service.client.chat.completions.create = mock_create
    
    # Test chat completion
    result = await llm_service.chat_completion([{"role": "user", "content": "Hello"}])
    
    # Verify default usage is returned
    assert result["usage"]["total_tokens"] == 0
