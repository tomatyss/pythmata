"""Token related schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    """Schema for token position response."""

    node_id: str
    state: str
    scope_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
