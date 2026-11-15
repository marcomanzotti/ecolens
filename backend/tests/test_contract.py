"""Contract tests: fixtures, models and routes must agree with docs/API_CONTRACT.md."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.schemas import ERROR_STATUS, ErrorEnvelope
from tests.api_fakes import FakeAssistant, make_app
from trend_detective import models as m

FIXTURES = Path(__file__).resolve().parents[2] / "frontend" / "fixtures"

FIXTURE_MODELS = {
    "health": m.Health,
    "catalog": m.Catalog,
    "places": m.PlacesResult,
    "case": m.CaseResult,
    "lineup": m.LineupResult,
    "witnesses": m.WitnessesResult,
    "trendmap": m.TrendMapResult,
    "ask": m.AskResult,
    "demo_list": m.DemoList,
    "demo": m.DemoCase,
}

PLACE = {"lat": 13.51, "lon": 2.11, "label": "Niamey, Niger"}
BBOX = {"lat_min": 10, "lat_max": 20, "lon_min": -5, "lon_max": 5}

ROUTES = [
    ("GET", "/health", None, m.Health),
    ("GET", "/catalog", None, m.Catalog),
    ("GET", "/places", None, m.PlacesResult),
    ("POST", "/case", {"location": PLACE, "variable_id": "PRECTOTCORR"}, m.CaseResult),
    ("POST", "/lineup", {"location": PLACE}, m.LineupResult),
    ("POST", "/witnesses", {"location": PLACE, "variable_id": "TQV"}, m.WitnessesResult),
    ("POST", "/trendmap", {"variable_id": "PRECTOTCORR", "bbox": BBOX}, m.TrendMapResult),
    ("POST", "/ask", {"question": "Is the Sahel getting wetter?"}, m.AskResult),
    ("GET", "/demo", None, m.DemoList),
    ("GET", "/demo/sahel-rain", None, m.DemoCase),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    # The engine and the assistant are injected as fakes that answer with the fixtures;
    # the rate limit is off because the whole module shares one client address.
    app = make_app(
        assistant=FakeAssistant(), rate_limit_per_minute=0, rate_limit_heavy_per_minute=0
    )
    return TestClient(app)


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(FIXTURE_MODELS))
def test_fixture_matches_its_model(name: str) -> None:
    body = load(name)

    assert body["success"] is True
    assert body["error"] is None
    FIXTURE_MODELS[name].model_validate(body["data"])


def test_error_fixture_matches_the_error_envelope() -> None:
    ErrorEnvelope.model_validate(load("error"))


@pytest.mark.parametrize(("method", "path", "payload", "model"), ROUTES)
def test_route_answers_with_a_valid_envelope(
    client: TestClient, method: str, path: str, payload: dict | None, model: type[m.Model]
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"success", "data", "error"}
    assert body["success"] is True
    model.model_validate(body["data"])


def test_unknown_demo_returns_not_found_envelope(client: TestClient) -> None:
    response = client.get("/demo/does-not-exist")

    assert response.status_code == ERROR_STATUS["not_found"]
    assert ErrorEnvelope.model_validate(response.json()).error.code == "not_found"


def test_unknown_path_returns_not_found_envelope(client: TestClient) -> None:
    response = client.get("/nope")

    assert response.status_code == 404
    assert ErrorEnvelope.model_validate(response.json()).error.code == "not_found"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/case", {"location": {"lat": 123, "lon": 0}, "variable_id": "T2M"}),
        ("/case", {"location": PLACE, "variable_id": "T2M", "unknown": 1}),
        ("/case", {"location": PLACE, "variable_id": "T2M", "season": "summer"}),
        (
            "/case",
            {
                "location": PLACE,
                "variable_id": "T2M",
                "period": {"start_year": 2020, "end_year": 2025},
            },
        ),
        (
            "/trendmap",
            {
                "variable_id": "T2M",
                "bbox": {"lat_min": 0, "lat_max": 30, "lon_min": 0, "lon_max": 5},
            },
        ),
        ("/ask", {"question": "x" * 501}),
    ],
)
def test_invalid_request_returns_validation_envelope(
    client: TestClient, path: str, payload: dict
) -> None:
    response = client.post(path, json=payload)

    assert response.status_code == ERROR_STATUS["validation_error"]
    error = ErrorEnvelope.model_validate(response.json()).error
    assert error.code == "validation_error"
    assert error.details


def test_period_must_span_at_least_ten_years() -> None:
    with pytest.raises(ValidationError):
        m.Period(start_year=2020, end_year=2025)


def test_models_are_immutable() -> None:
    period = m.Period()

    with pytest.raises(ValidationError):
        period.start_year = 1990  # type: ignore[misc]


def test_lineup_fixture_is_ranked_by_strength() -> None:
    items = [i for i in load("lineup")["data"]["items"] if i["status"] == "ok"]

    strengths = [abs(i["standardized_slope"]) for i in items]
    assert [i["rank"] for i in items] == list(range(1, len(items) + 1))
    assert strengths == sorted(strengths, reverse=True)
