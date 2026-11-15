"""In-memory sliding-window rate limiter, one window per client key.

State lives in the process: on Cloud Run every instance counts on its own, which
is enough to stop one client from hammering the upstream source.
"""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable

WINDOW_SECONDS = 60.0
MAX_TRACKED_CLIENTS = 10_000


class SlidingWindowLimiter:
    """Allows at most `limit` hits per `window` seconds for each key. `limit` 0 disables it."""

    def __init__(
        self,
        limit: int,
        window: float = WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        max_clients: int = MAX_TRACKED_CLIENTS,
    ) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._max_clients = max_clients
        self._hits: dict[str, deque[float]] = {}

    def retry_after(self, key: str) -> int | None:
        """Seconds to wait if `key` is over the limit right now, without recording a hit."""
        if self._limit <= 0:
            return None
        hits = self._fresh_hits(key, self._clock())
        if hits is None or len(hits) < self._limit:
            return None
        return max(1, math.ceil(hits[0] + self._window - self._clock()))

    def record(self, key: str) -> None:
        if self._limit <= 0:
            return
        now = self._clock()
        if key not in self._hits and len(self._hits) >= self._max_clients:
            self._evict(now)
        self._hits.setdefault(key, deque()).append(now)

    def tracked_clients(self) -> int:
        return len(self._hits)

    def _fresh_hits(self, key: str, now: float) -> deque[float] | None:
        hits = self._hits.get(key)
        if hits is None:
            return None
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return None
        return hits

    def _evict(self, now: float) -> None:
        """Drop the clients with no recent hit; if all are active, drop the oldest one."""
        for key in list(self._hits):
            self._fresh_hits(key, now)
        if len(self._hits) >= self._max_clients:
            del self._hits[next(iter(self._hits))]
