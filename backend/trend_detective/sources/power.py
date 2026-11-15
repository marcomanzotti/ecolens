"""NASA POWER as a SeriesSource (BE-1).

Monthly point and regional endpoints, community AG. Values stay in POWER's own units.
Failures become errors.UpstreamError / errors.UpstreamTimeoutError with fixed English messages:
the upstream body is never raised, never logged.

Request limits: one point call carries up to MAX_PARAMETERS_PER_CALL parameters (larger requests
are split into concurrent chunks); a regional call carries exactly one parameter.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

import httpx

from trend_detective.errors import UpstreamError, UpstreamTimeoutError
from trend_detective.models import MIN_YEAR, BBox, Location, Period, Season
from trend_detective.ports import AnnualSeries, GridSeries

logger = logging.getLogger(__name__)

POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/monthly"
COMMUNITY = "AG"
MAX_PARAMETERS_PER_CALL = 20
MISSING_VALUE = -999.0
ANNUAL_MEAN_MONTH = 13
SEASON_MONTHS: Mapping[str, tuple[int, int, int]] = {
    "DJF": (12, 1, 2),
    "MAM": (3, 4, 5),
    "JJA": (6, 7, 8),
    "SON": (9, 10, 11),
}
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
DEFAULT_CACHE_TTL_SECONDS = 6 * 3600.0
DEFAULT_CACHE_MAX_ENTRIES = 1024

MSG_UNAVAILABLE = "NASA POWER could not provide the data right now. Please try again in a moment."
MSG_TIMEOUT = "NASA POWER took too long to answer. Please try again in a moment."
MSG_UNREADABLE = "NASA POWER sent an answer that could not be read."

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]


# --------------------------------------------------------------------------
# Monthly values -> one value per year
# --------------------------------------------------------------------------


def _month_value(monthly: Mapping[str, Any], year: int, month: int) -> float | None:
    value = monthly.get(f"{year}{month:02d}")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if not math.isfinite(value) or value == MISSING_VALUE:
        return None
    return float(value)


def _season_value(monthly: Mapping[str, Any], year: int, season: str) -> float | None:
    parts: list[float] = []
    for month in SEASON_MONTHS[season]:
        # DJF belongs to the year of its January: its December is the previous year's.
        source_year = year - 1 if season == "DJF" and month == 12 else year
        value = _month_value(monthly, source_year, month)
        if value is None:
            return None
        parts.append(value)
    return sum(parts) / len(parts)


def annual_values(monthly: Mapping[str, Any], years: Sequence[int], season: Season) -> AnnualSeries:
    """One value per year: month 13 for 'annual', else the mean of the season's three months."""
    if season == "annual":
        return [_month_value(monthly, year, ANNUAL_MEAN_MONTH) for year in years]
    return [_season_value(monthly, year, season) for year in years]


def _request_start(period: Period, season: Season) -> int:
    """DJF of the first year needs the previous December, when POWER has it."""
    if season == "DJF" and period.start_year > MIN_YEAR:
        return period.start_year - 1
    return period.start_year


def _years_of(period: Period) -> range:
    return range(period.start_year, period.end_year + 1)


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------


class TtlCache:
    """Small in-memory cache: time-to-live and a bound on the number of entries (oldest out)."""

    def __init__(self, ttl_seconds: float, max_entries: int, clock: Clock) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._items: OrderedDict[Any, tuple[float, Any]] = OrderedDict()

    def get(self, key: Any) -> Any | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._items[key]
            return None
        return value

    def put(self, key: Any, value: Any) -> None:
        if self._ttl <= 0 or self._max <= 0:
            return
        self._items.pop(key, None)
        self._items[key] = (self._clock() + self._ttl, value)
        while len(self._items) > self._max:
            self._items.popitem(last=False)


# --------------------------------------------------------------------------
# Source
# --------------------------------------------------------------------------


