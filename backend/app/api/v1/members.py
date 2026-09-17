from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_pi, write_audit_log
from app.core.time import app_today, week_start_of
from app.core.responses import ok, paged
from app.database import get_db
from app.models.enums import Role
from app.models.user import MemberProfile, User
from app.permissions import ensure_can_view_member, is_staff
from app.schemas.member import (
    MemberCreate,
    MemberOut,
    MemberUpdate,
)
from app.schemas.user import UserOut

router = APIRouter(prefix="/members", tags=["members"])


def _member_out(member: MemberProfile) -> dict:
    return MemberOut.model_validate(member).model_dump()


def load_member_with_user(db: Session, member_id: int) -> MemberProfile | None:
    return db.scalar(
        select(MemberProfile)
        .options(joinedload(MemberProfile.user))
        .where(MemberProfile.id == member_id)
    )


@router.get("/me")
def my_member(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Current user's own member profile (students use this to resolve their id)."""
    if not user.member_profile:
        return ok(None)
    member = load_member_with_user(db, user.member_profile.id)
    if not member:
        return ok(None)
    item = _member_out(member)
    item["user"] = UserOut.model_validate(member.user).model_dump()
    return ok(item)


@router.get("")
def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member_type: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role == Role.EQUIPMENT_ADMIN or not is_staff(user):
        raise HTTPException(status_code=403, detail="没有查看成员列表的权限")
    stmt = select(MemberProfile).options(joinedload(MemberProfile.user))
    if member_type:
        stmt = stmt.where(MemberProfile.member_type == member_type)
    if status:
        stmt = stmt.where(MemberProfile.status == status)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.join(User, MemberProfile.user_id == User.id).where(
            or_(User.name.ilike(kw), User.username.ilike(kw), MemberProfile.student_no.ilike(kw),
                MemberProfile.research_direction.ilike(kw))
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(MemberProfile.id).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = []
    for m in rows:
        item = _member_out(m)
        item["user"] = UserOut.model_validate(m.user).model_dump()
        items.append(item)
    return paged(items, total, page, page_size)


@router.post("", status_code=201)
def create_member(
    body: MemberCreate,
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    target_user = db.get(User, body.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if db.scalar(select(MemberProfile).where(MemberProfile.user_id == body.user_id)):
        raise HTTPException(status_code=409, detail="该用户已有成员档案")
    member = MemberProfile(**body.model_dump())
    db.add(member)
    db.flush()
    write_audit_log(db, user, "create_member", "member", member.id, {"user_id": body.user_id})
    db.commit()
    return ok(_member_out(member), message="成员档案创建成功")


@router.get("/{member_id}")
def get_member(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    member = load_member_with_user(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    ensure_can_view_member(user, member)
    item = _member_out(member)
    item["user"] = UserOut.model_validate(member.user).model_dump()
    return ok(item)


@router.patch("/{member_id}")
def update_member(
    member_id: int,
    body: MemberUpdate,
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    member = db.get(MemberProfile, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(member, field, value)
    write_audit_log(db, user, "update_member", "member", member.id, {"fields": list(data.keys())})
    db.commit()
    return ok(_member_out(member), message="成员档案更新成功")


@router.get("/{member_id}/overview")
def member_overview(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    member = load_member_with_user(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    ensure_can_view_member(user, member)

    from app.models.experiment import Experiment
    from app.models.project import Project, ProjectMember, Task
    from app.models.report import WeeklyReport

    week_start = week_start_of()

    project_ids = db.scalars(
        select(ProjectMember.project_id).where(ProjectMember.user_id == member.user_id)
    ).all()
    projects = db.scalars(
        select(Project).where(
            Project.id.in_(project_ids or [0]), Project.deleted_at.is_(None),
            Project.status.in_(("planning", "active", "paused")),
        )
    ).all() if project_ids else []

    in_progress = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.assignee_id == member.user_id,
            Task.deleted_at.is_(None),
            Task.status.in_(("todo", "in_progress", "blocked", "review")),
        )
    ) or 0
    overdue = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.assignee_id == member.user_id,
            Task.deleted_at.is_(None),
            Task.status.in_(("todo", "in_progress", "blocked", "review")),
            Task.due_date < app_today(),
        )
    ) or 0

    report = db.scalar(
        select(WeeklyReport).where(
            WeeklyReport.member_id == member.id, WeeklyReport.week_start == week_start
        )
    )
    report_status = report.status if report else None

    latest_exp = db.scalar(
        select(func.max(Experiment.experiment_date)).where(
            Experiment.owner_id == member.user_id, Experiment.deleted_at.is_(None)
        )
    )

    return ok({
        "member": _member_out(member),
        "user": UserOut.model_validate(member.user).model_dump(),
        "current_projects": [
            {"id": p.id, "name": p.name, "status": p.status, "progress": p.progress} for p in projects
        ],
        "in_progress_tasks": in_progress,
        "overdue_tasks": overdue,
        "this_week_report_status": report_status,
        "latest_experiment_date": latest_exp.isoformat() if latest_exp else None,
    })
