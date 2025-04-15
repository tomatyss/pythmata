"""Add audit logs table.

Revision ID: 010
Revises: 009
Create Date: 2025-04-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema with audit logs table."""
    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create indexes
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    op.create_index(
        "ix_audit_logs_action_type", "audit_logs", ["action_type"], unique=False
    )
    op.create_index(
        "ix_audit_logs_resource_type", "audit_logs", ["resource_type"], unique=False
    )
    op.create_index(
        "ix_audit_logs_timestamp", "audit_logs", ["timestamp"], unique=False
    )


def downgrade() -> None:
    """Downgrade database schema by removing audit logs table."""
    # Drop indexes
    op.drop_index("ix_audit_logs_timestamp", "audit_logs")
    op.drop_index("ix_audit_logs_resource_type", "audit_logs")
    op.drop_index("ix_audit_logs_action_type", "audit_logs")
    op.drop_index("ix_audit_logs_user_id", "audit_logs")

    # Drop table
    op.drop_table("audit_logs")
