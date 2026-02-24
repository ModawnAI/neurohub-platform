"""Add additional indexes for hot query paths.

Revision ID: 0008_additional_indexes
Revises: 0007_rls_policies
"""

from alembic import op

revision = "0008_additional_indexes"
down_revision = "0007_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS to be idempotent
    op.execute("CREATE INDEX IF NOT EXISTS idx_run_steps_run ON run_steps (run_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_report_reviews_report ON report_reviews (report_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_qc_decisions_request ON qc_decisions (request_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_reports_request_created ON reports (request_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_patient_access_institution_created"
        " ON patient_access_logs (institution_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_api_keys_institution_status"
        " ON institution_api_keys (institution_id, status)"
        " WHERE status = 'ACTIVE'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_usage_ledger_billing"
        " ON usage_ledger (institution_id, service_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_usage_ledger_billing")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_institution_status")
    op.execute("DROP INDEX IF EXISTS idx_patient_access_institution_created")
    op.execute("DROP INDEX IF EXISTS idx_reports_request_created")
    op.execute("DROP INDEX IF EXISTS idx_qc_decisions_request")
    op.execute("DROP INDEX IF EXISTS idx_report_reviews_report")
    op.execute("DROP INDEX IF EXISTS idx_run_steps_run")
