"""extend group categories and preferences

Revision ID: 195f526457a7
Revises: de05551bf8cb
Create Date: 2026-11-26 16:38:51.176626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '195f526457a7'
down_revision: Union[str, Sequence[str], None] = 'de05551bf8cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "groups",
        sa.Column("description", sa.String(140), nullable=True),
    )

    op.add_column(
        "groups",
        sa.Column(
            "category",
            sa.String(20),
            server_default="Home",
            nullable=False,
        ),
    )

    op.add_column(
        "groups",
        sa.Column("custom_category", sa.String(50), nullable=True),
    )

    op.add_column(
        "groups",
        sa.Column(
            "currency",
            sa.String(3),
            server_default="USD",
            nullable=False,
        ),
    )

    op.add_column(
        "groups",
        sa.Column(
            "default_split",
            sa.String(10),
            server_default="Equal",
            nullable=False,
        ),
    )

    op.add_column(
        "groups",
        sa.Column(
            "color",
            sa.String(7),
            server_default="#4a7856",
            nullable=False,
        ),
    )

    op.create_check_constraint(
        "ck_groups_category",
        "groups",
        "category IN ('Home', 'Trip', 'Friends', 'Work', 'Other')",
    )

    op.create_check_constraint(
        "ck_groups_custom_category",
        "groups",
        "(category = 'Other' AND custom_category IS NOT NULL "
        "AND length(trim(custom_category)) > 0) OR "
        "(category <> 'Other' AND custom_category IS NULL)",
    )

    op.create_check_constraint(
        "ck_groups_currency",
        "groups",
        "currency IN ('USD', 'EUR', 'GBP', 'CAD', 'JPY')",
    )

    op.create_check_constraint(
        "ck_groups_default_split",
        "groups",
        "default_split IN ('Equal', 'Exact', 'Percent')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_groups_default_split",
        "groups",
        type_="check",
    )

    op.drop_constraint(
        "ck_groups_currency",
        "groups",
        type_="check",
    )

    op.drop_constraint(
        "ck_groups_custom_category",
        "groups",
        type_="check",
    )

    op.drop_constraint(
        "ck_groups_category",
        "groups",
        type_="check",
    )

    op.drop_column("groups", "color")
    op.drop_column("groups", "default_split")
    op.drop_column("groups", "currency")
    op.drop_column("groups", "custom_category")
    op.drop_column("groups", "category")
    op.drop_column("groups", "description")