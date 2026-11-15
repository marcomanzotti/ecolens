"""Middleware: rate limit, body size limit, CORS and security headers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.middleware import client_key
from api.schemas import ErrorEnvelope
from tests.api_fakes import CASE_BODY, LINEUP_BODY, TRENDMAP_BODY, FakeInvestigator, make_app

ORIGIN = "https://trend-detective.example"


def code_of(response) -> str:  # type: ignore[no-untyped-def]
    return ErrorEnvelope.model_validate(response.json()).error.code


# --------------------------------------------------------------- rate limit


def test_overall_limit_returns_rate_limited_with_retry_after() -> None:
    client = TestClient(make_app(rate_limit_per_minute=3))

    statuses = [client.get("/catalog").status_code for _ in range(4)]
    blocked = client.get("/catalog")

    assert statuses == [200, 200, 200, 429]
    assert code_of(blocked) == "rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= 60


def test_heavy_routes_have_a_tighter_limit() -> None:
    client = TestClient(make_app(rate_limit_heavy_per_minute=2))

    heavy = [
        client.post("/trendmap", json=TRENDMAP_BODY).status_code,
        client.post("/lineup", json=LINEUP_BODY).status_code,
        client.post("/trendmap", json=TRENDMAP_BODY).status_code,
    ]

    assert heavy == [200, 200, 429]
    assert client.post("/case", json=CASE_BODY).status_code == 200


def test_limit_is_counted_per_forwarded_client() -> None:
    # Cloud Run appends the address it saw to X-Forwarded-For: the client is the last hop.
    client = TestClient(make_app(rate_limit_per_minute=1))
    first = {"x-forwarded-for": "203.0.113.7"}
    second = {"x-forwarded-for": "203.0.113.8"}

    assert client.get("/catalog", headers=first).status_code == 200
    assert client.get("/catalog", headers=first).status_code == 429
    assert client.get("/catalog", headers=second).status_code == 200


def test_spoofed_forwarded_entries_do_not_bypass_the_limit() -> None:
    client = TestClient(make_app(rate_limit_per_minute=1))

    statuses = [
        client.get("/catalog", headers={"x-forwarded-for": f"{spoofed}, 203.0.113.7"}).status_code
        for spoofed in ("198.51.100.1", "198.51.100.2", "anything")
    ]

    assert statuses == [200, 429, 429]


def test_first_hop_can_be_chosen_for_a_proxy_that_appends_its_own_address() -> None:
    client = TestClient(make_app(rate_limit_per_minute=1, forwarded_ip_hop="first"))
    first = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
    second = {"x-forwarded-for": "203.0.113.8, 10.0.0.1"}

    assert client.get("/catalog", headers=first).status_code == 200
    assert client.get("/catalog", headers=first).status_code == 429
    assert client.get("/catalog", headers=second).status_code == 200


def test_health_is_not_rate_limited() -> None:
    client = TestClient(make_app(rate_limit_per_minute=1))

    assert [client.get("/health").status_code for _ in range(5)] == [200] * 5


def test_rejected_requests_do_not_reach_the_investigator() -> None:
    investigator = FakeInvestigator()
    client = TestClient(make_app(investigator, rate_limit_heavy_per_minute=1, cache_max_entries=0))

    client.post("/trendmap", json=TRENDMAP_BODY)
    client.post("/trendmap", json=TRENDMAP_BODY)

    assert len(investigator.calls) == 1


@pytest.mark.parametrize(
    ("headers", "hop", "expected"),
    [
        ([(b"x-forwarded-for", b"203.0.113.7, 10.0.0.1")], "first", "203.0.113.7"),
        ([(b"x-forwarded-for", b"203.0.113.7, 10.0.0.1")], "last", "10.0.0.1"),
        ([(b"x-forwarded-for", b" , ")], "first", "192.0.2.1"),
        ([], "first", "192.0.2.1"),
    ],
)
def test_client_key(headers: list[tuple[bytes, bytes]], hop: str, expected: str) -> None:
    scope = {"type": "http", "headers": headers, "client": ("192.0.2.1", 5000)}

    assert client_key(scope, hop) == expected  # type: ignore[arg-type]


def test_client_key_without_peer_and_with_oversized_header() -> None:
    assert client_key({"type": "http", "headers": []}, "first") == "unknown"
    long = [(b"x-forwarded-for", b"9" * 500)]
    assert len(client_key({"type": "http", "headers": long}, "first")) == 64


# ---------------------------------------------------------------- body size


def test_declared_body_above_the_limit_is_rejected() -> None:
    client = TestClient(make_app(max_body_bytes=200))

    response = client.post("/ask", json={"question": "x" * 400})

    assert response.status_code == 413
    assert code_of(response) == "validation_error"


def test_streamed_body_above_the_limit_is_rejected() -> None:
    investigator = FakeInvestigator()
    client = TestClient(make_app(investigator, max_body_bytes=200))

    def chunks():  # type: ignore[no-untyped-def]
        yield b'{"question": "'
        yield b"x" * 400
        yield b'"}'

    response = client.post("/ask", content=chunks(), headers={"content-type": "application/json"})

    assert response.status_code == 413
    assert code_of(response) == "validation_error"


def test_streamed_body_under_the_limit_is_replayed_to_the_route() -> None:
    investigator = FakeInvestigator()
    client = TestClient(make_app(investigator))

    def chunks():  # type: ignore[no-untyped-def]
        yield b'{"location": {"lat": 13.51, "lon": 2.11},'
        yield b' "variable_id": "T2M"}'

    response = client.post("/case", content=chunks(), headers={"content-type": "application/json"})

    assert response.status_code == 200
    assert investigator.calls[0][1][1] == "T2M"


# ------------------------------------------------------- CORS and headers


def test_cors_allows_only_the_configured_origins() -> None:
    client = TestClient(make_app(frontend_origins=(ORIGIN, "http://localhost:3000")))

    allowed = client.get("/health", headers={"origin": ORIGIN})
    other = client.get("/health", headers={"origin": "https://evil.example"})

    assert allowed.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-origin" not in other.headers


def test_cors_preflight_allows_get_and_post_only() -> None:
    client = TestClient(make_app(frontend_origins=(ORIGIN,)))
    preflight = {"origin": ORIGIN, "access-control-request-headers": "content-type"}

    post = client.options("/case", headers={**preflight, "access-control-request-method": "POST"})
    delete = client.options(
        "/case", headers={**preflight, "access-control-request-method": "DELETE"}
    )

    assert post.status_code == 200
    assert post.headers["access-control-allow-methods"] == "GET, POST"
    assert delete.status_code == 400


def test_error_responses_keep_cors_and_security_headers() -> None:
    client = TestClient(make_app(frontend_origins=(ORIGIN,), rate_limit_per_minute=1))
    client.get("/catalog", headers={"origin": ORIGIN})

    blocked = client.get("/catalog", headers={"origin": ORIGIN})

    assert blocked.status_code == 429
    assert blocked.headers["access-control-allow-origin"] == ORIGIN
    assert blocked.headers["x-content-type-options"] == "nosniff"
    assert blocked.headers["referrer-policy"] == "no-referrer"


def test_every_response_has_the_security_headers() -> None:
    client = TestClient(make_app())

    for response in (client.get("/health"), client.get("/nope"), client.post("/case", json={})):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
