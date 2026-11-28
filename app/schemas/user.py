from datetime import datetime
from typing import Literal
from pydantic import field_validator

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class GoogleLogin(BaseModel):
    credential: str = Field(
        min_length=1,
        max_length=8192,
    )
    remember_me: bool = False
    accepted_terms: bool = False

class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=1, max_length=100)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class Preferences(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    preferred_currency: Literal["USD", "EUR", "GBP", "CAD", "JPY", "INR"]
    reminders_enabled: bool


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
