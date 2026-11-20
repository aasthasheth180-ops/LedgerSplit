from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    to_user_id: int = Field(gt=0)

    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )


class PaymentResponse(BaseModel):
    id: int
    group_id: int
    from_user_id: int
    to_user_id: int
    amount: Decimal
    status: Literal["pending", "confirmed", "rejected"]
    created_at: datetime
    confirmed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)