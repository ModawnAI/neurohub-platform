"""Add model artifacts and code security scans tables.

Revision ID: 0013
Revises: 0009
Down revision: 0009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0013"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artifact_type", sa.String(30), nullable=False),
        # artifact_type: 'weights' | 'script' | 'requirements' | 'dockerfile' | 'config' | 'test_data'
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("runtime", sa.String(30), nullable=True),
        # runtime: 'python3.11' | 'pytorch' | 'tensorflow' | 'onnxruntime' | 'custom'
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING_SCAN"),
        # PENDING_SCAN | SCANNING | APPROVED | REJECTED | FLAGGED
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("container_image", sa.String(500), nullable=True),
        sa.Column("container_image_digest", sa.String(100), nullable=True),
        sa.Column("build_status", sa.String(20), nullable=True),
        # PENDING | BUILDING | BUILT | FAILED
        sa.Column("build_log", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_model_artifacts_service_id", "model_artifacts", ["service_id"])
    op.create_index("ix_model_artifacts_institution_id", "model_artifacts", ["institution_id"])
    op.create_index("ix_model_artifacts_status", "model_artifacts", ["status"])

    op.create_table(
        "code_security_scans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("artifact_id", UUID(as_uuid=True), sa.ForeignKey("model_artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scanner", sa.String(50), nullable=False),
        # 'ast_check' | 'bandit' | 'pip_audit' | 'allowlist'
        sa.Column("status", sa.String(10), nullable=False),
        # 'PASS' | 'WARN' | 'FAIL'
        sa.Column("severity", sa.String(10), nullable=True),
        # 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
        sa.Column("findings", JSONB, nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_code_security_scans_artifact_id", "code_security_scans", ["artifact_id"])


def downgrade() -> None:
    op.drop_table("code_security_scans")
    op.drop_table("model_artifacts")
