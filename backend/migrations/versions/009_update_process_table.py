"""Update process_definitions table to remove redundant columns

Revision ID: 009
Revises: 008
Create Date: 2025-04-01 18:00:00.123456

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop redundant columns from process_definitions and add index to process_versions."""
    # Add index on process_versions.number for better query performance
    op.create_index(
        "ix_process_versions_number",
        "process_versions",
        ["number"],
    )

    # Drop columns from process_definitions that are now in process_versions
    op.drop_column("process_definitions", "bpmn_xml")
    op.drop_column("process_definitions", "updated_at")
    op.drop_column("process_definitions", "version")


def downgrade() -> None:
    """Restore dropped columns and remove index."""
    # Restore columns to process_definitions
    op.add_column(
        "process_definitions",
        sa.Column("bpmn_xml", sa.Text(), nullable=False),
    )
    op.add_column(
        "process_definitions",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        "process_definitions",
        sa.Column("version", sa.Integer(), nullable=False),
    )

    # Drop the index we added
    op.drop_index("ix_process_versions_number", table_name="process_versions")
