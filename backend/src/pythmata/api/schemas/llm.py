"""LLM-related schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message model."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""

    messages: List[Message]
    process_id: Optional[str] = None
    project_id: Optional[str] = None
    current_xml: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    xml: Optional[str] = None
    model: str
    session_id: Optional[str] = None
    xml_validation: Optional["ValidationResult"] = None


class ChatSessionCreate(BaseModel):
    """Chat session creation model."""

    process_definition_id: Optional[str] = None
    project_id: Optional[str] = None
    title: str = "New Chat"
    context: Optional[str] = None


class ChatSessionResponse(BaseModel):
    """Chat session response model."""

    id: str
    process_definition_id: Optional[str] = None
    project_id: Optional[str] = None
    title: str
    context: Optional[str] = None
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
    project_id: Optional[str] = None
    model: Optional[str] = None


class XmlModificationRequest(BaseModel):
    """XML modification request model."""

    request: str
    current_xml: str
    model: Optional[str] = None


class ValidationError(BaseModel):
    """Validation error model."""

    code: str
    message: str
    element_id: Optional[str] = None


class ValidationResult(BaseModel):
    """Validation result model."""

    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    improvement_attempts: int = 0


class XmlResponse(BaseModel):
    """XML response model."""

    xml: str
    explanation: str
    validation: Optional[ValidationResult] = None
