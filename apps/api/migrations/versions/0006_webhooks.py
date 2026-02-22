"""Add webhooks table.

Revision ID: 0006_webhooks
Revises: 0005_api_key_scopes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0006_webhooks"
down_revision = "0005_api_key_scopes"


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("secret_hash", sa.String(128), nullable=False),
        sa.Column("events", JSONB, default=list),
        sa.Column("status", sa.String(20), default="ACTIVE"),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True)),
        sa.Column("failure_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("webhooks")
