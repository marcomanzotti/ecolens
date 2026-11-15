"""Test helpers of the investigation layer (BE-2).

* hand-made TrendStats / Variable objects;
* small deterministic fakes of the stats functions, so unit tests do not depend on BE-1;
* a parser for the saved NASA POWER samples and a FakeSeriesSource.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest

from trend_detective import catalog
from trend_detective import models as m
from trend_detective.errors import UpstreamError
from trend_detective.ports import AnnualSeries, GridSeries

DATA = Path(__file__).parent / "data"
FILL = -999.0
NIAMEY = m.Location(lat=13.51, lon=2.11, label="Niamey, Niger")
FULL = m.Period()
YEARS = list(range(1981, 2026))


# --------------------------------------------------------------------------
# Hand-made models
# --------------------------------------------------------------------------


def make_trend(
    *,
    direction: m.Direction = "up",
    evidence: m.Evidence = "strong",
    sen_slope: float = 0.5,
    ols_p: float = 0.001,
    mk_p: float = 0.002,
    mk_p_hr: float | None = None,
    corrected: bool = False,
    n: int = 45,
    n_missing: int = 0,
    lag1: float = 0.1,
    unit: str = "mm/day",
    std: float = 1.0,
    total_change: float = 2.0,
    percent_change: float | None = 10.0,
    mean: float = 5.0,
) -> m.TrendStats:
    return m.TrendStats(
        n=n,
        n_missing=n_missing,
        unit=unit,
        direction=direction,
        evidence=evidence,
        significant=evidence == "strong",
        methods_agree=evidence != "mixed",
        total_change=total_change,
        percent_change=percent_change,
        mean=mean,
        std=std,
        lag1_autocorrelation=lag1,
        autocorrelation_corrected=corrected,
        ols=m.OlsResult(
            slope_per_decade=sen_slope,
            stderr_per_decade=0.1,
            ci95_low=sen_slope - 0.2,
            ci95_high=sen_slope + 0.2,
            t_statistic=3.0,
            p_value=ols_p,
            r_squared=0.3,
            intercept=mean,
        ),
        mann_kendall=m.MannKendallResult(
            s=100.0, z=3.0, tau=0.4, p_value=mk_p, p_value_hamed_rao=mk_p_hr
        ),
        sen=m.SenResult(
            slope_per_decade=sen_slope, ci95_low=sen_slope - 0.2, ci95_high=sen_slope + 0.2
        ),
    )


# --------------------------------------------------------------------------
# Fakes of BE-1's functions (deterministic, simple, good enough for ranking tests)
# --------------------------------------------------------------------------


def _valid(years: Sequence[int], values: Sequence[float | None]) -> tuple[list[int], list[float]]:
    pairs = [(y, v) for y, v in zip(years, values, strict=True) if v is not None]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _ols(xs: list[int], ys: list[float]) -> tuple[float, float, float]:
    """slope per year, intercept, Pearson r."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    slope = sxy / sxx
    r = 0.0 if syy == 0 else sxy / math.sqrt(sxx * syy)
    return slope, my - slope * mx, r


def fake_compute_trend(
    years: Sequence[int], values: Sequence[float | None], unit: str
) -> m.TrendStats | None:
    xs, ys = _valid(years, values)
    if len(ys) < m.MIN_YEARS_FOR_TREND or max(ys) == min(ys):
        return None
    slope, _, r = _ols(xs, ys)
    mean = sum(ys) / len(ys)
    std = math.sqrt(sum((y - mean) ** 2 for y in ys) / (len(ys) - 1))
    z = abs(r) * math.sqrt(len(ys) - 1)
    p = min(1.0, math.erfc(z / math.sqrt(2)))
    significant = p < m.ALPHA
    direction: m.Direction = "flat" if slope == 0 else "up" if slope > 0 else "down"
    return make_trend(
        direction=direction,
        evidence="strong" if significant else "none",
        sen_slope=slope * 10,
        ols_p=p,
        mk_p=p,
        n=len(ys),
        n_missing=len(values) - len(ys),
        unit=unit,
        std=std,
        total_change=slope * (xs[-1] - xs[0]),
        percent_change=None,
        mean=mean,
    )


def fake_fit_line(years: Sequence[int], values: Sequence[float | None]) -> list[m.FitPoint]:
    xs, ys = _valid(years, values)
    if len(ys) < m.MIN_YEARS_FOR_TREND or max(ys) == min(ys):
        return []
    slope, intercept, _ = _ols(xs, ys)
    return [
        m.FitPoint(
            year=y,
            value=intercept + slope * y,
            ci_low=intercept + slope * y - 1,
            ci_high=intercept + slope * y + 1,
        )
        for y in range(xs[0], xs[-1] + 1)
    ]


def fake_benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    running = 1.0
    for rank, i in reversed(list(enumerate(order, start=1))):
        running = min(running, p_values[i] * n / rank)
        adjusted[i] = running
    return adjusted


