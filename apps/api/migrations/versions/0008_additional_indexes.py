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
    # run_steps queried by run_id in reviews.py
    op.create_index("idx_run_steps_run", "run_steps", ["run_id"])

    # report_reviews queried by report_id in reviews.py
    op.create_index("idx_report_reviews_report", "report_reviews", ["report_id"])

    # qc_decisions queried by request_id + created_at in reviews.py
    op.create_index("idx_qc_decisions_request", "qc_decisions", ["request_id", "created_at"])

    # reports queried by request_id + created_at in reviews.py
    op.create_index("idx_reports_request_created", "reports", ["request_id", "created_at"])

    # patient_access_logs queried by institution_id + created_at for audit
    op.create_index(
        "idx_patient_access_institution_created",
        "patient_access_logs",
        ["institution_id", "created_at"],
    )

    # institution_api_keys lookup by key_prefix
    op.create_index(
        "idx_api_keys_institution_active",
        "institution_api_keys",
        ["institution_id", "is_active"],
        postgresql_where="is_active = true",
    )

    # usage_ledger billing queries by institution + period
    op.create_index(
        "idx_usage_ledger_billing",
        "usage_ledger",
        ["institution_id", "period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_index("idx_usage_ledger_billing")
    op.drop_index("idx_api_keys_institution_active")
    op.drop_index("idx_patient_access_institution_created")
    op.drop_index("idx_reports_request_created")
    op.drop_index("idx_qc_decisions_request")
    op.drop_index("idx_report_reviews_report")
    op.drop_index("idx_run_steps_run")
