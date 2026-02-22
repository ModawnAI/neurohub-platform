"""Add scopes column to institution_api_keys.

Revision ID: 0005_api_key_scopes
Revises: 0004_add_indexes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_api_key_scopes"
down_revision = "0004_add_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "institution_api_keys",
        sa.Column("scopes", JSONB, nullable=True, server_default='["read", "write"]'),
    )


def downgrade() -> None:
    op.drop_column("institution_api_keys", "scopes")
