"""Internal interfaces between the back-end workstreams.

    BE-1 (engine)        implements SeriesSource (sources/power.py), stats.py, emergence.py
    BE-2 (investigation) implements Investigator (service.py) on top of BE-1
    BE-3 (API)           calls an Investigator and maps errors.py to the HTTP envelope

Each stream codes and tests against these signatures, using fakes for the other
side. Changing this file is a contract change: stop and report instead.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

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
    WitnessesResult,
)

# One value per year of the requested period, in order; None where missing.
AnnualSeries = list[float | None]


@dataclass(frozen=True)
class GridSeries:
    """The series of one grid point of a regional request."""

    lat: float
    lon: float
    values: tuple[float | None, ...]


class SeriesSource(Protocol):
    """Fetches yearly series. Values are in the source's own units (no conversion).

    Raises errors.UpstreamError / errors.UpstreamTimeoutError when the source fails.
    A variable the source does not return is simply absent from the result.
    """

    async def point_series(
        self,
        location: Location,
        variable_ids: Sequence[str],
        period: Period,
        season: Season,
    ) -> dict[str, AnnualSeries]: ...

    async def region_series(
        self,
        bbox: BBox,
        variable_id: str,
        period: Period,
        season: Season,
    ) -> list[GridSeries]: ...


class Investigator(Protocol):
    """The use cases behind the API routes. Implemented by service.TrendInvestigator.

    Raises errors.UnknownVariableError, errors.NoDataError, and lets the
    SeriesSource errors pass through.
    """

    def catalog(self) -> Catalog: ...

    def places(self) -> PlacesResult: ...

    async def case(
        self, location: Location, variable_id: str, period: Period, season: Season
    ) -> CaseResult: ...

    async def lineup(
        self,
        location: Location,
        period: Period,
        season: Season,
        themes: Sequence[ThemeId] | None = None,
        variable_ids: Sequence[str] | None = None,
    ) -> LineupResult: ...

    async def witnesses(
        self, location: Location, variable_id: str, period: Period, season: Season
    ) -> WitnessesResult: ...

    async def trendmap(
        self, variable_id: str, bbox: BBox, period: Period, season: Season
    ) -> TrendMapResult: ...
