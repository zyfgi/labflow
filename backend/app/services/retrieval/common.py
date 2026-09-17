"""Shared helpers for retrieval source modules."""

from app.core.time import time_range  # noqa: F401  (re-exported for modules)


def truncate(text: str | None, limit: int = 220) -> str:
    if not text:
        return ""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def first_non_empty(*values: str | None) -> str:
    for v in values:
        if v and str(v).strip():
            return str(v)
    return ""
