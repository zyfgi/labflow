"""Global search backed by the shared permission scopes.

All permission filtering is pushed into SQL (no Python can_read loops, no
per-result project lookups). This is the same scope layer the AI retrieval
engine uses, so search and AI can never diverge on permissions.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.core.responses import ok
from app.database import get_db
from app.models.equipment import Equipment
from app.models.experiment import Experiment
from app.models.project import Project, Task
from app.models.user import MemberProfile, User
from app.permissions import is_teaching_staff
from app.permissions.projects import apply_project_read_scope, visible_project_ids_subquery

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(
    q: str = Query(min_length=1, max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    kw = f"%{q}%"
    results: dict[str, list] = {
        "members": [],
        "projects": [],
        "tasks": [],
        "experiments": [],
        "equipment": [],
    }

    # members: PI / TEACHER only (equipment admins have no member-data access)
    if is_teaching_staff(user):
        rows = db.scalars(
            select(MemberProfile)
            .options(joinedload(MemberProfile.user))
            .join(User, MemberProfile.user_id == User.id)
            .where(
                User.name.ilike(kw)
                | User.username.ilike(kw)
                | MemberProfile.student_no.ilike(kw)
            )
            .limit(5)
        ).all()
        results["members"] = [
            {"id": m.id, "name": m.user.name if m.user else None, "member_type": m.member_type}
            for m in rows
        ]

    # projects: permission scope in SQL, then rank + limit
    proj_stmt = apply_project_read_scope(
        select(Project).where(Project.name.ilike(kw) | Project.code.ilike(kw)), user, Project.id
    ).order_by(Project.updated_at.desc())
    projects = db.scalars(proj_stmt.limit(5)).all()
    results["projects"] = [
        {"id": p.id, "name": p.name, "code": p.code, "status": p.status} for p in projects
    ]

    # tasks: assignee OR readable projects, ranked in SQL
    task_scope = (Task.assignee_id == user.id) | Task.project_id.in_(
        visible_project_ids_subquery(user)
    )
    tasks = db.scalars(
        select(Task)
        .where(
            Task.deleted_at.is_(None),
            task_scope,
            Task.title.ilike(kw),
        )
        .order_by(Task.updated_at.desc())
        .limit(5)
    ).all()
    results["tasks"] = [
        {"id": t.id, "title": t.title, "status": t.status, "project_id": t.project_id}
        for t in tasks
    ]

    # experiments: project scope only
    exp_stmt = apply_project_read_scope(
        select(Experiment).where(
            Experiment.deleted_at.is_(None),
            Experiment.experiment_no.ilike(kw) | Experiment.title.ilike(kw),
        ),
        user,
        Experiment.project_id,
    ).order_by(Experiment.experiment_date.desc().nullslast())
    experiments = db.scalars(exp_stmt.limit(5)).all()
    results["experiments"] = [
        {"id": e.id, "experiment_no": e.experiment_no, "title": e.title, "status": e.status}
        for e in experiments
    ]

    # equipment: visible to any authenticated member
    equipment_rows = db.scalars(
        select(Equipment)
        .where(
            Equipment.deleted_at.is_(None),
            Equipment.name.ilike(kw) | Equipment.asset_no.ilike(kw),
        )
        .limit(5)
    ).all()
    results["equipment"] = [
        {"id": e.id, "name": e.name, "asset_no": e.asset_no, "status": e.status}
        for e in equipment_rows
    ]

    return ok(results)
