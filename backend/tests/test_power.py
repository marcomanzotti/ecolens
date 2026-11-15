"""PowerSource against recorded NASA POWER answers (respx); no network in the default run."""

from __future__ import annotations

import logging
import math
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest
import respx

from tests.engine_series import (
    point_payload,
    recorded_point_response,
    recorded_region_response,
)
from trend_detective.errors import UpstreamError, UpstreamTimeoutError
from trend_detective.models import BBox, Location, Period
from trend_detective.ports import SeriesSource
from trend_detective.sources.power import (
    POWER_BASE_URL,
    PowerSource,
    annual_values,
)

POINT_URL = f"{POWER_BASE_URL}/point"
REGION_URL = f"{POWER_BASE_URL}/regional"
NIAMEY = Location(lat=13.51, lon=2.11, label="Niamey, Niger")
FULL = Period(start_year=1981, end_year=2025)
SECRET = "SECRET-UPSTREAM-BODY"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
async def source(sleeps: list[float]) -> AsyncIterator[PowerSource]:
    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async with httpx.AsyncClient() as client:
        yield PowerSource(client, sleep=fake_sleep, backoff_seconds=0.5)


def _point_responder(calls: list[httpx.Request]) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        params = request.url.params
        body = recorded_point_response(
            params["parameters"].split(","), int(params["start"]), int(params["end"])
        )
        return httpx.Response(200, json=body)

    return respond


def _annual(variable: str, year: int) -> float:
    return point_payload()["properties"]["parameter"][variable][f"{year}13"]


# --------------------------------------------------------------------------
# Monthly -> yearly
# --------------------------------------------------------------------------


def _months(year: int, values: list[float]) -> dict[str, float]:
    return {f"{year}{m:02d}": v for m, v in enumerate(values, start=1)}


def test_annual_uses_month_13() -> None:
    monthly = {**_months(2000, [1.0] * 12), "200013": 7.5}
    assert annual_values(monthly, [2000], "annual") == [7.5]


def test_missing_value_marker_becomes_none() -> None:
    assert annual_values({"200013": -999.0}, [2000], "annual") == [None]


def test_absent_or_non_numeric_year_becomes_none() -> None:
    monthly: dict[str, Any] = {"200113": "n/a", "200213": math.nan, "200313": True}
    assert annual_values(monthly, [2000, 2001, 2002, 2003], "annual") == [None] * 4


def test_season_is_mean_of_three_months() -> None:
    monthly = _months(2000, [0, 0, 3.0, 6.0, 9.0, 0, 0, 0, 0, 0, 0, 0])
    assert annual_values(monthly, [2000], "MAM") == [6.0]


def test_each_season_picks_its_months() -> None:
    monthly = _months(2000, [float(m) for m in range(1, 13)])
    assert annual_values(monthly, [2000], "JJA") == [7.0]  # (6 + 7 + 8) / 3
    assert annual_values(monthly, [2000], "SON") == [10.0]  # (9 + 10 + 11) / 3


def test_season_with_a_missing_month_is_none() -> None:
    monthly = _months(2000, [0, 0, 3.0, -999.0, 9.0, 0, 0, 0, 0, 0, 0, 0])
    assert annual_values(monthly, [2000], "MAM") == [None]


def test_djf_takes_december_of_the_previous_year() -> None:
    monthly = {"199912": 3.0, "200001": 6.0, "200002": 9.0, "200012": 100.0}
    assert annual_values(monthly, [2000], "DJF") == [6.0]


def test_djf_is_none_when_december_is_not_available() -> None:
    monthly = {"198101": 6.0, "198102": 9.0}
    assert annual_values(monthly, [1981], "DJF") == [None]


def test_annual_values_keep_period_order_and_length() -> None:
    monthly = {"200013": 1.0, "200213": 3.0}
    assert annual_values(monthly, [2000, 2001, 2002], "annual") == [1.0, None, 3.0]


# --------------------------------------------------------------------------
# Point series
# --------------------------------------------------------------------------


def test_power_source_satisfies_the_series_source_port() -> None:
    def accept(_source: SeriesSource) -> None: ...

    accept(PowerSource())


@respx.mock
async def test_point_series_annual_matches_recorded_data(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))

    result = await source.point_series(NIAMEY, ["PRECTOTCORR", "T2M"], FULL, "annual")

    assert set(result) == {"PRECTOTCORR", "T2M"}
    assert len(result["T2M"]) == 45
    assert result["T2M"][0] == _annual("T2M", 1981)
    assert result["PRECTOTCORR"][-1] == _annual("PRECTOTCORR", 2025)
    assert all(isinstance(v, float) for v in result["T2M"])


