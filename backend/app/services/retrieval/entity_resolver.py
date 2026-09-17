"""Layer A: resolve concrete entities (member / project / equipment) from the
question text. One query per entity type: load id/name pairs, pick the
longest occurring match in Python, then load that single row if needed.

Resolution only returns identity rows; data access still goes through the
permission-scoped retrievers, so resolving an entity the user cannot read
simply yields zero hits downstream (no existence leak).
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.experiment import Experiment
from app.models.project import Project
from app.models.user import MemberProfile, User

_EXPERIMENT_NO_RE = re.compile(r"EXP-\d{8}-\d{3,5}", re.IGNORECASE)


@dataclass
class ResolvedEntities:
    member: MemberProfile | None = None
    project: Project | None = None
    equipment: Equipment | None = None
    experiment_id: int | None = None

    @property
    def found(self) -> bool:
        return any((self.member, self.project, self.equipment, self.experiment_id))


def _best_match(names: list[str], text: str) -> str | None:
    """Longest name that literally occurs in the question (specific beats short)."""
    best: str | None = None
    for name in names:
        if name and len(name) >= 2 and name in text:
            if best is None or len(name) > len(best):
                best = name
    return best


def resolve_entities(
    db: Session, question: str, plan_member_name: str | None = None
) -> ResolvedEntities:
    result = ResolvedEntities()
    text = (question or "").strip()
    if not text:
        return result

    # experiment number (regex-shaped, exact)
    m = _EXPERIMENT_NO_RE.search(text.upper())
    if m:
        exp_id = db.scalar(select(Experiment.id).where(Experiment.experiment_no == m.group(0)))
        if exp_id:
            result.experiment_id = exp_id

    # member: one query for names, one for the chosen profile
    names = db.scalars(select(User.name)).all()
    chosen = _best_match(list(names), text) or plan_member_name
    if chosen:
        result.member = db.scalar(
            select(MemberProfile)
            .join(User, MemberProfile.user_id == User.id)
            .where(User.name == chosen)
        )

    # project: one query for (id, name, code), one for the chosen row
    rows = db.execute(
        select(Project.id, Project.name, Project.code).where(Project.deleted_at.is_(None))
    ).all()
    best_id, best_len = None, 0
    for pid, name, code in rows:
        for label in (name, code):
            if label and len(label) >= 2 and label in text and len(label) > best_len:
                best_id, best_len = pid, len(label)
    if best_id is not None:
        result.project = db.get(Project, best_id)

    # equipment: same pattern
    rows = db.execute(
        select(Equipment.id, Equipment.name, Equipment.asset_no).where(
            Equipment.deleted_at.is_(None)
        )
    ).all()
    best_id, best_len = None, 0
    for eid, name, asset_no in rows:
        for label in (name, asset_no):
            if label and len(label) >= 2 and label in text and len(label) > best_len:
                best_id, best_len = eid, len(label)
    if best_id is not None:
        result.equipment = db.get(Equipment, best_id)

    return result
