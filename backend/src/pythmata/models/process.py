import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, Boolean
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy import ForeignKey, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pythmata.models.base import Base


class ProcessStatus(str, Enum):
    """Process instance status."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SUSPENDED = "SUSPENDED"
    ERROR = "ERROR"


class ActivityType(str, Enum):
    """Process instance activity types."""

    INSTANCE_CREATED = "INSTANCE_CREATED"
    INSTANCE_STARTED = "INSTANCE_STARTED"
    NODE_ENTERED = "NODE_ENTERED"
    NODE_COMPLETED = "NODE_COMPLETED"
    SERVICE_TASK_EXECUTED = "SERVICE_TASK_EXECUTED"
    INSTANCE_SUSPENDED = "INSTANCE_SUSPENDED"
    INSTANCE_RESUMED = "INSTANCE_RESUMED"
    INSTANCE_COMPLETED = "INSTANCE_COMPLETED"
    INSTANCE_ERROR = "INSTANCE_ERROR"


class ProcessVariableDefinition(TypeDecorator):
    """Custom type for process variable definitions."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Optional[List[Dict[str, Any]]], dialect):
        """Convert Python object to JSON string."""
        if value is None:
            return []
        return value

    def process_result_value(self, value: Any, dialect) -> List[Dict[str, Any]]:
        """Convert JSON string to Python object."""
        if value is None:
            return []
        return value


class BranchType(str, Enum):
    """Process version branch types."""

    MAIN = "MAIN"
    FEATURE = "FEATURE"
    HOTFIX = "HOTFIX"
    DEVELOPMENT = "DEVELOPMENT"


class ProcessVersion(Base):
    """Version history for process definitions."""

    __tablename__ = "process_versions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    process_definition_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_definitions.id"), nullable=False
    )
    parent_version_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_versions.id"), nullable=True
    )
    version_number: Mapped[str] = mapped_column(String(50), nullable=False)
    major_version: Mapped[int] = mapped_column(nullable=False)
    minor_version: Mapped[int] = mapped_column(nullable=False)
    patch_version: Mapped[int] = mapped_column(nullable=False)
    branch_type: Mapped[BranchType] = mapped_column(
        SQLAEnum(BranchType), nullable=False, default=BranchType.MAIN
    )
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    bpmn_xml_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    variable_definitions_snapshot: Mapped[List[Dict[str, Any]]] = mapped_column(
        ProcessVariableDefinition, nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    process_definition: Mapped["ProcessDefinition"] = relationship(
        "ProcessDefinition", back_populates="versions"
    )
    parent_version: Mapped[Optional["ProcessVersion"]] = relationship(
        "ProcessVersion", remote_side=[id], backref="child_versions"
    )
    version_elements: Mapped[list["ProcessElementChange"]] = relationship(
        "ProcessElementChange", back_populates="version", cascade="all, delete-orphan"
    )


class ChangeType(str, Enum):
    """Process element change types."""

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    MOVED = "MOVED"
    RENAMED = "RENAMED"


class ProcessElementChange(Base):
    """Tracks changes to individual process elements between versions."""

    __tablename__ = "process_element_changes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_versions.id"), nullable=False
    )
    element_id: Mapped[str] = mapped_column(String(255), nullable=False)
    element_type: Mapped[str] = mapped_column(String(100), nullable=False)
    change_type: Mapped[ChangeType] = mapped_column(
        SQLAEnum(ChangeType), nullable=False
    )
    previous_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    version: Mapped[ProcessVersion] = relationship(
        "ProcessVersion", back_populates="version_elements"
    )


class ProcessDefinition(Base):
    """BPMN process definition."""

    __tablename__ = "process_definitions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    variable_definitions: Mapped[List[Dict[str, Any]]] = mapped_column(
        ProcessVariableDefinition, nullable=False, default=list
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    bpmn_xml: Mapped[str] = mapped_column(Text, nullable=False)
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
    # Version metadata fields
    current_version_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latest_commit_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True) 
    latest_commit_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latest_commit_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    instances: Mapped[list["ProcessInstance"]] = relationship(
        "ProcessInstance", back_populates="definition", cascade="all, delete-orphan"
    )
    scripts: Mapped[list["Script"]] = relationship(
        "Script", back_populates="process_definition", cascade="all, delete-orphan"
    )
    # Use string reference to avoid circular import
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="process_definition", cascade="all, delete-orphan"
    )
    versions: Mapped[list["ProcessVersion"]] = relationship(
        "ProcessVersion", back_populates="process_definition", cascade="all, delete-orphan"
    )


class ProcessInstance(Base):
    """Running instance of a process definition."""

    __tablename__ = "process_instances"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    definition_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_definitions.id"), nullable=False
    )
    status: Mapped[ProcessStatus] = mapped_column(
        SQLAEnum(ProcessStatus), nullable=False, default=ProcessStatus.RUNNING
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    definition: Mapped[ProcessDefinition] = relationship(
        "ProcessDefinition", back_populates="instances"
    )
    variables: Mapped[list["Variable"]] = relationship(
        "Variable", back_populates="instance", cascade="all, delete-orphan"
    )
    script_executions: Mapped[list["ScriptExecution"]] = relationship(
        "ScriptExecution", back_populates="instance", cascade="all, delete-orphan"
    )


class Script(Base):
    """Script definition for a process node."""

    __tablename__ = "scripts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    process_def_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_definitions.id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
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
    process_definition: Mapped[ProcessDefinition] = relationship(
        "ProcessDefinition", back_populates="scripts"
    )
    executions: Mapped[list["ScriptExecution"]] = relationship(
        "ScriptExecution", back_populates="script", cascade="all, delete-orphan"
    )


class ScriptExecution(Base):
    """Record of a script execution."""

    __tablename__ = "script_executions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    script_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False
    )
    instance_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_instances.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    script: Mapped[Script] = relationship("Script", back_populates="executions")
    instance: Mapped[ProcessInstance] = relationship(
        "ProcessInstance", back_populates="script_executions"
    )


class ActivityLog(Base):
    """Activity log for process instances."""

    __tablename__ = "activity_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_instances.id"), nullable=False
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        SQLAEnum(ActivityType), nullable=False
    )
    node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    instance: Mapped[ProcessInstance] = relationship(
        "ProcessInstance", back_populates="activities"
    )


class Variable(Base):
    """Process variable with history."""

    __tablename__ = "variables"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_instances.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    scope_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    instance: Mapped[ProcessInstance] = relationship(
        "ProcessInstance", back_populates="variables"
    )


# Update ProcessInstance relationships
ProcessInstance.activities: Mapped[list["ActivityLog"]] = relationship(
    "ActivityLog", back_populates="instance", cascade="all, delete-orphan"
)

# Import ChatSession at the end to avoid circular imports
from pythmata.models.chat import ChatSession  # noqa
