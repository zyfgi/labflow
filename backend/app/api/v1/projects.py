from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, write_audit_log
from app.core.responses import ok, paged
from app.database import get_db
from app.models.project import Milestone, Project, ProjectMember, Task
from app.models.user import MemberProfile, User
from app.permissions.projects import (
    ensure_project_manageable,
    ensure_project_visible,
    is_project_member,
)
from app.schemas.project import (
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectOut,
    ProjectUpdate,
)
from app.services.notifications import create_notification

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _out(project: Project, owner_name: str | None = None) -> dict:
    data = ProjectOut.model_validate(project).model_dump()
    data["owner_name"] = owner_name
    return data


def _owner_name(db: Session, project: Project) -> str | None:
    if project.owner_id:
        user = db.get(User, project.owner_id)
        return user.name if user else None
    return None


@router.get("")
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
    keyword: str | None = None,
    mine: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Project).where(Project.deleted_at.is_(None))
    if user.role != "PI":
        if user.role == "GUEST":
            member_ids: list[int] = []
            lab_visible = False
        else:
            member_ids = list(
                db.scalars(
                    select(ProjectMember.project_id).where(
                        ProjectMember.user_id == user.id, ProjectMember.left_at.is_(None)
                    )
                )
            )
            lab_visible = True
        conditions = Project.id.in_(member_ids or [0]) | (Project.owner_id == user.id)
        if lab_visible:
            conditions = conditions | (Project.visibility == "lab")
        stmt = stmt.where(conditions)
    if mine:
        stmt = stmt.where(Project.owner_id == user.id)
    if status:
        stmt = stmt.where(Project.status == status)
    if priority:
        stmt = stmt.where(Project.priority == priority)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(or_(Project.name.ilike(kw), Project.code.ilike(kw)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = []
    for p in rows:
        item = _out(p, _owner_name(db, p))
        item["my_role"] = _my_role(db, p, user)
        items.append(item)
    return paged(items, total, page, page_size)


def _my_role(db: Session, project: Project, user: User) -> str:
    if project.owner_id == user.id:
        return "owner"
    membership = is_project_member(db, project.id, user.id)
    if membership:
        return membership.project_role
    return "lab" if project.visibility == "lab" else "none"


@router.post("", status_code=201)
def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role not in ("PI", "TEACHER"):
        raise HTTPException(status_code=403, detail="只有 PI/教师可以创建项目")
    if db.scalar(select(Project).where(Project.code == body.code)):
        raise HTTPException(status_code=409, detail="项目编号已存在")
    project = Project(**body.model_dump(), owner_id=user.id)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, project_role="owner"))
    write_audit_log(db, user, "create_project", "project", project.id, {"code": project.code})
    db.commit()
    return ok(_out(project, user.name), message="项目创建成功")


@router.get("/{project_id}")
def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    ensure_project_visible(db, user, project)
    item = _out(project, _owner_name(db, project))
    item["my_role"] = _my_role(db, project, user)

    total_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.project_id == project.id, Task.deleted_at.is_(None)
        )
    ) or 0
    done_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.project_id == project.id, Task.deleted_at.is_(None), Task.status == "done"
        )
    ) or 0
    overdue_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.project_id == project.id,
            Task.deleted_at.is_(None),
            Task.status.notin_(("done", "cancelled")),
            Task.due_date < func.current_date(),
        )
    ) or 0
    milestones = db.scalars(
        select(Milestone).where(Milestone.project_id == project.id).order_by(Milestone.due_date)
    ).all()

    item["task_total"] = int(total_tasks or 0)
    item["task_done"] = int(done_tasks or 0)
    item["task_overdue"] = int(overdue_tasks)
    item["milestone_count"] = len(milestones)
    return ok(item)


@router.patch("/{project_id}")
def update_project(
    project_id: int,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    ensure_project_manageable(db, user, project)
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(project, field, value)
    write_audit_log(db, user, "update_project", "project", project.id, {"fields": list(data.keys())})
    db.commit()
    return ok(_out(project, _owner_name(db, project)), message="项目更新成功")


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    if user.role != "PI" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="只有 PI 或项目负责人可以删除项目")
    from app.models.base import utcnow

    project.deleted_at = utcnow()
    write_audit_log(db, user, "delete_project", "project", project.id, {"code": project.code})
    db.commit()
    return ok(message="项目已删除")


