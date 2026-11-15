"""Bounded in-memory cache with a time to live, least recently used entry evicted first."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Any

from pydantic import BaseModel

COORDINATE_DECIMALS = 2
COORDINATE_FIELDS = frozenset({"lat", "lon", "lat_min", "lat_max", "lon_min", "lon_max"})


class TtlLruCache:
    """`max_entries` 0 or `ttl` 0 disables the cache."""

    def __init__(
        self, max_entries: int, ttl: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._max_entries = max_entries
        self._ttl = ttl
        self._clock = clock
        self._entries: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()

    def get(self, key: Hashable) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at <= self._clock():
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return value

    def put(self, key: Hashable, value: Any) -> None:
        if self._max_entries <= 0 or self._ttl <= 0:
            return
        self._entries[key] = (self._clock() + self._ttl, value)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)


def _rounded(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            name: round(item, COORDINATE_DECIMALS)
            if name in COORDINATE_FIELDS and isinstance(item, int | float)
            else _rounded(item)
            for name, item in value.items()
        }
    if isinstance(value, list):
        return [_rounded(item) for item in value]
    return value


def request_key(route: str, body: BaseModel) -> str:
    """Cache key of a validated request. Coordinates are rounded for the key only."""
    import json

    payload = _rounded(body.model_dump(mode="json"))
    return f"{route}:{json.dumps(payload, sort_keys=True, separators=(',', ':'))}"
