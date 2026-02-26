"""Add DICOM Gateway tables (dicom_studies, dicom_series).

Revision ID: 0012
Revises: 0009
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0012"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dicom_studies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("study_instance_uid", sa.String(128), nullable=False),
        sa.Column("patient_id", sa.String(200), nullable=False, server_default=""),
        sa.Column("patient_name", sa.String(500)),
        sa.Column("study_date", sa.Date()),
        sa.Column("study_description", sa.String(500)),
        sa.Column("modality", sa.String(20)),
        sa.Column("num_series", sa.Integer, nullable=False, server_default="0"),
        sa.Column("num_instances", sa.Integer, nullable=False, server_default="0"),
        sa.Column("storage_prefix", sa.String(1000)),
        sa.Column("status", sa.String(20), nullable=False, server_default="RECEIVING"),
        sa.Column("source_aet", sa.String(64)),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dicom_metadata", JSONB),
        sa.UniqueConstraint("institution_id", "study_instance_uid", name="uq_dicom_study_institution_uid"),
    )
    op.create_index("ix_dicom_studies_institution_id", "dicom_studies", ["institution_id"])
    op.create_index("ix_dicom_studies_study_instance_uid", "dicom_studies", ["study_instance_uid"])
    op.create_index("ix_dicom_studies_status", "dicom_studies", ["status"])

    op.create_table(
        "dicom_series",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column("study_id", UUID(as_uuid=True), sa.ForeignKey("dicom_studies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("series_instance_uid", sa.String(128), nullable=False),
        sa.Column("series_number", sa.Integer),
        sa.Column("series_description", sa.String(500)),
        sa.Column("modality", sa.String(20)),
        sa.Column("num_instances", sa.Integer, nullable=False, server_default="0"),
        sa.Column("storage_prefix", sa.String(1000)),
    )
    op.create_index("ix_dicom_series_study_id", "dicom_series", ["study_id"])
    op.create_index("ix_dicom_series_series_instance_uid", "dicom_series", ["series_instance_uid"])


def downgrade() -> None:
    op.drop_table("dicom_series")
    op.drop_table("dicom_studies")
