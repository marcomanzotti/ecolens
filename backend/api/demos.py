"""Saved investigations served by /demo, loaded once from JSON files at startup."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from trend_detective.models import DemoCase, DemoList, DemoSummary

logger = logging.getLogger("api.demos")

DEMO_ID_PATTERN = re.compile(r"[a-z0-9-]{1,64}")


def is_valid_demo_id(demo_id: str) -> bool:
    return DEMO_ID_PATTERN.fullmatch(demo_id) is not None


def _summary(demo: DemoCase) -> DemoSummary:
    location = demo.case.location
    place_name = location.label or f"{location.lat:.2f}, {location.lon:.2f}"
    return DemoSummary(
        id=demo.id,
        title=demo.title,
        blurb=demo.blurb,
        place_name=place_name,
        variable_id=demo.case.variable.id,
    )


def _load_file(path: Path) -> DemoCase | None:
    """Parse one demo file; None (and a log line) when it cannot be served."""
    from pydantic import ValidationError

    if not is_valid_demo_id(path.stem):
        logger.warning("Demo file %s skipped: the file name is not a valid demo id", path.name)
        return None
    try:
        demo = DemoCase.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        problems = exc.error_count() if isinstance(exc, ValidationError) else exc
        logger.warning("Demo file %s skipped: not a valid demo case (%s)", path.name, problems)
        return None
    if demo.id != path.stem:
        logger.warning("Demo file %s skipped: its id is '%s'", path.name, demo.id)
        return None
    return demo


class DemoStore:
    """Read-only set of demo cases, keyed by id."""

    def __init__(self, demos: dict[str, DemoCase]) -> None:
        self._demos = dict(demos)
        self._list = DemoList(demos=[_summary(demo) for demo in self._demos.values()])

    @classmethod
    def from_directory(cls, directory: Path) -> DemoStore:
        if not directory.is_dir():
            logger.warning("Demo directory %s does not exist: no demo case is served", directory)
            return cls({})
        loaded = (_load_file(path) for path in sorted(directory.glob("*.json")))
        demos = {demo.id: demo for demo in loaded if demo is not None}
        logger.info("Loaded %d demo case(s)", len(demos))
        return cls(demos)

    def list(self) -> DemoList:
        return self._list

    def get(self, demo_id: str) -> DemoCase | None:
        """The demo with this id; None for an unknown or malformed id (never touches the disk)."""
        if not is_valid_demo_id(demo_id):
            return None
        return self._demos.get(demo_id)
