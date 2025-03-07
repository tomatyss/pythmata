"""WebSocket message schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProcessUpdate(BaseModel):
    """Base schema for process instance updates."""

    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str
    details: Dict[str, Any]


class ActivityUpdate(ProcessUpdate):
    """Activity completion update."""

    type: str = "ACTIVITY_COMPLETED"
    details: Dict[str, Any] = Field(
        ...,
        description="Activity details including node_id, activity_type, etc.",
    )


class VariableUpdate(ProcessUpdate):
    """Variable update notification."""

    type: str = "VARIABLE_UPDATED"
    details: Dict[str, Any] = Field(
        ...,
        description="Variable details including name, value, type, etc.",
    )


class StatusUpdate(ProcessUpdate):
    """Process status change notification."""

    type: str = "STATUS_CHANGED"
    details: Dict[str, Any] = Field(
        ...,
        description="Status details including old_status, new_status, etc.",
    )
