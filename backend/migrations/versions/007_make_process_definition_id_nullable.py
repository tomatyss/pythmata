"""Make process_definition_id nullable in chat_sessions table.

Revision ID: 007
Revises: 006
Create Date: 2025-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make process_definition_id nullable in chat_sessions table."""
    op.alter_column('chat_sessions', 'process_definition_id',
               existing_type=postgresql.UUID(),
               nullable=True)


def downgrade() -> None:
    """Make process_definition_id non-nullable in chat_sessions table."""
    op.alter_column('chat_sessions', 'process_definition_id',
               existing_type=postgresql.UUID(),
               nullable=False)
