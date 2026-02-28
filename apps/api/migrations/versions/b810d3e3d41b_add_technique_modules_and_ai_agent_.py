"""add_technique_modules_and_ai_agent_tables

Revision ID: b810d3e3d41b
Revises: df7879c4042a
Create Date: 2026-02-28 17:28:50.645984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b810d3e3d41b'
down_revision: Union[str, None] = 'df7879c4042a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New tables ---
    op.create_table('technique_modules',
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('title_ko', sa.String(length=200), nullable=False),
    sa.Column('title_en', sa.String(length=200), nullable=False),
    sa.Column('modality', sa.String(length=30), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('docker_image', sa.String(length=500), nullable=False),
    sa.Column('version', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('qc_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('output_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('resource_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )

    op.create_table('service_technique_weights',
    sa.Column('service_id', sa.UUID(), nullable=False),
    sa.Column('technique_module_id', sa.UUID(), nullable=False),
    sa.Column('base_weight', sa.Float(), nullable=False),
    sa.Column('is_required', sa.Boolean(), nullable=False),
    sa.Column('override_qc_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['service_id'], ['service_definitions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['technique_module_id'], ['technique_modules.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('service_id', 'technique_module_id', name='uq_service_technique')
    )
    op.create_index(op.f('ix_service_technique_weights_service_id'), 'service_technique_weights', ['service_id'], unique=False)
    op.create_index(op.f('ix_service_technique_weights_technique_module_id'), 'service_technique_weights', ['technique_module_id'], unique=False)

    op.create_table('ai_agent_runs',
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('agent_type', sa.String(length=50), nullable=False, comment='PRE_QC_REVIEW, REPORT_NARRATIVE, CLINICAL_SUMMARY, QC_ANOMALY'),
    sa.Column('model_id', sa.String(length=100), nullable=False),
    sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('tokens_used', sa.Integer(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_agent_runs_run_id'), 'ai_agent_runs', ['run_id'], unique=False)

    op.create_table('technique_runs',
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('technique_module_id', sa.UUID(), nullable=False),
    sa.Column('technique_key', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('job_spec', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('qc_score', sa.Float(), nullable=True),
    sa.Column('celery_task_id', sa.String(length=200), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['technique_module_id'], ['technique_modules.id']),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_technique_runs_run_id'), 'technique_runs', ['run_id'], unique=False)

    # --- Add columns to existing tables (idempotent) ---
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    sd_cols = [c['name'] for c in inspector.get_columns('service_definitions')]
    if 'clinical_config' not in sd_cols:
        op.add_column('service_definitions', sa.Column('clinical_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='fusion_method, qc_policy, clinical_purpose, report_structure, icon_key'))

    user_cols = [c['name'] for c in inspector.get_columns('users')]
    if 'password_hash' not in user_cols:
        op.add_column('users', sa.Column('password_hash', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_hash')
    op.drop_column('service_definitions', 'clinical_config')
    op.drop_index(op.f('ix_technique_runs_run_id'), table_name='technique_runs')
    op.drop_table('technique_runs')
    op.drop_index(op.f('ix_ai_agent_runs_run_id'), table_name='ai_agent_runs')
    op.drop_table('ai_agent_runs')
    op.drop_index(op.f('ix_service_technique_weights_technique_module_id'), table_name='service_technique_weights')
    op.drop_index(op.f('ix_service_technique_weights_service_id'), table_name='service_technique_weights')
    op.drop_table('service_technique_weights')
    op.drop_table('technique_modules')
