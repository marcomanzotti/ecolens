"""Helpers for yearly series: counting valid values and building the response points."""

from __future__ import annotations

import math
from collections.abc import Sequence

from trend_detective.models import SeriesPoint


def is_valid(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def valid_count(values: Sequence[float | None]) -> int:
    return sum(1 for v in values if is_valid(v))


def series_points(years: Sequence[int], values: Sequence[float | None]) -> list[SeriesPoint]:
    """One point per year; a value that is not a finite number becomes None."""
    return [
        SeriesPoint(year=year, value=value if is_valid(value) else None)
        for year, value in zip(years, values, strict=True)
    ]
