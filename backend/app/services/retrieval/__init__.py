"""Retrieval engine shared by the global Search API and the AI assistant.

Everything a user (or an AI request on behalf of a user) can see must come out
of this package. Permission scopes live in `access.py` and are always applied
inside SQL — no post-filtering of already-fetched rows.
"""

from app.services.retrieval.access import (  # noqa: F401
    apply_project_read_scope,
    is_teaching_staff,
    visible_project_ids_subquery,
)
from app.services.retrieval.types import RetrievalHit, RetrievalPlan, SourceType  # noqa: F401
