"""Add model feedback, training jobs, and performance metrics tables.

Revision ID: 0014
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0014"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- model_feedback ---
    op.create_table(
        "model_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evaluation_id", UUID(as_uuid=True), sa.ForeignKey("evaluations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feedback_type", sa.String(30), nullable=False),
        sa.Column("original_output", JSONB, nullable=True),
        sa.Column("corrected_output", JSONB, nullable=True),
        sa.Column("ground_truth", JSONB, nullable=True),
        sa.Column("label_annotations", JSONB, nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("included_in_training", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("training_job_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_model_feedback_service_id", "model_feedback", ["service_id"])
    op.create_index("ix_model_feedback_run_id", "model_feedback", ["run_id"])
    op.create_index("ix_model_feedback_included", "model_feedback", ["included_in_training"])

    # --- model_training_jobs ---
    op.create_table(
        "model_training_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("base_artifact_id", UUID(as_uuid=True), nullable=True),
        sa.Column("result_artifact_id", UUID(as_uuid=True), nullable=True),
        sa.Column("feedback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feedback_ids", JSONB, nullable=True),
        sa.Column("hyperparameters", JSONB, nullable=True),
        sa.Column("training_metrics", JSONB, nullable=True),
        sa.Column("celery_task_id", sa.String(200), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_model_training_jobs_service_id", "model_training_jobs", ["service_id"])
    op.create_index("ix_model_training_jobs_status", "model_training_jobs", ["status"])

    # --- model_performance_metrics ---
    op.create_table(
        "model_performance_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metric_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("sensitivity", sa.Float(), nullable=True),
        sa.Column("specificity", sa.Float(), nullable=True),
        sa.Column("auc_roc", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("avg_latency_s", sa.Float(), nullable=True),
        sa.Column("p95_latency_s", sa.Float(), nullable=True),
        sa.Column("total_runs", sa.Integer(), nullable=True),
        sa.Column("failure_rate", sa.Float(), nullable=True),
        sa.Column("expert_approval_rate", sa.Float(), nullable=True),
        sa.Column("evaluation_count", sa.Integer(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("service_id", "artifact_id", "metric_date", name="uq_perf_metrics"),
    )
    op.create_index("ix_model_performance_service_id", "model_performance_metrics", ["service_id"])


def downgrade() -> None:
    op.drop_table("model_performance_metrics")
    op.drop_table("model_training_jobs")
    op.drop_table("model_feedback")
