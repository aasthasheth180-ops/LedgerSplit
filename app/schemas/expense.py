
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExpenseSplitCreate(BaseModel):
    user_id: int = Field(gt=0)
    amount_owed: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )


class ExpenseCreate(BaseModel):
    description: str = Field(
        min_length=1,
        max_length=255,
    )
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    splits: list[ExpenseSplitCreate] = Field(
        min_length=1,
    )


class ExpenseSplitResponse(BaseModel):
    id: int
    expense_id: int
    user_id: int
    amount_owed: Decimal

    model_config = ConfigDict(from_attributes=True)


class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    paid_by: int
    description: str
    amount: Decimal
    created_at: datetime
    splits: list[ExpenseSplitResponse]
