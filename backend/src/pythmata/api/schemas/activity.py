"""Activity related schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityLogResponse(BaseModel):
    """Schema for activity log response."""

    id: UUID
    instance_id: UUID
    activity_id: str
    activity_name: str
    activity_type: str
    start_time: datetime
    end_time: datetime
    duration: float  # in seconds
    status: str
    
    model_config = ConfigDict(from_attributes=True)
