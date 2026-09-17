"""Weekly report retrieval.

Permission rule mirrors the WeeklyReport API exactly:
- PI / TEACHER: all reports
- others with a member profile: only their own reports
- GUEST / no profile: nothing

A student asking about someone else's reports therefore gets zero hits from
the scope itself — no existence signal, no side channel.
"""

from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.report import WeeklyReport
from app.models.user import MemberProfile, User
from app.permissions import is_teaching_staff
from app.core.time import time_range
from app.services.retrieval.common import truncate
from app.services.retrieval.entity_resolver import ResolvedEntities
from app.services.retrieval.types import RetrievalHit, RetrievalPlan

_FIELDS = (
    WeeklyReport.work_summary,
    WeeklyReport.learning_summary,
    WeeklyReport.experiment_summary,
    WeeklyReport.problems,
    WeeklyReport.next_week_plan,
    WeeklyReport.need_help,
)


def search_weekly_reports(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 6,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    stmt = select(WeeklyReport)
    if is_teaching_staff(user):
        pass  # full visibility
    else:
        profile: MemberProfile | None = user.member_profile
        if profile is None:
            return []
        stmt = stmt.where(WeeklyReport.member_id == profile.id)

    member_id: int | None
    if plan.mine_only:
        member_id = user.member_profile.id if user.member_profile else None
    elif entities.member:
        member_id = entities.member.id
    else:
        member_id = None
    if member_id:
        stmt = stmt.where(WeeklyReport.member_id == member_id)

    keywords = [k for k in plan.keywords if k]
    if keywords and use_keywords and not entities.found:
        stmt = stmt.where(or_(*(or_(*(f.ilike(f"%{kw}%") for f in _FIELDS)) for kw in keywords)))

    date_from, date_to = time_range(plan.time_preset)
    if date_from:
        stmt = stmt.where(WeeklyReport.week_start >= date_from)
    if date_to:
        stmt = stmt.where(WeeklyReport.week_start <= date_to)

    rows = db.scalars(
        stmt.order_by(WeeklyReport.week_start.desc()).limit(limit * 3)
    ).all()
    if not rows:
        return []

    member_names = {}
    member_ids = {r.member_id for r in rows}
    for mp in db.scalars(
        select(MemberProfile).where(MemberProfile.id.in_(member_ids))
    ).all():
        u = db.get(User, mp.user_id) if mp else None
        member_names[mp.id] = u.name if u else None

    hits: list[RetrievalHit] = []
    for r in rows:
        score = 1.0
        low = lambda s: (s or "").lower()
        for kw in keywords:
            if any(kw.lower() in low(getattr(r, c)) for c in (
                "work_summary", "learning_summary", "experiment_summary",
                "problems", "next_week_plan", "need_help",
            )):
                score += 3
        if member_id and r.member_id == member_id:
            score += 2
        week_label = f"{r.week_start.isoformat()} 周报"
        excerpt = truncate(
            " ".join(
                filter(None, [r.work_summary, r.problems and f"问题：{r.problems}", r.next_week_plan and f"计划：{r.next_week_plan}"])
            )
        )
        hits.append(
            RetrievalHit(
                source_type="weekly_report",
                source_id=r.id,
                title=f"{member_names.get(r.member_id) or ''} {week_label}".strip(),
                excerpt=excerpt,
                score=score,
                url="/weekly-reports",
                project_id=None,
                occurred_at=r.week_start,
                metadata={
                    "status": r.status,
                    "week_start": r.week_start.isoformat(),
                    "week_end": (r.week_start + timedelta(days=6)).isoformat(),
                    "member_name": member_names.get(r.member_id),
                    "review_comment": truncate(r.review_comment, 120) or None,
                    "context": {
                        "member_name": member_names.get(r.member_id),
                        "week_start": r.week_start.isoformat(),
                        "week_end": (r.week_start + timedelta(days=6)).isoformat(),
                        "work_summary": truncate(r.work_summary, 600),
                        "learning_summary": truncate(r.learning_summary, 400),
                        "experiment_summary": truncate(r.experiment_summary, 400),
                        "problems": truncate(r.problems, 400),
                        "next_week_plan": truncate(r.next_week_plan, 400),
                        "need_help": truncate(r.need_help, 300),
                        "review_comment": truncate(r.review_comment, 300),
                    },
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
