"""add INR currency support

Revision ID: bca06b0bc606
Revises: b8962d851ab4
Create Date: 2026-11-27 02:17:07.512665
"""

from typing import Sequence, Union

from alembic import op


revision: str = "bca06b0bc606"
down_revision: Union[str, Sequence[str], None] = "b8962d851ab4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_groups_currency",
        "groups",
        type_="check",
    )

    op.create_check_constraint(
        "ck_groups_currency",
        "groups",
        "currency IN ('USD', 'EUR', 'GBP', 'CAD', 'JPY', 'INR')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_groups_currency",
        "groups",
        type_="check",
    )

    op.create_check_constraint(
        "ck_groups_currency",
        "groups",
        "currency IN ('USD', 'EUR', 'GBP', 'CAD', 'JPY')",
    )