"""The routes of the contract (docs/API_CONTRACT.md). Paths and models must not change."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter

from api.cache import TtlLruCache, request_key
from api.deps import AssistantDep, CacheDep, DemosDep, InvestigatorDep, SettingsDep
from api.errors import ApiException
from api.schemas import (
    AskRequest,
    CaseRequest,
    Envelope,
    LineupRequest,
    Request,
    TrendMapRequest,
    WitnessesRequest,
)
from trend_detective import __version__
from trend_detective.errors import UpstreamTimeoutError
from trend_detective.models import (
    AskResult,
    CaseResult,
    Catalog,
    DemoCase,
    DemoList,
    Health,
    LineupResult,
    PlacesResult,
    TrendMapResult,
    WitnessesResult,
)

TIMEOUT_MESSAGE = "The data source took too long to answer. Please try again."

router = APIRouter()


def ok[T](data: T) -> Envelope[T]:
    return Envelope(success=True, data=data)


async def investigate[T](
    route: str,
    body: Request,
    cache: TtlLruCache,
    timeout: float,
    run: Callable[[], Awaitable[T]],
) -> T:
    """Answer from the cache, or run the investigation under the request timeout."""
    import asyncio

    key = request_key(route, body)
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        async with asyncio.timeout(timeout if timeout > 0 else None):
            result = await run()
    except TimeoutError as exc:
        raise UpstreamTimeoutError(TIMEOUT_MESSAGE) from exc
    cache.put(key, result)
    return result


@router.get("/health", response_model=Envelope[Health], tags=["meta"])
async def health(assistant: AssistantDep) -> Envelope[Health]:
    return ok(Health(version=__version__, assistant_available=assistant.available))


@router.get("/catalog", response_model=Envelope[Catalog], tags=["reference"])
async def catalog(investigator: InvestigatorDep) -> Envelope[Catalog]:
    return ok(investigator.catalog())


@router.get("/places", response_model=Envelope[PlacesResult], tags=["reference"])
async def places(investigator: InvestigatorDep) -> Envelope[PlacesResult]:
    return ok(investigator.places())


@router.post("/case", response_model=Envelope[CaseResult], tags=["investigation"])
async def case(
    body: CaseRequest, investigator: InvestigatorDep, cache: CacheDep, settings: SettingsDep
) -> Envelope[CaseResult]:
    result = await investigate(
        "case",
        body,
        cache,
        settings.request_timeout_seconds,
        lambda: investigator.case(body.location, body.variable_id, body.period, body.season),
    )
    return ok(result)


@router.post("/lineup", response_model=Envelope[LineupResult], tags=["investigation"])
async def lineup(
    body: LineupRequest, investigator: InvestigatorDep, cache: CacheDep, settings: SettingsDep
) -> Envelope[LineupResult]:
    result = await investigate(
        "lineup",
        body,
        cache,
        settings.request_timeout_seconds,
        lambda: investigator.lineup(
            body.location,
            body.period,
            body.season,
            themes=body.themes,
            variable_ids=body.variable_ids,
        ),
    )
    return ok(result)


@router.post("/witnesses", response_model=Envelope[WitnessesResult], tags=["investigation"])
async def witnesses(
    body: WitnessesRequest, investigator: InvestigatorDep, cache: CacheDep, settings: SettingsDep
) -> Envelope[WitnessesResult]:
    result = await investigate(
        "witnesses",
        body,
        cache,
        settings.request_timeout_seconds,
        lambda: investigator.witnesses(body.location, body.variable_id, body.period, body.season),
    )
    return ok(result)


@router.post("/trendmap", response_model=Envelope[TrendMapResult], tags=["investigation"])
async def trendmap(
    body: TrendMapRequest, investigator: InvestigatorDep, cache: CacheDep, settings: SettingsDep
) -> Envelope[TrendMapResult]:
    result = await investigate(
        "trendmap",
        body,
        cache,
        settings.request_timeout_seconds,
        lambda: investigator.trendmap(body.variable_id, body.bbox, body.period, body.season),
    )
    return ok(result)


@router.post("/ask", response_model=Envelope[AskResult], tags=["assistant"])
async def ask(body: AskRequest, assistant: AssistantDep) -> Envelope[AskResult]:
    return ok(await assistant.ask(body.question))


@router.get("/demo", response_model=Envelope[DemoList], tags=["demo"])
async def demo_list(demos: DemosDep) -> Envelope[DemoList]:
    return ok(demos.list())


@router.get("/demo/{demo_id}", response_model=Envelope[DemoCase], tags=["demo"])
async def demo(demo_id: str, demos: DemosDep) -> Envelope[DemoCase]:
    found = demos.get(demo_id)
    if found is None:
        raise ApiException("not_found", "There is no demo case with this id.")
    return ok(found)
