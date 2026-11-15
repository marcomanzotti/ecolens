"""FastAPI application: `uvicorn api.main:app`.

The routes are in routes.py, the envelope and error mapping in errors.py, the
shared resources in deps.py. Paths, models and the envelope are the contract of
docs/API_CONTRACT.md and must not change without updating it.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.assistant import build_assistant
from api.cache import TtlLruCache
from api.demos import DemoStore
from api.deps import lifespan
from api.errors import ERROR_RESPONSES, register_error_handlers
from api.middleware import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    UnhandledErrorMiddleware,
)
from api.ratelimit import SlidingWindowLimiter
from api.routes import router
from api.settings import Settings, get_settings
from trend_detective import __version__

HEAVY_PATHS = ("/trendmap", "/lineup")
CORS_MAX_AGE_SECONDS = 600


def add_middleware(app: FastAPI, settings: Settings) -> None:
    """Outermost first on the way in: CORS, security headers, error guard, rate limit, body."""
    # Starlette runs the middleware added last first, so they are added innermost first.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        overall=SlidingWindowLimiter(settings.rate_limit_per_minute),
        heavy=SlidingWindowLimiter(settings.rate_limit_heavy_per_minute),
        heavy_paths=HEAVY_PATHS,
        hop=settings.forwarded_ip_hop,
    )
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Retry-After"],
        max_age=CORS_MAX_AGE_SECONDS,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="EcoLens API",
        version=__version__,
        description="Finds and tests long-term trends in NASA Earth science variables.",
        responses=ERROR_RESPONSES,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.assistant = build_assistant(settings)
    app.state.demos = DemoStore.from_directory(settings.demo_dir)
    app.state.cache = TtlLruCache(settings.cache_max_entries, settings.cache_ttl_seconds)
    add_middleware(app, settings)
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
