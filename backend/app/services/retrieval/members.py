"""Member + learning plan retrieval.

Member hits expose only display fields (name / type / direction) and are
restricted to PI / TEACHER (or the member themselves). No student_no, email,
phone or progress scores ever leave this module.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.time import time_range
from app.models.learning import LearningPlan
from app.models.user import MemberProfile, User
from app.permissions import is_teaching_staff
from app.services.retrieval.common import truncate
from app.services.retrieval.entity_resolver import ResolvedEntities
from app.services.retrieval.types import RetrievalHit, RetrievalPlan


def search_members(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 5,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    if not is_teaching_staff(user):
        return []  # students/equipment-admin: no member directory hits

    stmt = (
        select(MemberProfile)
        .options(joinedload(MemberProfile.user))
        .where(MemberProfile.status == "active")
    )
    if entities.member:
        stmt = stmt.where(MemberProfile.id == entities.member.id)

    keywords = [k for k in plan.keywords if k]
    if keywords and use_keywords and not entities.member:
        fields = (User.name, User.username, MemberProfile.research_direction)
        stmt = stmt.join(User, MemberProfile.user_id == User.id).where(
            or_(*(or_(*(f.ilike(f"%{kw}%") for f in fields)) for kw in keywords))
        )

    rows = db.scalars(stmt.limit(limit * 2)).all()
    hits: list[RetrievalHit] = []
    for m in rows:
        score = 1.0
        name = m.user.name if m.user else ""
        for kw in keywords:
            if kw.lower() in (name or "").lower():
                score += 4
            if m.research_direction and kw.lower() in m.research_direction.lower():
                score += 2
        if entities.member and m.id == entities.member.id:
            score += 5
        hits.append(
            RetrievalHit(
                source_type="member",
                source_id=m.id,
                title=name,
                excerpt=truncate(
                    f"{m.member_type} · {m.research_direction or '研究方向未填写'}"
                ),
                score=score,
                url=f"/members/{m.id}",
                project_id=None,
                occurred_at=None,
                metadata={
                    "member_type": m.member_type,
                    "research_direction": m.research_direction,
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


def search_learning_plans(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 5,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    """Plan visibility: PI/TEACHER any; others only their own."""
    stmt = select(LearningPlan)
    if not is_teaching_staff(user):
        profile = user.member_profile
        if profile is None:
            return []
        stmt = stmt.where(LearningPlan.member_id == profile.id)

    if plan.mine_only:
        if not user.member_profile:
            return []
        stmt = stmt.where(LearningPlan.member_id == user.member_profile.id)
    elif entities.member:
        stmt = stmt.where(LearningPlan.member_id == entities.member.id)

    keywords = [k for k in plan.keywords if k]
    if keywords and not entities.member:
        fields = (LearningPlan.title, LearningPlan.description, LearningPlan.category)
        stmt = stmt.where(
            or_(*(or_(*(f.ilike(f"%{kw}%") for f in fields)) for kw in keywords))
        )

    date_from, date_to = time_range(plan.time_preset)
    if date_from:
        stmt = stmt.where(LearningPlan.updated_at >= date_from)

    rows = db.scalars(
        stmt.order_by(LearningPlan.updated_at.desc()).limit(limit * 2)
    ).all()
    member_names = {}
    member_ids = {r.member_id for r in rows}
    for mp in db.scalars(
        select(MemberProfile).where(MemberProfile.id.in_(member_ids))
    ).all():
        u = db.get(User, mp.user_id) if mp else None
        member_names[mp.id] = u.name if u else None

    hits: list[RetrievalHit] = []
    for p in rows:
        score = 1.5
        for kw in keywords:
            if kw.lower() in (p.title or "").lower():
                score += 4
            if p.description and kw.lower() in p.description.lower():
                score += 2
        hits.append(
            RetrievalHit(
                source_type="learning_plan",
                source_id=p.id,
                title=p.title,
                excerpt=truncate(
                    f"状态 {p.status} · 进度 {p.progress}% · {p.description or ''}"
                ),
                score=score,
                url="/learning-plans",
                project_id=None,
                occurred_at=p.updated_at,
                metadata={
                    "status": p.status,
                    "progress": p.progress,
                    "member_name": member_names.get(p.member_id),
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
