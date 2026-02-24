"""Add evaluations, payments, and service evaluation support.

New tables: service_evaluators, evaluations, payments
New columns: service_definitions.service_type, service_definitions.requires_evaluator
New columns: reports.watermarked_storage_path

Revision ID: 0009
Revises: 0008_merge
Create Date: 2026-02-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0009"
down_revision = "0008_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- service_definitions: add service_type and requires_evaluator ---
    op.add_column(
        "service_definitions",
        sa.Column("service_type", sa.String(30), nullable=True),
    )
    op.add_column(
        "service_definitions",
        sa.Column("requires_evaluator", sa.Boolean(), nullable=True),
    )
    # Backfill defaults
    op.execute("UPDATE service_definitions SET service_type = 'AUTOMATIC' WHERE service_type IS NULL")
    op.execute("UPDATE service_definitions SET requires_evaluator = false WHERE requires_evaluator IS NULL")
    # Set NOT NULL
    op.alter_column("service_definitions", "service_type", nullable=False)
    op.alter_column("service_definitions", "requires_evaluator", nullable=False)

    # --- reports: add watermarked_storage_path ---
    op.add_column(
        "reports",
        sa.Column("watermarked_storage_path", sa.String(1000), nullable=True),
    )

    # --- service_evaluators ---
    op.create_table(
        "service_evaluators",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("service_id", "user_id", name="uq_service_evaluator"),
    )
    op.create_index("ix_service_evaluators_service_id", "service_evaluators", ["service_id"])
    op.create_index("ix_service_evaluators_user_id", "service_evaluators", ["user_id"])
    op.create_index("ix_service_evaluators_institution_id", "service_evaluators", ["institution_id"])

    # --- evaluations ---
    op.create_table(
        "evaluations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evaluator_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("watermark_text", sa.String(500), nullable=True),
        sa.Column("output_storage_path", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evaluations_institution_id", "evaluations", ["institution_id"])
    op.create_index("ix_evaluations_request_id", "evaluations", ["request_id"])

    # --- payments ---
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", sa.String(100), nullable=False, unique=True),
        sa.Column("payment_key", sa.String(200), nullable=True, unique=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default=sa.text("'KRW'")),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("method", sa.String(50), nullable=True),
        sa.Column("toss_response", JSONB, nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_payments_institution_id", "payments", ["institution_id"])
    op.create_index("ix_payments_request_id", "payments", ["request_id"])
    op.create_index("ix_payments_order_id", "payments", ["order_id"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("evaluations")
    op.drop_table("service_evaluators")
    op.drop_column("reports", "watermarked_storage_path")
    op.drop_column("service_definitions", "requires_evaluator")
    op.drop_column("service_definitions", "service_type")
