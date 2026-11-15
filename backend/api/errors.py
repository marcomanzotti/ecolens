"""The error envelope and the mapping from exceptions to it."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, cast, get_args

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.schemas import ERROR_STATUS, ApiError, ErrorCode, ErrorEnvelope
from trend_detective.errors import TrendDetectiveError

logger = logging.getLogger("api.errors")

INTERNAL_MESSAGE = "Something went wrong on our side. Please try again."
KNOWN_CODES: frozenset[str] = frozenset(get_args(ErrorCode))
HTTP_CLIENT_ERROR_MESSAGES: dict[int, str] = {
    400: "The request could not be read.",
    405: "This method is not allowed on this path.",
    413: "The request body is too large.",
    415: "The request body must be JSON.",
}

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorEnvelope} for status in sorted(set(ERROR_STATUS.values()))
}


class ApiException(Exception):
    """An error raised by the API layer itself, already expressed as an error code."""

    def __init__(self, code: ErrorCode, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.details = details


def error_response(
    code: ErrorCode,
    message: str,
    details: list[str] | None = None,
    *,
    status_code: int | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorEnvelope(error=ApiError(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code or ERROR_STATUS[code],
        content=body.model_dump(),
        headers=dict(headers) if headers else None,
    )


def internal_error_response() -> JSONResponse:
    return error_response("internal_error", INTERNAL_MESSAGE)


def engine_error_response(exc: TrendDetectiveError) -> JSONResponse:
    """Map an engine error to the envelope using its own code and message."""
    if exc.code not in KNOWN_CODES or exc.code == "internal_error":
        logger.error("Engine error without a public code: %r", exc, exc_info=exc)
        return internal_error_response()
    return error_response(cast(ErrorCode, exc.code), exc.message)


def http_error_response(exc: StarletteHTTPException) -> JSONResponse:
    """Errors raised by the framework (unknown path, wrong method, ...)."""
    if exc.status_code == 404:
        return error_response("not_found", "Not found.")
    if 400 <= exc.status_code < 500:
        message = HTTP_CLIENT_ERROR_MESSAGES.get(exc.status_code, "The request is not valid.")
        # No error code of the contract fits these: the HTTP status is kept as it is.
        return error_response(
            "validation_error", message, status_code=exc.status_code, headers=exc.headers
        )
    logger.error("HTTP error %s from the framework: %s", exc.status_code, exc.detail)
    return internal_error_response()


def validation_details(exc: RequestValidationError) -> list[str]:
    details = []
    for error in exc.errors():
        where = ".".join(str(part) for part in error["loc"] if part != "body")
        details.append(f"{where}: {error['msg']}" if where else str(error["msg"]))
    return details


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def _api_error(_: Request, exc: ApiException) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.details)

    @app.exception_handler(TrendDetectiveError)
    async def _engine_error(_: Request, exc: TrendDetectiveError) -> JSONResponse:
        return engine_error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            "validation_error", "The request is not valid.", validation_details(exc)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return http_error_response(exc)
