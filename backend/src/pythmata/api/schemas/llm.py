"""LLM-related schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

class Message(BaseModel):
    """Chat message model."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""

    messages: List[Message]
    process_id: Optional[str] = None
    current_xml: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    xml: Optional[str] = None
    model: str
    session_id: Optional[str] = None


class ChatSessionCreate(BaseModel):
    """Chat session creation model."""

    process_definition_id: str
    title: str = "New Chat"


class ChatSessionResponse(BaseModel):
    """Chat session response model."""

    id: str
    process_definition_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    """Chat message response model."""

    id: str
    role: str
    content: str
    xml_content: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime


class XmlGenerationRequest(BaseModel):
    """XML generation request model."""

    description: str
    model: Optional[str] = None


class XmlModificationRequest(BaseModel):
    """XML modification request model."""

    request: str
    current_xml: str
    model: Optional[str] = None


class XmlResponse(BaseModel):
    """XML response model."""

    xml: str
    explanation: str
