"""Process version related schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProcessVersionCreate(BaseModel):
    """Schema for creating a new process version."""

    bpmn_xml: str
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ProcessVersionResponse(BaseModel):
    """Schema for process version response."""

    id: UUID
    process_id: UUID
    number: int
    bpmn_xml: str
    created_at: datetime
    notes: Optional[str] = None
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProcessVersionUpdate(BaseModel):
    """Schema for updating a process version."""

    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid") 