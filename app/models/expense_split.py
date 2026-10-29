
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    __table_args__ = (
        UniqueConstraint(
            "expense_id",
            "user_id",
            name="uq_expense_splits_expense_user",
        ),
        CheckConstraint(
            "amount_owed >= 0",
            name="ck_expense_splits_nonnegative_amount",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id"),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    amount_owed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
