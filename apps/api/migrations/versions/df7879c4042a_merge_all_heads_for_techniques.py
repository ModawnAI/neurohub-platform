"""merge_all_heads_for_techniques

Revision ID: df7879c4042a
Revises: 0010_add_fk_indexes, 0010, 0011, 0012, 0013, 0014
Create Date: 2026-02-28 17:24:52.192253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df7879c4042a'
down_revision: Union[str, None] = ('0010_add_fk_indexes', '0010', '0011', '0012', '0013', '0014')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

