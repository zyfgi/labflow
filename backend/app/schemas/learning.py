from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PLAN_STATUSES, SKILL_LEVELS
from app.schemas.base import StrictSchema


class SkillCreate(StrictSchema):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(default="general", max_length=50)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int = 0
    is_active: bool = True


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    description: str | None
    sort_order: int
    is_active: bool


class MemberSkillItem(BaseModel):
    skill_id: int
    level: int
    note: str | None = Field(default=None, max_length=500)

    @field_validator("level")
    @classmethod
    def check_level(cls, v: int) -> int:
        if v not in SKILL_LEVELS:
            raise ValueError("技能等级必须是 0-4 之间的整数")
        return v


class MemberSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int
    level: int
    note: str | None
    updated_at: datetime


class LearningPlanCreate(StrictSchema):
    member_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(default="general", max_length=50)
    start_date: date | None = None
    target_date: date | None = None
    status: str = "not_started"
    progress: int = Field(default=0, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        return validate_plan_status(v)


class LearningPlanUpdate(StrictSchema):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=50)
    start_date: date | None = None
    target_date: date | None = None
    status: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str | None) -> str | None:
        return v if v is None else validate_plan_status(v)


class LearningPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    title: str
    description: str | None
    category: str
    start_date: date | None
    target_date: date | None
    status: str
    progress: int
    created_by: int | None
    created_at: datetime
    updated_at: datetime


def validate_plan_status(value: str) -> str:
    if value not in PLAN_STATUSES:
        raise ValueError(f"无效的学习计划状态: {value}")
    return value


__all__ = [
    "LearningPlanCreate",
    "LearningPlanOut",
    "LearningPlanUpdate",
    "MemberSkillItem",
    "MemberSkillOut",
    "SkillCreate",
    "SkillOut",
    "validate_plan_status",
]
