"""Add google_id to usuarios for account linking

Revision ID: 20260811000000
Revises: 20260727000000
Create Date: 2026-08-11 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260811000000"
down_revision: Union[str, Sequence[str], None] = "20260727000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "google_id",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_usuarios_google_id",
        "usuarios",
        ["google_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_usuarios_google_id", table_name="usuarios")
    op.drop_column("usuarios", "google_id")
