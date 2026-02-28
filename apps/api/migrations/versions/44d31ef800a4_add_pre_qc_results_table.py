"""add pre_qc_results table

Revision ID: 44d31ef800a4
Revises: b810d3e3d41b
Create Date: 2026-02-28 18:20:37.406850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '44d31ef800a4'
down_revision: Union[str, None] = 'b810d3e3d41b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('pre_qc_results',
        sa.Column('case_file_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('institution_id', sa.UUID(), nullable=False),
        sa.Column('modality', sa.String(length=30), nullable=False),
        sa.Column('check_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('message_ko', sa.Text(), nullable=True),
        sa.Column('message_en', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_file_id'], ['case_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pre_qc_results_case_file_id'), 'pre_qc_results', ['case_file_id'], unique=False)
    op.create_index(op.f('ix_pre_qc_results_case_id'), 'pre_qc_results', ['case_id'], unique=False)
    op.create_index(op.f('ix_pre_qc_results_institution_id'), 'pre_qc_results', ['institution_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pre_qc_results_institution_id'), table_name='pre_qc_results')
    op.drop_index(op.f('ix_pre_qc_results_case_id'), table_name='pre_qc_results')
    op.drop_index(op.f('ix_pre_qc_results_case_file_id'), table_name='pre_qc_results')
    op.drop_table('pre_qc_results')
