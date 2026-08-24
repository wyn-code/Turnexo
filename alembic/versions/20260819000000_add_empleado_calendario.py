"""Add empleado calendario columns

Revision ID: 20260819000000
Revises: 20260818000002
Create Date: 2026-08-19 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260819000000"
down_revision: Union[str, Sequence[str], None] = "20260818000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("empleado", sa.Column("calendario_token", sa.String(64), unique=True, nullable=True))
    op.add_column("empleado", sa.Column("calendario_token_revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("empleado", sa.Column("calendario_enviado_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("empleado", "calendario_enviado_at")
    op.drop_column("empleado", "calendario_token_revoked_at")
    op.drop_column("empleado", "calendario_token")