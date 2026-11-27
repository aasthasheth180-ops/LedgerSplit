from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


GroupCategory = Literal[
    "Home", "Trip", "Friends", "Work", "Other"
]

GroupCurrency = Literal[
    "USD", "EUR", "GBP", "CAD", "JPY", "INR"
]

SplitMethod = Literal[
    "Equal", "Exact", "Percent"
]


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    description: str | None = Field(
        default=None,
        max_length=140,
    )

    category: GroupCategory = "Home"

    custom_category: str | None = Field(
        default=None,
        max_length=50,
    )

    currency: GroupCurrency = "USD"

    default_split: SplitMethod = "Equal"

    color: str = Field(
        default="#4a7856",
        pattern=r"^#[0-9a-fA-F]{6}$",
    )

    member_emails: list[EmailStr] = Field(
        default_factory=list,
        max_length=50,
    )

    @field_validator(
        "name",
        "description",
        "custom_category",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def validate_group(self):
        if self.category == "Other":
            if not self.custom_category:
                raise ValueError(
                    "Custom category is required for Other"
                )
        elif self.custom_category is not None:
            raise ValueError(
                "Custom category is only allowed for Other"
            )

        emails = [
            str(email).lower()
            for email in self.member_emails
        ]

        if len(emails) != len(set(emails)):
            raise ValueError(
                "Member email addresses must be unique"
            )

        self.member_emails = emails

        return self


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    category: GroupCategory
    custom_category: str | None
    currency: GroupCurrency
    default_split: SplitMethod
    color: str
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupMemberAdd(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    email: EmailStr | None = None

    @model_validator(mode="after")
    def validate_member_identifier(self):
        if (self.user_id is None) == (self.email is None):
            raise ValueError(
                "Provide either user_id or email"
            )

        if self.email is not None:
            self.email = str(self.email).lower()

        return self


class GroupMemberResponse(BaseModel):
    id: int
    group_id: int
    user_id: int
    role: str
    joined_at: datetime

    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)