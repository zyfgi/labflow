from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import ok, paged
from app.database import get_db
from app.models.system import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    unread = (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        )
        or 0
    )
    rows = db.scalars(
        stmt.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "related_type": n.related_type,
            "related_id": n.related_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]
    data = paged(items, total, page, page_size)
    data["data"]["unread"] = unread
    return data


@router.post("/read-all")
def read_all(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return ok(message="已全部标记为已读")


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="通知不存在")
    n.is_read = True
    db.commit()
    return ok(message="已标记为已读")
