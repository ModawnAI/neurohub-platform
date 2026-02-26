"""Add extended fields to runs table.

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("progress_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column("runs", sa.Column("current_step", sa.String(200), nullable=True))
    op.add_column("runs", sa.Column("output_data", JSONB, nullable=True))
    op.add_column("runs", sa.Column("metrics", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "metrics")
    op.drop_column("runs", "output_data")
    op.drop_column("runs", "current_step")
    op.drop_column("runs", "progress_pct")
