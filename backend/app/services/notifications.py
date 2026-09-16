"""Notification service: single place to create in-app notifications."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.system import Notification


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