@respx.mock
async def test_point_request_has_the_expected_query(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))

    await source.point_series(NIAMEY, ["T2M", "PRECTOTCORR"], FULL, "annual")

    assert len(calls) == 1
    params = calls[0].url.params
    assert params["parameters"] == "T2M,PRECTOTCORR"
    assert params["community"] == "AG"
    assert params["longitude"] == "2.11"
    assert params["latitude"] == "13.51"
    assert (params["start"], params["end"], params["format"]) == ("1981", "2025", "JSON")


@respx.mock
async def test_point_series_follows_the_requested_period(source: PowerSource) -> None:
    respx.get(POINT_URL).mock(side_effect=_point_responder([]))

    result = await source.point_series(
        NIAMEY, ["T2M"], Period(start_year=1990, end_year=2001), "annual"
    )

    assert len(result["T2M"]) == 12
    assert result["T2M"][0] == _annual("T2M", 1990)
    assert result["T2M"][-1] == _annual("T2M", 2001)


@respx.mock
async def test_series_that_start_late_have_none_before_they_start(source: PowerSource) -> None:
    respx.get(POINT_URL).mock(side_effect=_point_responder([]))

    result = await source.point_series(NIAMEY, ["CLOUD_AMT", "T2M"], FULL, "annual")

    assert result["CLOUD_AMT"][:3] == [None, None, None]
    assert result["CLOUD_AMT"][-1] is not None
    assert None not in result["T2M"]


@respx.mock
async def test_variable_returned_only_as_missing_values_is_all_none(source: PowerSource) -> None:
    respx.get(POINT_URL).mock(side_effect=_point_responder([]))

    result = await source.point_series(NIAMEY, ["IMERG_PRECTOT"], FULL, "annual")

    assert result["IMERG_PRECTOT"] == [None] * 45


@respx.mock
async def test_variable_not_returned_by_the_source_is_absent(source: PowerSource) -> None:
    respx.get(POINT_URL).mock(side_effect=_point_responder([]))

    result = await source.point_series(NIAMEY, ["T2M", "NOT_A_PARAMETER"], FULL, "annual")

    assert list(result) == ["T2M"]


@respx.mock
async def test_djf_requests_one_extra_earlier_year(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))

    result = await source.point_series(
        NIAMEY, ["T2M"], Period(start_year=1990, end_year=2000), "DJF"
    )

    assert calls[0].url.params["start"] == "1989"
    monthly = point_payload()["properties"]["parameter"]["T2M"]
    expected = (monthly["198912"] + monthly["199001"] + monthly["199002"]) / 3
    assert result["T2M"][0] == pytest.approx(expected)
    assert len(result["T2M"]) == 11


@respx.mock
async def test_djf_of_the_first_data_year_is_none(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))

    result = await source.point_series(NIAMEY, ["T2M"], FULL, "DJF")

    assert calls[0].url.params["start"] == "1981"
    assert result["T2M"][0] is None
    assert result["T2M"][1] is not None


@respx.mock
async def test_more_than_twenty_variables_are_split_into_concurrent_chunks(
    source: PowerSource,
) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))
    pool = list(point_payload()["properties"]["parameter"]) + [f"EXTRA_{i}" for i in range(11)]
    assert len(pool) == 25

    result = await source.point_series(NIAMEY, pool, FULL, "annual")

    sizes = sorted(len(c.url.params["parameters"].split(",")) for c in calls)
    assert sizes == [5, 20]
    assert len(result) == 14  # the extras are not returned by POWER


@respx.mock
async def test_duplicate_ids_are_requested_once(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))

    result = await source.point_series(NIAMEY, ["T2M", "T2M"], FULL, "annual")

    assert calls[0].url.params["parameters"] == "T2M"
    assert list(result) == ["T2M"]


@respx.mock
async def test_no_variables_means_no_request(source: PowerSource) -> None:
    route = respx.get(POINT_URL).mock(side_effect=_point_responder([]))

    assert await source.point_series(NIAMEY, [], FULL, "annual") == {}
    assert not route.called


@respx.mock
async def test_returned_lists_are_independent_copies(source: PowerSource) -> None:
    respx.get(POINT_URL).mock(side_effect=_point_responder([]))

    first = await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
    first["T2M"][0] = 12345.0
    second = await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert second["T2M"][0] == _annual("T2M", 1981)


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------


