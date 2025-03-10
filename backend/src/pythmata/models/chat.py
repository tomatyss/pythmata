"""Models for chat functionality."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from pythmata.models.base import Base


class ChatSession(Base):
    """
    Model for storing chat sessions related to process definitions.

    Attributes:
        id: Unique identifier for the chat session
        process_definition_id: ID of the related process definition
        title: Title of the chat session
        created_at: Timestamp when the session was created
        updated_at: Timestamp when the session was last updated
        process_definition: Relationship to the process definition
        messages: Relationship to the chat messages
    """

    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_definition_id = Column(
        UUID(as_uuid=True), ForeignKey("process_definitions.id"), nullable=True
    )
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    process_definition = relationship(
        "ProcessDefinition", back_populates="chat_sessions"
    )
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """
    Model for storing individual chat messages.

    Attributes:
        id: Unique identifier for the message
        session_id: ID of the related chat session
        role: Role of the message sender ('user', 'assistant', 'system')
        content: Text content of the message
        xml_content: XML content if the message contains BPMN XML
        model: The LLM model that generated this response
        tokens_used: Number of tokens used for this message
        created_at: Timestamp when the message was created
        session: Relationship to the chat session
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    xml_content = Column(Text, nullable=True)  # Store XML if generated
    model = Column(
        String(100), nullable=True
    )  # Store which model generated this response
    tokens_used = Column(Integer, nullable=True)  # For tracking usage
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
