"""Activity log schemas."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel

from pythmata.models.process import ActivityType


class ActivityLogResponse(BaseModel):
    """Activity log response schema."""

    id: UUID
    instance_id: UUID
    activity_type: ActivityType
    node_id: Optional[str] = None
    details: Optional[Dict] = None
    timestamp: datetime
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
