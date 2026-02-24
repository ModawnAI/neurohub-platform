"""Add dynamic service schema columns.

Revision ID: 0008
Revises: 0007
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_definitions", sa.Column("category", sa.String(100), nullable=True))
    op.add_column("service_definitions", sa.Column("input_schema", JSONB, nullable=True))
    op.add_column("service_definitions", sa.Column("upload_slots", JSONB, nullable=True))
    op.add_column("service_definitions", sa.Column("pricing", JSONB, nullable=True))
    op.add_column("service_definitions", sa.Column("output_schema", JSONB, nullable=True))
    op.add_column("service_definitions", sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("service_definitions", sa.Column("parent_service_id", sa.Uuid(), nullable=True))
    op.add_column("service_definitions", sa.Column("version_label", sa.String(30), nullable=False, server_default="1.0.0"))

    # Rename version (string) -> keep as version_label, add integer version
    # The old 'version' was string; we add an integer version column
    op.alter_column("service_definitions", "version", new_column_name="version_legacy", existing_type=sa.String(30))
    op.add_column("service_definitions", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    op.create_foreign_key(
        "fk_service_parent",
        "service_definitions",
        "service_definitions",
        ["parent_service_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_service_parent", "service_definitions", type_="foreignkey")
    op.drop_column("service_definitions", "version")
    op.alter_column("service_definitions", "version_legacy", new_column_name="version", existing_type=sa.String(30))
    op.drop_column("service_definitions", "version_label")
    op.drop_column("service_definitions", "parent_service_id")
    op.drop_column("service_definitions", "is_immutable")
    op.drop_column("service_definitions", "output_schema")
    op.drop_column("service_definitions", "pricing")
    op.drop_column("service_definitions", "upload_slots")
    op.drop_column("service_definitions", "input_schema")
    op.drop_column("service_definitions", "category")
