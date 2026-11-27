from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentRequestCreate(BaseModel):
    due_date: date | None = None
    debtor_id: int = Field(gt=0)

    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class PaymentRequestResponse(BaseModel):
    fulfilled_amount: Decimal
    due_date: date | None
    id: int
    group_id: int
    requester_id: int
    debtor_id: int
    amount: Decimal
    description: str | None

    status: Literal[
        "pending",
        "fulfilled",
        "cancelled",
    ]

    created_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)