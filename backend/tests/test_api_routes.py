"""Routes: dependency injection, error mapping, demo, assistant, cache and timeout."""

from __future__ import annotations

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient

from api.schemas import ERROR_STATUS, ErrorEnvelope
from tests.api_fakes import (
    BBOX,
    CASE_BODY,
    LINEUP_BODY,
    PLACE,
    TRENDMAP_BODY,
    WITNESSES_BODY,
    FakeAssistant,
    FakeInvestigator,
    make_app,
)
from trend_detective import errors as engine_errors
from trend_detective import models as m


@pytest.fixture
def investigator() -> FakeInvestigator:
    return FakeInvestigator()


@pytest.fixture
def client(investigator: FakeInvestigator) -> TestClient:
    return TestClient(make_app(investigator))


def error_of(response) -> m.Model:  # type: ignore[no-untyped-def]
    return ErrorEnvelope.model_validate(response.json()).error


# ---------------------------------------------------------------- injection


def test_case_passes_the_validated_request_to_the_investigator(
    client: TestClient, investigator: FakeInvestigator
) -> None:
    body = {**CASE_BODY, "period": {"start_year": 1990, "end_year": 2020}, "season": "JJA"}

    response = client.post("/case", json=body)

    assert response.status_code == 200
    assert investigator.calls == [
        (
            "case",
            (m.Location(**PLACE), "PRECTOTCORR", m.Period(start_year=1990, end_year=2020), "JJA"),
        )
    ]


def test_lineup_passes_themes_and_variable_ids(
    client: TestClient, investigator: FakeInvestigator
) -> None:
    body = {**LINEUP_BODY, "themes": ["water"], "variable_ids": ["T2M", "TQV"]}

    client.post("/lineup", json=body)

    assert investigator.calls == [
        ("lineup", (m.Location(**PLACE), m.Period(), "annual", ["water"], ["T2M", "TQV"]))
    ]


def test_witnesses_and_trendmap_pass_their_arguments(
    client: TestClient, investigator: FakeInvestigator
) -> None:
    client.post("/witnesses", json=WITNESSES_BODY)
    client.post("/trendmap", json=TRENDMAP_BODY)

    assert investigator.calls == [
        ("witnesses", (m.Location(**PLACE), "TQV", m.Period(), "annual")),
        ("trendmap", ("PRECTOTCORR", m.BBox(**BBOX), m.Period(), "annual")),
    ]


def test_route_fails_cleanly_when_the_app_has_not_started() -> None:
    from api.main import create_app
    from tests.api_fakes import TEST_SETTINGS

    client = TestClient(create_app(TEST_SETTINGS))  # no lifespan, no override

    response = client.get("/catalog")

    assert response.status_code == 500
    assert error_of(response).code == "internal_error"


# ------------------------------------------------------------ error mapping


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (engine_errors.UnknownVariableError("'XYZ' is not in the catalog."), "validation_error"),
        (engine_errors.NoDataError("There is no snow data here."), "no_data"),
        (engine_errors.UpstreamError("NASA POWER answered with an error."), "upstream_unavailable"),
        (engine_errors.UpstreamTimeoutError("NASA POWER did not answer."), "upstream_timeout"),
    ],
)
def test_engine_error_becomes_its_code_message_and_status(
    client: TestClient, investigator: FakeInvestigator, error: Exception, code: str
) -> None:
    investigator.error = error

    response = client.post("/case", json=CASE_BODY)

    assert response.status_code == ERROR_STATUS[code]
    assert error_of(response).code == code
    assert error_of(response).message == str(error)


def test_unknown_exception_is_logged_and_never_leaked(
    client: TestClient, investigator: FakeInvestigator, caplog: pytest.LogCaptureFixture
) -> None:
    investigator.error = ValueError("secret detail at /srv/app.py")

    with caplog.at_level(logging.ERROR, logger="api"):
        response = client.post("/case", json=CASE_BODY)

    assert response.status_code == 500
    assert error_of(response).code == "internal_error"
    assert "secret detail" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    logged = [r for r in caplog.records if r.exc_info and r.exc_info[0] is ValueError]
    assert logged, "the stack trace must be logged server-side"


def test_base_engine_error_is_treated_as_internal(
    client: TestClient, investigator: FakeInvestigator
) -> None:
    investigator.error = engine_errors.TrendDetectiveError("inner detail")

    response = client.post("/case", json=CASE_BODY)

    assert response.status_code == 500
    assert "inner detail" not in response.text


def test_wrong_method_returns_the_envelope_with_405(client: TestClient) -> None:
    response = client.get("/case")

    assert response.status_code == 405
    assert error_of(response).code == "validation_error"
    assert "POST" in response.headers["allow"]


