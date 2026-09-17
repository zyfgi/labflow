"""Single source for business time.

`app_now()/app_today()` follow APP_TIMEZONE (business calendar: "today",
"this week", overdue checks, AI metadata); `utcnow()` is the naive-UTC clock
used for DB timestamp columns. Do not call date.today()/datetime.now()
elsewhere.
"""

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import settings


@lru_cache
def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.APP_TIMEZONE)
    except Exception:
        return ZoneInfo("UTC")


def utcnow() -> datetime:
    """Naive UTC — matches DateTime columns written by models/base.py."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def app_now() -> datetime:
    """Naive local business time in APP_TIMEZONE."""
    return datetime.now(_tz()).replace(tzinfo=None)


def app_today() -> date:
    return app_now().date()


def week_start_of(d: date | None = None) -> date:
    d = d or app_today()
    return d - timedelta(days=d.weekday())


def time_range(preset: str) -> tuple[date | None, date | None]:
    """Resolve a retrieval time preset to an inclusive (from, to) date range."""
    today = app_today()
    if preset == "today":
        return today, today
    if preset == "this_week":
        return week_start_of(today), today
    if preset == "last_week":
        ws = week_start_of(today)
        return ws - timedelta(days=7), ws - timedelta(days=1)
    if preset == "last_7_days":
        return today - timedelta(days=6), today
    if preset == "last_30_days":
        return today - timedelta(days=29), today
    if preset == "this_month":
        return today.replace(day=1), today
    return None, None
