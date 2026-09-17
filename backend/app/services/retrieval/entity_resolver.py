"""Layer A: resolve concrete entities (member / project / equipment) from the
question text. Resolution only returns identity rows; data access still goes
through the permission-scoped retrievers, so resolving an entity the user
cannot read simply yields zero hits downstream (no existence leak).
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.experiment import Experiment
from app.models.project import Project
from app.models.user import MemberProfile, User


@dataclass
class ResolvedEntities:
    member: MemberProfile | None = None
    project: Project | None = None
    equipment: Equipment | None = None
    experiment_id: int | None = None

    @property
    def found(self) -> bool:
        return any((self.member, self.project, self.equipment, self.experiment_id))


_EXPERIMENT_NO_RE = re.compile(r"EXP-\d{8}-\d{3,5}", re.IGNORECASE)


def resolve_entities(
    db: Session, question: str, plan_member_name: str | None = None
) -> ResolvedEntities:
    result = ResolvedEntities()
    text = (question or "").strip()
    if not text:
        return result

    # experiment number (exact, regex-shaped)
    m = _EXPERIMENT_NO_RE.search(text.upper())
    if m:
        exp = db.scalar(select(Experiment.id).where(Experiment.experiment_no == m.group(0)))
        if exp:
            result.experiment_id = exp

    # member: DB names occurring in the question (2+ chars)
    for name in db.scalars(select(User.name)).all()[:1000]:
        if name and len(name) >= 2 and name in text:
            profile = db.scalar(
                select(MemberProfile).where(
                    MemberProfile.user_id == db.scalar(select(User.id).where(User.name == name))
                )
            )
            if profile is not None:
                result.member = profile
                break
    if result.member is None and plan_member_name:
        result.member = db.scalar(
            select(MemberProfile)
            .join(User, MemberProfile.user_id == User.id)
            .where(User.name == plan_member_name)
        )

    # project: DB names / codes occurring in the question
    for name in db.scalars(select(Project.name).where(Project.deleted_at.is_(None))).all()[:500]:
        if name and len(name) >= 2 and name in text:
            result.project = db.scalar(
                select(Project).where(Project.deleted_at.is_(None), Project.name == name)
            )
            if result.project:
                break
    if result.project is None:
        for code in db.scalars(select(Project.code).where(Project.deleted_at.is_(None))).all()[:500]:
            if code and len(code) >= 2 and code.upper() in text.upper():
                result.project = db.scalar(
                    select(Project).where(Project.deleted_at.is_(None), Project.code == code)
                )
                if result.project:
                    break

    # equipment: DB names / asset numbers occurring in the question
    for name in db.scalars(select(Equipment.name).where(Equipment.deleted_at.is_(None))).all()[:500]:
        if name and len(name) >= 2 and name in text:
            result.equipment = db.scalar(
                select(Equipment).where(Equipment.deleted_at.is_(None), Equipment.name == name)
            )
            if result.equipment:
                break
    if result.equipment is None:
        for no in db.scalars(select(Equipment.asset_no).where(Equipment.deleted_at.is_(None))).all()[:500]:
            if no and len(no) >= 2 and no.upper() in text.upper():
                result.equipment = db.scalar(
                    select(Equipment).where(Equipment.deleted_at.is_(None), Equipment.asset_no == no)
                )
                if result.equipment:
                    break

    return result
