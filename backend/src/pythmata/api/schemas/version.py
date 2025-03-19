"""Version control related schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VersionBase(BaseModel):
    """Base schema for version information."""

    process_id: UUID
    branch_name: str = "main"
    commit_message: str
    commit_author: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class VersionCreate(VersionBase):
    """Schema for creating a version."""

    version_number: Optional[str] = None  # If None, will be auto-generated

    model_config = ConfigDict(extra="forbid")


class VersionResponse(VersionBase):
    """Schema for version response."""

    id: UUID
    version_number: str
    created_at: datetime
    elements_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class VersionListResponse(BaseModel):
    """Schema for version list response."""

    id: UUID
    version_number: str
    branch_name: str
    commit_message: str
    commit_author: Optional[str]
    created_at: datetime
    elements_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class VersionDetailResponse(VersionResponse):
    """Schema for detailed version response."""

    changes: List[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True) 