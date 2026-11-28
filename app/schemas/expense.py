from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


ExpenseCategory = Literal[
    "Groceries",
    "Dining",
    "Home",
    "Utilities",
    "Travel",
    "Rent",
    "Other",
]

ExpenseSplitMethod = Literal[
    "Equal",
    "Exact",
    "Percent",
]


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

    category: ExpenseCategory = "Other"

    expense_date: date | None = None

    reference: str | None = Field(
        default=None,
        max_length=100,
    )

    split_method: ExpenseSplitMethod = "Exact"

    splits: list[ExpenseSplitCreate] = Field(
        min_length=1,
    )

    @field_validator("reference", mode="before")
    @classmethod
    def normalize_reference(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


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

    category: ExpenseCategory
    expense_date: date | None
    reference: str | None
    split_method: ExpenseSplitMethod

    created_at: datetime
    splits: list[ExpenseSplitResponse]

class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=255)
    category: ExpenseCategory
    expense_date: date | None
    reference: str | None = Field(max_length=100)

    @field_validator("description", "reference", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value
