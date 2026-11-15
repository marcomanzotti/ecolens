"""Block D: the same quantity seen by several products, compared over their common period.

All variables of one witness group are cut to the years where every one of them has data
(from the latest first year to the earliest last year). Trend, fit and Pearson correlation
are computed on that window only.

`stats` is used through the module so that tests can substitute its functions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations

from trend_detective import catalog, limitations, stats
from trend_detective.errors import NoDataError
from trend_detective.external_witnesses import ExternalWitnesses
from trend_detective.models import (
    MIN_YEARS_FOR_TREND,
    Location,
    Period,
    Season,
    TrendStats,
    Variable,
    Witness,
    WitnessAgreement,
    WitnessesResult,
)
from trend_detective.series import is_valid, series_points
from trend_detective.wording import lowercase_first

Series = Mapping[str, Sequence[float | None]]
MIN_WITNESSES = 2


def _valid_span(years: Sequence[int], values: Sequence[float | None]) -> tuple[int, int] | None:
    valid = [year for year, value in zip(years, values, strict=True) if is_valid(value)]
    return (valid[0], valid[-1]) if valid else None


def common_span(
    years: Sequence[int], members: Sequence[Variable], series: Series
) -> tuple[int, int]:
    """First and last year shared by all witnesses. NoDataError when it is shorter than ten
    years or when a witness has no data at all."""
    spans = []
    for member in members:
        values = series.get(member.id)
        span = None if values is None else _valid_span(years, values)
        if span is None:
            raise NoDataError(
                f"There is no data for {lowercase_first(member.name)} here, so the witnesses "
                "cannot be compared."
            )
        spans.append(span)
    start, end = max(s[0] for s in spans), min(s[1] for s in spans)
    length = end - start + 1
    if length < MIN_YEARS_FOR_TREND:
        shared = f"only {length} years" if length > 0 else "no years in common"
        raise NoDataError(
            f"The witnesses share {shared} of data here; at least {MIN_YEARS_FOR_TREND} "
            "are needed to compare them."
        )
    return start, end


def _witness(variable: Variable, years: Sequence[int], values: Sequence[float | None]) -> Witness:
    return Witness(
        variable=variable,
        series=series_points(years, values),
        fit=stats.fit_line(years, values),
        trend=stats.compute_trend(years, values, variable.unit),
    )


def _correlation(windows: Sequence[Sequence[float | None]]) -> float | None:
    found = [stats.pearson(a, b) for a, b in combinations(windows, 2)]
    usable = [r for r in found if r is not None]
    if len(usable) < len(found) or not usable:
        return None
    return sum(usable) / len(usable)


def _agreement_text(level: str, direction: str | None) -> str:
    if level == "agree":
        return f"All witnesses point the same way ({direction}) and every trend is significant."
    if level == "partly":
        return (
            f"The witnesses point the same way ({direction}), but not every trend reaches "
            "significance."
        )
    if level == "disagree":
        return "The witnesses point in different directions, so the result is not reliable."
    return "At least one witness has too few valid years, or too little variation, to test."


def _agreement(trends: Sequence[TrendStats | None], correlation: float | None) -> WitnessAgreement:
    tested = [t for t in trends if t is not None]
    if len(tested) < len(trends):
        return WitnessAgreement(
            level="insufficient",
            same_direction=None,
            all_significant=None,
            correlation=correlation,
            text=_agreement_text("insufficient", None),
        )
    directions = {t.direction for t in tested}
    same = len(directions) == 1
    all_significant = all(t.significant for t in tested)
    if not same and not any(t.significant for t in tested):
        # Opposite signs inside the noise are not a contradiction: nobody claims a trend.
        return WitnessAgreement(
            level="partly",
            same_direction=False,
            all_significant=False,
            correlation=correlation,
            text=(
                "No witness finds a significant trend; their small slopes differ in sign, "
                "which is within the noise."
            ),
        )
    level = "disagree" if not same else "agree" if all_significant else "partly"
    return WitnessAgreement(
        level=level,
        same_direction=same,
        all_significant=all_significant,
        correlation=correlation,
        text=_agreement_text(level, next(iter(directions)) if same else None),
    )


def _merged(
    members: Sequence[Variable], series: Series, extra: ExternalWitnesses
) -> tuple[list[Variable], dict[str, Sequence[float | None]]]:
    """POWER members first, then the external witnesses, with every series by variable id."""
    all_members = [*members, *(e.variable for e in extra.series)]
    all_series: dict[str, Sequence[float | None]] = {
        **series,
        **{e.variable.id: e.values for e in extra.series},
    }
    return all_members, all_series


def _need_two(members: Sequence[Variable], extra: ExternalWitnesses) -> None:
    if len(members) >= MIN_WITNESSES:
        return
    reason = " ".join(extra.unavailable) or "No other dataset covers this quantity here."
    raise NoDataError(f"There is no second source to compare with here. {reason}")


def build_witnesses(
    location: Location,
    period: Period,
    season: Season,
    group: str,
    members: Sequence[Variable],
    series: Series,
    extra: ExternalWitnesses | None = None,
) -> WitnessesResult:
    """`series` holds display-unit values, one per year of `period`, by variable id. `extra`
    adds witnesses from outside NASA POWER (their values are aligned the same way)."""
    external = extra or ExternalWitnesses()
    members, series = _merged(members, series, external)
    _need_two(members, external)
    years = catalog.period_years(period)
    start, end = common_span(years, members, series)
    keep = [i for i, year in enumerate(years) if start <= year <= end]
    window_years = [years[i] for i in keep]
    windows = [[series[m.id][i] for i in keep] for m in members]
    witnesses = [_witness(m, window_years, w) for m, w in zip(members, windows, strict=True)]
    common = Period(start_year=start, end_year=end)
    notes = [note for e in external.series for note in e.notes]
    return WitnessesResult(
        location=location,
        quantity=catalog.WITNESS_QUANTITIES.get(group, group.replace("_", " ").capitalize()),
        season=season,
        common_period=common,
        witnesses=witnesses,
        agreement=_agreement([w.trend for w in witnesses], _correlation(windows)),
        limitations=limitations.witness_limitations(members, common, season, notes),
    )
