"""Block A: every variable tested at one place, ranked by the size of its trend.

Each variable gets a Mann-Kendall p-value; the p-values are corrected together with
Benjamini-Hochberg and `significant` means `p_adjusted < alpha`. Items are ranked by
|Sen's slope / standard deviation| so that variables in different units can be compared.
Variables with no testable data (missing, too few valid years, constant) come last.

`stats` is used through the module so that tests can substitute its functions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from trend_detective import catalog, stats
from trend_detective.models import (
    ALPHA,
    Correction,
    LineupItem,
    LineupResult,
    Location,
    Period,
    Season,
    TrendStats,
    Variable,
)
from trend_detective.series import valid_count
from trend_detective.wording import plural

Series = Mapping[str, Sequence[float | None]]


@dataclass(frozen=True)
class _Tested:
    variable: Variable
    values: tuple[float | None, ...]
    trend: TrendStats

    @property
    def standardized_slope(self) -> float:
        return self.trend.sen.slope_per_decade / self.trend.std


def _testable(
    variable: Variable, values: tuple[float | None, ...], trend: TrendStats | None
) -> _Tested | None:
    if trend is None or trend.std <= 0:
        return None
    return _Tested(variable, values, trend)


def _item(tested: _Tested, rank: int, p_adjusted: float) -> LineupItem:
    trend = tested.trend
    return LineupItem(
        rank=rank,
        variable=tested.variable,
        status="ok",
        n=trend.n,
        direction=trend.direction,
        slope_per_decade=trend.sen.slope_per_decade,
        standardized_slope=tested.standardized_slope,
        tau=trend.mann_kendall.tau,
        p_value=trend.mann_kendall.p_value,
        p_adjusted=p_adjusted,
        significant=p_adjusted < ALPHA,
        sparkline=list(tested.values),
    )


def _no_data_item(variable: Variable, values: tuple[float | None, ...]) -> LineupItem:
    return LineupItem(
        rank=None,
        variable=variable,
        status="no_data",
        n=valid_count(values),
        direction=None,
        slope_per_decade=None,
        standardized_slope=None,
        tau=None,
        p_value=None,
        p_adjusted=None,
        significant=False,
        sparkline=list(values),
    )


def _summary(n_significant: int, n_tested: int, n_untested: int) -> str:
    if n_tested == 0:
        return "No variable had enough data to test for a trend."
    verb = "shows" if n_significant == 1 else "show"
    text = (
        f"{n_significant} of {n_tested} tested variables {verb} a significant trend "
        "after correcting for the number of tests."
    )
    if n_untested:
        text += f" {plural(n_untested, 'variable')} had too little data to test."
    return text


def build_lineup(
    location: Location,
    period: Period,
    season: Season,
    variables: Sequence[Variable],
    series: Series,
) -> LineupResult:
    """`series` holds display-unit values, one per year of `period`, by variable id.
    A variable missing from `series` has no data."""
    years = catalog.period_years(period)
    blank: tuple[float | None, ...] = (None,) * len(years)
    values_of = {v.id: tuple(series.get(v.id, blank)) for v in variables}
    trends = {v.id: stats.compute_trend(years, values_of[v.id], v.unit) for v in variables}
    candidates = [_testable(v, values_of[v.id], trends[v.id]) for v in variables]
    tested = sorted(
        (c for c in candidates if c is not None),
        key=lambda c: -abs(c.standardized_slope),
    )
    adjusted = stats.benjamini_hochberg([t.trend.mann_kendall.p_value for t in tested])
    ok_items = [
        _item(t, rank, p) for rank, (t, p) in enumerate(zip(tested, adjusted, strict=True), start=1)
    ]
    untested = [
        _no_data_item(v, values_of[v.id])
        for v, c in zip(variables, candidates, strict=True)
        if c is None
    ]
    n_significant = sum(1 for i in ok_items if i.significant)
    return LineupResult(
        location=location,
        period=period,
        season=season,
        correction=Correction(n_tests=len(tested)),
        items=[*ok_items, *untested],
        n_significant=n_significant,
        summary=_summary(n_significant, len(tested), len(untested)),
    )
