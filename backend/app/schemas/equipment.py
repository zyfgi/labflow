from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    BOOKING_STATUSES,
    BORROW_STATUSES,
    EQUIPMENT_STATUSES,
    MAINTENANCE_STATUSES,
    MAINTENANCE_TYPES,
)
from app.schemas.base import StrictSchema


def _check(value: str | None, allowed: list | tuple, label: str) -> str | None:
    if value is not None and value not in allowed:
        raise ValueError(f"无效的{label}: {value}")
    return value


class EquipmentCreate(StrictSchema):
    asset_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    serial_no: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    manager_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    manual_url: str | None = Field(default=None, max_length=500)
    booking_required: bool = False
    status: str = "available"

    _status_v = field_validator("status")(
        lambda v: _check(v, EQUIPMENT_STATUSES, "设备状态")
    )


class EquipmentUpdate(StrictSchema):
    name: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    serial_no: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    manager_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    manual_url: str | None = Field(default=None, max_length=500)
    booking_required: bool | None = None
    is_active: bool | None = None
    status: str | None = None

    _status_v = field_validator("status")(
        lambda v: _check(v, EQUIPMENT_STATUSES, "设备状态")
    )


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_no: str
    name: str
    category: str
    manufacturer: str | None
    model: str | None
    serial_no: str | None
    location: str | None
    manager_id: int | None
    purchase_date: datetime | None = None
    purchase_price: Decimal | None
    status: str
    description: str | None
    manual_url: str | None
    booking_required: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BookingCreate(StrictSchema):
    equipment_id: int
    project_id: int | None = None
    start_time: datetime
    end_time: datetime
    purpose: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check_times(self) -> "BookingCreate":
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class BookingUpdate(StrictSchema):
    start_time: datetime | None = None
    end_time: datetime | None = None
    purpose: str | None = Field(default=None, max_length=2000)
    project_id: int | None = None


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    user_id: int
    project_id: int | None
    start_time: datetime
    end_time: datetime
    purpose: str | None
    status: str
    approved_by: int | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BorrowCreate(StrictSchema):
    equipment_id: int
    expected_return_time: datetime
    purpose: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)


class BorrowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    borrower_id: int
    borrow_time: datetime | None
    expected_return_time: datetime | None
    actual_return_time: datetime | None
    purpose: str | None
    status: str
    note: str | None
    approved_by: int | None
    created_at: datetime
    updated_at: datetime


class MaintenanceCreate(StrictSchema):
    equipment_id: int
    type: str = "fault"
    description: str | None = Field(default=None, max_length=5000)

    _type_v = field_validator("type")(
        lambda v: _check(v, MAINTENANCE_TYPES, "维修类型")
    )


class MaintenanceUpdate(StrictSchema):
    type: str | None = None
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    vendor: str | None = Field(default=None, max_length=200)
    result: str | None = Field(default=None, max_length=5000)

    _type_v = field_validator("type")(
        lambda v: _check(v, MAINTENANCE_TYPES, "维修类型")
    )
    _status_v = field_validator("status")(
        lambda v: _check(v, MAINTENANCE_STATUSES, "维修状态")
    )


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    reporter_id: int | None
    type: str
    description: str | None
    reported_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    status: str
    cost: Decimal | None
    vendor: str | None
    result: str | None
    created_at: datetime
    updated_at: datetime


__all__ = [
    "BOOKING_STATUSES",
    "BORROW_STATUSES",
    "BookingCreate",
    "BookingOut",
    "BookingUpdate",
    "BorrowCreate",
    "BorrowOut",
    "EquipmentCreate",
    "EquipmentOut",
    "EquipmentUpdate",
    "MaintenanceCreate",
    "MaintenanceOut",
    "MaintenanceUpdate",
]