@respx.mock
async def test_repeated_request_is_served_from_the_cache(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))

    first = await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
    second = await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert first == second
    assert len(calls) == 1


@respx.mock
async def test_cache_is_keyed_by_place_period_season_and_variable(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))

    await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
    await source.point_series(Location(lat=14.0, lon=2.11), ["T2M"], FULL, "annual")
    await source.point_series(NIAMEY, ["T2M"], Period(start_year=1990, end_year=2000), "annual")
    await source.point_series(NIAMEY, ["T2M"], FULL, "JJA")
    await source.point_series(NIAMEY, ["T2M", "PRECTOTCORR"], FULL, "annual")

    assert len(calls) == 5
    assert calls[-1].url.params["parameters"] == "PRECTOTCORR"  # T2M was cached


@respx.mock
async def test_cache_entries_expire() -> None:
    clock = FakeClock()
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))
    async with httpx.AsyncClient() as client:
        source = PowerSource(client, clock=clock, cache_ttl_seconds=60)
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
        clock.now += 59
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
        assert len(calls) == 1
        clock.now += 2
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
        assert len(calls) == 2


@respx.mock
async def test_cache_can_be_disabled() -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))
    async with httpx.AsyncClient() as client:
        source = PowerSource(client, cache_ttl_seconds=0)
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
    assert len(calls) == 2


@respx.mock
async def test_cache_is_bounded() -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))
    async with httpx.AsyncClient() as client:
        source = PowerSource(client, cache_max_entries=2)
        for variable in ("T2M", "PS", "WS2M"):
            await source.point_series(NIAMEY, [variable], FULL, "annual")
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")  # evicted, fetched again
        await source.point_series(NIAMEY, ["WS2M"], FULL, "annual")  # still cached
    assert len(calls) == 4


# --------------------------------------------------------------------------
# Failures
# --------------------------------------------------------------------------


@respx.mock
async def test_server_errors_are_retried_a_bounded_number_of_times(
    source: PowerSource, sleeps: list[float]
) -> None:
    route = respx.get(POINT_URL).mock(return_value=httpx.Response(500, text=SECRET))

    with pytest.raises(UpstreamError) as caught:
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert route.call_count == 3  # first try + 2 retries
    assert sleeps == [0.5, 1.0]  # exponential backoff
    assert SECRET not in str(caught.value)
    assert SECRET not in caught.value.message


@respx.mock
async def test_a_transient_error_is_recovered(source: PowerSource) -> None:
    ok = recorded_point_response(["T2M"], 1981, 2025)
    route = respx.get(POINT_URL).mock(
        side_effect=[httpx.Response(503), httpx.Response(429), httpx.Response(200, json=ok)]
    )

    result = await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert route.call_count == 3
    assert len(result["T2M"]) == 45


@respx.mock
@pytest.mark.parametrize("status", [400, 404, 422])
async def test_client_errors_are_not_retried(source: PowerSource, status: int) -> None:
    route = respx.get(POINT_URL).mock(return_value=httpx.Response(status, text=SECRET))

    with pytest.raises(UpstreamError) as caught:
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert route.call_count == 1
    assert SECRET not in caught.value.message


@respx.mock
async def test_timeouts_map_to_the_timeout_error(source: PowerSource) -> None:
    route = respx.get(POINT_URL).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(UpstreamTimeoutError):
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert route.call_count == 3


@respx.mock
async def test_connection_failures_map_to_the_upstream_error(source: PowerSource) -> None:
    respx.get(POINT_URL).mock(side_effect=httpx.ConnectError(SECRET))

    with pytest.raises(UpstreamError) as caught:
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert not isinstance(caught.value, UpstreamTimeoutError)
    assert SECRET not in caught.value.message


@respx.mock
@pytest.mark.parametrize(
    "body",
    [
        httpx.Response(200, text=f"<html>{SECRET}</html>"),
        httpx.Response(200, json={"properties": {}}),
        httpx.Response(200, json={"properties": {"parameter": [1, 2]}}),
        httpx.Response(200, json=[1, 2, 3]),
        httpx.Response(200, json={"properties": {"parameter": {"T2M": "oops"}}}),
    ],
)
async def test_unreadable_answers_map_to_the_upstream_error(
    source: PowerSource, body: httpx.Response
) -> None:
    respx.get(POINT_URL).mock(return_value=body)

    with pytest.raises(UpstreamError) as caught:
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert SECRET not in caught.value.message


