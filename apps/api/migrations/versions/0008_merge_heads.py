"""Merge two 0008 migration heads.

Revision ID: 0008_merge
Revises: 0008, 0008_additional_indexes
Create Date: 2026-02-24
"""

revision = "0008_merge"
down_revision = ("0008", "0008_additional_indexes")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
