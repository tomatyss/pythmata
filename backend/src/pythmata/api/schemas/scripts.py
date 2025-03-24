"""Script-related schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScriptContent(BaseModel):
    """Schema for script content."""

    content: str
    version: int = 1

    model_config = ConfigDict(extra="forbid")


class ScriptResponse(BaseModel):
    """Schema for script response."""

    id: UUID
    process_def_id: UUID
    node_id: str
    content: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True) 