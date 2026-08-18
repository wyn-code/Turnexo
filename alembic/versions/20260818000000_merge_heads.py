"""Merge heads (20260811000000 + 20260812000000)

Revision ID: 20260818000000
Revises: 20260811000000, 20260812000000
Create Date: 2026-08-18 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260818000000"
down_revision: Union[str, Sequence[str], None] = (
    "20260811000000",
    "20260812000000",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass