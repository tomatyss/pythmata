from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class ProcessDefinitionBase(BaseModel):
    """Base schema for process definition."""
    name: str
    bpmn_xml: str
    version: int


class ProcessDefinitionCreate(BaseModel):
    """Schema for creating a process definition."""
    name: str
    bpmn_xml: str
    version: Optional[int] = 1  # Default to version 1 for new processes


class ProcessDefinitionUpdate(BaseModel):
    """Schema for updating a process definition."""
    name: Optional[str] = None
    bpmn_xml: Optional[str] = None
    version: Optional[int] = None  # Allow updating version


class ProcessDefinitionResponse(ProcessDefinitionBase):
    """Schema for process definition response."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True  # Allow ORM model conversion
