"""Add indexes for hot query paths.

Revision ID: 0004_add_indexes
Revises: 0003_outbox_err
"""
from alembic import op

revision = "0004_add_indexes"
down_revision = "0003_outbox_err"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_requests_institution_status", "requests", ["institution_id", "status"])
    op.create_index("idx_requests_institution_created", "requests", ["institution_id", "created_at"])
    op.create_index(
        "idx_outbox_unprocessed", "outbox_events", ["processed_at", "created_at"],
        postgresql_where="processed_at IS NULL",
    )
    op.create_index("idx_audit_logs_institution", "audit_logs", ["institution_id", "created_at"])
    op.create_index("idx_usage_ledger_institution", "usage_ledger", ["institution_id", "created_at"])
    op.create_index(
        "idx_runs_stale", "runs", ["status", "heartbeat_at"],
        postgresql_where="status = 'RUNNING'",
    )
    op.create_index(
        "idx_notifications_unread", "notifications", ["user_id", "read_at"],
        postgresql_where="read_at IS NULL",
    )
    op.create_index("idx_cases_request", "cases", ["request_id"])
    op.create_index("idx_case_files_case", "case_files", ["case_id"])


def downgrade() -> None:
    op.drop_index("idx_case_files_case")
    op.drop_index("idx_cases_request")
    op.drop_index("idx_notifications_unread")
    op.drop_index("idx_runs_stale")
    op.drop_index("idx_usage_ledger_institution")
    op.drop_index("idx_audit_logs_institution")
    op.drop_index("idx_outbox_unprocessed")
    op.drop_index("idx_requests_institution_created")
    op.drop_index("idx_requests_institution_status")
