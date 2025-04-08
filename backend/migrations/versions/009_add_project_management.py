"""Add project management tables.

Revision ID: 009
Revises: 008_create_process_versions_table
Create Date: 2025-04-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008_create_process_versions_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema with project management tables."""
    # Create project_roles table
    op.create_table(
        "project_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ACTIVE", "ARCHIVED", "COMPLETED", name="projectstatus"),
            nullable=False,
        ),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create project_members table
    op.create_table(
        "project_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "role_id", UUID(as_uuid=True), sa.ForeignKey("project_roles.id"), nullable=False
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create project_descriptions table
    op.create_table(
        "project_descriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create description_tags association table
    op.create_table(
        "description_tags",
        sa.Column(
            "description_id",
            UUID(as_uuid=True),
            sa.ForeignKey("project_descriptions.id"),
            primary_key=True,
        ),
        sa.Column("tag_id", UUID(as_uuid=True), sa.ForeignKey("tags.id"), primary_key=True),
    )

    # Add project_id and source_description_id columns to process_definitions table
    op.add_column(
        "process_definitions",
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
    )
    op.add_column(
        "process_definitions",
        sa.Column(
            "source_description_id",
            UUID(as_uuid=True),
            sa.ForeignKey("project_descriptions.id"),
            nullable=True,
        ),
    )
    
    # Add project_id and context columns to chat_sessions table
    op.add_column(
        "chat_sessions",
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("context", sa.Text(), nullable=True),
    )

    # Create indexes
    op.create_index(
        "ix_projects_owner_id", "projects", ["owner_id"], unique=False
    )
    op.create_index(
        "ix_chat_sessions_project_id", "chat_sessions", ["project_id"], unique=False
    )
    op.create_index(
        "ix_project_members_project_id", "project_members", ["project_id"], unique=False
    )
    op.create_index(
        "ix_project_members_user_id", "project_members", ["user_id"], unique=False
    )
    op.create_index(
        "ix_project_descriptions_project_id",
        "project_descriptions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_process_definitions_project_id",
        "process_definitions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_process_definitions_source_description_id",
        "process_definitions",
        ["source_description_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema by removing project management tables."""
    # Remove indexes
    op.drop_index("ix_process_definitions_source_description_id", "process_definitions")
    op.drop_index("ix_process_definitions_project_id", "process_definitions")
    op.drop_index("ix_project_descriptions_project_id", "project_descriptions")
    op.drop_index("ix_project_members_user_id", "project_members")
    op.drop_index("ix_project_members_project_id", "project_members")
    op.drop_index("ix_projects_owner_id", "projects")
    op.drop_index("ix_chat_sessions_project_id", "chat_sessions")

    # Remove columns from process_definitions and chat_sessions
    op.drop_column("process_definitions", "source_description_id")
    op.drop_column("process_definitions", "project_id")
    op.drop_column("chat_sessions", "project_id")
    op.drop_column("chat_sessions", "context")

    # Drop tables
    op.drop_table("description_tags")
    op.drop_table("project_descriptions")
    op.drop_table("tags")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("project_roles")

    # Drop enum type
    op.execute("DROP TYPE projectstatus")
