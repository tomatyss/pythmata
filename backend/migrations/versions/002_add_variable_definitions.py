"""Add variable definitions to process definitions

Revision ID: 002
Revises: 001
Create Date: 2024-02-12 14:26:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add variable_definitions JSON column to process_definitions table
    op.add_column(
        "process_definitions",
        sa.Column("variable_definitions", postgresql.JSON, nullable=True),
    )

    # Initialize existing rows with empty variable definitions
    op.execute(
        """
        UPDATE process_definitions 
        SET variable_definitions = '[]'::jsonb 
        WHERE variable_definitions IS NULL
    """
    )

    # Make the column non-nullable after initialization
    op.alter_column(
        "process_definitions",
        "variable_definitions",
        existing_type=postgresql.JSON,
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("process_definitions", "variable_definitions")
