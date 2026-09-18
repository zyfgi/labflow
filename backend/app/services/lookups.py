"""Batch id->name lookups shared by list endpoints.

Keeps list rendering at a constant query count (one IN query per relation)
instead of per-row db.get() calls, which the AGENTS.md rules forbid.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session


def id_name_map(db: Session, id_column, name_column, ids) -> dict[int, str]:
    unique = {i for i in ids if i is not None}
    if not unique:
        return {}
    return dict(
        db.execute(select(id_column, name_column).where(id_column.in_(unique))).all()
    )
