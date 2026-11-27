from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_payment_requests_positive_amount",
        ),
        CheckConstraint(
            "requester_id <> debtor_id",
            name="ck_payment_requests_different_users",
        ),
        CheckConstraint(
            "status IN ('pending', 'fulfilled', 'cancelled')",
            name="ck_payment_requests_valid_status",
        ),
        CheckConstraint(
            "fulfilled_amount >= 0 AND fulfilled_amount <= amount",
            name="ck_payment_requests_fulfilled_amount",
        ),
        UniqueConstraint(
            "group_id",
            "requester_id",
            "idempotency_key",
            name="uq_payment_requests_idempotency",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id"),
        nullable=False,
        index=True,
    )

    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    debtor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    fulfilled_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    due_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )