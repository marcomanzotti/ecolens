"""Request bodies and the response envelope of the HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trend_detective.models import (
    MAX_QUESTION_LENGTH,
    BBox,
    Location,
    Period,
    Season,
    ThemeId,
)

ErrorCode = Literal[
    "validation_error",
    "not_found",
    "no_data",
    "rate_limited",
    "upstream_unavailable",
    "upstream_timeout",
    "assistant_unavailable",
    "internal_error",
]

# HTTP status used for each error code.
ERROR_STATUS: dict[str, int] = {
    "validation_error": 422,
    "not_found": 404,
    "no_data": 422,
    "rate_limited": 429,
    "upstream_unavailable": 502,
    "upstream_timeout": 504,
    "assistant_unavailable": 503,
    "internal_error": 500,
}


class Request(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ApiError(BaseModel):
    code: ErrorCode
    message: str = Field(description="Safe to show to the user, in English")
    details: list[str] | None = None


class Envelope[T](BaseModel):
    """Every response, success or failure, has this shape."""

    success: bool
    data: T | None = None
    error: ApiError | None = None


class ErrorEnvelope(BaseModel):
    success: Literal[False] = False
    data: None = None
    error: ApiError


class CaseRequest(Request):
    location: Location
    variable_id: str = Field(min_length=1, max_length=40)
    period: Period = Period()
    season: Season = "annual"


class LineupRequest(Request):
    location: Location
    themes: list[ThemeId] | None = Field(
        default=None, description="Restrict to these themes; omit for the whole catalog"
    )
    variable_ids: list[str] | None = Field(
        default=None, max_length=40, description="Restrict to these variables; wins over `themes`"
    )
    period: Period = Period()
    season: Season = "annual"


class WitnessesRequest(Request):
    location: Location
    variable_id: str = Field(
        min_length=1,
        max_length=40,
        description="Any variable that has a witness_group; its whole group is compared",
    )
    period: Period = Period()
    season: Season = "annual"


class TrendMapRequest(Request):
    variable_id: str = Field(min_length=1, max_length=40)
    bbox: BBox
    period: Period = Period()
    season: Season = "annual"


class AskRequest(Request):
    question: str = Field(min_length=3, max_length=MAX_QUESTION_LENGTH)
