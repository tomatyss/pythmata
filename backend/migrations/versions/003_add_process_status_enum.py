"""Add ProcessStatus enum type

Revision ID: 003
Revises: 002
Create Date: 2025-02-12 19:11:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ProcessStatus enum type
    op.execute(
        "CREATE TYPE processstatus AS ENUM ('RUNNING', 'COMPLETED', 'SUSPENDED', 'ERROR')"
    )

    # Convert status column to use the enum
    op.execute(
        "ALTER TABLE process_instances ALTER COLUMN status TYPE processstatus USING status::processstatus"
    )


def downgrade() -> None:
    # Convert status column back to string
    op.execute(
        "ALTER TABLE process_instances ALTER COLUMN status TYPE varchar(50) USING status::varchar"
    )

    # Drop the enum type
    op.execute("DROP TYPE processstatus")
