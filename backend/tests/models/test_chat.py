"""Tests for chat models."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.models.chat import ChatMessage, ChatSession
from pythmata.models.process import ProcessDefinition


@pytest.fixture
async def process_definition(session: AsyncSession) -> ProcessDefinition:
    """Create a test process definition."""
    definition = ProcessDefinition(
        name="Test Process",
        bpmn_xml="<xml></xml>",
        version=1,
        variable_definitions=[],
    )
    session.add(definition)
    await session.commit()
    await session.refresh(definition)
    return definition


@pytest.fixture
async def chat_session(
    session: AsyncSession, process_definition: ProcessDefinition
) -> ChatSession:
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
    # Create messages with different timestamps to test ordering
    base_time = datetime.now()
    messages = [
        ChatMessage(
            id=uuid.uuid4(),
            session_id=chat_session.id,
            role="user",
            content="Hello, I need help with my BPMN process.",
            created_at=base_time,
        ),
        ChatMessage(
            id=uuid.uuid4(),
            session_id=chat_session.id,
            role="assistant",
            content="I'd be happy to help! What specific aspects of your BPMN process do you need assistance with?",
            model="anthropic:claude-3-7-sonnet-latest",
            created_at=base_time + timedelta(minutes=1),
        ),
        ChatMessage(
            id=uuid.uuid4(),
            session_id=chat_session.id,
            role="user",
            content="I need to add a service task.",
            created_at=base_time + timedelta(minutes=2),
        ),
    ]
    session.add_all(messages)
    await session.commit()
    return messages


async def test_chat_session_creation(
    session: AsyncSession, process_definition: ProcessDefinition
):
    """Test creating a chat session."""
    # Create a chat session
    session_id = uuid.uuid4()
    chat_session = ChatSession(
        id=session_id,
        process_definition_id=process_definition.id,
        title="New Chat Session",
    )
    session.add(chat_session)
    await session.commit()

    # Verify session was created
    result = await session.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    db_session = result.scalars().first()

    assert db_session is not None
    assert db_session.id == session_id
    assert db_session.process_definition_id == process_definition.id
    assert db_session.title == "New Chat Session"
    assert db_session.created_at is not None
    assert db_session.updated_at is not None


async def test_chat_message_creation(session: AsyncSession, chat_session: ChatSession):
    """Test creating a chat message."""
    # Create a chat message
    message_id = uuid.uuid4()
    message = ChatMessage(
        id=message_id,
        session_id=chat_session.id,
        role="user",
        content="Test message",
    )
    session.add(message)
    await session.commit()

    # Verify message was created
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.id == message_id)
    )
    db_message = result.scalars().first()

    assert db_message is not None
    assert db_message.id == message_id
    assert db_message.session_id == chat_session.id
    assert db_message.role == "user"
    assert db_message.content == "Test message"
    assert db_message.created_at is not None


async def test_chat_session_relationship(
    session: AsyncSession, chat_session: ChatSession, chat_messages: list[ChatMessage]
):
    """Test relationship between chat session and messages."""
    # Refresh chat session to load relationships
    await session.refresh(chat_session, ["messages"])

    # Verify messages relationship
    assert len(chat_session.messages) == 3

    # Verify messages are in the correct order (by created_at)
    messages = sorted(chat_session.messages, key=lambda m: m.created_at)
    assert messages[0].content == "Hello, I need help with my BPMN process."
    assert (
        messages[1].content
        == "I'd be happy to help! What specific aspects of your BPMN process do you need assistance with?"
    )
    assert messages[2].content == "I need to add a service task."


async def test_process_definition_relationship(
    session: AsyncSession,
    process_definition: ProcessDefinition,
    chat_session: ChatSession,
):
    """Test relationship between process definition and chat sessions."""
    # Refresh process definition to load relationships
    await session.refresh(process_definition, ["chat_sessions"])

    # Verify chat_sessions relationship
    assert len(process_definition.chat_sessions) == 1
    assert process_definition.chat_sessions[0].id == chat_session.id


async def test_chat_message_with_xml_content(
    session: AsyncSession, chat_session: ChatSession
):
    """Test chat message with XML content."""
    # Create a chat message with XML content
    xml_content = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:task id="Task_1" name="Review Application" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""

    message_id = uuid.uuid4()
    message = ChatMessage(
        id=message_id,
        session_id=chat_session.id,
        role="assistant",
        content="Here's the BPMN XML you requested.",
        xml_content=xml_content,
        model="anthropic:claude-3-7-sonnet-latest",
        tokens_used=500,
    )
    session.add(message)
    await session.commit()

    # Verify message was created with XML content
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.id == message_id)
    )
    db_message = result.scalars().first()

    assert db_message is not None
    assert db_message.xml_content == xml_content
    assert db_message.model == "anthropic:claude-3-7-sonnet-latest"
    assert db_message.tokens_used == 500


async def test_cascade_delete(
    session: AsyncSession, chat_session: ChatSession, chat_messages: list[ChatMessage]
):
    """Test that deleting a chat session cascades to its messages."""
    # Delete the chat session
    await session.delete(chat_session)
    await session.commit()

    # Verify messages were also deleted
    for message in chat_messages:
        result = await session.execute(
            select(ChatMessage).where(ChatMessage.id == message.id)
        )
        assert result.scalars().first() is None


async def test_chat_session_updated_at(
    session: AsyncSession, chat_session: ChatSession
):
    """Test that updated_at is updated when chat session is modified."""
    # Get original updated_at
    original_updated_at = chat_session.updated_at

    # Wait a moment to ensure timestamp difference
    from sqlalchemy import text

    await session.execute(text("SELECT pg_sleep(0.1)"))

    # Update the chat session
    chat_session.title = "Updated Title"
    await session.commit()
    await session.refresh(chat_session)

    # Verify updated_at was updated
    assert chat_session.updated_at > original_updated_at


async def test_chat_session_ordering(
    session: AsyncSession, process_definition: ProcessDefinition
):
    """Test that chat sessions are ordered by updated_at."""
    # Create multiple chat sessions with different updated_at timestamps
    base_time = datetime.now()

    session1 = ChatSession(
        id=uuid.uuid4(),
        process_definition_id=process_definition.id,
        title="Session 1",
        created_at=base_time - timedelta(days=2),
        updated_at=base_time - timedelta(days=2),
    )

    session2 = ChatSession(
        id=uuid.uuid4(),
        process_definition_id=process_definition.id,
        title="Session 2",
        created_at=base_time - timedelta(days=1),
        updated_at=base_time,  # Most recent
    )

    session3 = ChatSession(
        id=uuid.uuid4(),
        process_definition_id=process_definition.id,
        title="Session 3",
        created_at=base_time,
        updated_at=base_time - timedelta(days=1),
    )

    session.add_all([session1, session2, session3])
    await session.commit()

    # Query sessions ordered by updated_at desc
    result = await session.execute(
        select(ChatSession)
        .where(ChatSession.process_definition_id == process_definition.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()

    # Verify order
    assert len(sessions) == 3
    assert sessions[0].title == "Session 2"  # Most recent updated_at
    assert sessions[1].title == "Session 3"
    assert sessions[2].title == "Session 1"  # Oldest updated_at
