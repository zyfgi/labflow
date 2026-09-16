"""Global search across members / projects / tasks / experiments / equipment."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.core.responses import ok
from app.database import get_db
from app.models.equipment import Equipment
from app.models.experiment import Experiment
from app.models.project import Project, ProjectMember, Task
from app.models.user import MemberProfile, User
from app.permissions import is_staff
from app.permissions.projects import can_read_project

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(
    q: str = Query(min_length=1, max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    kw = f"%{q}%"
    results: dict[str, list] = {"members": [], "projects": [], "tasks": [], "experiments": [], "equipment": []}

    # members: staff only
    if is_staff(user):
        rows = db.scalars(
            select(MemberProfile)
            .options(joinedload(MemberProfile.user))
            .join(User, MemberProfile.user_id == User.id)
            .where(User.name.ilike(kw) | User.username.ilike(kw) | MemberProfile.student_no.ilike(kw))
            .limit(5)
        ).all()
        results["members"] = [
            {"id": m.id, "name": m.user.name if m.user else None, "member_type": m.member_type}
            for m in rows
        ]

    # projects: respect visibility
    stmt = select(Project).where(
        Project.deleted_at.is_(None),
        (Project.name.ilike(kw) | Project.code.ilike(kw)),
    )
    projects = db.scalars(stmt.order_by(Project.updated_at.desc()).limit(20)).all()
    visible = [p for p in projects if can_read_project(db, user, p)][:5]
    results["projects"] = [
        {"id": p.id, "name": p.name, "code": p.code, "status": p.status} for p in visible
    ]

    # tasks: in readable projects or assigned to me
    tasks = db.scalars(
        select(Task).where(Task.deleted_at.is_(None), Task.title.ilike(kw)).limit(20)
    ).all()
    visible_tasks = []
    for t in tasks:
        if t.assignee_id == user.id:
            visible_tasks.append(t)
            continue
        project = db.get(Project, t.project_id)
        if project and can_read_project(db, user, project):
            visible_tasks.append(t)
        if len(visible_tasks) >= 5:
            break
    results["tasks"] = [
        {"id": t.id, "title": t.title, "status": t.status, "project_id": t.project_id}
        for t in visible_tasks
    ]

    # experiments: readable projects only (query via experiment no / title)
    exp_stmt = select(Project.id).where(Project.deleted_at.is_(None))
    experiments = db.scalars(
        select(Experiment).where(
            Experiment.deleted_at.is_(None),
            Experiment.experiment_no.ilike(kw) | Experiment.title.ilike(kw),
        ).limit(20)
    ).all()
    visible_exps = []
    for e in experiments:
        project = db.get(Project, e.project_id)
        if project and can_read_project(db, user, project):
            visible_exps.append(e)
        if len(visible_exps) >= 5:
            break
    results["experiments"] = [
        {"id": e.id, "experiment_no": e.experiment_no, "title": e.title, "status": e.status}
        for e in visible_exps
    ]

    # equipment: any member can see the ledger
    equipment_rows = db.scalars(
        select(Equipment).where(
            Equipment.deleted_at.is_(None),
            Equipment.name.ilike(kw) | Equipment.asset_no.ilike(kw),
        ).limit(5)
    ).all()
    results["equipment"] = [
        {"id": e.id, "name": e.name, "asset_no": e.asset_no, "status": e.status} for e in equipment_rows
    ]

    return ok(results)
