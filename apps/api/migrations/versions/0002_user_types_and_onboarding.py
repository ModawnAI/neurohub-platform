"""user_types_and_onboarding

Revision ID: 0002_user_types
Revises: 0001_initial_prd
Create Date: 2026-02-21 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_types"
down_revision: Union[str, None] = "0001_initial_prd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- users table: add user_type, onboarding, expert fields --
    op.add_column("users", sa.Column("user_type", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("phone", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("specialization", sa.String(length=200), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("expert_status", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("expert_approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("expert_approved_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_users_expert_approved_by",
        "users",
        "users",
        ["expert_approved_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- institutions table: add type, contact fields --
    op.add_column("institutions", sa.Column("institution_type", sa.String(length=20), nullable=False, server_default=sa.text("'HOSPITAL'")))
    op.add_column("institutions", sa.Column("contact_email", sa.String(length=200), nullable=True))
    op.add_column("institutions", sa.Column("contact_phone", sa.String(length=30), nullable=True))
    op.add_column("institutions", sa.Column("created_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_institutions_created_by",
        "institutions",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- institution_invites table --
    op.create_table(
        "institution_invites",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("role_scope", sa.String(length=50), nullable=True),
        sa.Column("invite_token", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("invite_token"),
    )
    op.create_index("ix_institution_invites_institution_id", "institution_invites", ["institution_id"])


def downgrade() -> None:
    op.drop_table("institution_invites")
    op.drop_constraint("fk_institutions_created_by", "institutions", type_="foreignkey")
    op.drop_column("institutions", "created_by")
    op.drop_column("institutions", "contact_phone")
    op.drop_column("institutions", "contact_email")
    op.drop_column("institutions", "institution_type")
    op.drop_constraint("fk_users_expert_approved_by", "users", type_="foreignkey")
    op.drop_column("users", "expert_approved_by")
    op.drop_column("users", "expert_approved_at")
    op.drop_column("users", "expert_status")
    op.drop_column("users", "bio")
    op.drop_column("users", "specialization")
    op.drop_column("users", "phone")
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "user_type")
