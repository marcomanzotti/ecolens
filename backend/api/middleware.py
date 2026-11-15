"""ASGI middleware: last-resort error guard, security headers, rate limit, body size limit.

Written as plain ASGI classes (no BaseHTTPMiddleware) so that each one can answer
with the error envelope without buffering the responses of the routes.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.errors import error_response, internal_error_response
from api.ratelimit import SlidingWindowLimiter
from api.settings import ForwardedHop

logger = logging.getLogger("api.middleware")

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
MAX_CLIENT_KEY_LENGTH = 64
RATE_LIMIT_MESSAGE = "Too many requests. Please wait a moment and try again."
BODY_TOO_LARGE_MESSAGE = "The request body is too large."


class UnhandledErrorMiddleware:
    """Turns any exception no handler caught into `internal_error`, logging the stack trace."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            logger.exception("Unhandled error on %s %s", scope.get("method"), scope.get("path"))
            if started:
                raise
            await internal_error_response()(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)


def client_key(scope: Scope, hop: ForwardedHop) -> str:
    """The client address: the chosen hop of X-Forwarded-For, else the socket peer."""
    forwarded = Headers(scope=scope).get("x-forwarded-for", "")
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    if hops:
        address = hops[0] if hop == "first" else hops[-1]
    else:
        client = scope.get("client")
        address = client[0] if client else "unknown"
    return address[:MAX_CLIENT_KEY_LENGTH]


class RateLimitMiddleware:
    """Counts every request per client, and the paths in `heavy_paths` on a tighter limit too."""

    def __init__(
        self,
        app: ASGIApp,
        overall: SlidingWindowLimiter,
        heavy: SlidingWindowLimiter,
        heavy_paths: Iterable[str],
        exempt_paths: Iterable[str] = ("/health",),
        hop: ForwardedHop = "last",
    ) -> None:
        self.app = app
        self._overall = overall
        self._heavy = heavy
        self._heavy_paths = frozenset(heavy_paths)
        self._exempt_paths = frozenset(exempt_paths)
        self._hop = hop

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self._exempt_paths:
            await self.app(scope, receive, send)
            return
        key = client_key(scope, self._hop)
        limiters = [self._overall]
        if scope["path"].rstrip("/") in self._heavy_paths and scope["method"] == "POST":
            limiters.append(self._heavy)
        waits = [wait for limiter in limiters if (wait := limiter.retry_after(key)) is not None]
        if waits:
            response = error_response(
                "rate_limited", RATE_LIMIT_MESSAGE, headers={"Retry-After": str(max(waits))}
            )
            await response(scope, receive, send)
            return
        for limiter in limiters:
            limiter.record(key)
        await self.app(scope, receive, send)


class BodySizeLimitMiddleware:
    """Rejects request bodies above `max_bytes`, declared or streamed."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in BODY_METHODS:
            await self.app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            await self._reject(scope, receive, send)
            return
        messages = await self._read_body(receive)
        if messages is None:
            await self._reject(scope, receive, send)
            return
        pending = iter(messages)

        async def replay() -> Message:
            buffered = next(pending, None)
            return buffered if buffered is not None else await receive()

        await self.app(scope, replay, send)

    async def _read_body(self, receive: Receive) -> list[Message] | None:
        """Read the whole body (it is small by definition); None when it is too large."""
        messages: list[Message] = []
        size = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                return messages
            size += len(message.get("body", b""))
            if size > self._max_bytes:
                return None
            if not message.get("more_body", False):
                return messages

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = error_response("validation_error", BODY_TOO_LARGE_MESSAGE, status_code=413)
        await response(scope, receive, send)
