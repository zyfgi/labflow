"""Daily due-date checker (PRD §10): run via `python -m app.due_checker`.

- tasks due within 3 days (not done)      -> notify assignee once per day
- overdue tasks (not done/cancelled)      -> notify assignee once per day
- overdue borrows                          -> mark overdue + notify borrower
- approved bookings whose end has passed   -> mark completed (recycle equipment status)

Designed to be scheduled daily (cron / Docker sidecar / 手动执行). Idempotent
within a day via notification dedupe.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models.equipment import Equipment, EquipmentBooking, EquipmentBorrow
from app.models.enums import BookingStatus, BorrowStatus, EquipmentStatus, TaskStatus
from app.models.project import Task
from app.models.system import Notification
from app.models.user import User

logger = logging.getLogger("labflow.due_checker")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def notified_today(db, user_id: int, type: str, related_type: str, related_id) -> bool:
    # created_at is naive UTC; dedupe window must be the current UTC day
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.type == type,
            Notification.related_type == related_type,
            Notification.related_id == str(related_id),
            Notification.created_at >= start,
        )
    ) is not None


def run() -> dict:
    db = SessionLocal()
    stats = {"task_due_soon": 0, "task_overdue": 0, "borrow_overdue": 0, "booking_completed": 0}
    today = date.today()
    now = utcnow()

    # ---- tasks due soon / overdue ----
    open_statuses = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.REVIEW)
    due_soon = db.scalars(
        select(Task).where(
            Task.deleted_at.is_(None),
            Task.status.in_(open_statuses),
            Task.assignee_id.is_not(None),
            Task.due_date >= today,
            Task.due_date <= today + timedelta(days=3),
        )
    ).all()
    for t in due_soon:
        if notified_today(db, t.assignee_id, "task_due_soon", "task", t.id):
            continue
        db.add(Notification(
            user_id=t.assignee_id, type="task_due_soon", title="任务临近截止",
            content=f"任务「{t.title}」将于 {t.due_date} 截止", related_type="task", related_id=str(t.id),
        ))
        stats["task_due_soon"] += 1

    overdue = db.scalars(
        select(Task).where(
            Task.deleted_at.is_(None),
            Task.status.in_(open_statuses),
            Task.assignee_id.is_not(None),
            Task.due_date < today,
        )
    ).all()
    for t in overdue:
        if notified_today(db, t.assignee_id, "task_overdue", "task", t.id):
            continue
        db.add(Notification(
            user_id=t.assignee_id, type="task_overdue", title="任务已逾期",
            content=f"任务「{t.title}」已逾期（截止 {t.due_date}），请尽快处理", related_type="task", related_id=str(t.id),
        ))
        stats["task_overdue"] += 1

    # ---- overdue borrows ----
    borrows = db.scalars(
        select(EquipmentBorrow).where(EquipmentBorrow.status == BorrowStatus.BORROWED)
    ).all()
    for b in borrows:
        if b.expected_return_time and b.expected_return_time < now:
            b.status = BorrowStatus.OVERDUE
            if not notified_today(db, b.borrower_id, "borrow_overdue", "equipment_borrow", b.id):
                eq = db.get(Equipment, b.equipment_id)
                db.add(Notification(
                    user_id=b.borrower_id, type="borrow_overdue", title="借用设备已逾期",
                    content=f"设备「{eq.name if eq else b.equipment_id}」已超过预定归还时间，请尽快归还",
                    related_type="equipment_borrow", related_id=str(b.id),
                ))
                stats["borrow_overdue"] += 1

    # ---- finished approved bookings -> completed ----
    finished = db.scalars(
        select(EquipmentBooking).where(
            EquipmentBooking.status == BookingStatus.APPROVED,
            EquipmentBooking.end_time < now,
        )
    ).all()
    affected_equipment: set[int] = set()
    for b in finished:
        b.status = BookingStatus.COMPLETED
        affected_equipment.add(b.equipment_id)
        stats["booking_completed"] += 1
    for equipment_id in affected_equipment:
        remaining = db.scalar(
            select(EquipmentBooking.id).where(
                EquipmentBooking.equipment_id == equipment_id,
                EquipmentBooking.status == BookingStatus.APPROVED,
                EquipmentBooking.end_time > now,
            )
        )
        if not remaining:
            eq = db.get(Equipment, equipment_id)
            if eq and eq.status == EquipmentStatus.RESERVED:
                eq.status = EquipmentStatus.AVAILABLE

    db.commit()
    db.close()
    logger.info("due checker: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
