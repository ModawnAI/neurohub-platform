"""Add missing foreign key indexes for query performance.

Revision ID: 0010_add_fk_indexes
Revises: a0a895db89cc
Create Date: 2026-02-26
"""

from alembic import op

revision = "0010_add_fk_indexes"
down_revision = "a0a895db89cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_requests_service_id", "requests", ["service_id"])
    op.create_index("idx_requests_pipeline_id", "requests", ["pipeline_id"])
    op.create_index("idx_runs_case_id", "runs", ["case_id"])
    op.create_index("idx_services_inst_status_name", "service_definitions", ["institution_id", "status", "display_name"])


def downgrade() -> None:
    op.drop_index("idx_services_inst_status_name", "service_definitions")
    op.drop_index("idx_runs_case_id", "runs")
    op.drop_index("idx_requests_pipeline_id", "requests")
    op.drop_index("idx_requests_service_id", "requests")
