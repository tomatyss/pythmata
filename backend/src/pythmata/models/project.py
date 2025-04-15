"""Models for project management functionality."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pythmata.models.base import Base
from pythmata.models.process import ProcessDefinition
from pythmata.models.user import User


class ProjectStatus(str, enum.Enum):
    """Project status enum."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    COMPLETED = "COMPLETED"


# Association table for many-to-many relationship between project descriptions and tags
description_tags = Table(
    "description_tags",
    Base.metadata,
    Column("description_id", ForeignKey("project_descriptions.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class Project(Base):
    """
    Project model for organizing process definitions.

    Attributes:
        id: Unique identifier for the project
        name: Name of the project
        description: Description of the project
        status: Current status of the project
        owner_id: ID of the user who owns the project
        created_at: Timestamp when the project was created
        updated_at: Timestamp when the project was last updated
        owner: Relationship to the user who owns the project
        members: Relationship to project members
        process_definitions: Relationship to process definitions
        descriptions: Relationship to project descriptions
    """

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), nullable=False, default=ProjectStatus.DRAFT
    )
    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner: Mapped[User] = relationship("User", back_populates="owned_projects")
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    process_definitions: Mapped[List[ProcessDefinition]] = relationship(
        "ProcessDefinition", back_populates="project"
    )
    descriptions: Mapped[List["ProjectDescription"]] = relationship(
        "ProjectDescription", back_populates="project", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectRole(Base):
    """
    Project role model for role-based access control.

    Attributes:
        id: Unique identifier for the role
        name: Name of the role
        permissions: JSON object containing role permissions
        created_at: Timestamp when the role was created
        updated_at: Timestamp when the role was last updated
        members: Relationship to project members with this role
    """

    __tablename__ = "project_roles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[Dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="role"
    )


class ProjectMember(Base):
    """
    Project member model for user-project associations.

    Attributes:
        id: Unique identifier for the membership
        project_id: ID of the project
        user_id: ID of the user
        role_id: ID of the role assigned to the user
        joined_at: Timestamp when the user joined the project
        created_at: Timestamp when the membership was created
        updated_at: Timestamp when the membership was last updated
        project: Relationship to the project
        user: Relationship to the user
        role: Relationship to the role
    """

    __tablename__ = "project_members"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_roles.id"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="members")
    user: Mapped[User] = relationship("User", back_populates="project_memberships")
    role: Mapped[ProjectRole] = relationship("ProjectRole", back_populates="members")


class Tag(Base):
    """
    Tag model for categorizing project descriptions.

    Attributes:
        id: Unique identifier for the tag
        name: Name of the tag
        color: Color code for the tag
        created_at: Timestamp when the tag was created
        descriptions: Relationship to project descriptions with this tag
    """

    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#808080")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    descriptions: Mapped[List["ProjectDescription"]] = relationship(
        secondary=description_tags, back_populates="tags"
    )


class ProjectDescription(Base):
    """
    Project description model for storing project requirements.

    Attributes:
        id: Unique identifier for the description
        project_id: ID of the project
        content: Text content of the description
        version: Version number of the description
        is_current: Whether this is the current version
        created_at: Timestamp when the description was created
        project: Relationship to the project
        tags: Relationship to tags
        process_definitions: Relationship to process definitions generated from this description
    """

    __tablename__ = "project_descriptions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="descriptions")
    tags: Mapped[List[Tag]] = relationship(
        secondary=description_tags, back_populates="descriptions"
    )
    process_definitions: Mapped[List[ProcessDefinition]] = relationship(
        "ProcessDefinition", back_populates="source_description"
    )


# Update User model relationships
User.owned_projects: Mapped[List[Project]] = relationship(
    "Project", back_populates="owner", foreign_keys=[Project.owner_id]
)
User.project_memberships: Mapped[List[ProjectMember]] = relationship(
    "ProjectMember", back_populates="user"
)

# Import ChatSession at the end to avoid circular imports
from pythmata.models.chat import ChatSession  # noqa

# ProcessDefinition relationships are already defined in process.py
# No need to redefine them here
