"""Models for audit logging."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pythmata.models.base import Base
from pythmata.models.user import User


class AuditActionType(str, Enum):
    """Audit action types."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    ROLE_CHANGE = "ROLE_CHANGE"
    PROJECT_ACCESS = "PROJECT_ACCESS"
    PROCESS_ACCESS = "PROCESS_ACCESS"


class AuditLog(Base):
    """
    Audit log model for tracking system actions.

    Attributes:
        id: Unique identifier for the audit log entry
        user_id: ID of the user who performed the action
        action_type: Type of action performed
        resource_type: Type of resource affected (e.g., "project", "process", "user")
        resource_id: ID of the resource affected
        details: Additional details about the action
        ip_address: IP address of the user
        timestamp: Timestamp when the action occurred
        created_at: Timestamp when the log entry was created
        user: Relationship to the user who performed the action
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
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
    user: Mapped[Optional[User]] = relationship("User")


# Audit logging service functions
async def log_audit_event(
    db,
    user_id: Optional[uuid.UUID],
    action_type: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log an audit event.

    Args:
        db: Database session
        user_id: ID of the user who performed the action
        action_type: Type of action performed
        resource_type: Type of resource affected
        resource_id: ID of the resource affected
        details: Additional details about the action
        ip_address: IP address of the user

    Returns:
        Created audit log entry
    """
    audit_log = AuditLog(
        user_id=user_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def log_permission_change(
    db,
    user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    project_id: uuid.UUID,
    old_role_id: Optional[uuid.UUID],
    new_role_id: uuid.UUID,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log a permission change event.

    Args:
        db: Database session
        user_id: ID of the user who performed the action
        target_user_id: ID of the user whose permissions were changed
        project_id: ID of the project
        old_role_id: ID of the old role
        new_role_id: ID of the new role
        ip_address: IP address of the user

    Returns:
        Created audit log entry
    """
    details = {
        "target_user_id": str(target_user_id),
        "project_id": str(project_id),
        "new_role_id": str(new_role_id),
    }

    if old_role_id:
        details["old_role_id"] = str(old_role_id)
        action_type = AuditActionType.ROLE_CHANGE
    else:
        action_type = AuditActionType.PERMISSION_CHANGE

    return await log_audit_event(
        db=db,
        user_id=user_id,
        action_type=action_type,
        resource_type="project_member",
        resource_id=str(project_id),
        details=details,
        ip_address=ip_address,
    )
