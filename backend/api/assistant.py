"""The assistant behind /ask.

Stage 5 plugs a Gemini implementation in `build_assistant`. Until then the only
implementation answers `assistant_unavailable`, with or without a key configured.
"""

from __future__ import annotations

from typing import Protocol

from api.errors import ApiException
from api.settings import Settings
from trend_detective.models import AskResult

NOT_CONFIGURED_MESSAGE = "The assistant is not configured on this server."
NOT_ENABLED_MESSAGE = "The assistant is not enabled yet."


class Assistant(Protocol):
    """Interprets a free-text question. Never produces numbers or verdicts."""

    @property
    def available(self) -> bool:
        """Whether /ask can answer; reported by /health as `assistant_available`."""
        ...

    async def ask(self, question: str) -> AskResult:
        """Raises ApiException('assistant_unavailable', ...) when it cannot answer."""
        ...


class UnavailableAssistant:
    """Refuses every question with `assistant_unavailable`."""

    available = False

    def __init__(self, message: str) -> None:
        self._message = message

    async def ask(self, question: str) -> AskResult:
        raise ApiException("assistant_unavailable", self._message)


def build_assistant(settings: Settings) -> Assistant:
    if not settings.gemini_key_present:
        return UnavailableAssistant(NOT_CONFIGURED_MESSAGE)
    # Stage 5: return the Gemini-backed assistant here.
    return UnavailableAssistant(NOT_ENABLED_MESSAGE)
