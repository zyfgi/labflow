"""Project retrieval (scope: shared project read scope)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.time import time_range
from app.models.project import Project
from app.models.user import User
from app.permissions.projects import visible_project_ids_subquery
from app.services.retrieval.common import truncate
from app.services.retrieval.entity_resolver import ResolvedEntities
from app.services.retrieval.types import RetrievalHit, RetrievalPlan

_FIELDS = (Project.name, Project.code, Project.description, Project.research_direction)


def search_projects(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 5,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    stmt = select(Project).where(Project.id.in_(visible_project_ids_subquery(user)))

    if entities.project:
        stmt = stmt.where(Project.id == entities.project.id)

    keywords = [k for k in plan.keywords if k]
    if keywords and use_keywords and not entities.found:
        stmt = stmt.where(
            or_(*(or_(*(f.ilike(f"%{kw}%") for f in _FIELDS)) for kw in keywords))
        )

    date_from, date_to = time_range(plan.time_preset)
    if date_from:
        stmt = stmt.where(Project.updated_at >= date_from)

    rows = db.scalars(stmt.order_by(Project.updated_at.desc()).limit(limit * 2)).all()
    hits: list[RetrievalHit] = []
    for p in rows:
        score = 1.0
        for kw in keywords:
            if kw.lower() in (p.name or "").lower():
                score += 4
            if kw.lower() in (p.code or "").lower():
                score += 4
            if p.description and kw.lower() in p.description.lower():
                score += 2
        if entities.project and p.id == entities.project.id:
            score += 5
        hits.append(
            RetrievalHit(
                source_type="project",
                source_id=p.id,
                title=f"{p.name} ({p.code})",
                excerpt=truncate(
                    f"状态 {p.status} · 进度 {p.progress}% · {p.description or p.research_direction or ''}"
                ),
                score=score,
                url=f"/projects/{p.id}",
                project_id=p.id,
                occurred_at=p.updated_at,
                metadata={
                    "status": p.status,
                    "progress": p.progress,
                    "visibility": p.visibility,
                    "context": {
                        "name": p.name,
                        "code": p.code,
                        "description": truncate(p.description, 600),
                        "status": p.status,
                        "progress": p.progress,
                        "start_date": p.start_date.isoformat()
                        if p.start_date
                        else None,
                        "expected_end_date": p.expected_end_date.isoformat()
                        if p.expected_end_date
                        else None,
                    },
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
