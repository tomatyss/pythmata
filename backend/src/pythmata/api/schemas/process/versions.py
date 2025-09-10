from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProcessVersionResponse(BaseModel):
    """Schema for process version response."""

    id: UUID
    process_id: UUID
    number: int
    bpmn_xml: str
    created_at: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
