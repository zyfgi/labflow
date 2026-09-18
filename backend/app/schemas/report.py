from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.base import StrictSchema


def normalize_week_start(value: date) -> date:
    """Snap any date to the Monday of its week."""
    return date.fromordinal(value.toordinal() - value.weekday())


class WeeklyReportCreate(StrictSchema):
    week_start: date
    work_summary: str | None = Field(default=None, max_length=5000)
    learning_summary: str | None = Field(default=None, max_length=5000)
    experiment_summary: str | None = Field(default=None, max_length=5000)
    problems: str | None = Field(default=None, max_length=5000)
    next_week_plan: str | None = Field(default=None, max_length=5000)
    need_help: str | None = Field(default=None, max_length=5000)
    self_progress: int = Field(default=0, ge=0, le=100)

    _normalize = field_validator("week_start")(lambda v: normalize_week_start(v))


class WeeklyReportUpdate(StrictSchema):
    work_summary: str | None = Field(default=None, max_length=5000)
    learning_summary: str | None = Field(default=None, max_length=5000)
    experiment_summary: str | None = Field(default=None, max_length=5000)
    problems: str | None = Field(default=None, max_length=5000)
    next_week_plan: str | None = Field(default=None, max_length=5000)
    need_help: str | None = Field(default=None, max_length=5000)
    self_progress: int | None = Field(default=None, ge=0, le=100)


class WeeklyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    week_start: date
    week_end: date
    work_summary: str | None
    learning_summary: str | None
    experiment_summary: str | None
    problems: str | None
    next_week_plan: str | None
    need_help: str | None
    self_progress: int
    status: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WeeklyReportCommentCreate(StrictSchema):
    content: str = Field(min_length=1, max_length=2000)


class WeeklyReportCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    user_id: int
    content: str
    created_at: datetime


__all__ = [
    "WeeklyReportCommentCreate",
    "WeeklyReportCommentOut",
    "WeeklyReportCreate",
    "WeeklyReportOut",
    "WeeklyReportUpdate",
    "normalize_week_start",
]