# ---------- project members ----------


@router.get("/{project_id}/members")
def list_project_members(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    ensure_project_visible(db, user, project)
    rows = db.scalars(
        select(ProjectMember)
        .options(joinedload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
    ).all()
    items = []
    for m in rows:
        items.append(
            {
                "id": m.id,
                "user_id": m.user_id,
                "name": m.user.name if m.user else None,
                "username": m.user.username if m.user else None,
                "project_role": m.project_role,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                "left_at": m.left_at.isoformat() if m.left_at else None,
            }
        )
    return ok(items)


@router.post("/{project_id}/members", status_code=201)
def add_project_member(
    project_id: int,
    body: ProjectMemberAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    ensure_project_manageable(db, user, project)
    target = db.get(User, body.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if is_project_member(db, project_id, body.user_id):
        raise HTTPException(status_code=409, detail="该用户已是项目成员")
    db.add(ProjectMember(project_id=project_id, user_id=body.user_id, project_role=body.project_role))
    create_notification(
        db,
        body.user_id,
        "project_added",
        "加入项目",
        f"你被加入项目「{project.name}」",
        "project",
        project.id,
    )
    write_audit_log(db, user, "add_project_member", "project", project_id, {"user_id": body.user_id})
    db.commit()
    return ok(message="成员已加入")


@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    ensure_project_manageable(db, user, project)
    if project.owner_id == user_id:
        raise HTTPException(status_code=400, detail="不能移除项目负责人")
    membership = is_project_member(db, project_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="该用户不是项目成员")
    db.delete(membership)
    write_audit_log(db, user, "remove_project_member", "project", project_id, {"user_id": user_id})
    db.commit()
    return ok(message="成员已移除")


# ---------- milestones ----------


@router.get("/{project_id}/milestones")
def list_milestones(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    ensure_project_visible(db, user, project)
    rows = db.scalars(
        select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.due_date)
    ).all()
    return ok([MilestoneOut.model_validate(m).model_dump() for m in rows])


@router.post("/{project_id}/milestones", status_code=201)
def create_milestone(
    project_id: int,
    body: MilestoneCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = _get_project(db, project_id)
    ensure_project_manageable(db, user, project)
    milestone = Milestone(**body.model_dump(), project_id=project_id)
    db.add(milestone)
    db.flush()
    write_audit_log(db, user, "create_milestone", "milestone", milestone.id)
    db.commit()
    return ok(MilestoneOut.model_validate(milestone).model_dump(), message="里程碑已创建")


milestones_router = APIRouter(prefix="/milestones", tags=["milestones"])


def _get_milestone(db: Session, milestone_id: int) -> Milestone:
    milestone = db.get(Milestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="里程碑不存在")
    return milestone


@milestones_router.patch("/{milestone_id}")
def update_milestone(
    milestone_id: int,
    body: MilestoneUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    milestone = _get_milestone(db, milestone_id)
    project = _get_project(db, milestone.project_id)
    ensure_project_manageable(db, user, project)
    data = body.model_dump(exclude_unset=True)
    if data.get("status") == "completed" and milestone.completed_at is None:
        from app.models.base import utcnow

        milestone.completed_at = utcnow()
    for field, value in data.items():
        setattr(milestone, field, value)
    write_audit_log(db, user, "update_milestone", "milestone", milestone.id)
    db.commit()
    return ok(MilestoneOut.model_validate(milestone).model_dump(), message="里程碑已更新")


@milestones_router.delete("/{milestone_id}")
def delete_milestone(
    milestone_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    milestone = _get_milestone(db, milestone_id)
    project = _get_project(db, milestone.project_id)
    ensure_project_manageable(db, user, project)
    db.delete(milestone)
    write_audit_log(db, user, "delete_milestone", "milestone", milestone.id)
    db.commit()
    return ok(message="里程碑已删除")
