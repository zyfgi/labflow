"""Retrieval engine entry point.

retrieve() is independent of any LLM: question in, permission-filtered
RetrievalHits out. The AI service and the /search + /ai/retrieve APIs all
sit on top of this.
"""

import re

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.retrieval import equipment as equipment_retriever
from app.services.retrieval import experiments as experiment_retriever
from app.services.retrieval import members as member_retriever
from app.services.retrieval import projects as project_retriever
from app.services.retrieval import tasks as task_retriever
from app.services.retrieval import weekly_reports as report_retriever
from app.services.retrieval.entity_resolver import resolve_entities
from app.services.retrieval.intent_parser import parse_query
from app.services.retrieval.types import ALL_SOURCE_TYPES, RetrievalHit, RetrievalPlan


def retrieve(
    db: Session,
    user: User,
    query: str,
    *,
    plan: RetrievalPlan | None = None,
    source_types: list[str] | None = None,
    limit: int = 16,
) -> tuple[RetrievalPlan, list[RetrievalHit]]:
    """Return (effective_plan, hits). Never raises on empty results."""
    effective_plan = plan or parse_query(query)
    if source_types:
        effective_plan.source_types = list(dict.fromkeys(source_types))

    entities = resolve_entities(db, query, effective_plan.member_name)

    wanted = [s for s in (effective_plan.source_types or []) if s in ALL_SOURCE_TYPES]
    if not wanted:
        wanted = ["project", "task", "experiment", "weekly_report", "equipment"]
    # entity-driven widening: asking about a concrete thing must surface it
    if entities.equipment and "equipment" not in wanted:
        wanted += ["equipment", "maintenance"]
    if entities.experiment_id and "experiment" not in wanted:
        wanted.append("experiment")
    if entities.project and "project" not in wanted:
        wanted.append("project")
    if entities.member and "member" not in wanted:
        wanted.append("member")
    # maintenance/bookings intents imply equipment context
    if effective_plan.intent == "maintenance" and "equipment" not in wanted:
        wanted.append("equipment")
    if effective_plan.intent == "bookings" and "booking" not in wanted:
        wanted.append("booking")

    per_source = max(3, min(8, limit))
    # Recency-fallback (keyword pass found nothing) is only safe for open
    # natural-language questions. It must NOT run for exact-token lookups or
    # entity-targeted questions: asking about a hidden entity must yield zero
    # hits, never "some other recent rows" (plan §43/§44).
    fallback_allowed = not entities.found and not re.match(
        r"^[A-Za-z0-9_\-]{8,}$", (query or "").strip()
    )
    hits: list[RetrievalHit] = []
    # date-sensitive sources keep their time filter even in relaxed recall,
    # otherwise stale records would be presented as "recent" activity
    UNDATED_SOURCES = {"task", "booking", "equipment", "maintenance", "member", "learning_plan"}
    searchers = {
        "project": project_retriever.search_projects,
        "task": task_retriever.search_tasks,
        "experiment": experiment_retriever.search_experiments,
        "weekly_report": report_retriever.search_weekly_reports,
        "equipment": equipment_retriever.search_equipment,
        "maintenance": equipment_retriever.search_maintenance,
        "booking": equipment_retriever.search_bookings,
        "member": member_retriever.search_members,
        "learning_plan": member_retriever.search_learning_plans,
    }
    for source in wanted:
        fn = searchers.get(source)
        if fn is None:
            continue
        try:
            found = fn(db, user, effective_plan, entities, limit=per_source)
            if not found and effective_plan.keywords and fallback_allowed:
                # keyword filters too narrow -> relaxed recall inside permission scope
                updates: dict = {"keywords": []}
                if source in UNDATED_SOURCES:
                    updates["time_preset"] = "all"
                relaxed = effective_plan.model_copy(update=updates)
                found = fn(db, user, relaxed, entities, limit=per_source, use_keywords=False)
            hits.extend(found)
        except Exception:  # a failing source must not sink the whole retrieval
            continue

    hits.sort(key=lambda h: h.score, reverse=True)
    return effective_plan, hits[:limit]
