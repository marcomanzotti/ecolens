"""Build the saved demo cases and the front-end fixtures with the real engine.

Run from the repo root:  backend/.venv/bin/python scripts/build_demos.py

Every number comes from `TrendInvestigator` on live NASA POWER data, the same code path as
the API. Titles, blurbs and narrative are written by hand below; they ask questions and
never state a cause. A demo whose verdict does not match the direction its title expects
is refused, so a story can never contradict its own evidence.

Outputs:
  backend/api/demo_data/<id>.json   one DemoCase per demo, served by GET /demo/{id}
  frontend/fixtures/*.json          envelopes for `npm run dev:fixtures` and the contract tests
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from api.schemas import Envelope  # noqa: E402
from trend_detective import models as m  # noqa: E402

DEMO_DIR = ROOT / "backend" / "api" / "demo_data"
FIXTURES = ROOT / "frontend" / "fixtures"
MAP_HALF_SIDE = 5
HTTP_TIMEOUT_SECONDS = 120.0
FIXTURE_DEMO_ID = "sahel-rain"
FIXTURE_WITNESS_VARIABLE = "TQV"
APP_VERSION = "0.1.0"


@dataclass(frozen=True)
class DemoSpec:
    id: str
    title: str
    blurb: str
    place: m.Location
    variable_id: str
    expected_direction: m.Direction
    narrative: tuple[str, ...]
    season: m.Season = "annual"


DEMOS: tuple[DemoSpec, ...] = (
    DemoSpec(
        id="sahel-rain",
        title="The rain that came back",
        blurb="After the droughts of the 1980s, is the Sahel really getting wetter?",
        place=m.Location(lat=13.51, lon=2.11, label="Niamey, Niger"),
        variable_id="PRECTOTCORR",
        expected_direction="up",
        narrative=(
            "Open the case: rainfall around Niamey, Niger, since 1981.",
            "Check the evidence: the yearly series, its trend line and both tests.",
            "Call the line-up: which other variables changed at the same place?",
            "Look at the map: does the whole region agree, or does it flip nearby?",
        ),
    ),
    DemoSpec(
        id="delhi-sunlight",
        title="Less sun over Delhi",
        blurb="Is less sunlight reaching the ground in one of the world's busiest cities?",
        place=m.Location(lat=28.61, lon=77.21, label="Delhi, India"),
        variable_id="ALLSKY_SFC_SW_DWN",
        expected_direction="down",
        narrative=(
            "Open the case: sunlight reaching the ground around Delhi, India, since 1981.",
            "Check the evidence: is the drop larger than year-to-year noise?",
            "Call the line-up: haze, clouds and water vapour are questioned too.",
            "Look at the map: is the dimming local or regional?",
        ),
    ),
    DemoSpec(
        id="pantanal-rain",
        title="The wetland's missing rain",
        blurb="The Pantanal lives on its floods. Is rainfall over it falling?",
        place=m.Location(lat=-19.01, lon=-57.65, label="Pantanal, Brazil"),
        variable_id="PRECTOTCORR",
        expected_direction="down",
        narrative=(
            "Open the case: rainfall over the Pantanal, Brazil, since 1981.",
            "Check the evidence: the yearly series, its trend line and both tests.",
            "Call the line-up: did evaporation, clouds and sunlight change with it?",
            "Look at the map: where around the wetland does the trend hold?",
        ),
    ),
    DemoSpec(
        id="venice-heat",
        title="A warmer lagoon",
        blurb="How much warmer is the air over the Venice Lagoon than in 1981?",
        place=m.Location(lat=45.44, lon=12.33, label="Venice Lagoon, Italy"),
        variable_id="T2M",
        expected_direction="up",
        narrative=(
            "Open the case: air temperature over the Venice Lagoon, Italy, since 1981.",
            "Check the evidence: when did the warming become impossible to dismiss?",
            "Call the line-up: what else changed in the same air?",
            "Look at the map: is the Adriatic coast alone, or the whole region?",
        ),
    ),
)


def map_box(place: m.Location) -> m.BBox:
    """The same 10° × 10° box the case page asks for (see frontend/lib/case-query.ts)."""
    lat = min(max(round(place.lat), -90 + MAP_HALF_SIDE), 90 - MAP_HALF_SIDE)
    lon = min(max(round(place.lon), -180 + MAP_HALF_SIDE), 180 - MAP_HALF_SIDE)
    return m.BBox(
        lat_min=lat - MAP_HALF_SIDE,
        lat_max=lat + MAP_HALF_SIDE,
        lon_min=lon - MAP_HALF_SIDE,
        lon_max=lon + MAP_HALF_SIDE,
    )


async def build_demo(investigator, spec: DemoSpec) -> m.DemoCase:  # noqa: ANN001
    period = m.Period()
    case = await investigator.case(spec.place, spec.variable_id, period, spec.season)
    if case.trend is None or case.trend.direction != spec.expected_direction:
        found = None if case.trend is None else case.trend.direction
        raise SystemExit(f"{spec.id}: expected '{spec.expected_direction}', engine says '{found}'")
    lineup = await investigator.lineup(spec.place, period, spec.season)
    witnesses = None
    if case.variable.witness_group is not None:
        witnesses = await investigator.witnesses(spec.place, spec.variable_id, period, spec.season)
    trendmap = await investigator.trendmap(
        spec.variable_id, map_box(spec.place), period, spec.season
    )
    return m.DemoCase(
        id=spec.id,
        title=spec.title,
        blurb=spec.blurb,
        narrative=list(spec.narrative),
        case=case,
        lineup=lineup,
        witnesses=witnesses,
        trendmap=trendmap,
    )


def dump(model: m.Model) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=1) + "\n"


def write_fixture(name: str, data: m.Model) -> None:
    envelope = Envelope[type(data)](success=True, data=data, error=None)
    (FIXTURES / f"{name}.json").write_text(dump(envelope), encoding="utf-8")
    sys.stdout.write(f"fixture {name}.json\n")


def summary(demo: m.DemoCase) -> m.DemoSummary:
    return m.DemoSummary(
        id=demo.id,
        title=demo.title,
        blurb=demo.blurb,
        place_name=demo.case.location.label or "",
        variable_id=demo.case.variable.id,
    )


async def write_fixtures(investigator, demos: list[m.DemoCase]) -> None:  # noqa: ANN001
    main = next(d for d in demos if d.id == FIXTURE_DEMO_ID)
    place = main.case.location
    witnesses = await investigator.witnesses(
        place, FIXTURE_WITNESS_VARIABLE, m.Period(), "annual"
    )
    write_fixture("catalog", investigator.catalog())
    write_fixture("places", investigator.places())
    write_fixture("case", main.case)
    if main.lineup is not None:
        write_fixture("lineup", main.lineup)
    write_fixture("witnesses", witnesses)
    if main.trendmap is not None:
        write_fixture("trendmap", main.trendmap)
    write_fixture("demo", main)
    write_fixture("demo_list", m.DemoList(demos=[summary(d) for d in demos]))
    write_fixture("health", m.Health(version=APP_VERSION, assistant_available=False))
    # ask.json and error.json are not engine output (assistant and error envelope): kept as is.


async def main() -> None:
    import httpx

    from trend_detective.service import TrendInvestigator
    from trend_detective.sources.power import PowerSource

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        investigator = TrendInvestigator(PowerSource(client))
        demos = []
        for spec in DEMOS:
            demo = await build_demo(investigator, spec)
            (DEMO_DIR / f"{spec.id}.json").write_text(dump(demo), encoding="utf-8")
            sys.stdout.write(f"demo {spec.id}: {demo.case.verdict.headline}\n")
            demos.append(demo)
        await write_fixtures(investigator, demos)


if __name__ == "__main__":
    asyncio.run(main())
