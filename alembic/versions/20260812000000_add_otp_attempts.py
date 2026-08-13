"""Add otp_attempts to usuarios

Revision ID: 20260812000000
Revises: 20260727000000
Create Date: 2026-08-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812000000"
down_revision: Union[str, Sequence[str], None] = "20260727000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "otp_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "otp_attempts")
