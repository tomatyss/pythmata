"""Create process_versions table

Revision ID: 008
Revises: 007
Create Date: 2025-04-01 17:52:00.123456

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Creates the process_versions table."""
    op.create_table(
        "process_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "process_id", postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("bpmn_xml", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["process_id"],
            ["process_definitions.id"],
            name=op.f("fk_process_versions_process_id_process_definitions"),
        ),
        sa.UniqueConstraint(
            "process_id", "number", name=op.f("uq_process_versions_process_id_number")
        ),
    )


def downgrade() -> None:
    """Drops the process_versions table."""
    op.drop_constraint(
        op.f("uq_process_versions_process_id_number"),
        "process_versions",
        type_="unique",
    )
    op.drop_constraint(
        op.f("fk_process_versions_process_id_process_definitions"),
        "process_versions",
        type_="foreignkey",
    )
    op.drop_index("ix_process_versions_process_id", table_name="process_versions")
    op.drop_table("process_versions")
