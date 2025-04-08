"""API schemas for project management."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, UUID4

from pythmata.api.schemas.user import UserResponse


class ProjectRoleBase(BaseModel):
    """Base schema for project role."""

    name: str = Field(..., description="Name of the role")
    permissions: Dict[str, Union[bool, str, List[str]]] = Field(
        default_factory=dict, description="Role permissions"
    )


class ProjectRoleCreate(ProjectRoleBase):
    """Schema for creating a project role."""

    pass


class ProjectRoleUpdate(ProjectRoleBase):
    """Schema for updating a project role."""

    name: Optional[str] = Field(None, description="Name of the role")


class ProjectRoleResponse(ProjectRoleBase):
    """Schema for project role response."""

    id: UUID4 = Field(..., description="Unique identifier for the role")
    created_at: datetime = Field(..., description="Timestamp when the role was created")
    updated_at: datetime = Field(..., description="Timestamp when the role was last updated")

    class Config:
        """Pydantic config."""

        from_attributes = True


class ProjectMemberBase(BaseModel):
    """Base schema for project member."""

    user_id: UUID4 = Field(..., description="ID of the user")
    role_id: UUID4 = Field(..., description="ID of the role")


class ProjectMemberCreate(ProjectMemberBase):
    """Schema for creating a project member."""

    pass


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a project member."""

    role_id: UUID4 = Field(..., description="ID of the role")


class ProjectMemberResponse(BaseModel):
    """Schema for project member response."""

    id: UUID4 = Field(..., description="Unique identifier for the membership")
    user: UserResponse = Field(..., description="User information")
    role: ProjectRoleResponse = Field(..., description="Role information")
    joined_at: datetime = Field(..., description="Timestamp when the user joined the project")
    created_at: datetime = Field(..., description="Timestamp when the membership was created")
    updated_at: datetime = Field(..., description="Timestamp when the membership was last updated")

    class Config:
        """Pydantic config."""

        from_attributes = True


class TagBase(BaseModel):
    """Base schema for tag."""

    name: str = Field(..., description="Name of the tag")
    color: str = Field("#808080", description="Color code for the tag")


class TagCreate(TagBase):
    """Schema for creating a tag."""

    pass


class TagUpdate(TagBase):
    """Schema for updating a tag."""

    name: Optional[str] = Field(None, description="Name of the tag")
    color: Optional[str] = Field(None, description="Color code for the tag")


class TagResponse(TagBase):
    """Schema for tag response."""

    id: UUID4 = Field(..., description="Unique identifier for the tag")
    created_at: datetime = Field(..., description="Timestamp when the tag was created")

    class Config:
        """Pydantic config."""

        from_attributes = True


class ProjectDescriptionBase(BaseModel):
    """Base schema for project description."""

    content: str = Field(..., description="Text content of the description")


class ProjectDescriptionCreate(ProjectDescriptionBase):
    """Schema for creating a project description."""

    tag_ids: Optional[List[UUID4]] = Field(
        default_factory=list, description="IDs of tags to associate with the description"
    )


class ProjectDescriptionUpdate(ProjectDescriptionBase):
    """Schema for updating a project description."""

    content: Optional[str] = Field(None, description="Text content of the description")
    tag_ids: Optional[List[UUID4]] = Field(
        None, description="IDs of tags to associate with the description"
    )


class ProjectDescriptionResponse(ProjectDescriptionBase):
    """Schema for project description response."""

    id: UUID4 = Field(..., description="Unique identifier for the description")
    project_id: UUID4 = Field(..., description="ID of the project")
    version: int = Field(..., description="Version number of the description")
    is_current: bool = Field(..., description="Whether this is the current version")
    created_at: datetime = Field(..., description="Timestamp when the description was created")
    tags: List[TagResponse] = Field(default_factory=list, description="Tags associated with the description")

    class Config:
        """Pydantic config."""

        from_attributes = True


class ProjectBase(BaseModel):
    """Base schema for project."""

    name: str = Field(..., description="Name of the project")
    description: Optional[str] = Field(None, description="Description of the project")
    status: str = Field("DRAFT", description="Status of the project")


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    pass


class ProjectUpdate(ProjectBase):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, description="Name of the project")
    description: Optional[str] = Field(None, description="Description of the project")
    status: Optional[str] = Field(None, description="Status of the project")


class ProjectResponse(ProjectBase):
    """Schema for project response."""

    id: UUID4 = Field(..., description="Unique identifier for the project")
    owner_id: UUID4 = Field(..., description="ID of the user who owns the project")
    created_at: datetime = Field(..., description="Timestamp when the project was created")
    updated_at: datetime = Field(..., description="Timestamp when the project was last updated")
    owner: UserResponse = Field(..., description="Owner information")
    members: List[ProjectMemberResponse] = Field(
        default_factory=list, description="Project members"
    )
    current_description: Optional[ProjectDescriptionResponse] = Field(
        None, description="Current project description"
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Schema for detailed project response."""

    descriptions: List[ProjectDescriptionResponse] = Field(
        default_factory=list, description="Project descriptions"
    )
    process_count: int = Field(0, description="Number of process definitions in the project")

    class Config:
        """Pydantic config."""

        from_attributes = True
