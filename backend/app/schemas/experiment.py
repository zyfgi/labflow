from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EXPERIMENT_STATUSES
from app.schemas.base import StrictSchema


class ExperimentCreate(StrictSchema):
    project_id: int
    task_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    objective: str | None = Field(default=None, max_length=5000)
    background: str | None = Field(default=None, max_length=5000)
    experiment_date: date | None = None
    environment: str | None = Field(default=None, max_length=5000)
    method: str | None = Field(default=None, max_length=5000)
    parameters: str | None = Field(default=None, max_length=5000)


class ExperimentUpdate(StrictSchema):
    task_id: int | None = None
    title: str | None = Field(default=None, max_length=200)
    objective: str | None = Field(default=None, max_length=5000)
    background: str | None = Field(default=None, max_length=5000)
    experiment_date: date | None = None
    status: str | None = None
    environment: str | None = Field(default=None, max_length=5000)
    method: str | None = Field(default=None, max_length=5000)
    parameters: str | None = Field(default=None, max_length=5000)
    result_summary: str | None = Field(default=None, max_length=5000)
    conclusion: str | None = Field(default=None, max_length=5000)
    problems: str | None = Field(default=None, max_length=5000)
    next_step: str | None = Field(default=None, max_length=5000)
    code_repo_url: str | None = Field(default=None, max_length=500)
    git_commit: str | None = Field(default=None, max_length=100)
    dataset_path: str | None = Field(default=None, max_length=500)
    software_version: str | None = Field(default=None, max_length=200)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in EXPERIMENT_STATUSES:
            raise ValueError(f"无效的实验状态: {v}")
        return v


class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_no: str
    project_id: int
    task_id: int | None
    title: str
    objective: str | None
    background: str | None
    owner_id: int | None
    experiment_date: date | None
    status: str
    environment: str | None
    method: str | None
    parameters: str | None
    result_summary: str | None
    conclusion: str | None
    problems: str | None
    next_step: str | None
    code_repo_url: str | None
    git_commit: str | None
    dataset_path: str | None
    software_version: str | None
    is_locked: bool
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExperimentAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    file_name: str
    file_type: str
    file_size: int
    uploaded_by: int | None
    uploaded_at: datetime


__all__ = [
    "ExperimentAttachmentOut",
    "ExperimentCreate",
    "ExperimentOut",
    "ExperimentUpdate",
]
