"""Fakes and app builders shared by the API tests (no engine, no network)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from api.deps import get_assistant, get_investigator
from api.fixture_investigator import load_fixture
from api.main import create_app
from api.settings import Settings
from trend_detective import models as m
from trend_detective.ports import Investigator

FIXTURES = Path(__file__).resolve().parents[2] / "frontend" / "fixtures"

PLACE = {"lat": 13.51, "lon": 2.11, "label": "Niamey, Niger"}
BBOX = {"lat_min": 10, "lat_max": 20, "lon_min": -5, "lon_max": 5}
CASE_BODY = {"location": PLACE, "variable_id": "PRECTOTCORR"}
LINEUP_BODY = {"location": PLACE}
WITNESSES_BODY = {"location": PLACE, "variable_id": "TQV"}
TRENDMAP_BODY = {"variable_id": "PRECTOTCORR", "bbox": BBOX}

# The fake investigator is injected, so the app never builds a real one.
TEST_SETTINGS = Settings(use_fixtures=True, fixtures_dir=FIXTURES)


class FakeInvestigator:
    """Answers with the fixtures, records every call, and can be told to fail or to hang."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.error: Exception | None = None
        self.before_answer: Callable[[], Any] | None = None

    def catalog(self) -> m.Catalog:
        return load_fixture(FIXTURES, "catalog", m.Catalog)

    def places(self) -> m.PlacesResult:
        return load_fixture(FIXTURES, "places", m.PlacesResult)

    async def _answer[M: m.Model](self, name: str, model: type[M], *args: Any) -> M:
        self.calls.append((name, args))
        if self.before_answer is not None:
            await self.before_answer()
        if self.error is not None:
            raise self.error
        return load_fixture(FIXTURES, name, model)

    async def case(
        self, location: m.Location, variable_id: str, period: m.Period, season: m.Season
    ) -> m.CaseResult:
        return await self._answer("case", m.CaseResult, location, variable_id, period, season)

    async def lineup(
        self,
        location: m.Location,
        period: m.Period,
        season: m.Season,
        themes: Sequence[m.ThemeId] | None = None,
        variable_ids: Sequence[str] | None = None,
    ) -> m.LineupResult:
        return await self._answer(
            "lineup", m.LineupResult, location, period, season, themes, variable_ids
        )

    async def witnesses(
        self, location: m.Location, variable_id: str, period: m.Period, season: m.Season
    ) -> m.WitnessesResult:
        return await self._answer(
            "witnesses", m.WitnessesResult, location, variable_id, period, season
        )

    async def trendmap(
        self, variable_id: str, bbox: m.BBox, period: m.Period, season: m.Season
    ) -> m.TrendMapResult:
        return await self._answer("trendmap", m.TrendMapResult, variable_id, bbox, period, season)


class FakeAssistant:
    """Stands in for the stage-5 assistant: answers with the `ask` fixture."""

    available = True

    def __init__(self) -> None:
        self.questions: list[str] = []

    async def ask(self, question: str) -> m.AskResult:
        self.questions.append(question)
        return load_fixture(FIXTURES, "ask", m.AskResult)


def make_app(
    investigator: Investigator | None = None,
    assistant: FakeAssistant | None = None,
    **overrides: Any,
) -> FastAPI:
    """An app with `investigator` (a fake by default) injected; `overrides` change the settings."""
    app = create_app(replace(TEST_SETTINGS, **overrides))
    fake = investigator or FakeInvestigator()
    app.dependency_overrides[get_investigator] = lambda: fake
    if assistant is not None:
        app.dependency_overrides[get_assistant] = lambda: assistant
    return app
