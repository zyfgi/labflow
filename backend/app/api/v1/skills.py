from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_pi, write_audit_log
from app.core.responses import ok
from app.database import get_db
from app.models.learning import MemberSkill, Skill
from app.models.user import MemberProfile, User
from app.permissions import ensure_can_view_member
from app.schemas.learning import MemberSkillItem, MemberSkillOut, SkillCreate, SkillOut

router = APIRouter(prefix="/skills", tags=["skills"])
member_skills_router = APIRouter(prefix="/members/{member_id}/skills", tags=["skills"])


@router.get("")
def list_skills(
    include_inactive: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Skill).order_by(Skill.sort_order, Skill.id)
    if not include_inactive:
        stmt = stmt.where(Skill.is_active.is_(True))
    rows = db.scalars(stmt).all()
    return ok([SkillOut.model_validate(s).model_dump() for s in rows])


@router.post("", status_code=201)
def create_skill(
    body: SkillCreate,
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    if db.scalar(select(Skill).where(Skill.name == body.name)):
        raise HTTPException(status_code=409, detail="同名技能已存在")
    skill = Skill(**body.model_dump())
    db.add(skill)
    db.flush()
    write_audit_log(db, user, "create_skill", "skill", skill.id, {"name": skill.name})
    db.commit()
    return ok(SkillOut.model_validate(skill).model_dump(), message="技能创建成功")


@member_skills_router.get("")
def get_member_skills(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    member = db.get(MemberProfile, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    ensure_can_view_member(user, member)
    rows = db.scalars(
        select(MemberSkill).where(MemberSkill.member_id == member_id)
    ).all()
    return ok([MemberSkillOut.model_validate(r).model_dump() for r in rows])


@member_skills_router.put("")
def set_member_skills(
    member_id: int,
    body: list[MemberSkillItem],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    member = db.get(MemberProfile, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    is_self = user.member_profile is not None and user.member_profile.id == member_id
    if user.role != "PI" and not (is_self or user.role == "TEACHER"):
        raise HTTPException(status_code=403, detail="只能编辑自己的技能")

    skill_ids = {item.skill_id for item in body}
    existing_skills = set(
        db.scalars(select(Skill.id).where(Skill.id.in_(skill_ids or [0]))).all()
    )
    missing = skill_ids - existing_skills
    if missing:
        raise HTTPException(status_code=400, detail=f"技能不存在: {sorted(missing)}")

    current = {
        ms.skill_id: ms
        for ms in db.scalars(
            select(MemberSkill).where(MemberSkill.member_id == member_id)
        ).all()
    }
    seen = set()
    for item in body:
        seen.add(item.skill_id)
        if item.skill_id in current:
            current[item.skill_id].level = item.level
            current[item.skill_id].note = item.note
        else:
            db.add(
                MemberSkill(
                    member_id=member_id,
                    skill_id=item.skill_id,
                    level=item.level,
                    note=item.note,
                )
            )
    # remove entries not present anymore
    for skill_id, ms in current.items():
        if skill_id not in seen:
            db.delete(ms)
    write_audit_log(
        db, user, "update_member_skills", "member", member_id, {"count": len(body)}
    )
    db.commit()
    rows = db.scalars(
        select(MemberSkill).where(MemberSkill.member_id == member_id)
    ).all()
    return ok(
        [MemberSkillOut.model_validate(r).model_dump() for r in rows],
        message="技能已更新",
    )