@respx.mock
async def test_upstream_body_is_never_logged(
    source: PowerSource, caplog: pytest.LogCaptureFixture
) -> None:
    respx.get(POINT_URL).mock(return_value=httpx.Response(500, text=SECRET))

    with caplog.at_level(logging.DEBUG), pytest.raises(UpstreamError):
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert caplog.records
    assert SECRET not in caplog.text


@respx.mock
async def test_failures_are_not_cached(source: PowerSource) -> None:
    ok = recorded_point_response(["T2M"], 1981, 2025)
    respx.get(POINT_URL).mock(
        side_effect=[httpx.Response(422)] + [httpx.Response(200, json=ok)] * 2
    )

    with pytest.raises(UpstreamError):
        await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
    result = await source.point_series(NIAMEY, ["T2M"], FULL, "annual")

    assert len(result["T2M"]) == 45


@respx.mock
async def test_one_failing_chunk_fails_the_whole_request(source: PowerSource) -> None:
    ok = recorded_point_response(["T2M"], 1981, 2025)
    respx.get(POINT_URL).mock(side_effect=[httpx.Response(200, json=ok), httpx.Response(422)])
    ids = [f"P{i}" for i in range(25)]

    with pytest.raises(UpstreamError):
        await source.point_series(NIAMEY, ids, FULL, "annual")


# --------------------------------------------------------------------------
# Region series
# --------------------------------------------------------------------------

BOX = BBox(lat_min=10, lat_max=20, lon_min=-5, lon_max=5)


def _region_responder(calls: list[httpx.Request]) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        params = request.url.params
        return httpx.Response(
            200, json=recorded_region_response(int(params["start"]), int(params["end"]))
        )

    return respond


