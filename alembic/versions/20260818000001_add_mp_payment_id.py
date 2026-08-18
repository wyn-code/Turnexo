"""Add mp_payment_id to suscripciones

Revision ID: 20260818000001
Revises: 20260818000000
Create Date: 2026-08-18 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260818000001"
down_revision: Union[str, Sequence[str], None] = "20260818000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "suscripciones",
        sa.Column(
            "mp_payment_id",
            sa.String(length=150),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_suscripciones_mp_payment_id",
        "suscripciones",
        ["mp_payment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_suscripciones_mp_payment_id",
        "suscripciones",
        type_="unique",
    )
    op.drop_column("suscripciones", "mp_payment_id")