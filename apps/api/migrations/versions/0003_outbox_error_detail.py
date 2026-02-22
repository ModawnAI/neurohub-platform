"""outbox_error_detail

Revision ID: 0003_outbox_err
Revises: 0002_user_types
Create Date: 2026-02-22 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_outbox_err"
down_revision: Union[str, None] = "0002_user_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("error_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("outbox_events", "error_detail")
