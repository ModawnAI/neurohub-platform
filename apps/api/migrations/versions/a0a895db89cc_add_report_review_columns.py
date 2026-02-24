"""add_report_review_columns

Revision ID: a0a895db89cc
Revises: 0009
Create Date: 2026-02-24 16:18:40.333644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a0a895db89cc'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to report_reviews
    op.add_column('report_reviews', sa.Column('severity', sa.String(length=20), nullable=True))
    op.add_column('report_reviews', sa.Column('category', sa.String(length=50), nullable=True))
    op.add_column('report_reviews', sa.Column('recommendation', sa.Text(), nullable=True))
    op.add_column('report_reviews', sa.Column('findings', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add description to webhooks
    op.add_column('webhooks', sa.Column('description', sa.String(length=500), nullable=True))

    # Create review_assignments table
    op.create_table('review_assignments',
        sa.Column('request_id', sa.UUID(), nullable=False),
        sa.Column('reviewer_id', sa.UUID(), nullable=False),
        sa.Column('assigned_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_assignments_request_id'), 'review_assignments', ['request_id'], unique=False)

    # Create webhook_delivery_logs table
    op.create_table('webhook_delivery_logs',
        sa.Column('webhook_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_delivery_logs_webhook_id'), 'webhook_delivery_logs', ['webhook_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_webhook_delivery_logs_webhook_id'), table_name='webhook_delivery_logs')
    op.drop_table('webhook_delivery_logs')
    op.drop_index(op.f('ix_review_assignments_request_id'), table_name='review_assignments')
    op.drop_table('review_assignments')
    op.drop_column('webhooks', 'description')
    op.drop_column('report_reviews', 'findings')
    op.drop_column('report_reviews', 'recommendation')
    op.drop_column('report_reviews', 'category')
    op.drop_column('report_reviews', 'severity')