class PowerSource:
    """Fetches yearly and seasonal series from NASA POWER (implements ports.SeriesSource)."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        base_url: str = POWER_BASE_URL,
        timeout: httpx.Timeout | float | None = None,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
        cache_max_entries: int = DEFAULT_CACHE_MAX_ENTRIES,
        max_parameters_per_call: int = MAX_PARAMETERS_PER_CALL,
        max_concurrency: int = 4,
        clock: Clock = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._chunk_size = max_parameters_per_call
        self._gate = asyncio.Semaphore(max_concurrency)
        self._cache = TtlCache(cache_ttl_seconds, cache_max_entries, clock)
        self._sleep = sleep

    async def aclose(self) -> None:
        """Close the HTTP client when this source created it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # -- public port ---------------------------------------------------------

    async def point_series(
        self,
        location: Location,
        variable_ids: Sequence[str],
        period: Period,
        season: Season,
    ) -> dict[str, AnnualSeries]:
        ids = list(dict.fromkeys(variable_ids))
        found: dict[str, tuple[float | None, ...]] = {}
        missing: list[str] = []
        for variable_id in ids:
            hit = self._cache.get(self._point_key(location, variable_id, period, season))
            if hit is None:
                missing.append(variable_id)
            else:
                found[variable_id] = hit
        chunks = [
            missing[i : i + self._chunk_size] for i in range(0, len(missing), self._chunk_size)
        ]
        fetched = await asyncio.gather(
            *(self._fetch_point_chunk(location, chunk, period, season) for chunk in chunks)
        )
        for chunk_result in fetched:
            for variable_id, series in chunk_result.items():
                found[variable_id] = series
                self._cache.put(self._point_key(location, variable_id, period, season), series)
        return {
            variable_id: list(found[variable_id]) for variable_id in ids if variable_id in found
        }

    async def region_series(
        self,
        bbox: BBox,
        variable_id: str,
        period: Period,
        season: Season,
    ) -> list[GridSeries]:
        key = ("region", bbox.lat_min, bbox.lat_max, bbox.lon_min, bbox.lon_max)
        key += (variable_id, period.start_year, period.end_year, season)
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached)
        payload = await self._get_json(
            f"{self._base_url}/regional",
            {
                "parameters": variable_id,
                "community": COMMUNITY,
                "latitude-min": bbox.lat_min,
                "latitude-max": bbox.lat_max,
                "longitude-min": bbox.lon_min,
                "longitude-max": bbox.lon_max,
                "start": _request_start(period, season),
                "end": period.end_year,
                "format": "JSON",
            },
        )
        cells = _parse_region(payload, variable_id, _years_of(period), season)
        self._cache.put(key, tuple(cells))
        return cells

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _point_key(
        location: Location, variable_id: str, period: Period, season: Season
    ) -> tuple[Any, ...]:
        return (
            "point",
            location.lat,
            location.lon,
            variable_id,
            period.start_year,
            period.end_year,
            season,
        )

    async def _fetch_point_chunk(
        self, location: Location, chunk: list[str], period: Period, season: Season
    ) -> dict[str, tuple[float | None, ...]]:
        payload = await self._get_json(
            f"{self._base_url}/point",
            {
                "parameters": ",".join(chunk),
                "community": COMMUNITY,
                "longitude": location.lon,
                "latitude": location.lat,
                "start": _request_start(period, season),
                "end": period.end_year,
                "format": "JSON",
            },
        )
        parameters = _parameters_of(payload, "properties")
        return {
            variable_id: tuple(annual_values(monthly, _years_of(period), season))
            for variable_id in chunk
            if (monthly := parameters.get(variable_id)) is not None
        }

    async def _get_json(self, url: str, params: Mapping[str, Any]) -> Any:
        async with self._gate:
            response = await self._request_with_retries(url, params)
        try:
            return response.json()
        except ValueError:
            logger.warning("NASA POWER answer is not JSON (status %s)", response.status_code)
            raise UpstreamError(MSG_UNREADABLE) from None

    async def _request_with_retries(self, url: str, params: Mapping[str, Any]) -> httpx.Response:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": "trend-detective"}, timeout=DEFAULT_TIMEOUT
            )
        # An explicit timeout wins; otherwise the client's own setting applies.
        options: dict[str, Any] = {} if self._timeout is None else {"timeout": self._timeout}
        timed_out = False
        for attempt in range(self._max_retries + 1):
            if attempt:
                await self._sleep(self._backoff * 2 ** (attempt - 1))
            try:
                response = await self._client.get(url, params=params, **options)
            except httpx.TimeoutException:
                timed_out = True
                logger.warning("NASA POWER request timed out (attempt %d)", attempt + 1)
                continue
            except httpx.HTTPError as exc:
                timed_out = False
                logger.warning(
                    "NASA POWER request failed: %s (attempt %d)", type(exc).__name__, attempt + 1
                )
                continue
            timed_out = False
            if response.is_success:
                return response
            logger.warning(
                "NASA POWER answered status %d (attempt %d)", response.status_code, attempt + 1
            )
            if response.status_code not in RETRYABLE_STATUSES:
                break
        raise UpstreamTimeoutError(MSG_TIMEOUT) if timed_out else UpstreamError(MSG_UNAVAILABLE)


# --------------------------------------------------------------------------
# Parsing of POWER answers
# --------------------------------------------------------------------------


def _parameters_of(container: Any, key: str) -> Mapping[str, Mapping[str, Any]]:
    """`container[key]["parameter"]` as {parameter id: {month key: value}}, validated."""
    properties = container.get(key) if isinstance(container, dict) else None
    parameters = properties.get("parameter") if isinstance(properties, dict) else None
    if not isinstance(parameters, dict) or not all(
        isinstance(v, dict) for v in parameters.values()
    ):
        raise UpstreamError(MSG_UNREADABLE)
    return parameters


def _parse_region(
    payload: Any, variable_id: str, years: Sequence[int], season: Season
) -> list[GridSeries]:
    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list):
        raise UpstreamError(MSG_UNREADABLE)
    cells = [
        cell
        for feature in features
        if (cell := _parse_feature(feature, variable_id, years, season)) is not None
    ]
    return sorted(cells, key=lambda c: (c.lat, c.lon))


def _parse_feature(
    feature: Any, variable_id: str, years: Sequence[int], season: Season
) -> GridSeries | None:
    geometry = feature.get("geometry") if isinstance(feature, dict) else None
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if (
        not isinstance(coordinates, list)
        or len(coordinates) < 2
        or not all(isinstance(c, int | float) for c in coordinates[:2])
    ):
        raise UpstreamError(MSG_UNREADABLE)
    parameters = _parameters_of(feature, "properties")
    monthly = parameters.get(variable_id)
    if monthly is None:
        return None
    return GridSeries(
        lat=float(coordinates[1]),
        lon=float(coordinates[0]),
        values=tuple(annual_values(monthly, years, season)),
    )
