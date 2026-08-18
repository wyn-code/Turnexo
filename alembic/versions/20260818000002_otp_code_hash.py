"""Enlarge otp_code to store HMAC-SHA256 hash

Revision ID: 20260818000002
Revises: 20260818000001
Create Date: 2026-08-18 00:00:02.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260818000002"
down_revision: Union[str, Sequence[str], None] = "20260818000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "usuarios",
        "otp_code",
        existing_type=sa.String(length=10),
        type_=sa.String(length=64),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "usuarios",
        "otp_code",
        existing_type=sa.String(length=64),
        type_=sa.String(length=10),
        existing_nullable=True,
    )