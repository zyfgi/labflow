
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, write_audit_log
from app.core.time import app_today
from app.core.responses import ok, paged
from app.database import get_db
from app.models.base import utcnow
from app.models.project import Project, Task, TaskComment
from app.models.user import User
from app.permissions.projects import (
    ensure_project_manageable,
    ensure_project_visible,
    visible_task_scope_conditions,
)
from app.schemas.project import (
    TaskCommentCreate,
    TaskCreate,
    TaskOut,
    TaskStatusRequest,
    TaskUpdate,
)
from app.services.notifications import create_notification

router = APIRouter(prefix="/tasks", tags=["tasks"])

OPEN_STATUSES = ("todo", "in_progress", "blocked", "review")
DONE_STATUSES = ("done", "cancelled")


def _get_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def _out(task: Task) -> dict:
    return TaskOut.model_validate(task).model_dump()


def _can_edit_task(db: Session, user: User, task: Task) -> bool:
    from app.permissions.projects import can_manage_project

    project = db.get(Project, task.project_id)
    if project and can_manage_project(db, user, project):
        return True
    return user.id in (task.assignee_id, task.creator_id)


@router.get("")
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: int | None = None,
    assignee_id: int | None = None,
    status: str | None = None,
    keyword: str | None = None,
    overdue: bool = False,
    mine: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Task).where(Task.deleted_at.is_(None))
    if mine:
        assignee_id = user.id
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)

    if project_id:
        if user.role != "PI":
            proj = db.get(Project, project_id)
            if proj:
                ensure_project_visible(db, user, proj)
        stmt = stmt.where(Task.project_id == project_id)
    else:
        # shared permission scope: own tasks OR tasks in readable projects
        stmt = stmt.where(visible_task_scope_conditions(user))

    if status:
        stmt = stmt.where(Task.status == status)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(Task.title.ilike(kw))
    if overdue:
        stmt = stmt.where(
            Task.status.notin_(DONE_STATUSES), Task.due_date.is_not(None), Task.due_date < app_today()
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Task.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    # batch maps: constant query count regardless of page size
    project_names = dict(
        db.execute(
            select(Project.id, Project.name).where(Project.id.in_({t.project_id for t in rows} or [0]))
        ).all()
    )
    assignee_ids = {t.assignee_id for t in rows if t.assignee_id}
    assignee_names = dict(
        db.execute(select(User.id, User.name).where(User.id.in_(assignee_ids or [0]))).all()
    )
    today = app_today()

    items = []
    for t in rows:
        item = _out(t)
        item["project_name"] = project_names.get(t.project_id)
        item["assignee_name"] = assignee_names.get(t.assignee_id)
        item["is_overdue"] = bool(
            t.due_date and t.due_date < today and t.status not in DONE_STATUSES
        )
        items.append(item)
    return paged(items, total, page, page_size)


@router.post("", status_code=201)
def create_task(
    body: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = db.get(Project, body.project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="项目不存在")
    ensure_project_manageable(db, user, project)

    task = Task(**body.model_dump(), creator_id=user.id)
    db.add(task)
    db.flush()
    if task.assignee_id and task.assignee_id != user.id:
        create_notification(
            db,
            task.assignee_id,
            "task_assigned",
            "新任务分配",
            f"「{task.title}」由 {user.name} 分配给你，项目：{project.name}",
            "task",
            task.id,
        )
    write_audit_log(db, user, "create_task", "task", task.id, {"title": task.title})
    db.commit()
    return ok(_out(task), message="任务创建成功")


@router.get("/{task_id}")
def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = _get_task(db, task_id)
    project = db.get(Project, task.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if user.id != task.assignee_id:
        ensure_project_visible(db, user, project)
    item = _out(task)
    proj = project
    item["project_name"] = proj.name
    if task.assignee_id:
        assignee = db.get(User, task.assignee_id)
        item["assignee_name"] = assignee.name if assignee else None
    else:
        item["assignee_name"] = None
    item["can_edit"] = _can_edit_task(db, user, task)
    item["is_overdue"] = bool(
        task.due_date and task.due_date < app_today() and task.status not in DONE_STATUSES
    )
    return ok(item)


@router.patch("/{task_id}")
def update_task(
    task_id: int,
    body: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = _get_task(db, task_id)
    if not _can_edit_task(db, user, task):
        raise HTTPException(status_code=403, detail="没有修改该任务的权限")
    data = body.model_dump(exclude_unset=True)
    old_assignee = task.assignee_id
    for field, value in data.items():
        setattr(task, field, value)
    if task.status == "done":
        if task.completed_at is None:
            task.completed_at = utcnow()
    elif task.status == "cancelled":
        task.completed_at = None
    if task.assignee_id and task.assignee_id != old_assignee and task.assignee_id != user.id:
        create_notification(
            db,
            task.assignee_id,
            "task_assigned",
            "新任务分配",
            f"「{task.title}」分配给你，由 {user.name} 更新",
            "task",
            task.id,
        )
    write_audit_log(db, user, "update_task", "task", task.id, {"fields": list(data.keys())})
    db.commit()
    return ok(_out(task), message="任务已更新")


@router.post("/{task_id}/status")
def update_task_status(
    task_id: int,
    body: TaskStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = _get_task(db, task_id)
    if not _can_edit_task(db, user, task):
        raise HTTPException(status_code=403, detail="没有更新该任务状态的权限")
    task.status = body.status
    if body.progress is not None:
        task.progress = body.progress
    if body.status == "done":
        task.progress = 100
        task.completed_at = utcnow()
    elif body.status in DONE_STATUSES:
        task.completed_at = None
    write_audit_log(db, user, "update_task_status", "task", task.id, {"status": body.status})
    db.commit()
    return ok(_out(task), message="任务状态已更新")


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = _get_task(db, task_id)
    project = db.get(Project, task.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_project_manageable(db, user, project)
    task.deleted_at = utcnow()
    write_audit_log(db, user, "delete_task", "task", task.id)
    db.commit()
    return ok(message="任务已删除")


# ---------- comments / activity ----------


@router.get("/{task_id}/comments")
def list_task_comments(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = _get_task(db, task_id)
    project = db.get(Project, task.project_id)
    if project is None or (
        user.id != task.assignee_id and not _can_read(db, user, project)
    ):
        raise HTTPException(status_code=403, detail="没有查看该任务的权限")
    rows = db.scalars(
        select(TaskComment)
        .options(joinedload(TaskComment.user))
        .where(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at)
    ).all()
    return ok(
        [
            {
                "id": c.id,
                "task_id": c.task_id,
                "user_id": c.user_id,
                "user_name": c.user.name if c.user else None,
                "content": c.content,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in rows
        ]
    )


def _can_read(db: Session, user: User, project: Project) -> bool:
    from app.permissions.projects import can_read_project

    return can_read_project(db, user, project)


@router.post("/{task_id}/comments", status_code=201)
def add_task_comment(
    task_id: int,
    body: TaskCommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = _get_task(db, task_id)
    project = db.get(Project, task.project_id)
    if project is None or (
        user.id != task.assignee_id and not _can_read(db, user, project)
    ):
        raise HTTPException(status_code=403, detail="没有评论该任务的权限")
    comment = TaskComment(task_id=task_id, user_id=user.id, content=body.content)
    db.add(comment)
    write_audit_log(db, user, "comment_task", "task", task_id)
    db.commit()
    return ok(
        {
            "id": comment.id,
            "task_id": comment.task_id,
            "user_id": comment.user_id,
            "user_name": user.name,
            "content": comment.content,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        },
        message="评论已添加",
    )
