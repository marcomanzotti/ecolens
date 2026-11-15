"""The HTTP API on top of the real TrendInvestigator (no fake of the engine).

Only the data source is replaced: a FakeSeriesSource serving the saved NASA POWER
samples (Niamey and the Sahel box). These tests check the wiring between the
routes, the engine and the envelope, not specific statistics.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.schemas import ERROR_STATUS, ErrorEnvelope
from api.settings import Settings
from tests.api_fakes import CASE_BODY, LINEUP_BODY, TRENDMAP_BODY, WITNESSES_BODY, make_app
from tests.investigation_helpers import (
    FULL,
    FakeSeriesSource,
    load_grid_samples,
    sample_point_source,
)
from trend_detective import catalog
from trend_detective import models as m
from trend_detective.errors import UpstreamError, UpstreamTimeoutError
from trend_detective.service import TrendInvestigator

N_YEARS = FULL.end_year - FULL.start_year + 1
SAHEL_CELLS = 357
ROUTE_BODIES = [
    ("/case", CASE_BODY),
    ("/lineup", LINEUP_BODY),
    ("/witnesses", WITNESSES_BODY),
    ("/trendmap", TRENDMAP_BODY),
]


def client_on(source: FakeSeriesSource) -> TestClient:
    app = make_app(
        TrendInvestigator(source), rate_limit_per_minute=0, rate_limit_heavy_per_minute=0
    )
    return TestClient(app)


@pytest.fixture
def source() -> FakeSeriesSource:
    saved = sample_point_source()
    return FakeSeriesSource(points=saved.points, grid=load_grid_samples(FULL))


@pytest.fixture
def client(source: FakeSeriesSource) -> TestClient:
    return client_on(source)


def data_of[M: m.Model](response: httpx.Response, model: type[M]) -> M:
    body = response.json()
    assert response.status_code == 200, body
    assert body["success"] is True and body["error"] is None
    return model.model_validate(body["data"])


def error_of(response: httpx.Response) -> tuple[int, str]:
    return response.status_code, ErrorEnvelope.model_validate(response.json()).error.code


# ------------------------------------------------------------- happy paths


def test_case_runs_the_real_engine(client: TestClient) -> None:
    result = data_of(client.post("/case", json=CASE_BODY), m.CaseResult)

    assert result.variable.id == "PRECTOTCORR"
    assert result.location.label == "Niamey, Niger"
    assert [p.year for p in result.series] == list(range(FULL.start_year, FULL.end_year + 1))
    assert result.trend is not None
    assert result.verdict.evidence in {"strong", "mixed", "none"}
    assert "Niamey, Niger" in result.verdict.where


def test_case_applies_the_default_period_and_season(
    client: TestClient, source: FakeSeriesSource
) -> None:
    result = data_of(client.post("/case", json=CASE_BODY), m.CaseResult)

    assert (result.period, result.season) == (m.Period(start_year=1981, end_year=2025), "annual")
    assert source.point_calls[0][2:] == (FULL, "annual")


def test_case_passes_a_custom_period_and_season_to_the_source(
    client: TestClient, source: FakeSeriesSource
) -> None:
    period = {"start_year": 1990, "end_year": 2020}

    result = data_of(
        client.post("/case", json={**CASE_BODY, "period": period, "season": "JJA"}), m.CaseResult
    )

    assert (result.period, result.season) == (m.Period(**period), "JJA")
    assert len(result.series) == 31
    assert source.point_calls[0][2:] == (m.Period(**period), "JJA")


def test_lineup_covers_the_whole_catalog(client: TestClient) -> None:
    result = data_of(client.post("/lineup", json=LINEUP_BODY), m.LineupResult)

    assert {item.variable.id for item in result.items} == {v.id for v in catalog.VARIABLES}
    assert result.correction.method == "fdr_bh"
    assert all(len(item.sparkline) == N_YEARS for item in result.items)


def test_lineup_narrowed_by_theme(client: TestClient) -> None:
    result = data_of(
        client.post("/lineup", json={**LINEUP_BODY, "themes": ["water"]}), m.LineupResult
    )

    assert result.items
    assert {item.variable.theme for item in result.items} == {"water"}


def test_witnesses_compares_the_whole_group(client: TestClient) -> None:
    result = data_of(client.post("/witnesses", json=WITNESSES_BODY), m.WitnessesResult)

    assert {w.variable.id for w in result.witnesses} == {"TQV", "PW"}
    assert result.agreement.level in {"agree", "partly", "disagree", "insufficient"}


def test_trendmap_returns_one_cell_per_grid_point(
    client: TestClient, source: FakeSeriesSource
) -> None:
    result = data_of(client.post("/trendmap", json=TRENDMAP_BODY), m.TrendMapResult)

    assert len(result.cells) == SAHEL_CELLS
    assert result.correction.n_tests == SAHEL_CELLS
    assert source.region_calls[0][1:] == ("PRECTOTCORR", FULL, "annual")


def test_catalog_and_places_come_from_the_engine(client: TestClient) -> None:
    served = data_of(client.get("/catalog"), m.Catalog)
    places = data_of(client.get("/places"), m.PlacesResult)

    assert [v.id for v in served.variables] == [v.id for v in catalog.VARIABLES]
    assert places.places


# ------------------------------------------------------------ engine errors


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/case", {**CASE_BODY, "variable_id": "NOT_A_VARIABLE"}),
        ("/lineup", {**LINEUP_BODY, "variable_ids": ["T2M", "NOT_A_VARIABLE"]}),
        ("/witnesses", {**WITNESSES_BODY, "variable_id": "NOT_A_VARIABLE"}),
        ("/witnesses", {**WITNESSES_BODY, "variable_id": "WS10M"}),  # no witness group
        ("/trendmap", {**TRENDMAP_BODY, "variable_id": "NOT_A_VARIABLE"}),
    ],
)
def test_unknown_variable_is_a_validation_error(
    client: TestClient, source: FakeSeriesSource, path: str, body: dict
) -> None:
    assert error_of(client.post(path, json=body)) == (422, "validation_error")
    assert source.point_calls == [] and source.region_calls == []


@pytest.mark.parametrize(("path", "body"), ROUTE_BODIES)
def test_source_without_data_is_no_data(path: str, body: dict) -> None:
    client = client_on(FakeSeriesSource())

    assert error_of(client.post(path, json=body)) == (422, "no_data")


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (UpstreamError("NASA POWER answered with an error."), "upstream_unavailable"),
        (UpstreamTimeoutError("NASA POWER did not answer in time."), "upstream_timeout"),
    ],
)
@pytest.mark.parametrize(("path", "body"), ROUTE_BODIES)
def test_source_failure_passes_through_the_engine(
    path: str, body: dict, error: Exception, code: str
) -> None:
    client = client_on(FakeSeriesSource(error=error))

    response = client.post(path, json=body)

    assert error_of(response) == (ERROR_STATUS[code], code)
    assert response.json()["error"]["message"] == str(error)


@pytest.mark.parametrize(("path", "body"), ROUTE_BODIES)
def test_unexpected_source_failure_is_internal_and_leaks_nothing(path: str, body: dict) -> None:
    leak = httpx.ConnectError("boom at https://upstream.example/?token=do-not-leak")
    client = client_on(FakeSeriesSource(error=leak))

    response = client.post(path, json=body)

    assert error_of(response) == (500, "internal_error")
    assert "do-not-leak" not in response.text
    assert "Traceback" not in response.text


def test_failed_answer_is_not_cached_and_the_good_one_is(source: FakeSeriesSource) -> None:
    client = client_on(source)
    source.error = UpstreamError("NASA POWER answered with an error.")
    assert error_of(client.post("/case", json=CASE_BODY)) == (502, "upstream_unavailable")
    source.error = None

    first = client.post("/case", json=CASE_BODY)
    second = client.post("/case", json=CASE_BODY)

    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(source.point_calls) == 2  # the failure and one success; the third is cached


# ------------------------------------------------------------------ startup


def test_default_settings_start_the_real_engine_and_close_its_client() -> None:
    app = create_app(Settings())

    with TestClient(app) as client:
        investigator = app.state.investigator
        assert isinstance(investigator, TrendInvestigator)
        assert data_of(client.get("/catalog"), m.Catalog).variables
        health = data_of(client.get("/health"), m.Health)

    assert health.assistant_available is False
    assert app.state.investigator is None
    assert _http_client_of(investigator).is_closed is True


def _http_client_of(investigator: TrendInvestigator) -> httpx.AsyncClient:
    """The httpx client the lifespan handed to the POWER source."""
    clients = [
        value
        for holder in vars(investigator).values()
        for value in vars(holder).values()
        if isinstance(value, httpx.AsyncClient)
    ]
    assert len(clients) == 1
    return clients[0]
