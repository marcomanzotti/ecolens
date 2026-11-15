"""Errors raised by the engine. The API layer maps each one to an error code."""

from __future__ import annotations


class TrendDetectiveError(Exception):
    """Base class. `message` is written in English and is safe to show to the user."""

    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnknownVariableError(TrendDetectiveError):
    """The variable id is not in the catalog, or has no witness group when one is needed."""

    code = "validation_error"


class NoDataError(TrendDetectiveError):
    """The request is valid but the source has no usable data for it."""

    code = "no_data"


class UpstreamError(TrendDetectiveError):
    """The data source answered with an error or with something unreadable."""

    code = "upstream_unavailable"


class UpstreamTimeoutError(TrendDetectiveError):
    """The data source did not answer in time."""

    code = "upstream_timeout"
