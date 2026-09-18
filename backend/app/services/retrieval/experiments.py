"""Experiment retrieval (permission scope: readable projects, always in SQL)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.time import app_today, time_range
from app.models.experiment import Experiment
from app.models.project import Project
from app.models.user import User
from app.permissions.projects import apply_project_read_scope
from app.services.retrieval.common import first_non_empty, truncate
from app.services.retrieval.entity_resolver import ResolvedEntities
from app.services.retrieval.types import RetrievalHit, RetrievalPlan

_TEXT_FIELDS = (
    Experiment.title,
    Experiment.objective,
    Experiment.method,
    Experiment.parameters,
    Experiment.result_summary,
    Experiment.conclusion,
    Experiment.problems,
    Experiment.next_step,
)


def search_experiments(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 6,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    stmt = select(Experiment).where(Experiment.deleted_at.is_(None))
    stmt = apply_project_read_scope(stmt, user, Experiment.project_id)

    if entities.experiment_id:
        stmt = stmt.where(Experiment.id == entities.experiment_id)
    if entities.project:
        stmt = stmt.where(Experiment.project_id == entities.project.id)

    member_user_id = (
        user.id
        if plan.mine_only
        else (entities.member.user_id if entities.member else None)
    )
    if member_user_id:
        stmt = stmt.where(Experiment.owner_id == member_user_id)

    keywords = [k for k in plan.keywords if k]
    if keywords and use_keywords and not entities.found:
        kws = [or_(*(f.ilike(f"%{kw}%") for f in _TEXT_FIELDS)) for kw in keywords]
        stmt = stmt.where(or_(*kws))

    date_from, date_to = time_range(plan.time_preset)
    if date_from:
        stmt = stmt.where(Experiment.experiment_date >= date_from)
    if date_to:
        stmt = stmt.where(Experiment.experiment_date <= date_to)

    rows = db.scalars(
        stmt.order_by(Experiment.experiment_date.desc().nullslast()).limit(limit * 3)
    ).all()
    if not rows:
        return []

    project_names = {
        p.id: p.name
        for p in db.scalars(
            select(Project).where(Project.id.in_([r.project_id for r in rows]))
        ).all()
    }
    hits: list[RetrievalHit] = []
    for e in rows:
        score = 1.0
        title_low = (e.title or "").lower()
        no_low = (e.experiment_no or "").lower()
        for kw in keywords:
            if kw.lower() in no_low:
                score += 6
            if kw.lower() in title_low:
                score += 4
            for f in (e.result_summary, e.conclusion):
                if f and kw.lower() in f.lower():
                    score += 3
            for f in (e.method, e.objective, e.problems, e.parameters):
                if f and kw.lower() in f.lower():
                    score += 2
        if e.experiment_date:
            days = (app_today() - e.experiment_date).days
            if days <= 7:
                score += 2
            elif days <= 30:
                score += 1
        if member_user_id and e.owner_id == member_user_id:
            score += 2

        excerpt = truncate(
            first_non_empty(
                e.result_summary, e.conclusion, e.problems, e.objective, e.method
            )
        )
        hits.append(
            RetrievalHit(
                source_type="experiment",
                source_id=e.id,
                title=f"{e.experiment_no} {e.title}",
                excerpt=excerpt,
                score=score,
                url=f"/experiments/{e.id}",
                project_id=e.project_id,
                occurred_at=e.experiment_date,
                metadata={
                    "status": e.status,
                    "is_locked": e.is_locked,
                    "project_name": project_names.get(e.project_id),
                    "context": {
                        "experiment_no": e.experiment_no,
                        "title": e.title,
                        "objective": truncate(e.objective, 500),
                        "method": truncate(e.method, 500),
                        "result_summary": truncate(e.result_summary, 600),
                        "conclusion": truncate(e.conclusion, 600),
                        "problems": truncate(e.problems, 400),
                        "next_step": truncate(e.next_step, 300),
                        "experiment_date": e.experiment_date.isoformat()
                        if e.experiment_date
                        else None,
                        "project_name": project_names.get(e.project_id),
                    },
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
