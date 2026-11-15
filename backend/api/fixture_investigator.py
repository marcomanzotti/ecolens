"""Fallback Investigator that answers every question with the stage-1 fixtures.

Used only when USE_FIXTURES=1 (local front-end work without the engine). It
ignores the request: the answer is always the Niamey example.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from trend_detective.models import (
    BBox,
    CaseResult,
    Catalog,
    LineupResult,
    Location,
    Model,
    Period,
    PlacesResult,
    Season,
    ThemeId,
    TrendMapResult,
    WitnessesResult,
)


def load_fixture[M: Model](directory: Path, name: str, model: type[M]) -> M:
    """Read `<directory>/<name>.json` and parse its `data` into `model`."""
    import json

    path = directory / f"{name}.json"
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Fixture '{name}' cannot be read from {directory}.") from exc
    return model.model_validate(body["data"])


class FixtureInvestigator:
    def __init__(self, directory: Path) -> None:
        self._catalog = load_fixture(directory, "catalog", Catalog)
        self._places = load_fixture(directory, "places", PlacesResult)
        self._case = load_fixture(directory, "case", CaseResult)
        self._lineup = load_fixture(directory, "lineup", LineupResult)
        self._witnesses = load_fixture(directory, "witnesses", WitnessesResult)
        self._trendmap = load_fixture(directory, "trendmap", TrendMapResult)

    def catalog(self) -> Catalog:
        return self._catalog

    def places(self) -> PlacesResult:
        return self._places

    async def case(
        self, location: Location, variable_id: str, period: Period, season: Season
    ) -> CaseResult:
        return self._case

    async def lineup(
        self,
        location: Location,
        period: Period,
        season: Season,
        themes: Sequence[ThemeId] | None = None,
        variable_ids: Sequence[str] | None = None,
    ) -> LineupResult:
        return self._lineup

    async def witnesses(
        self, location: Location, variable_id: str, period: Period, season: Season
    ) -> WitnessesResult:
        return self._witnesses

    async def trendmap(
        self, variable_id: str, bbox: BBox, period: Period, season: Season
    ) -> TrendMapResult:
        return self._trendmap
