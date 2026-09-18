from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ALL_ROLES
from app.schemas.base import StrictSchema


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


def _validate_email(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    # lightweight check: keep intranet/edu domains usable (EmailStr rejects
    # reserved names like .local / example.com which are handy in dev/tests)
    if "@" not in value or value.startswith("@") or value.endswith("@") or " " in value:
        raise ValueError("邮箱格式不正确")
    return value


class UserBase(BaseModel):
    username: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    role: str = "STUDENT"
    status: str = "active"

    _validate_email_value = field_validator("email")(_validate_email)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(StrictSchema):
    name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    avatar_url: str | None = Field(default=None, max_length=500)
    role: str | None = None
    status: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)

    _validate_email_value = field_validator("email")(_validate_email)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    email: str
    phone: str | None
    avatar_url: str | None
    role: str
    status: str
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    user: UserOut


__all__ = [
    "ALL_ROLES",
    "ChangePasswordRequest",
    "LoginRequest",
    "TokenOut",
    "UserBase",
    "UserCreate",
    "UserOption",
    "UserOut",
    "UserUpdate",
]
