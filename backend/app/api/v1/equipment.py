"""Equipment ledger + booking + borrow + maintenance APIs.

Booking overlap rule (PRD §9.2): for the same equipment, two bookings in
status pending/approved must never overlap in time:
    new_start < existing_end AND new_end > existing_start
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, write_audit_log
from app.core.time import utcnow
from app.core.responses import ok, paged
from app.database import get_db
from app.models.equipment import (
    Equipment,
    EquipmentBooking,
    EquipmentBorrow,
    EquipmentMaintenance,
)
from app.models.enums import (
    BookingStatus,
    BorrowStatus,
    EquipmentStatus,
    MaintenanceStatus,
    Role,
)
from app.models.user import User
from app.permissions import is_staff
from app.schemas.equipment import (
    BookingCreate,
    BookingOut,
    BookingUpdate,
    BorrowCreate,
    BorrowOut,
    EquipmentCreate,
    EquipmentOut,
    EquipmentUpdate,
    MaintenanceCreate,
    MaintenanceOut,
    MaintenanceUpdate,
)
from app.services.notifications import create_notification

router = APIRouter(prefix="/equipment", tags=["equipment"])
bookings_router = APIRouter(prefix="/equipment-bookings", tags=["equipment"])
borrows_router = APIRouter(prefix="/equipment-borrows", tags=["equipment"])
maintenance_router = APIRouter(prefix="/equipment-maintenance", tags=["equipment"])

MANAGE_ROLES = (Role.PI, Role.EQUIPMENT_ADMIN)


def _get_equipment(db: Session, equipment_id: int) -> Equipment:
    eq = db.get(Equipment, equipment_id)
    if not eq or eq.deleted_at is not None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return eq


def _can_manage_equipment(user: User) -> bool:
    return user.role in MANAGE_ROLES


def _active_booking_conflict(db: Session, equipment_id: int, start: datetime, end: datetime, exclude_id: int | None = None) -> EquipmentBooking | None:
    stmt = select(EquipmentBooking).where(
        EquipmentBooking.equipment_id == equipment_id,
        EquipmentBooking.status.in_((BookingStatus.PENDING, BookingStatus.APPROVED)),
        EquipmentBooking.start_time < end,
        EquipmentBooking.end_time > start,
    )
    if exclude_id:
        stmt = stmt.where(EquipmentBooking.id != exclude_id)
    return db.scalar(stmt)


# ---------------- ledger ----------------


@router.get("")
def list_equipment(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Equipment).where(Equipment.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Equipment.status == status)
    if category:
        stmt = stmt.where(Equipment.category == category)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(
            Equipment.name.ilike(kw) | Equipment.asset_no.ilike(kw) | Equipment.model.ilike(kw)
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Equipment.id).offset((page - 1) * page_size).limit(page_size)).all()
    items = []
    for e in rows:
        item = EquipmentOut.model_validate(e).model_dump(mode="json")
        if e.manager_id:
            manager = db.get(User, e.manager_id)
            item["manager_name"] = manager.name if manager else None
        else:
            item["manager_name"] = None
        items.append(item)
    return paged(items, total, page, page_size)


@router.post("", status_code=201)
def create_equipment(
    body: EquipmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not _can_manage_equipment(user):
        raise HTTPException(status_code=403, detail="只有 PI/设备管理员可以管理设备台账")
    if db.scalar(select(Equipment).where(Equipment.asset_no == body.asset_no)):
        raise HTTPException(status_code=409, detail="资产编号已存在")
    eq = Equipment(**body.model_dump())
    db.add(eq)
    db.flush()
    write_audit_log(db, user, "create_equipment", "equipment", eq.id, {"asset_no": eq.asset_no})
    db.commit()
    return ok(EquipmentOut.model_validate(eq).model_dump(mode="json"), message="设备已创建")


@router.get("/{equipment_id}")
def get_equipment(
    equipment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    eq = _get_equipment(db, equipment_id)
    item = EquipmentOut.model_validate(eq).model_dump(mode="json")
    manager = db.get(User, eq.manager_id) if eq.manager_id else None
    item["manager_name"] = manager.name if manager else None

    next_booking = db.scalar(
        select(EquipmentBooking)
        .options(joinedload(EquipmentBooking.user))
        .where(
            EquipmentBooking.equipment_id == eq.id,
            EquipmentBooking.status == BookingStatus.APPROVED,
            EquipmentBooking.end_time > utcnow(),
        )
        .order_by(EquipmentBooking.start_time)
    )
    item["next_booking"] = (
        {
            "id": next_booking.id,
            "start_time": next_booking.start_time.isoformat(),
            "end_time": next_booking.end_time.isoformat(),
            "user_name": next_booking.user.name if next_booking.user else None,
        }
        if next_booking
        else None
    )

    last_maintenance = db.scalar(
        select(EquipmentMaintenance)
        .where(EquipmentMaintenance.equipment_id == eq.id)
        .order_by(EquipmentMaintenance.reported_at.desc())
    )
    item["latest_maintenance"] = (
        {
            "id": last_maintenance.id,
            "type": last_maintenance.type,
            "status": last_maintenance.status,
            "reported_at": last_maintenance.reported_at.isoformat() if last_maintenance.reported_at else None,
        }
        if last_maintenance
        else None
    )
    return ok(item)


@router.patch("/{equipment_id}")
def update_equipment(
    equipment_id: int,
    body: EquipmentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not _can_manage_equipment(user):
        raise HTTPException(status_code=403, detail="只有 PI/设备管理员可以修改设备台账")
    eq = _get_equipment(db, equipment_id)
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(eq, field, value)
    write_audit_log(db, user, "update_equipment", "equipment", eq.id, {"fields": list(data.keys())})
    db.commit()
    return ok(EquipmentOut.model_validate(eq).model_dump(mode="json"), message="设备已更新")


@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not _can_manage_equipment(user):
        raise HTTPException(status_code=403, detail="只有 PI/设备管理员可以删除设备")
    eq = _get_equipment(db, equipment_id)
    eq.deleted_at = utcnow()
    eq.is_active = False
    write_audit_log(db, user, "delete_equipment", "equipment", eq.id, {"asset_no": eq.asset_no})
    db.commit()
    return ok(message="设备已删除")


# ---------------- bookings ----------------


@bookings_router.get("")
def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    equipment_id: int | None = None,
    status: str | None = None,
    mine: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(EquipmentBooking)
    if mine or not is_staff(user):
        mine_user_id = user.id if mine else (user.id if not is_staff(user) else None)
        if mine_user_id:
            stmt = stmt.where(EquipmentBooking.user_id == mine_user_id)
    if equipment_id:
        stmt = stmt.where(EquipmentBooking.equipment_id == equipment_id)
    if status:
        stmt = stmt.where(EquipmentBooking.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(joinedload(EquipmentBooking.user))
        .order_by(EquipmentBooking.start_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for b in rows:
        item = BookingOut.model_validate(b).model_dump(mode="json")
        eq = db.get(Equipment, b.equipment_id)
        item["equipment_name"] = eq.name if eq else None
        item["user_name"] = b.user.name if b.user else None
        items.append(item)
    return paged(items, total, page, page_size)


@bookings_router.post("", status_code=201)
def create_booking(
    body: BookingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    eq = _get_equipment(db, body.equipment_id)
    if not eq.is_active or eq.status == EquipmentStatus.DISABLED:
        raise HTTPException(status_code=400, detail="该设备当前不可预约")
    conflict = _active_booking_conflict(db, eq.id, body.start_time, body.end_time)
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"预约时间冲突：该设备在 {conflict.start_time.strftime('%m-%d %H:%M')} ~ "
            f"{conflict.end_time.strftime('%m-%d %H:%M')} 已有有效预约",
        )
    booking = EquipmentBooking(**body.model_dump(), user_id=user.id)
    db.add(booking)
    db.flush()
    write_audit_log(db, user, "create_booking", "equipment_booking", booking.id)
    db.commit()
    return ok(BookingOut.model_validate(booking).model_dump(mode="json"), message="预约已提交，等待审批")


@bookings_router.patch("/{booking_id}")
def update_booking(
    booking_id: int,
    body: BookingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    booking = db.get(EquipmentBooking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    is_owner = booking.user_id == user.id
    if not (is_owner or _can_manage_equipment(user)):
        raise HTTPException(status_code=403, detail="没有修改该预约的权限")
    if booking.status not in (BookingStatus.PENDING, BookingStatus.APPROVED):
        raise HTTPException(status_code=400, detail="当前状态不能修改预约")
    data = body.model_dump(exclude_unset=True)
    start = data.get("start_time", booking.start_time)
    end = data.get("end_time", booking.end_time)
    if end <= start:
        raise HTTPException(status_code=422, detail="结束时间必须晚于开始时间")
    conflict = _active_booking_conflict(db, booking.equipment_id, start, end, exclude_id=booking.id)
    if conflict:
        raise HTTPException(status_code=409, detail="修改后的时间与已有预约冲突")
    for field, value in data.items():
        setattr(booking, field, value)
    write_audit_log(db, user, "update_booking", "equipment_booking", booking.id)
    db.commit()
    return ok(BookingOut.model_validate(booking).model_dump(mode="json"), message="预约已更新")


@bookings_router.post("/{booking_id}/approve")
def approve_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not _can_manage_equipment(user):
        raise HTTPException(status_code=403, detail="只有 PI/设备管理员可以审批预约")
    booking = db.get(EquipmentBooking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有待审批状态的预约可以审批")
    conflict = _active_booking_conflict(
        db, booking.equipment_id, booking.start_time, booking.end_time, exclude_id=booking.id
    )
    approved_conflict = conflict and conflict.status == BookingStatus.APPROVED
    if approved_conflict:
        raise HTTPException(status_code=409, detail="与已批准的预约时间冲突，无法批准")
    booking.status = BookingStatus.APPROVED
    booking.approved_by = user.id
    booking.approved_at = utcnow()
    eq = db.get(Equipment, booking.equipment_id)
    if eq and eq.status == EquipmentStatus.AVAILABLE:
        eq.status = EquipmentStatus.RESERVED
    create_notification(
        db, booking.user_id, "booking_approved", "设备预约已通过",
        f"你的预约已通过审批", "equipment", booking.equipment_id,
    )
    write_audit_log(db, user, "approve_booking", "equipment_booking", booking.id)
    db.commit()
    return ok(BookingOut.model_validate(booking).model_dump(mode="json"), message="预约已批准")


@bookings_router.post("/{booking_id}/reject")
def reject_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not _can_manage_equipment(user):
        raise HTTPException(status_code=403, detail="只有 PI/设备管理员可以审批预约")
    booking = db.get(EquipmentBooking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有待审批状态的预约可以拒绝")
    booking.status = BookingStatus.REJECTED
    booking.approved_by = user.id
    booking.approved_at = utcnow()
    create_notification(
        db, booking.user_id, "booking_rejected", "设备预约被拒绝",
        "你的设备预约被拒绝，请查看或重新预约", "equipment", booking.equipment_id,
    )
    write_audit_log(db, user, "reject_booking", "equipment_booking", booking.id)
    db.commit()
    return ok(BookingOut.model_validate(booking).model_dump(mode="json"), message="预约已拒绝")


@bookings_router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    booking = db.get(EquipmentBooking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if not (booking.user_id == user.id or _can_manage_equipment(user)):
        raise HTTPException(status_code=403, detail="没有取消该预约的权限")
    if booking.status not in (BookingStatus.PENDING, BookingStatus.APPROVED):
        raise HTTPException(status_code=400, detail="当前状态不能取消")
    was_approved = booking.status == BookingStatus.APPROVED
    booking.status = BookingStatus.CANCELLED
    if was_approved:
        eq = db.get(Equipment, booking.equipment_id)
        remaining = db.scalar(
            select(func.count()).select_from(EquipmentBooking).where(
                EquipmentBooking.equipment_id == booking.equipment_id,
                EquipmentBooking.status == BookingStatus.APPROVED,
                EquipmentBooking.end_time > utcnow(),
            )
        )
        if eq and eq.status == EquipmentStatus.RESERVED and not remaining:
            eq.status = EquipmentStatus.AVAILABLE
    write_audit_log(db, user, "cancel_booking", "equipment_booking", booking.id)
    db.commit()
    return ok(BookingOut.model_validate(booking).model_dump(mode="json"), message="预约已取消")


# ---------------- borrows ----------------


@borrows_router.get("")
def list_borrows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    equipment_id: int | None = None,
    status: str | None = None,
    mine: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(EquipmentBorrow)
    if mine or not is_staff(user):
        uid = user.id if mine else (user.id if not is_staff(user) else None)
        if uid:
            stmt = stmt.where(EquipmentBorrow.borrower_id == uid)
    if equipment_id:
        stmt = stmt.where(EquipmentBorrow.equipment_id == equipment_id)
    if status:
        stmt = stmt.where(EquipmentBorrow.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    items = []
    for b in rows:
        item = BorrowOut.model_validate(b).model_dump(mode="json")
        eq = db.get(Equipment, b.equipment_id)
        item["equipment_name"] = eq.name if eq else None
        borrower = db.get(User, b.borrower_id)
        item["borrower_name"] = borrower.name if borrower else None
        if b.status == BorrowStatus.BORROWED and b.expected_return_time and b.expected_return_time < utcnow():
            item["is_overdue"] = True
        else:
            item["is_overdue"] = b.status == BorrowStatus.OVERDUE
        items.append(item)
    return paged(items, total, page, page_size)


@borrows_router.post("", status_code=201)
def create_borrow(
    body: BorrowCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    eq = _get_equipment(db, body.equipment_id)
    if eq.status in (EquipmentStatus.FAULT, EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED):
        raise HTTPException(status_code=400, detail="该设备当前状态不可借用")
    active = db.scalar(
        select(EquipmentBorrow).where(
            EquipmentBorrow.equipment_id == eq.id,
            EquipmentBorrow.status == BorrowStatus.BORROWED,
        )
    )
    if active:
        raise HTTPException(status_code=409, detail="该设备已被借出，尚未归还")
    borrow = EquipmentBorrow(
        equipment_id=eq.id,
        borrower_id=user.id,
        borrow_time=utcnow(),
        expected_return_time=body.expected_return_time,
        purpose=body.purpose,
        note=body.note,
        status=BorrowStatus.BORROWED,
    )
    db.add(borrow)
    eq.status = EquipmentStatus.BORROWED
    write_audit_log(db, user, "borrow_equipment", "equipment_borrow", borrow.id)
    db.commit()
    return ok(BorrowOut.model_validate(borrow).model_dump(mode="json"), message="借出成功")


@borrows_router.post("/{borrow_id}/return")
def return_borrow(
    borrow_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    borrow = db.get(EquipmentBorrow, borrow_id)
    if not borrow:
        raise HTTPException(status_code=404, detail="借用记录不存在")
    if not (borrow.borrower_id == user.id or _can_manage_equipment(user)):
        raise HTTPException(status_code=403, detail="没有归还该设备的权限")
    if borrow.status not in (BorrowStatus.BORROWED, BorrowStatus.OVERDUE):
        raise HTTPException(status_code=400, detail="该记录已归还")
    borrow.status = BorrowStatus.RETURNED
    borrow.actual_return_time = utcnow()
    eq = db.get(Equipment, borrow.equipment_id)
    if eq:
        eq.status = EquipmentStatus.AVAILABLE
    write_audit_log(db, user, "return_equipment", "equipment_borrow", borrow.id)
    db.commit()
    return ok(BorrowOut.model_validate(borrow).model_dump(mode="json"), message="归还成功")


# ---------------- maintenance ----------------


@maintenance_router.get("")
def list_maintenance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    equipment_id: int | None = None,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(EquipmentMaintenance)
    if equipment_id:
        stmt = stmt.where(EquipmentMaintenance.equipment_id == equipment_id)
    if status:
        stmt = stmt.where(EquipmentMaintenance.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    items = []
    for m in rows:
        item = MaintenanceOut.model_validate(m).model_dump(mode="json")
        eq = db.get(Equipment, m.equipment_id)
        item["equipment_name"] = eq.name if eq else None
        reporter = db.get(User, m.reporter_id) if m.reporter_id else None
        item["reporter_name"] = reporter.name if reporter else None
        items.append(item)
    return paged(items, total, page, page_size)


@maintenance_router.post("", status_code=201)
def create_maintenance(
    body: MaintenanceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    eq = _get_equipment(db, body.equipment_id)
    record = EquipmentMaintenance(
        equipment_id=eq.id,
        reporter_id=user.id,
        type=body.type,
        description=body.description,
        reported_at=utcnow(),
        status=MaintenanceStatus.REPORTED,
    )
    db.add(record)
    if body.type == "fault":
        eq.status = EquipmentStatus.FAULT
    create_notification(
        db, eq.manager_id, "equipment_fault", "设备故障上报",
        f"设备「{eq.name}」被上报故障，请及时处理", "equipment", eq.id,
    ) if eq.manager_id else None
    if user.role != Role.EQUIPMENT_ADMIN:
        for admin_id in db.scalars(select(User.id).where(User.role == Role.EQUIPMENT_ADMIN, User.status == "active")):
            create_notification(
                db, admin_id, "equipment_fault", "设备故障上报",
                f"设备「{eq.name}」被上报故障", "equipment", eq.id,
            )
    write_audit_log(db, user, "report_fault", "equipment_maintenance", record.id)
    db.commit()
    return ok(MaintenanceOut.model_validate(record).model_dump(mode="json"), message="故障/维修已上报")


@maintenance_router.patch("/{maintenance_id}")
def update_maintenance(
    maintenance_id: int,
    body: MaintenanceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not _can_manage_equipment(user):
        raise HTTPException(status_code=403, detail="只有 PI/设备管理员可以处理维修记录")
    record = db.get(EquipmentMaintenance, maintenance_id)
    if not record:
        raise HTTPException(status_code=404, detail="维修记录不存在")
    data = body.model_dump(exclude_unset=True)
    old_status = record.status
    for field, value in data.items():
        setattr(record, field, value)
    eq = db.get(Equipment, record.equipment_id)
    if body.status == MaintenanceStatus.PROCESSING and old_status == MaintenanceStatus.REPORTED:
        record.started_at = utcnow()
        if eq and eq.status == EquipmentStatus.FAULT:
            eq.status = EquipmentStatus.MAINTENANCE
    if body.status == MaintenanceStatus.COMPLETED:
        record.finished_at = utcnow()
        if eq and eq.status in (EquipmentStatus.FAULT, EquipmentStatus.MAINTENANCE):
            eq.status = EquipmentStatus.AVAILABLE
    write_audit_log(db, user, "update_maintenance", "equipment_maintenance", record.id)
    db.commit()
    return ok(MaintenanceOut.model_validate(record).model_dump(mode="json"), message="维修记录已更新")
