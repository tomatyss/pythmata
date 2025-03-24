"""Version control schemas."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field


class BranchTypeEnum(str, Enum):
    """Branch type enum."""

    MAIN = "MAIN"
    FEATURE = "FEATURE"
    HOTFIX = "HOTFIX"
    DEVELOPMENT = "DEVELOPMENT"


class ChangeTypeEnum(str, Enum):
    """Change type enum."""

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    MOVED = "MOVED"
    RENAMED = "RENAMED"


class ElementChangeBase(BaseModel):
    """Base schema for element changes."""

    element_id: str
    element_type: str
    change_type: ChangeTypeEnum
    previous_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None


class ElementChangeResponse(ElementChangeBase):
    """Response schema for element changes."""

    id: UUID
    version_id: UUID
    created_at: datetime


class VersionIncrementEnum(str, Enum):
    """Version increment type enum."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class VersionBase(BaseModel):
    """Base schema for versions."""

    commit_message: str
    author: str = Field(..., min_length=1)
    branch_type: BranchTypeEnum = BranchTypeEnum.MAIN
    branch_name: Optional[str] = None


class VersionCreate(VersionBase):
    """Schema for creating a new version."""

    process_definition_id: UUID
    parent_version_id: Optional[UUID] = None
    bpmn_xml: Optional[str] = None
    variable_definitions: Optional[List[Dict[str, Any]]] = None
    version_increment: VersionIncrementEnum = VersionIncrementEnum.PATCH
    element_changes: Optional[List[ElementChangeBase]] = None


class VersionResponse(BaseModel):
    """Base response schema for version."""

    id: UUID
    process_definition_id: UUID
    parent_version_id: Optional[UUID] = None
    version_number: str
    major_version: int
    minor_version: int
    patch_version: int
    branch_type: BranchTypeEnum
    branch_name: Optional[str] = None
    commit_message: str
    author: str
    is_current: bool
    created_at: datetime


class VersionListResponse(BaseModel):
    """Response schema for version list."""

    versions: List[VersionResponse]
    total: int


class VersionDetailResponse(VersionResponse):
    """Detailed response schema for version with element changes."""

    bpmn_xml_snapshot: str
    variable_definitions_snapshot: List[Dict[str, Any]]
    element_changes: Optional[List[ElementChangeResponse]] = None 