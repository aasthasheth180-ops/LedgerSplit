"""add payment requests expense metadata and group idempotency

Revision ID: b8962d851ab4
Revises: 195f526457a7
Create Date: 2026-11-26 22:33:24.995575

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8962d851ab4"
down_revision: Union[str, Sequence[str], None] = "195f526457a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Create payment requests table.

    op.create_table(
        "payment_requests",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("debtor_id", sa.Integer(), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "fulfilled_amount",
            sa.Numeric(precision=12, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'fulfilled', 'cancelled')",
            name="ck_payment_requests_valid_status",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_payment_requests_positive_amount",
        ),
        sa.CheckConstraint(
            "fulfilled_amount >= 0 AND fulfilled_amount <= amount",
            name="ck_payment_requests_fulfilled_amount",
        ),
        sa.CheckConstraint(
            "requester_id <> debtor_id",
            name="ck_payment_requests_different_users",
        ),
        sa.ForeignKeyConstraint(
            ["debtor_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id",
            "requester_id",
            "idempotency_key",
            name="uq_payment_requests_idempotency",
        ),
    )

    op.create_index(
        op.f("ix_payment_requests_group_id"),
        "payment_requests",
        ["group_id"],
        unique=False,
    )

    # 2. Add expense metadata.

    op.add_column(
        "expenses",
        sa.Column(
            "category",
            sa.String(length=30),
            server_default="Other",
            nullable=False,
        ),
    )

    op.add_column(
        "expenses",
        sa.Column(
            "expense_date",
            sa.Date(),
            nullable=True,
        ),
    )

    op.add_column(
        "expenses",
        sa.Column(
            "reference",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "expenses",
        sa.Column(
            "split_method",
            sa.String(length=10),
            server_default="Exact",
            nullable=False,
        ),
    )

    # 3. Add missing expense check constraints.

    op.create_check_constraint(
        "ck_expenses_valid_category",
        "expenses",
        "category IN ('Groceries', 'Dining', 'Home', "
        "'Utilities', 'Travel', 'Rent', 'Other')",
    )

    op.create_check_constraint(
        "ck_expenses_valid_split_method",
        "expenses",
        "split_method IN ('Equal', 'Exact', 'Percent')",
    )

    # 4. Add group creation idempotency.

    op.add_column(
        "groups",
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=True,
        ),
    )

    op.add_column(
        "groups",
        sa.Column(
            "request_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_groups_creator_idempotency",
        "groups",
        ["created_by", "idempotency_key"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    # 1. Remove group idempotency.

    op.drop_constraint(
        "uq_groups_creator_idempotency",
        "groups",
        type_="unique",
    )

    op.drop_column("groups", "request_fingerprint")
    op.drop_column("groups", "idempotency_key")

    # 2. Remove expense check constraints.

    op.drop_constraint(
        "ck_expenses_valid_split_method",
        "expenses",
        type_="check",
    )

    op.drop_constraint(
        "ck_expenses_valid_category",
        "expenses",
        type_="check",
    )

    # 3. Remove expense metadata.

    op.drop_column("expenses", "split_method")
    op.drop_column("expenses", "reference")
    op.drop_column("expenses", "expense_date")
    op.drop_column("expenses", "category")

    # 4. Remove payment requests.

    op.drop_index(
        op.f("ix_payment_requests_group_id"),
        table_name="payment_requests",
    )

    op.drop_table("payment_requests")