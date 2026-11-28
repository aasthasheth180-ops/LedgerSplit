from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Group(Base):
    __tablename__ = "groups"

    __table_args__ = (
        UniqueConstraint(
            "created_by",
            "idempotency_key",
            name="uq_groups_creator_idempotency",
        ),
        CheckConstraint(
            "category IN ('Home', 'Trip', 'Friends', 'Work', 'Other')",
            name="ck_groups_category",
        ),
        CheckConstraint(
            "(category = 'Other' AND custom_category IS NOT NULL "
            "AND length(trim(custom_category)) > 0) OR "
            "(category <> 'Other' AND custom_category IS NULL)",
            name="ck_groups_custom_category",
        ),
        CheckConstraint(
            "currency IN ('USD', 'EUR', 'GBP', 'CAD', 'JPY', 'INR')",
            name="ck_groups_currency",
        ),
        CheckConstraint(
            "default_split IN ('Equal', 'Exact', 'Percent')",
            name="ck_groups_default_split",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(140),
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(20),
        default="Home",
        server_default="Home",
        nullable=False,
    )

    custom_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        server_default="USD",
        nullable=False,
    )

    default_split: Mapped[str] = mapped_column(
        String(10),
        default="Equal",
        server_default="Equal",
        nullable=False,
    )

    color: Mapped[str] = mapped_column(
        String(7),
        default="#4a7856",
        server_default="#4a7856",
        nullable=False,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    request_fingerprint: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )