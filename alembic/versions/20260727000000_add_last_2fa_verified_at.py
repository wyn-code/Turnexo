"""Add last_2fa_verified_at to usuarios

Revision ID: 20260727000000
Revises: 20260723000000
Create Date: 2026-07-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727000000"
down_revision: Union[str, Sequence[str], None] = "20260723000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "last_2fa_verified_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "last_2fa_verified_at")
