"""dicom_gateway — DICOM studies/series tables + SCP metadata columns

Revision ID: 0012
Revises: a0a895db89cc
Create Date: 2026-02-26 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, None] = "a0a895db89cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # dicom_studies
    # ------------------------------------------------------------------
    op.create_table(
        "dicom_studies",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("study_instance_uid", sa.String(128), nullable=False),
        sa.Column("patient_id", sa.String(64), nullable=True),
        sa.Column("patient_name", sa.String(256), nullable=True),
        sa.Column("study_date", sa.Date(), nullable=True),
        sa.Column("study_description", sa.String(256), nullable=True),
        sa.Column("modality", sa.String(16), nullable=True),
        sa.Column("source_ae_title", sa.String(64), nullable=True),
        sa.Column(
            "received_via",
            sa.String(16),
            nullable=True,
            comment="STOW_RS or C_STORE",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "study_instance_uid", name="uq_dicom_study_uid"),
    )
    op.create_index(
        "ix_dicom_studies_institution_id", "dicom_studies", ["institution_id"]
    )
    op.create_index(
        "ix_dicom_studies_study_instance_uid", "dicom_studies", ["study_instance_uid"]
    )

    # ------------------------------------------------------------------
    # dicom_series
    # ------------------------------------------------------------------
    op.create_table(
        "dicom_series",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("series_instance_uid", sa.String(128), nullable=False),
        sa.Column("series_number", sa.Integer(), nullable=True),
        sa.Column("series_description", sa.String(256), nullable=True),
        sa.Column("modality", sa.String(16), nullable=True),
        sa.Column("instance_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["study_id"], ["dicom_studies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("study_id", "series_instance_uid", name="uq_dicom_series_uid"),
    )
    op.create_index(
        "ix_dicom_series_study_id", "dicom_series", ["study_id"]
    )


def downgrade() -> None:
    op.drop_table("dicom_series")
    op.drop_table("dicom_studies")
