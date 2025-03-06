"""Tests for LLM API routes."""

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.routes import router
from pythmata.models.chat import ChatMessage, ChatSession
from tests.data.process_samples import SIMPLE_PROCESS_XML

# Setup test application
app = FastAPI()
app.include_router(router)


@pytest.fixture
async def process_definition(session: AsyncSession) -> str:
    """Create a test process definition and return its ID."""
    from pythmata.models.process import ProcessDefinition

    # Create a process definition
    definition = ProcessDefinition(
        name="Test Process",
        bpmn_xml=SIMPLE_PROCESS_XML,
        version=1,
        variable_definitions=[],
    )
    session.add(definition)
    await session.commit()
    await session.refresh(definition)

    return definition


@pytest.fixture
async def chat_session(session: AsyncSession, process_definition) -> ChatSession:
    """Create a test chat session."""
    chat_session = ChatSession(
        id=uuid.uuid4(),
        process_definition_id=process_definition.id,
        title="Test Chat Session",
    )
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return chat_session


@pytest.fixture
async def chat_messages(
    session: AsyncSession, chat_session: ChatSession
) -> list[ChatMessage]:
    """Create test chat messages."""
    messages = [
        ChatMessage(
            id=uuid.uuid4(),
            session_id=chat_session.id,
            role="user",
            content="Hello, I need help with my BPMN process.",
            created_at=datetime.now(),
        ),
        ChatMessage(
            id=uuid.uuid4(),
            session_id=chat_session.id,
            role="assistant",
            content="I'd be happy to help! What specific aspects of your BPMN process do you need assistance with?",
            model="anthropic:claude-3-7-sonnet-latest",
            created_at=datetime.now(),
        ),
    ]
    session.add_all(messages)
    await session.commit()
    return messages


@pytest.fixture
def mock_llm_response():
    """Mock response from the LLM service."""
    return {
        "content": 'I\'ve analyzed your process and here\'s my suggestion: ```xml\n<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">\n  <bpmn:process id="Process_1">\n    <bpmn:startEvent id="StartEvent_1" />\n  </bpmn:process>\n</bpmn:definitions>\n```',
        "model": "anthropic:claude-3-7-sonnet-latest",
        "finish_reason": "stop",
        "usage": {"total_tokens": 150},
    }


@patch("pythmata.core.llm.service.LlmService.chat_completion")
async def test_chat_completion_new_session(
    mock_chat_completion,
    mock_llm_response,
    async_client: AsyncClient,
    process_definition,
    session: AsyncSession,
):
    """Test chat completion with a new session."""
    # Setup mock
    mock_chat_completion.return_value = mock_llm_response

    # Test request
    response = await async_client.post(
        "/llm/chat",
        json={
            "messages": [{"role": "user", "content": "Help me design a process"}],
            "process_id": str(process_definition.id),
        },
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "xml" in data
    assert data["model"] == "anthropic:claude-3-7-sonnet-latest"
    assert data["session_id"] is not None

    # Verify session was created
    result = await session.execute(
        select(ChatSession).where(
            ChatSession.process_definition_id == process_definition.id
        )
    )
    db_session = result.scalars().first()
    assert db_session is not None
    assert str(db_session.id) == data["session_id"]

    # Verify messages were stored
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.session_id == db_session.id)
    )
    messages = result.scalars().all()
    assert len(messages) == 2  # User message and assistant response
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].xml_content is not None


@patch("pythmata.core.llm.service.LlmService.chat_completion")
async def test_chat_completion_existing_session(
    mock_chat_completion,
    mock_llm_response,
    async_client: AsyncClient,
    chat_session: ChatSession,
    session: AsyncSession,
):
    """Test chat completion with an existing session."""
    # Setup mock
    mock_chat_completion.return_value = mock_llm_response

    # Test request
    response = await async_client.post(
        "/llm/chat",
        json={
            "messages": [{"role": "user", "content": "Add a service task"}],
            "process_id": str(chat_session.process_definition_id),
            "session_id": str(chat_session.id),
        },
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == str(chat_session.id)

    # Verify messages were added to existing session
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.session_id == chat_session.id)
    )
    messages = result.scalars().all()
    assert len(messages) == 2  # User message and assistant response


