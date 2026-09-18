"""Notification service: single place to create in-app notifications.

Design (light-process collaboration):
- actions succeed immediately; the notification IS the coordination mechanism
- fan out only to people actually involved — never broadcast to the whole lab
- read/unread only; there is no confirm/approve interaction on a notification
- NOTIFICATION_ENABLED=false drops everything (quiet mode)

Event vocabulary (see NOTIFICATION_EVENTS): one row per event type so the
frontend can filter and the audit report can count coverage.
"""

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.equipment import Equipment
from app.models.system import Notification
from app.models.user import User
from app.services import runtime_settings

NOTIFICATION_EVENTS = [
    "project_created",
    "project_member_added",
    "task_assigned",
    "task_reassigned",
    "task_due_changed",
    "task_completed",
    "task_due_soon",
    "task_overdue",
    "weekly_report_published",
    "weekly_report_updated",
    "weekly_report_commented",
    "experiment_created",
    "experiment_locked",
    "experiment_unlocked",
    "experiment_updated",
    "equipment_booked",
    "equipment_booking_cancelled",
    "equipment_borrowed",
    "equipment_returned",
    "equipment_overdue",
    "equipment_fault",
    "maintenance_updated",
    "wechat_bound",
    "wechat_unbound",
]


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    content: str | None = None,
    related_type: str | None = None,
    related_id: Any = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        related_type=related_type,
        related_id=str(related_id) if related_id is not None else None,
    )
    db.add(n)
    return n


def notify(
    db: Session,
    user_ids: Iterable[int | None],
    type: str,
    title: str,
    content: str | None = None,
    related_type: str | None = None,
    related_id: Any = None,
    exclude_user_id: int | None = None,
) -> int:
    """Create one notification per recipient (deduped, non-null, not the actor).
    Returns the number created; 0 when notifications are disabled."""
    if not runtime_settings.effective(db).NOTIFICATION_ENABLED:
        return 0
    seen: set[int] = set()
    count = 0
    for uid in user_ids:
        if uid is None or uid in seen or uid == exclude_user_id:
            continue
        seen.add(uid)
        create_notification(db, uid, type, title, content, related_type, related_id)
        count += 1
    return count


def user_ids_with_roles(db: Session, roles: Iterable[str]) -> list[int]:
    return list(
        db.scalars(
            select(User.id).where(User.role.in_(tuple(roles)), User.status == "active")
        )
    )


def equipment_watcher_ids(db: Session, eq: Equipment) -> list[int]:
    """People responsible for an equipment: its manager plus equipment admins."""
    ids = user_ids_with_roles(db, (Role.EQUIPMENT_ADMIN,))
    if eq.manager_id:
        ids.append(eq.manager_id)
    return ids


def weekly_report_audience_ids(db: Session, member_user_id: int) -> list[int]:
    """Recipients of a weekly-report publish/update, per WEEKLY_REPORT_NOTIFY_ROLES."""
    roles = runtime_settings.effective(db).WEEKLY_REPORT_NOTIFY_ROLES
    if not roles:
        return []
    return user_ids_with_roles(db, roles)
