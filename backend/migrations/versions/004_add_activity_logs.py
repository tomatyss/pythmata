"""Add activity logs table

Revision ID: 004
Revises: 003
Create Date: 2025-02-20 12:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create activity_logs table with enum type reference
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "activity_type",
            sa.Enum(
                "INSTANCE_CREATED",
                "INSTANCE_STARTED",
                "NODE_ENTERED",
                "NODE_COMPLETED",
                "INSTANCE_SUSPENDED",
                "INSTANCE_RESUMED",
                "INSTANCE_COMPLETED",
                "INSTANCE_ERROR",
                name="activitytype",
                create_type=False,  # Don't create the type as it's created by SQLAlchemy
            ),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["instance_id"], ["process_instances.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_activity_logs_instance_id", "activity_logs", ["instance_id"])
    op.create_index("idx_activity_logs_timestamp", "activity_logs", ["timestamp"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_activity_logs_timestamp")
    op.drop_index("idx_activity_logs_instance_id")

    # Drop table
    op.drop_table("activity_logs")

    # Note: We don't drop the enum type as it's managed by SQLAlchemy
