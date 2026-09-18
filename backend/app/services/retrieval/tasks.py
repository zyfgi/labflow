"""Task retrieval (scope: assignee OR readable projects — always in SQL)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.time import app_today, time_range
from app.models.project import Project, Task
from app.models.user import User
from app.permissions.projects import visible_task_scope_conditions
from app.services.retrieval.common import truncate
from app.services.retrieval.entity_resolver import ResolvedEntities
from app.services.retrieval.types import RetrievalHit, RetrievalPlan

_OPEN = ("todo", "in_progress", "blocked", "review")
_DONE = ("done", "cancelled")
_FIELDS = (Task.title, Task.description)


def search_tasks(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 6,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    stmt = select(Task).where(
        Task.deleted_at.is_(None),
        visible_task_scope_conditions(user),
    )

    assignee_id: int | None
    if plan.mine_only:
        assignee_id = user.id
    elif entities.member:
        assignee_id = entities.member.user_id
    else:
        assignee_id = None
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)

    if entities.project:
        stmt = stmt.where(Task.project_id == entities.project.id)

    if plan.intent == "overdue_tasks":
        today = app_today()
        stmt = stmt.where(
            Task.status.in_(_OPEN),
            Task.due_date.is_not(None),
            Task.due_date < today,
        )

    keywords = [k for k in plan.keywords if k]
    if keywords and use_keywords and not entities.found:
        stmt = stmt.where(
            or_(*(or_(*(f.ilike(f"%{kw}%") for f in _FIELDS)) for kw in keywords))
        )

    date_from, date_to = time_range(plan.time_preset)
    if date_from:
        stmt = stmt.where(Task.due_date >= date_from)
    if date_to:
        stmt = stmt.where(Task.due_date <= date_to)

    rows = db.scalars(stmt.order_by(Task.updated_at.desc()).limit(limit * 3)).all()
    if not rows:
        return []

    project_names = {
        p.id: p.name
        for p in db.scalars(
            select(Project).where(Project.id.in_([r.project_id for r in rows]))
        ).all()
    }
    user_names = {}
    assignee_ids = {r.assignee_id for r in rows if r.assignee_id}
    if assignee_ids:
        from app.models.user import User

        for u in db.scalars(select(User).where(User.id.in_(assignee_ids))).all():
            user_names[u.id] = u.name

    today = app_today()
    hits: list[RetrievalHit] = []
    for t in rows:
        score = 1.0
        title_low = (t.title or "").lower()
        for kw in keywords:
            if kw.lower() in title_low:
                score += 4
            if t.description and kw.lower() in t.description.lower():
                score += 2
        is_overdue = bool(t.due_date and t.due_date < today and t.status not in _DONE)
        if plan.intent == "overdue_tasks" and is_overdue:
            score += 3
        if assignee_id and t.assignee_id == assignee_id:
            score += 2

        due = t.due_date.isoformat() if t.due_date else "无"
        excerpt = truncate(f"状态 {t.status} · 截止 {due} · {t.description or t.title}")
        hits.append(
            RetrievalHit(
                source_type="task",
                source_id=t.id,
                title=t.title,
                excerpt=excerpt,
                score=score,
                url=f"/tasks/{t.id}",
                project_id=t.project_id,
                occurred_at=t.due_date,
                metadata={
                    "status": t.status,
                    "priority": t.priority,
                    "progress": t.progress,
                    "assignee_name": user_names.get(t.assignee_id),
                    "project_name": project_names.get(t.project_id),
                    "is_overdue": is_overdue,
                    "context": {
                        "title": t.title,
                        "description": truncate(t.description, 500),
                        "status": t.status,
                        "priority": t.priority,
                        "progress": t.progress,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "assignee_name": user_names.get(t.assignee_id),
                        "project_name": project_names.get(t.project_id),
                    },
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
