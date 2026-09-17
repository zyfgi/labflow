"""Simple in-process per-user rate limiter (fixed window, no Redis).

Sufficient for a single-instance lab deployment; swap for Redis if the
backend is ever scaled out.
"""

import threading
import time
from collections import defaultdict, deque

from app.core.config import settings
from app.services.ai.errors import AIRateLimitedError


class _Window:
    __slots__ = ("minute", "day")

    def __init__(self) -> None:
        self.minute: deque[float] = deque()
        self.day: deque[float] = deque()


class RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[int, _Window] = defaultdict(_Window)

    def check(self, user_id: int) -> None:
        now = time.time()
        with self._lock:
            w = self._windows[user_id]
            while w.minute and now - w.minute[0] > 60:
                w.minute.popleft()
            while w.day and now - w.day[0] > 86400:
                w.day.popleft()
            if len(w.minute) >= settings.AI_RATE_LIMIT_PER_MINUTE:
                raise AIRateLimitedError("per-minute limit exceeded")
            if len(w.day) >= settings.AI_RATE_LIMIT_PER_DAY:
                raise AIRateLimitedError("per-day limit exceeded")
            w.minute.append(now)
            w.day.append(now)


limiter = RateLimiter()