def test_malformed_json_returns_validation_envelope(client: TestClient) -> None:
    response = client.post(
        "/case", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 422
    assert error_of(response).code == "validation_error"


# --------------------------------------------------------------------- demo


def test_demo_list_is_built_from_the_demo_files(client: TestClient) -> None:
    demos = m.DemoList.model_validate(client.get("/demo").json()["data"]).demos

    by_id = {d.id: d for d in demos}
    assert set(by_id) == {"sahel-rain", "delhi-sunlight", "pantanal-rain", "venice-heat"}
    assert by_id["sahel-rain"].place_name == "Niamey, Niger"
    assert by_id["sahel-rain"].variable_id == "PRECTOTCORR"


def test_demo_returns_the_saved_case(client: TestClient) -> None:
    response = client.get("/demo/sahel-rain")

    assert response.status_code == 200
    assert m.DemoCase.model_validate(response.json()["data"]).id == "sahel-rain"


@pytest.mark.parametrize(
    "demo_id", ["Sahel-Rain", "sahel_rain", "..%2F..%2Fetc%2Fpasswd", "%2e%2e", "a" * 65, "x.json"]
)
def test_demo_rejects_ids_outside_the_allowed_alphabet(client: TestClient, demo_id: str) -> None:
    response = client.get(f"/demo/{demo_id}")

    assert response.status_code == 404
    assert error_of(response).code == "not_found"


# ---------------------------------------------------------------- assistant


def test_ask_is_unavailable_without_a_key(client: TestClient) -> None:
    response = client.post("/ask", json={"question": "Is the Sahel getting wetter?"})

    assert response.status_code == 503
    assert error_of(response).code == "assistant_unavailable"


def test_ask_is_still_unavailable_with_a_key_until_stage_five() -> None:
    client = TestClient(make_app(gemini_key_present=True))

    response = client.post("/ask", json={"question": "Is the Sahel getting wetter?"})

    assert response.status_code == 503
    assert "not enabled yet" in error_of(response).message
    assert client.get("/health").json()["data"]["assistant_available"] is False


def test_ask_uses_the_injected_assistant() -> None:
    assistant = FakeAssistant()
    client = TestClient(make_app(assistant=assistant))

    response = client.post("/ask", json={"question": "Is the Sahel getting wetter?"})

    assert response.status_code == 200
    m.AskResult.model_validate(response.json()["data"])
    assert assistant.questions == ["Is the Sahel getting wetter?"]
    assert client.get("/health").json()["data"]["assistant_available"] is True


def test_health_reports_no_assistant_by_default(client: TestClient) -> None:
    health = m.Health.model_validate(client.get("/health").json()["data"])

    assert health.status == "ok"
    assert health.assistant_available is False


# ------------------------------------------------------------ cache, timeout


def test_identical_requests_are_answered_from_the_cache(
    client: TestClient, investigator: FakeInvestigator
) -> None:
    first = client.post("/case", json=CASE_BODY)
    second = client.post("/case", json=CASE_BODY)

    assert first.json() == second.json()
    assert len(investigator.calls) == 1


def test_cache_key_rounds_coordinates_to_two_decimals(
    client: TestClient, investigator: FakeInvestigator
) -> None:
    near = {**CASE_BODY, "location": {**PLACE, "lat": 13.5101, "lon": 2.1149}}
    far = {**CASE_BODY, "location": {**PLACE, "lat": 13.53}}

    client.post("/case", json=CASE_BODY)
    client.post("/case", json=near)
    client.post("/case", json=far)

    assert len(investigator.calls) == 2


def test_cache_separates_routes_and_parameters(
    client: TestClient, investigator: FakeInvestigator
) -> None:
    client.post("/case", json=CASE_BODY)
    client.post("/case", json={**CASE_BODY, "season": "JJA"})
    client.post("/witnesses", json={**CASE_BODY, "variable_id": "TQV"})

    assert len(investigator.calls) == 3


def test_errors_are_not_cached(client: TestClient, investigator: FakeInvestigator) -> None:
    investigator.error = engine_errors.UpstreamError("NASA POWER answered with an error.")
    client.post("/case", json=CASE_BODY)
    investigator.error = None

    response = client.post("/case", json=CASE_BODY)

    assert response.status_code == 200
    assert len(investigator.calls) == 2


def test_hung_investigation_becomes_upstream_timeout(investigator: FakeInvestigator) -> None:
    investigator.before_answer = lambda: asyncio.sleep(30)
    client = TestClient(make_app(investigator, request_timeout_seconds=0.05))

    response = client.post("/trendmap", json=TRENDMAP_BODY)

    assert response.status_code == 504
    assert error_of(response).code == "upstream_timeout"
