"""Context builder: render permission-filtered hits into a bounded, minimal
text context. Only whitelisted fields (added by the retrievers) are rendered;
raw rows are never serialized. Every record is wrapped in an explicit
untrusted-source boundary.
"""

from app.core.config import settings
from app.services.ai.prompts import SYSTEM_PROMPT  # noqa: F401  (re-export)
from app.services.retrieval.types import RetrievalHit

_SOURCE_LABELS = {
    "project": "项目",
    "task": "任务",
    "experiment": "实验",
    "weekly_report": "周报",
    "equipment": "设备",
    "maintenance": "维修记录",
    "booking": "设备预约",
    "member": "成员",
    "learning_plan": "学习计划",
}

_EXCERPT_LIMIT = 500


def source_label(hit: RetrievalHit) -> str:
    label = _SOURCE_LABELS.get(hit.source_type, hit.source_type)
    return f"[{label} {hit.title}]"


def _render_hit(hit: RetrievalHit) -> str:
    ctx = hit.metadata.get("context") or {}
    lines: list[str] = []
    for key, value in ctx.items():
        if value is None or str(value).strip() == "":
            continue
        lines.append(f"{key}: {value}")
    body = "\n".join(lines) if lines else hit.excerpt
    if len(body) > _EXCERPT_LIMIT:
        body = body[: _EXCERPT_LIMIT - 1] + "…"
    return (
        f'<labflow_source id="{hit.source_type}:{hit.source_id}" '
        f'title="{hit.title}" url="{hit.url or ""}">\n{body}\n</labflow_source>'
    )


def build_context(question: str, hits: list[RetrievalHit]) -> str:
    """Build the bounded source block appended to the user message.

    Hits must already be permission-filtered by the retrieval engine; this
    function performs NO additional data access.
    """
    from datetime import date

    header = (
        f"<labflow_metadata>\ncurrent_date: {date.today().isoformat()}\n"
        f"timezone: {settings.APP_TIMEZONE}\n</labflow_metadata>"
    )
    chunks: list[str] = [header]
    total = sum(len(c) for c in chunks)
    max_chars = settings.AI_MAX_CONTEXT_CHARS
    used: list[RetrievalHit] = []
    for hit in sorted(hits, key=lambda h: h.score, reverse=True):
        block = _render_hit(hit)
        if total + len(block) > max_chars:
            break
        chunks.append(block)
        total += len(block)
        used.append(hit)
    if not used:
        return header + "\n<labflow_sources>\n(no matching records found)\n</labflow_sources>"
    return header + "\n<labflow_sources>\n" + "\n".join(chunks) + "\n</labflow_sources>"
