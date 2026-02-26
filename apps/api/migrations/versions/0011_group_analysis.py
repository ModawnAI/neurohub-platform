"""Add group analysis tables (group_studies, group_study_members).

Revision ID: 0011
Revises: 0009
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0011"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_studies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "institution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "service_id",
            UUID(as_uuid=True),
            sa.ForeignKey("service_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("analysis_type", sa.String(30), nullable=False),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("result", JSONB, nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_group_studies_institution_id", "group_studies", ["institution_id"])

    op.create_table(
        "group_study_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "study_id",
            UUID(as_uuid=True),
            sa.ForeignKey("group_studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("group_label", sa.String(100), nullable=False, server_default="default"),
        sa.Column("member_metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_group_study_members_study_id", "group_study_members", ["study_id"])


def downgrade() -> None:
    op.drop_table("group_study_members")
    op.drop_table("group_studies")
