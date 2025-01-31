"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-01-31 09:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create process_definitions table
    op.create_table(
        'process_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('bpmn_xml', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version')
    )

    # Create process_instances table
    op.create_table(
        'process_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('definition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['definition_id'], ['process_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create scripts table
    op.create_table(
        'scripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_def_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['process_def_id'], ['process_definitions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('process_def_id', 'node_id', 'version')
    )

    # Create script_executions table
    op.create_table(
        'script_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('script_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['process_instances.id'], ),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create variables table
    op.create_table(
        'variables',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('value_type', sa.String(50), nullable=False),
        sa.Column('value_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('scope_id', sa.String(255), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['process_instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'name', 'version')
    )

    # Create indexes
    op.create_index(
        'ix_process_instances_definition_id',
        'process_instances',
        ['definition_id']
    )
    op.create_index(
        'ix_process_instances_status',
        'process_instances',
        ['status']
    )
    op.create_index(
        'ix_scripts_process_def_id',
        'scripts',
        ['process_def_id']
    )
    op.create_index(
        'ix_script_executions_instance_id',
        'script_executions',
        ['instance_id']
    )
    op.create_index(
        'ix_variables_instance_id',
        'variables',
        ['instance_id']
    )
    op.create_index(
        'ix_variables_name',
        'variables',
        ['name']
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('variables')
    op.drop_table('script_executions')
    op.drop_table('scripts')
    op.drop_table('process_instances')
    op.drop_table('process_definitions')
