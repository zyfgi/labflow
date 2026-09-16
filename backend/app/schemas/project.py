from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    PROJECT_MEMBER_ROLES,
    PROJECT_PRIORITIES,
    PROJECT_STATUSES,
    PROJECT_VISIBILITIES,
    TASK_PRIORITIES,
    TASK_STATUSES,
)


def _check(value: str | None, allowed: tuple | list, label: str) -> str | None:
    if value is not None and value not in allowed:
        raise ValueError(f"无效的{label}: {value}")
    return value


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=5000)
    research_direction: str | None = Field(default=None, max_length=200)
    status: str = "planning"
    priority: str = "medium"
    start_date: date | None = None
    expected_end_date: date | None = None
    progress: int = Field(default=0, ge=0, le=100)
    visibility: str = "project_members"

    _status_v = field_validator("status")(lambda v: _check(v, PROJECT_STATUSES, "项目状态"))
    _prio_v = field_validator("priority")(lambda v: _check(v, PROJECT_PRIORITIES, "优先级"))
    _vis_v = field_validator("visibility")(lambda v: _check(v, PROJECT_VISIBILITIES, "可见性"))


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    research_direction: str | None = Field(default=None, max_length=200)
    status: str | None = None
    priority: str | None = None
    start_date: date | None = None
    expected_end_date: date | None = None
    actual_end_date: date | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    visibility: str | None = None

    _status_v = field_validator("status")(lambda v: _check(v, PROJECT_STATUSES, "项目状态"))
    _prio_v = field_validator("priority")(lambda v: _check(v, PROJECT_PRIORITIES, "优先级"))
    _vis_v = field_validator("visibility")(lambda v: _check(v, PROJECT_VISIBILITIES, "可见性"))


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str | None
    research_direction: str | None
    owner_id: int | None
    status: str
    priority: str
    start_date: date | None
    expected_end_date: date | None
    actual_end_date: date | None
    progress: int
    visibility: str
    created_at: datetime
    updated_at: datetime


class ProjectMemberAdd(BaseModel):
    user_id: int
    project_role: str = "student"

    _role_v = field_validator("project_role")(lambda v: _check(v, PROJECT_MEMBER_ROLES, "项目角色"))


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    due_date: date | None = None
    status: str = "pending"
    progress: int = Field(default=0, ge=0, le=100)


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    due_date: date | None = None
    status: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    due_date: date | None
    status: str
    progress: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    project_id: int
    milestone_id: int | None = None
    parent_task_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: int | None = None
    priority: str = "medium"
    status: str = "todo"
    start_date: date | None = None
    due_date: date | None = None
    progress: int = Field(default=0, ge=0, le=100)

    _prio_v = field_validator("priority")(lambda v: _check(v, TASK_PRIORITIES, "优先级"))
    _status_v = field_validator("status")(lambda v: _check(v, TASK_STATUSES, "任务状态"))


class TaskUpdate(BaseModel):
    milestone_id: int | None = None
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: int | None = None
    priority: str | None = None
    status: str | None = None
    start_date: date | None = None
    due_date: date | None = None
    progress: int | None = Field(default=None, ge=0, le=100)

    _prio_v = field_validator("priority")(lambda v: _check(v, TASK_PRIORITIES, "优先级"))
    _status_v = field_validator("status")(lambda v: _check(v, TASK_STATUSES, "任务状态"))


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    milestone_id: int | None
    parent_task_id: int | None
    title: str
    description: str | None
    assignee_id: int | None
    creator_id: int | None
    priority: str
    status: str
    start_date: date | None
    due_date: date | None
    completed_at: datetime | None
    progress: int
    created_at: datetime
    updated_at: datetime


class TaskStatusRequest(BaseModel):
    status: str
    progress: int | None = Field(default=None, ge=0, le=100)


class TaskCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class TaskCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    user_id: int | None
    content: str
    created_at: datetime


__all__ = [
    "Any",
    "MilestoneCreate",
    "MilestoneOut",
    "MilestoneUpdate",
    "ProjectCreate",
    "ProjectMemberAdd",
    "ProjectOut",
    "ProjectUpdate",
    "TaskCommentCreate",
    "TaskCommentOut",
    "TaskCreate",
    "TaskOut",
    "TaskStatusRequest",
    "TaskUpdate",
]
