"""The use cases behind the API routes: TrendInvestigator implements ports.Investigator.

It fetches yearly series from a SeriesSource, converts them to the catalog's display units
(before any statistic) and hands them to the engine (stats, emergence) and to the builders of
each block (verdict, lineup, witnesses, trendmap).

Errors: UnknownVariableError for ids outside the catalog (or without a witness group when one
is needed), NoDataError when the source has nothing usable, and everything the source raises
(UpstreamError, UpstreamTimeoutError) passes through unchanged.

`stats` and `emergence` are used through their modules so that tests can substitute them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from trend_detective import catalog, emergence, limitations, places, stats
from trend_detective.errors import NoDataError, UnknownVariableError, UpstreamError
from trend_detective.lineup import build_lineup
from trend_detective.models import (
    BBox,
    CaseResult,
    Catalog,
    LineupResult,
    Location,
    Period,
    PlacesResult,
    Season,
    ThemeId,
    TrendMapResult,
    Variable,
    WitnessesResult,
)
from trend_detective.ports import AnnualSeries, GridSeries, SeriesSource
from trend_detective.series import series_points, valid_count
from trend_detective.trendmap import build_trendmap
from trend_detective.verdict import build_verdict
from trend_detective.witnesses import build_witnesses

MSG_UNREADABLE = "NASA POWER sent an answer that could not be read."


def _checked(values: Sequence[float | None], n_years: int) -> AnnualSeries:
    if len(values) != n_years:
        raise UpstreamError(MSG_UNREADABLE)
    return list(values)


def _no_data(variable: Variable, where: str) -> NoDataError:
    return NoDataError(f"NASA POWER has no usable data for {variable.name.lower()} {where}.")


class TrendInvestigator:
    def __init__(self, source: SeriesSource) -> None:
        self._source = source
        self._catalog = catalog.build_catalog()
        self._places = places.build_places()

    # -- reference data ------------------------------------------------------

    def catalog(self) -> Catalog:
        return self._catalog

    def places(self) -> PlacesResult:
        return self._places

    # -- helpers -------------------------------------------------------------

    async def _point_series(
        self, location: Location, variables: Sequence[Variable], period: Period, season: Season
    ) -> dict[str, AnnualSeries]:
        """Series in display units, one value per year of the period, by variable id.
        Variables the source did not return are absent."""
        n_years = len(catalog.period_years(period))
        raw = await self._source.point_series(location, [v.id for v in variables], period, season)
        return {
            v.id: catalog.to_display_units(v.id, _checked(raw[v.id], n_years))
            for v in variables
            if v.id in raw
        }

    # -- case ----------------------------------------------------------------

    async def case(
        self, location: Location, variable_id: str, period: Period, season: Season
    ) -> CaseResult:
        variable = catalog.get_variable(variable_id)
        found = await self._point_series(location, [variable], period, season)
        values = found.get(variable.id, [])
        n_valid = valid_count(values)
        if n_valid == 0:
            raise _no_data(variable, "at this place and period")
        years = catalog.period_years(period)
        trend = stats.compute_trend(years, values, variable.unit)
        return CaseResult(
            location=location,
            variable=variable,
            period=period,
            season=season,
            series=series_points(years, values),
            fit=stats.fit_line(years, values),
            trend=trend,
            emergence=emergence.compute_emergence(years, values),
            verdict=build_verdict(variable, location, period, season, trend, n_valid=n_valid),
            limitations=limitations.case_limitations(variable, period, season),
        )

    # -- line-up -------------------------------------------------------------

    async def lineup(
        self,
        location: Location,
        period: Period,
        season: Season,
        themes: Sequence[ThemeId] | None = None,
        variable_ids: Sequence[str] | None = None,
    ) -> LineupResult:
        variables = catalog.select_variables(themes, variable_ids)
        found = await self._point_series(location, variables, period, season)
        result = build_lineup(location, period, season, variables, found)
        if result.correction.n_tests == 0:
            raise NoDataError("NASA POWER has no usable data for these variables at this place.")
        return result

    # -- witnesses -----------------------------------------------------------

    async def witnesses(
        self, location: Location, variable_id: str, period: Period, season: Season
    ) -> WitnessesResult:
        variable = catalog.get_variable(variable_id)
        if variable.witness_group is None:
            raise UnknownVariableError(
                f"'{variable_id}' has no witness group: no second product measures the same thing."
            )
        members = catalog.witness_group_members(variable.witness_group)
        found = await self._point_series(location, members, period, season)
        return build_witnesses(location, period, season, variable.witness_group, members, found)

    # -- trend map -----------------------------------------------------------

    async def trendmap(
        self, variable_id: str, bbox: BBox, period: Period, season: Season
    ) -> TrendMapResult:
        variable = catalog.get_variable(variable_id)
        n_years = len(catalog.period_years(period))
        raw = await self._source.region_series(bbox, variable.id, period, season)
        grid = _display_grid(variable, raw, n_years)
        return build_trendmap(variable, bbox, period, season, grid)


def _display_grid(variable: Variable, grid: Sequence[GridSeries], n_years: int) -> list[GridSeries]:
    return [
        replace(
            point,
            values=tuple(catalog.to_display_units(variable.id, _checked(point.values, n_years))),
        )
        for point in grid
    ]


__all__ = ["TrendInvestigator"]