def fake_pearson(a: Sequence[float | None], b: Sequence[float | None]) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b, strict=True) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx * syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def fake_compute_emergence(
    years: Sequence[int], values: Sequence[float | None]
) -> m.Emergence | None:
    xs, ys = _valid(years, values)
    if len(ys) < m.MIN_YEARS_FOR_TREND or max(ys) == min(ys):
        return None
    return m.Emergence(
        status="not_yet",
        emerged_year=None,
        years_needed=None,
        additional_years=None,
        noise_std=1.0,
        autocorrelation=0.0,
        running=[],
        explanation="fake",
    )


@pytest.fixture
def fake_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace BE-1's stats and emergence functions with the fakes above."""
    from trend_detective import emergence, stats

    monkeypatch.setattr(stats, "compute_trend", fake_compute_trend)
    monkeypatch.setattr(stats, "fit_line", fake_fit_line)
    monkeypatch.setattr(stats, "benjamini_hochberg", fake_benjamini_hochberg)
    monkeypatch.setattr(stats, "pearson", fake_pearson)
    monkeypatch.setattr(emergence, "compute_emergence", fake_compute_emergence)


# --------------------------------------------------------------------------
# Series builders
# --------------------------------------------------------------------------


def line(
    start: float, step: float, n: int = 45, noise: Callable[[int], float] | None = None
) -> list[float | None]:
    """A straight line with optional deterministic noise."""
    return [start + step * i + (noise(i) if noise else 0.0) for i in range(n)]


def wiggle(i: int) -> float:
    """Deterministic, zero-mean-ish noise."""
    return 0.3 * math.sin(i * 1.7) + 0.2 * math.cos(i * 0.9)


def variable(variable_id: str) -> m.Variable:
    return catalog.get_variable(variable_id)


# --------------------------------------------------------------------------
# Saved POWER samples (real Niamey data) and a fake source built on them
# --------------------------------------------------------------------------


def load_point_samples() -> dict[str, dict[str, float]]:
    raw: dict[str, dict[str, float]] = {}
    for name in ("power_point_sahel.json", "power_point_sahel_2.json"):
        raw.update(json.loads((DATA / name).read_text())["properties"]["parameter"])
    return raw


def annual_values(raw: Mapping[str, float], period: m.Period) -> AnnualSeries:
    """Annual means: POWER stores them under month 13. -999 becomes None."""
    values = (raw.get(f"{y}13", FILL) for y in range(period.start_year, period.end_year + 1))
    return [None if v == FILL else v for v in values]


def load_grid_samples(period: m.Period) -> list[GridSeries]:
    raw = json.loads((DATA / "power_regional_sahel.json").read_text())
    grid = []
    for feature in raw["features"]:
        lon, lat = feature["geometry"]["coordinates"][:2]
        series = annual_values(feature["properties"]["parameter"]["PRECTOTCORR"], period)
        grid.append(GridSeries(lat=lat, lon=lon, values=tuple(series)))
    return grid


class FakeSeriesSource:
    """Serves canned series and records the calls. Values are in POWER's own units."""

    def __init__(
        self,
        points: Mapping[str, AnnualSeries] | None = None,
        grid: Sequence[GridSeries] = (),
        error: Exception | None = None,
    ) -> None:
        self.points = dict(points or {})
        self.grid = list(grid)
        self.error = error
        self.point_calls: list[tuple[m.Location, tuple[str, ...], m.Period, m.Season]] = []
        self.region_calls: list[tuple[m.BBox, str, m.Period, m.Season]] = []

    async def point_series(
        self,
        location: m.Location,
        variable_ids: Sequence[str],
        period: m.Period,
        season: m.Season,
    ) -> dict[str, AnnualSeries]:
        self.point_calls.append((location, tuple(variable_ids), period, season))
        if self.error:
            raise self.error
        n = period.end_year - period.start_year + 1
        return {i: list(self.points[i])[-n:] for i in variable_ids if i in self.points}

    async def region_series(
        self, bbox: m.BBox, variable_id: str, period: m.Period, season: m.Season
    ) -> list[GridSeries]:
        self.region_calls.append((bbox, variable_id, period, season))
        if self.error:
            raise self.error
        return list(self.grid)


def sample_point_source(period: m.Period = FULL) -> FakeSeriesSource:
    """A source that serves the saved Niamey samples (POWER units, 1981-2025)."""
    raw = load_point_samples()
    return FakeSeriesSource(points={k: annual_values(v, FULL) for k, v in raw.items()})


def stats_is_implemented() -> bool:
    """False while BE-1's stats module is still a stub."""
    from trend_detective import emergence, stats

    try:
        stats.compute_trend(YEARS[:12], [float(i % 3) for i in range(12)], "x")
        stats.fit_line(YEARS[:12], [float(i % 3) for i in range(12)])
        stats.benjamini_hochberg([0.01, 0.5])
        stats.pearson([1.0, 2.0, 3.0], [1.0, 2.0, 4.0])
        emergence.compute_emergence(YEARS[:12], [float(i % 3) for i in range(12)])
    except NotImplementedError:
        return False
    return True


__all__ = ["UpstreamError"]
