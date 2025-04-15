"""API schemas for user data."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RoleResponse(BaseModel):
    """Schema for role response."""

    id: UUID = Field(..., description="Unique identifier for the role")
    name: str = Field(..., description="Name of the role")
    permissions: Optional[dict] = Field(None, description="Role permissions")
    created_at: datetime = Field(..., description="Timestamp when the role was created")

    class Config:
        """Pydantic config."""

        from_attributes = True


class UserResponse(BaseModel):
    """Schema for user response in API endpoints."""

    id: UUID = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="Email address of the user")
    full_name: str = Field(..., description="Full name of the user")
    is_active: bool = Field(..., description="Whether the user account is active")
    roles: List[RoleResponse] = Field(default_factory=list, description="User roles")
    created_at: datetime = Field(..., description="Timestamp when the user was created")
    updated_at: datetime = Field(
        ..., description="Timestamp when the user was last updated"
    )

    class Config:
        """Pydantic config."""

        from_attributes = True
