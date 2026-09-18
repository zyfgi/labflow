from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, write_audit_log
from app.core.responses import ok
from app.database import get_db
from app.models.learning import LearningPlan
from app.models.user import MemberProfile, User
from app.permissions import is_staff
from app.schemas.learning import (
    LearningPlanCreate,
    LearningPlanOut,
    LearningPlanUpdate,
)

router = APIRouter(prefix="/learning-plans", tags=["learning-plans"])


def _plan_out(plan: LearningPlan) -> dict:
    return LearningPlanOut.model_validate(plan).model_dump()


def _get_plan_or_404(db: Session, plan_id: int) -> LearningPlan:
    plan = db.get(LearningPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    return plan


def _resolve_member_id(db: Session, user: User, member_id: int | None) -> int:
    if member_id is not None:
        if not db.get(MemberProfile, member_id):
            raise HTTPException(status_code=404, detail="成员不存在")
        return member_id
    profile = user.member_profile
    if not profile:
        raise HTTPException(
            status_code=400, detail="当前用户没有成员档案，请指定 member_id"
        )
    return profile.id


def _ensure_can_edit(db: Session, user: User, member_id: int) -> None:
    if is_staff(user):
        return
    profile = user.member_profile
    if profile is None or profile.id != member_id:
        raise HTTPException(status_code=403, detail="只能编辑自己的学习计划")


@router.get("")
def list_plans(
    member_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query_member_id = member_id
    if user.role == "EQUIPMENT_ADMIN":
        raise HTTPException(status_code=403, detail="设备管理员无权访问学习计划模块")
    if not is_staff(user):
        profile = user.member_profile
        if not profile:
            raise HTTPException(status_code=403, detail="没有成员档案")
        # students only ever see their own plans
        if query_member_id is not None and query_member_id != profile.id:
            raise HTTPException(status_code=403, detail="只能查看自己的学习计划")
        query_member_id = profile.id

    stmt = select(LearningPlan)
    if query_member_id is not None:
        stmt = stmt.where(LearningPlan.member_id == query_member_id)
    if status:
        stmt = stmt.where(LearningPlan.status == status)
    stmt = stmt.order_by(LearningPlan.updated_at.desc())
    plans = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    # plans are personal lists; no heavy pagination UI needed but still bounded
    return ok([_plan_out(p) for p in plans])


@router.post("", status_code=201)
def create_plan(
    body: LearningPlanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_can_edit(db, user, body.member_id)
    if not db.get(MemberProfile, body.member_id):
        raise HTTPException(status_code=404, detail="成员不存在")
    plan = LearningPlan(**body.model_dump(), created_by=user.id)
    db.add(plan)
    db.flush()
    write_audit_log(db, user, "create_learning_plan", "learning_plan", plan.id)
    db.commit()
    return ok(_plan_out(plan), message="学习计划创建成功")


@router.patch("/{plan_id}")
def update_plan(
    plan_id: int,
    body: LearningPlanUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    plan = _get_plan_or_404(db, plan_id)
    _ensure_can_edit(db, user, plan.member_id)
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(plan, field, value)
    write_audit_log(db, user, "update_learning_plan", "learning_plan", plan.id)
    db.commit()
    return ok(_plan_out(plan), message="学习计划更新成功")


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    plan = _get_plan_or_404(db, plan_id)
    _ensure_can_edit(db, user, plan.member_id)
    db.delete(plan)
    write_audit_log(db, user, "delete_learning_plan", "learning_plan", plan.id)
    db.commit()
    return ok(message="学习计划已删除")
