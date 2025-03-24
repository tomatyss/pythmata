"""Add version control

Revision ID: 008_add_version_control
Revises: 007_process_def_nullable
Create Date: 2023-05-19 14:30:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008_add_version_control"
down_revision: Union[str, None] = "007_process_def_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    connection = op.get_bind()
    
    # Check if enums exist and create if they don't
    inspector = sa.inspect(connection)
    existing_enums = [enum['name'] for enum in inspector.get_enums()]
    
    if 'branchtype' not in existing_enums:
        branch_type = sa.Enum("MAIN", "FEATURE", "HOTFIX", "DEVELOPMENT", name="branchtype")
        branch_type.create(connection)
    
    if 'changetype' not in existing_enums:
        change_type = sa.Enum("ADDED", "MODIFIED", "DELETED", "MOVED", "RENAMED", name="changetype")
        change_type.create(connection)

    # Add version metadata fields to process_definitions table
    op.add_column(
        "process_definitions",
        sa.Column("current_version_number", sa.String(50), nullable=True),
    )
    op.add_column(
        "process_definitions",
        sa.Column("current_branch", sa.String(255), nullable=True),
    )
    op.add_column(
        "process_definitions",
        sa.Column("latest_commit_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "process_definitions",
        sa.Column("latest_commit_author", sa.String(255), nullable=True),
    )
    op.add_column(
        "process_definitions",
        sa.Column(
            "latest_commit_timestamp",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Create process_versions table
    op.create_table(
        "process_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "process_definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("process_definitions.id"),
            nullable=False,
        ),
        sa.Column(
            "parent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("process_versions.id"),
            nullable=True,
        ),
        sa.Column("version_number", sa.String(50), nullable=False),
        sa.Column("major_version", sa.Integer(), nullable=False),
        sa.Column("minor_version", sa.Integer(), nullable=False),
        sa.Column("patch_version", sa.Integer(), nullable=False),
        sa.Column(
            "branch_type",
            sa.Enum("MAIN", "FEATURE", "HOTFIX", "DEVELOPMENT", name="branchtype"),
            nullable=False,
            default="MAIN",
        ),
        sa.Column("branch_name", sa.String(255), nullable=True),
        sa.Column("commit_message", sa.Text(), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("bpmn_xml_snapshot", sa.Text(), nullable=False),
        sa.Column("variable_definitions_snapshot", sa.JSON(), nullable=False, default="[]"),
        sa.Column("is_current", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow,
        ),
    )

    # Create process_element_changes table
    op.create_table(
        "process_element_changes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("process_versions.id"),
            nullable=False,
        ),
        sa.Column("element_id", sa.String(255), nullable=False),
        sa.Column("element_type", sa.String(100), nullable=False),
        sa.Column(
            "change_type",
            sa.Enum("ADDED", "MODIFIED", "DELETED", "MOVED", "RENAMED", name="changetype"),
            nullable=False,
        ),
        sa.Column("previous_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow,
        ),
    )

    # Create indexes for better query performance
    op.create_index(
        "ix_process_versions_process_definition_id",
        "process_versions",
        ["process_definition_id"],
    )
    op.create_index(
        "ix_process_versions_version_number",
        "process_versions",
        ["version_number"],
    )
    op.create_index(
        "ix_process_versions_is_current",
        "process_versions",
        ["is_current"],
    )
    op.create_index(
        "ix_process_element_changes_version_id",
        "process_element_changes",
        ["version_id"],
    )
    op.create_index(
        "ix_process_element_changes_element_id",
        "process_element_changes",
        ["element_id"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_process_element_changes_element_id", "process_element_changes")
    op.drop_index("ix_process_element_changes_version_id", "process_element_changes")
    op.drop_index("ix_process_versions_is_current", "process_versions")
    op.drop_index("ix_process_versions_version_number", "process_versions")
    op.drop_index("ix_process_versions_process_definition_id", "process_versions")

    # Drop tables
    op.drop_table("process_element_changes")
    op.drop_table("process_versions")

    # Drop version metadata columns from process_definitions
    op.drop_column("process_definitions", "latest_commit_timestamp")
    op.drop_column("process_definitions", "latest_commit_author")
    op.drop_column("process_definitions", "latest_commit_message")
    op.drop_column("process_definitions", "current_branch")
    op.drop_column("process_definitions", "current_version_number")

    # Drop enum types
    sa.Enum(name="changetype").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="branchtype").drop(op.get_bind(), checkfirst=False) 