@patch("pythmata.core.llm.service.LlmService.chat_completion")
async def test_chat_completion_with_xml_extraction(
    mock_chat_completion,
    async_client: AsyncClient,
    process_definition,
):
    """Test XML extraction from LLM response."""
    # Setup mock with XML in response
    mock_chat_completion.return_value = {
        "content": 'Here\'s the BPMN XML you requested:\n\n```xml\n<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">\n  <bpmn:process id="Process_1">\n    <bpmn:startEvent id="StartEvent_1" />\n    <bpmn:task id="Task_1" name="New Task" />\n  </bpmn:process>\n</bpmn:definitions>\n```\n\nThis XML defines a simple process with a start event and a task.',
        "model": "anthropic:claude-3-7-sonnet-latest",
        "finish_reason": "stop",
        "usage": {"total_tokens": 200},
    }

    # Test request
    response = await async_client.post(
        "/llm/chat",
        json={
            "messages": [
                {"role": "user", "content": "Generate XML for a simple process"}
            ],
            "process_id": str(process_definition.id),
        },
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["xml"] is not None
    assert "<bpmn:definitions" in data["xml"]
    assert '<bpmn:task id="Task_1" name="New Task" />' in data["xml"]


@patch("pythmata.core.llm.service.LlmService.chat_completion")
async def test_chat_completion_with_current_xml(
    mock_chat_completion,
    mock_llm_response,
    async_client: AsyncClient,
    process_definition,
):
    """Test chat completion with current XML context."""
    # Setup mock
    mock_chat_completion.return_value = mock_llm_response

    # Test request with current XML
    response = await async_client.post(
        "/llm/chat",
        json={
            "messages": [{"role": "user", "content": "Improve this process"}],
            "process_id": str(process_definition.id),
            "current_xml": SIMPLE_PROCESS_XML,
        },
    )

    # Verify response
    assert response.status_code == 200

    # Verify that current XML was included in the system prompt
    args, kwargs = mock_chat_completion.call_args
    messages = kwargs.get("messages", [])
    system_message = next((m for m in messages if m["role"] == "system"), None)
    assert system_message is not None
    assert SIMPLE_PROCESS_XML in system_message["content"]


@patch("pythmata.core.llm.service.LlmService.generate_xml")
async def test_generate_xml(
    mock_generate_xml,
    async_client: AsyncClient,
):
    """Test XML generation endpoint."""
    # Setup mock
    mock_generate_xml.return_value = {
        "xml": '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">\n  <bpmn:process id="Process_1">\n    <bpmn:startEvent id="StartEvent_1" />\n    <bpmn:task id="Task_1" name="Review Application" />\n    <bpmn:endEvent id="EndEvent_1" />\n  </bpmn:process>\n</bpmn:definitions>',
        "explanation": "This XML defines a simple process with a start event, a task for reviewing applications, and an end event.",
        "model": "anthropic:claude-3-7-sonnet-latest",
    }

    # Test request
    response = await async_client.post(
        "/llm/generate-xml",
        json={
            "description": "Create a process for reviewing applications",
        },
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "xml" in data
    assert "explanation" in data
    assert '<bpmn:task id="Task_1" name="Review Application" />' in data["xml"]


@patch("pythmata.core.llm.service.LlmService.modify_xml")
async def test_modify_xml(
    mock_modify_xml,
    async_client: AsyncClient,
):
    """Test XML modification endpoint."""
    # Setup mock
    mock_modify_xml.return_value = {
        "xml": '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">\n  <bpmn:process id="Process_1">\n    <bpmn:startEvent id="StartEvent_1" />\n    <bpmn:task id="Task_1" name="Review Application" />\n    <bpmn:task id="Task_2" name="Approve Application" />\n    <bpmn:endEvent id="EndEvent_1" />\n  </bpmn:process>\n</bpmn:definitions>',
        "explanation": "Added a new task for approving applications after the review task.",
        "model": "anthropic:claude-3-7-sonnet-latest",
    }

    # Test request
    response = await async_client.post(
        "/llm/modify-xml",
        json={
            "request": "Add a task for approving applications",
            "current_xml": SIMPLE_PROCESS_XML,
        },
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "xml" in data
    assert "explanation" in data
    assert '<bpmn:task id="Task_2" name="Approve Application" />' in data["xml"]


async def test_create_chat_session(
    async_client: AsyncClient,
    process_definition,
    session: AsyncSession,
):
    """Test creating a new chat session."""
    # Test request
    response = await async_client.post(
        "/llm/sessions",
        json={
            "process_definition_id": str(process_definition.id),
            "title": "New Discussion",
        },
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["process_definition_id"] == str(process_definition.id)
    assert data["title"] == "New Discussion"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Verify session was created in database
    result = await session.execute(
        select(ChatSession).where(ChatSession.id == uuid.UUID(data["id"]))
    )
    db_session = result.scalars().first()
    assert db_session is not None
    assert db_session.title == "New Discussion"


async def test_list_chat_sessions(
    async_client: AsyncClient,
    chat_session: ChatSession,
):
    """Test listing chat sessions for a process."""
    # Test request
    response = await async_client.get(
        f"/llm/sessions/{chat_session.process_definition_id}"
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(chat_session.id)
    assert data[0]["title"] == chat_session.title
    assert data[0]["process_definition_id"] == str(chat_session.process_definition_id)


async def test_get_chat_messages(
    async_client: AsyncClient,
    chat_session: ChatSession,
    chat_messages: list[ChatMessage],
):
    """Test getting messages for a chat session."""
    # Test request
    response = await async_client.get(f"/llm/sessions/{chat_session.id}/messages")

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[1]["role"] == "assistant"
    assert data[0]["content"] == chat_messages[0].content
    assert data[1]["content"] == chat_messages[1].content


@patch("pythmata.core.llm.service.LlmService.chat_completion")
async def test_error_handling(
    mock_chat_completion,
    async_client: AsyncClient,
    process_definition,
):
    """Test error handling in chat completion."""
    # Setup mock to raise exception
    mock_chat_completion.side_effect = Exception("LLM service unavailable")

    # Test request
    response = await async_client.post(
        "/llm/chat",
        json={
            "messages": [{"role": "user", "content": "Help me design a process"}],
            "process_id": str(process_definition.id),
        },
    )

    # Verify response
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Failed to generate response" in data["detail"]
