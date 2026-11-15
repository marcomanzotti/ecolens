"""Dependencies of the routes, and the lifespan that owns the shared resources.

Tests replace `get_investigator` / `get_assistant` through
`app.dependency_overrides`; nothing here is imported from the engine at module
import time, so the API can be loaded before the engine is complete.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request

from api.assistant import Assistant
from api.cache import TtlLruCache
from api.demos import DemoStore
from api.settings import Settings
from trend_detective.ports import Investigator

logger = logging.getLogger("api.deps")

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
UPSTREAM_CONNECT_TIMEOUT_SECONDS = 10.0
ENGINE_MISSING_MESSAGE = (
    "The trend engine (trend_detective.service / trend_detective.sources.power) cannot be "
    "imported. Set USE_FIXTURES=1 to serve the fixtures instead."
)


async def build_investigator(settings: Settings, stack: AsyncExitStack) -> Investigator:
    """The fixture fallback when USE_FIXTURES=1, otherwise the real engine on NASA POWER."""
    if settings.use_fixtures:
        from api.fixture_investigator import FixtureInvestigator

        logger.warning("USE_FIXTURES is on: every investigation answers with the fixtures")
        return FixtureInvestigator(settings.fixtures_dir)
    try:
        from trend_detective.service import TrendInvestigator
        from trend_detective.sources.power import PowerSource
    except ImportError as exc:
        raise RuntimeError(ENGINE_MISSING_MESSAGE) from exc
    import httpx

    timeout = httpx.Timeout(
        settings.request_timeout_seconds, connect=UPSTREAM_CONNECT_TIMEOUT_SECONDS
    )
    client = await stack.enter_async_context(httpx.AsyncClient(timeout=timeout))
    return TrendInvestigator(PowerSource(client))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    if not logging.getLogger().handlers:
        logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)
    logging.getLogger("api").setLevel(settings.log_level)
    logger.info("CORS allows: %s", ", ".join(settings.frontend_origins))
    if "*" in settings.frontend_origins:
        logger.warning("FRONTEND_ORIGIN is '*': CORS is open to every origin")
    async with AsyncExitStack() as stack:
        app.state.investigator = await build_investigator(settings, stack)
        yield
        app.state.investigator = None


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_investigator(request: Request) -> Investigator:
    investigator = getattr(request.app.state, "investigator", None)
    if investigator is None:
        raise RuntimeError("The investigator is not ready: the application has not started.")
    return investigator


def get_assistant(request: Request) -> Assistant:
    return request.app.state.assistant


def get_demos(request: Request) -> DemoStore:
    return request.app.state.demos


def get_cache(request: Request) -> TtlLruCache:
    return request.app.state.cache


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
InvestigatorDep = Annotated[Investigator, Depends(get_investigator)]
AssistantDep = Annotated[Assistant, Depends(get_assistant)]
DemosDep = Annotated[DemoStore, Depends(get_demos)]
CacheDep = Annotated[TtlLruCache, Depends(get_cache)]
