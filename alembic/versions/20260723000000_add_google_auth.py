"""Add Google auth support

Revision ID: 20260723000000
Revises: 20260622173000
Create Date: 2026-07-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260723000000"
down_revision: Union[str, Sequence[str], None] = "20260622173000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "usuarios",
        "contrasena_us",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.add_column(
        "usuarios",
        sa.Column(
            "auth_provider",
            sa.String(length=20),
            nullable=False,
            server_default="local",
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "auth_provider")
    op.alter_column(
        "usuarios",
        "contrasena_us",
        existing_type=sa.String(length=255),
        nullable=False,
    )
