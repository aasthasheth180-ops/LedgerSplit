from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_payments_positive_amount",
        ),
        CheckConstraint(
            "from_user_id <> to_user_id",
            name="ck_payments_different_users",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'rejected')",
            name="ck_payments_valid_status",
        ),
        UniqueConstraint(
            "group_id",
            "from_user_id",
            "idempotency_key",
            name="uq_payments_group_sender_idempotency",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id"),
        nullable=False,
    )

    from_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    to_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
)

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )