from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import MEMBER_STATUSES, MEMBER_TYPES
from app.schemas.base import StrictSchema
from app.schemas.user import UserOut


def _check_member_type(value: str | None) -> str | None:
    if value is not None and value not in MEMBER_TYPES:
        raise ValueError(f"无效的成员类型: {value}")
    return value


def _check_member_status(value: str | None) -> str | None:
    if value is not None and value not in MEMBER_STATUSES:
        raise ValueError(f"无效的成员状态: {value}")
    return value


class MemberCreate(StrictSchema):
    user_id: int
    student_no: str | None = Field(default=None, max_length=30)
    member_type: str = "master"
    grade_year: str | None = Field(default=None, max_length=20)
    research_direction: str | None = Field(default=None, max_length=200)
    join_date: date | None = None
    expected_leave_date: date | None = None
    supervisor_id: int | None = None
    office_location: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=2000)
    status: str = "active"

    _type_v = field_validator("member_type")(_check_member_type)
    _status_v = field_validator("status")(_check_member_status)


class MemberUpdate(StrictSchema):
    student_no: str | None = Field(default=None, max_length=30)
    member_type: str | None = None
    grade_year: str | None = Field(default=None, max_length=20)
    research_direction: str | None = Field(default=None, max_length=200)
    join_date: date | None = None
    expected_leave_date: date | None = None
    supervisor_id: int | None = None
    office_location: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=2000)
    status: str | None = None

    _type_v = field_validator("member_type")(_check_member_type)
    _status_v = field_validator("status")(_check_member_status)


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    student_no: str | None
    member_type: str
    grade_year: str | None
    research_direction: str | None
    join_date: date | None
    expected_leave_date: date | None
    supervisor_id: int | None
    office_location: str | None
    bio: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class MemberDetailOut(MemberOut):
    user: UserOut


class MemberOverviewOut(BaseModel):
    member: MemberOut
    user: UserOut
    current_projects: list[dict]
    in_progress_tasks: int
    overdue_tasks: int
    this_week_report_status: str | None
    latest_experiment_date: date | None


def validate_member_type(value: str) -> str:
    if value not in MEMBER_TYPES:
        raise ValueError(f"无效的成员类型: {value}")
    return value


def validate_member_status(value: str) -> str:
    if value not in MEMBER_STATUSES:
        raise ValueError(f"无效的成员状态: {value}")
    return value


__all__ = [
    "MEMBER_STATUSES",
    "MEMBER_TYPES",
    "MemberCreate",
    "MemberDetailOut",
    "MemberOut",
    "MemberOverviewOut",
    "MemberUpdate",
    "UserOut",
    "validate_member_status",
    "validate_member_type",
]