@respx.mock
async def test_region_series_returns_one_series_per_grid_point(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(REGION_URL).mock(side_effect=_region_responder(calls))

    cells = await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")

    assert len(cells) == 357
    assert all(len(c.values) == 45 for c in cells)
    assert (cells[0].lat, cells[0].lon) == (10.0, -5.0)
    assert (cells[1].lat, cells[1].lon) == (10.0, -4.375)
    assert (cells[-1].lat, cells[-1].lon) == (20.0, 5.0)


@respx.mock
async def test_region_cells_are_listed_row_by_row(source: PowerSource) -> None:
    respx.get(REGION_URL).mock(side_effect=_region_responder([]))

    cells = await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")

    keys = [(c.lat, c.lon) for c in cells]
    assert keys == sorted(keys)
    assert len({c.lat for c in cells}) == 21
    assert len({c.lon for c in cells}) == 17


@respx.mock
async def test_region_values_match_the_recorded_annual_means(source: PowerSource) -> None:
    respx.get(REGION_URL).mock(side_effect=_region_responder([]))
    from tests.engine_series import region_payload

    feature = region_payload()["features"][40]
    lon, lat, _ = feature["geometry"]["coordinates"]
    monthly = feature["properties"]["parameter"]["PRECTOTCORR"]

    cells = await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")

    cell = next(c for c in cells if (c.lat, c.lon) == (lat, lon))
    assert cell.values[0] == monthly["198113"]
    assert cell.values[-1] == monthly["202513"]


@respx.mock
async def test_region_request_has_the_expected_query(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(REGION_URL).mock(side_effect=_region_responder(calls))

    await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")

    params = calls[0].url.params
    assert params["parameters"] == "PRECTOTCORR"
    assert params["community"] == "AG"
    assert (params["latitude-min"], params["latitude-max"]) == ("10.0", "20.0")
    assert (params["longitude-min"], params["longitude-max"]) == ("-5.0", "5.0")
    assert (params["start"], params["end"], params["format"]) == ("1981", "2025", "JSON")


@respx.mock
async def test_region_season_uses_three_month_means(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(REGION_URL).mock(side_effect=_region_responder(calls))
    from tests.engine_series import region_payload

    feature = region_payload()["features"][0]
    lon, lat, _ = feature["geometry"]["coordinates"]
    m = feature["properties"]["parameter"]["PRECTOTCORR"]

    cells = await source.region_series(
        BOX, "PRECTOTCORR", Period(start_year=1990, end_year=2000), "DJF"
    )

    assert calls[0].url.params["start"] == "1989"
    cell = next(c for c in cells if (c.lat, c.lon) == (lat, lon))
    assert cell.values[0] == pytest.approx((m["198912"] + m["199001"] + m["199002"]) / 3)
    assert len(cell.values) == 11


@respx.mock
async def test_region_answers_are_cached(source: PowerSource) -> None:
    calls: list[httpx.Request] = []
    respx.get(REGION_URL).mock(side_effect=_region_responder(calls))

    first = await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")
    second = await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")

    assert first == second
    assert len(calls) == 1


@respx.mock
async def test_region_without_features_is_empty(source: PowerSource) -> None:
    respx.get(REGION_URL).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )

    assert await source.region_series(BOX, "PRECTOTCORR", FULL, "annual") == []


@respx.mock
async def test_region_feature_without_the_parameter_is_skipped(source: PowerSource) -> None:
    body = recorded_region_response(1981, 2025)
    del body["features"][0]["properties"]["parameter"]["PRECTOTCORR"]
    respx.get(REGION_URL).mock(return_value=httpx.Response(200, json=body))

    cells = await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")

    assert len(cells) == 356


@respx.mock
@pytest.mark.parametrize(
    "body",
    [
        {"features": "nope"},
        {"nothing": 1},
        {"features": [{"geometry": {"coordinates": [1.0]}, "properties": {}}]},
        {"features": [{"geometry": None, "properties": {"parameter": {}}}]},
    ],
)
async def test_region_unreadable_answers_map_to_the_upstream_error(
    source: PowerSource, body: dict[str, Any]
) -> None:
    respx.get(REGION_URL).mock(return_value=httpx.Response(200, json=body))

    with pytest.raises(UpstreamError):
        await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")


@respx.mock
async def test_region_timeout_maps_to_the_timeout_error(source: PowerSource) -> None:
    respx.get(REGION_URL).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(UpstreamTimeoutError):
        await source.region_series(BOX, "PRECTOTCORR", FULL, "annual")


@respx.mock
async def test_injected_client_timeout_is_respected_unless_overridden() -> None:
    calls: list[httpx.Request] = []
    respx.get(POINT_URL).mock(side_effect=_point_responder(calls))
    async with httpx.AsyncClient(timeout=7.0) as client:
        await PowerSource(client).point_series(NIAMEY, ["T2M"], FULL, "annual")
        await PowerSource(client, timeout=3.0).point_series(NIAMEY, ["PS"], FULL, "annual")

    assert calls[0].extensions["timeout"]["read"] == 7.0
    assert calls[1].extensions["timeout"]["read"] == 3.0


# --------------------------------------------------------------------------
# Client ownership
# --------------------------------------------------------------------------


@respx.mock
async def test_source_creates_and_closes_its_own_client() -> None:
    respx.get(POINT_URL).mock(side_effect=_point_responder([]))
    source = PowerSource()

    result = await source.point_series(NIAMEY, ["T2M"], FULL, "annual")
    await source.aclose()

    assert len(result["T2M"]) == 45


async def test_aclose_leaves_an_injected_client_open() -> None:
    async with httpx.AsyncClient() as client:
        source = PowerSource(client)
        await source.aclose()
        assert not client.is_closed


# --------------------------------------------------------------------------
# Live (deselected by default)
# --------------------------------------------------------------------------


@pytest.mark.live
async def test_live_point_series_for_niamey() -> None:
    source = PowerSource()
    try:
        result = await source.point_series(NIAMEY, ["T2M", "PRECTOTCORR"], FULL, "annual")
    finally:
        await source.aclose()
    assert len(result["T2M"]) == 45
    assert None not in result["T2M"]
    assert 25 < result["T2M"][-1] < 40  # degrees C, Sahel


@pytest.mark.live
async def test_live_parameter_limit_per_call() -> None:
    """Documents what POWER does with more than 20 parameters in one call."""
    ids = list(point_payload()["properties"]["parameter"]) + [
        "ALLSKY_SFC_LW_DWN",
        "CLRSKY_SFC_SW_DWN",
        "EVPTRNS",
        "FROST_DAYS",
        "GWETPROF",
        "PS",
        "QV2M",
        "T2MDEW",
        "T2M_MAX",
        "TQV",
        "WS2M",
    ]
    assert len(ids) == 25
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            POINT_URL,
            params={
                "parameters": ",".join(ids),
                "community": "AG",
                "longitude": 2.11,
                "latitude": 13.51,
                "start": 2024,
                "end": 2025,
                "format": "JSON",
            },
        )
    assert response.status_code in (200, 422)
