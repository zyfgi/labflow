"""Context builder: render permission-filtered hits into one bounded JSON block.

Only whitelisted fields (added by the retrievers) are rendered; raw rows are
never serialized. Records travel as JSON objects so titles/content containing
quotes or angle brackets cannot break any tag boundary — the outer
<labflow_sources> wrapper plus the system prompt's untrusted-data rule are the
only contract with the model.
"""

import json

from app.core.time import app_today
from app.services.retrieval.types import RetrievalHit


def _render_hit(hit: RetrievalHit) -> dict:
    data = {
        k: v
        for k, v in (hit.metadata.get("context") or {}).items()
        if v not in (None, "")
    }
    return {
        "type": hit.source_type,
        "id": hit.source_id,
        "title": hit.title,
        "data": data or {"excerpt": hit.excerpt},
    }


def build_context(hits: list[RetrievalHit], max_chars: int, timezone_label: str) -> str:
    """Build the bounded JSON source block appended to the user message.

    Hits must already be permission-filtered by the retrieval engine; this
    function performs NO additional data access.
    """
    header = (
        f"<labflow_metadata>\ncurrent_date: {app_today().isoformat()}\n"
        f"timezone: {timezone_label}\n</labflow_metadata>"
    )
    records: list[dict] = []
    total = len(header)
    for hit in sorted(hits, key=lambda h: h.score, reverse=True):
        record = _render_hit(hit)
        size = len(json.dumps(record, ensure_ascii=False))
        if total + size > max_chars:
            break
        records.append(record)
        total += size
    body = json.dumps(records, ensure_ascii=False) if records else "[]"
    return f"{header}\n<labflow_sources>\n{body}\n</labflow_sources>"
