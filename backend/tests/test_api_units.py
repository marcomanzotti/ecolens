"""Units of the API layer: settings, cache, limiter, demo store, assistant, lifespan."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from api.assistant import NOT_CONFIGURED_MESSAGE, NOT_ENABLED_MESSAGE, build_assistant
from api.cache import TtlLruCache, request_key
from api.demos import DemoStore
from api.errors import ApiException
from api.fixture_investigator import FixtureInvestigator, load_fixture
from api.main import create_app
from api.ratelimit import SlidingWindowLimiter
from api.settings import DEFAULT_ORIGIN, Settings, load_settings
from tests.api_fakes import FIXTURES, TEST_SETTINGS
from trend_detective import models as m


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


# ----------------------------------------------------------------- settings


def test_settings_defaults() -> None:
    settings = load_settings({})

    assert settings.frontend_origins == (DEFAULT_ORIGIN,)
    assert settings.use_fixtures is False
    assert settings.gemini_key_present is False
    assert (settings.rate_limit_per_minute, settings.rate_limit_heavy_per_minute) == (60, 10)
    assert settings.cache_ttl_seconds == 6 * 60 * 60
    assert settings.demo_dir.name == "demo_data"
    assert settings.forwarded_ip_hop == "last"


def test_settings_read_the_environment() -> None:
    env = {
        "FRONTEND_ORIGIN": "https://a.example/, https://b.example ,",
        "USE_FIXTURES": "1",
        "GEMINI_API_KEY": "not-a-real-key",
        "RATE_LIMIT_PER_MINUTE": "5",
        "CACHE_TTL_SECONDS": "1.5",
        "FORWARDED_IP_HOP": "First",
        "FIXTURES_DIR": "/tmp/fixtures",
        "LOG_LEVEL": "debug",
    }

    settings = load_settings(env)

    assert settings.frontend_origins == ("https://a.example", "https://b.example")
    assert settings.use_fixtures is True
    assert settings.gemini_key_present is True
    assert settings.rate_limit_per_minute == 5
    assert settings.cache_ttl_seconds == 1.5
    assert settings.forwarded_ip_hop == "first"
    assert settings.fixtures_dir == Path("/tmp/fixtures")
    assert settings.log_level == "DEBUG"
    assert "not-a-real-key" not in repr(settings)


@pytest.mark.parametrize("value", ["many", "-1"])
def test_settings_reject_bad_numbers(value: str) -> None:
    with pytest.raises(ValueError, match="RATE_LIMIT_PER_MINUTE"):
        load_settings({"RATE_LIMIT_PER_MINUTE": value})


def test_unknown_forwarded_hop_falls_back_to_the_safe_default() -> None:
    assert load_settings({"FORWARDED_IP_HOP": "middle"}).forwarded_ip_hop == "last"


def test_blank_origin_falls_back_to_the_default() -> None:
    assert load_settings({"FRONTEND_ORIGIN": " , "}).frontend_origins == (DEFAULT_ORIGIN,)


# -------------------------------------------------------------------- cache


def test_cache_expires_entries_after_the_ttl() -> None:
    clock = Clock()
    cache = TtlLruCache(max_entries=4, ttl=10, clock=clock)
    cache.put("k", "v")

    clock.now += 9
    assert cache.get("k") == "v"
    clock.now += 2
    assert cache.get("k") is None
    assert len(cache) == 0


def test_cache_evicts_the_least_recently_used_entry() -> None:
    cache = TtlLruCache(max_entries=2, ttl=10, clock=Clock())
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")

    cache.put("c", 3)

    assert (cache.get("a"), cache.get("b"), cache.get("c")) == (1, None, 3)


@pytest.mark.parametrize(("max_entries", "ttl"), [(0, 10), (4, 0)])
def test_cache_can_be_disabled(max_entries: int, ttl: float) -> None:
    cache = TtlLruCache(max_entries=max_entries, ttl=ttl, clock=Clock())

    cache.put("k", "v")

    assert cache.get("k") is None


def test_request_key_rounds_nested_coordinates_only() -> None:
    class Body(BaseModel):
        location: m.Location
        bbox: m.BBox
        variable_id: str

    def body(lat: float, lat_min: float) -> Body:
        return Body(
            location=m.Location(lat=lat, lon=2.11),
            bbox=m.BBox(lat_min=lat_min, lat_max=20, lon_min=-5, lon_max=5),
            variable_id="T2M",
        )

    assert request_key("r", body(13.511, 10.001)) == request_key("r", body(13.514, 10.004))
    assert request_key("r", body(13.51, 10)) != request_key("r", body(13.52, 10))
    assert request_key("r", body(13.51, 10)) != request_key("other", body(13.51, 10))


# ------------------------------------------------------------------ limiter


def test_limiter_blocks_then_frees_as_the_window_slides() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(limit=2, window=60, clock=clock)
    limiter.record("ip")
    clock.now += 20
    limiter.record("ip")

    assert limiter.retry_after("ip") == 40
    assert limiter.retry_after("other") is None
    clock.now += 41
    assert limiter.retry_after("ip") is None
    clock.now += 60
    assert limiter.retry_after("ip") is None
    assert limiter.tracked_clients() == 0


def test_limiter_with_zero_limit_is_disabled() -> None:
    limiter = SlidingWindowLimiter(limit=0)

    limiter.record("ip")

    assert limiter.retry_after("ip") is None
    assert limiter.tracked_clients() == 0


def test_limiter_bounds_the_number_of_tracked_clients() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(limit=5, window=60, clock=clock, max_clients=3)
    for name in ("a", "b", "c"):
        limiter.record(name)

    limiter.record("d")  # all still active: the oldest is dropped
    assert limiter.tracked_clients() == 3
    clock.now += 61
    limiter.record("e")  # all stale: they are all dropped
    assert limiter.tracked_clients() == 1


# --------------------------------------------------------------- demo store


def demo_json(demo_id: str) -> str:
    data = json.loads((FIXTURES / "demo.json").read_text(encoding="utf-8"))["data"]
    return json.dumps({**data, "id": demo_id})


def test_demo_store_skips_invalid_files(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "good-one.json").write_text(demo_json("good-one"), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "wrong-shape.json").write_text('{"id": "wrong-shape"}', encoding="utf-8")
    (tmp_path / "other-id.json").write_text(demo_json("something-else"), encoding="utf-8")
    (tmp_path / "Bad_Name.json").write_text(demo_json("Bad_Name"), encoding="utf-8")

    with caplog.at_level("WARNING", logger="api.demos"):
        store = DemoStore.from_directory(tmp_path)

    assert [d.id for d in store.list().demos] == ["good-one"]
    assert store.get("good-one") is not None
    assert store.get("broken") is None
    assert store.get("../good-one") is None
    assert len([r for r in caplog.records if "skipped" in r.message]) == 4


def test_demo_store_of_a_missing_directory_is_empty(tmp_path: Path) -> None:
    store = DemoStore.from_directory(tmp_path / "nope")

    assert store.list().demos == []


def test_demo_summary_falls_back_to_coordinates(tmp_path: Path) -> None:
    data = json.loads(demo_json("no-label"))
    data["case"]["location"]["label"] = None
    (tmp_path / "no-label.json").write_text(json.dumps(data), encoding="utf-8")

    summary = DemoStore.from_directory(tmp_path).list().demos[0]

    assert summary.place_name == "13.51, 2.11"


# ---------------------------------------------------------------- assistant


@pytest.mark.parametrize(
    ("key_present", "message"), [(False, NOT_CONFIGURED_MESSAGE), (True, NOT_ENABLED_MESSAGE)]
)
async def test_built_assistant_is_unavailable(key_present: bool, message: str) -> None:
    assistant = build_assistant(Settings(gemini_key_present=key_present))

    assert assistant.available is False
    with pytest.raises(ApiException) as raised:
        await assistant.ask("Is the Sahel getting wetter?")
    assert (raised.value.code, raised.value.message) == ("assistant_unavailable", message)


# ----------------------------------------------- investigators and lifespan


async def test_fixture_investigator_answers_every_use_case() -> None:
    investigator = FixtureInvestigator(FIXTURES)
    place, period = m.Location(lat=0, lon=0), m.Period()
    bbox = m.BBox(lat_min=10, lat_max=20, lon_min=-5, lon_max=5)

    assert investigator.catalog().variables
    assert investigator.places().places
    assert isinstance(await investigator.case(place, "T2M", period, "annual"), m.CaseResult)
    assert isinstance(await investigator.lineup(place, period, "annual"), m.LineupResult)
    assert isinstance(
        await investigator.witnesses(place, "TQV", period, "annual"), m.WitnessesResult
    )
    assert isinstance(await investigator.trendmap("T2M", bbox, period, "annual"), m.TrendMapResult)


def test_missing_fixture_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="catalog"):
        load_fixture(tmp_path, "catalog", m.Catalog)


def test_lifespan_with_use_fixtures_serves_the_fixtures() -> None:
    with TestClient(create_app(TEST_SETTINGS)) as client:
        response = client.post("/case", json={"location": {"lat": 1, "lon": 2}, "variable_id": "X"})

    assert response.status_code == 200
    m.CaseResult.model_validate(response.json()["data"])


def test_lifespan_fails_fast_when_the_engine_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "trend_detective.service", None)

    with pytest.raises(RuntimeError, match="USE_FIXTURES=1"), TestClient(create_app(Settings())):
        pass


def test_lifespan_builds_the_real_investigator_on_one_shared_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: dict[str, object] = {}

    class StubSource:
        def __init__(self, client: object) -> None:
            built["client"] = client

    class StubInvestigator(FixtureInvestigator):
        def __init__(self, source: StubSource) -> None:
            super().__init__(FIXTURES)
            built["source"] = source

    service = types.ModuleType("trend_detective.service")
    service.TrendInvestigator = StubInvestigator  # type: ignore[attr-defined]
    power = types.ModuleType("trend_detective.sources.power")
    power.PowerSource = StubSource  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "trend_detective.service", service)
    monkeypatch.setitem(sys.modules, "trend_detective.sources.power", power)

    with TestClient(create_app(Settings())) as client:
        assert client.get("/catalog").status_code == 200
        assert built["client"].is_closed is False  # type: ignore[attr-defined]

    assert isinstance(built["source"], StubSource)
    assert built["client"].is_closed is True  # type: ignore[attr-defined]


def test_startup_logs_the_allowed_origins(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(
        use_fixtures=True, fixtures_dir=FIXTURES, frontend_origins=("https://a.example",)
    )

    with caplog.at_level("INFO", logger="api"), TestClient(create_app(settings)):
        pass

    assert "CORS allows: https://a.example" in caplog.text
    assert not [r for r in caplog.records if r.levelname == "WARNING" and "CORS" in r.message]


def test_startup_warns_when_cors_is_open_to_every_origin(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(use_fixtures=True, fixtures_dir=FIXTURES, frontend_origins=("*",))

    with caplog.at_level("INFO", logger="api"), TestClient(create_app(settings)):
        pass

    assert [r for r in caplog.records if r.levelname == "WARNING" and "every origin" in r.message]
