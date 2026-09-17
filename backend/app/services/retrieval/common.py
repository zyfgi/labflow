"""Shared helpers for retrieval source modules."""

from datetime import date, timedelta


def time_range(preset: str) -> tuple[date | None, date | None]:
    """Resolve a time preset to (from, to) using the server-local calendar."""
    today = date.today()
    if preset == "today":
        return today, today
    if preset == "this_week":
        ws = today - timedelta(days=today.weekday())
        return ws, today
    if preset == "last_week":
        ws = today - timedelta(days=today.weekday())
        return ws - timedelta(days=7), ws - timedelta(days=1)
    if preset == "last_7_days":
        return today - timedelta(days=6), today
    if preset == "last_30_days":
        return today - timedelta(days=29), today
    if preset == "this_month":
        return today.replace(day=1), today
    return None, None


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
