"""Small text helpers shared by the verdict and the other plain-English summaries."""

from __future__ import annotations

import math

from trend_detective import catalog
from trend_detective.models import Location, Period, Season

SIGNIFICANT_FIGURES = 3
MAX_DECIMALS = 8
# Units that carry no useful label when written after a number.
DIMENSIONLESS_UNITS = frozenset({"0–1", "unitless", "index"})
P_VALUE_FLOOR = 0.001


def format_number(value: float, *, signed: bool = False) -> str:
    """Three significant figures, fixed notation, optional explicit sign."""
    if value == 0 or not math.isfinite(value):
        return "0" if value == 0 else str(value)
    magnitude = math.floor(math.log10(abs(value)))
    decimals = min(MAX_DECIMALS, max(0, SIGNIFICANT_FIGURES - 1 - magnitude))
    return f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}"


def with_unit(number: str, unit: str) -> str:
    return number if unit in DIMENSIONLESS_UNITS else f"{number} {unit}"


def format_p(p_value: float) -> str:
    if p_value < P_VALUE_FLOOR:
        return f"p < {P_VALUE_FLOOR:g}"
    return f"p = {p_value:.2g}"


def lowercase_first(text: str) -> str:
    """'Air temperature' -> 'air temperature', but 'UV index' stays as it is."""
    if len(text) > 1 and text[1].isupper():
        return text
    return text[:1].lower() + text[1:]


def coordinates(location: Location) -> str:
    ns = "N" if location.lat >= 0 else "S"
    ew = "E" if location.lon >= 0 else "W"
    return f"{abs(location.lat):.2f}°{ns}, {abs(location.lon):.2f}°{ew}"


def place_name(location: Location) -> str:
    """The label the user gave, or the coordinates when there is none."""
    label = (location.label or "").strip()
    return label or coordinates(location)


def period_text(period: Period, season: Season) -> str:
    years = f"{period.start_year}–{period.end_year}"
    if season == "annual":
        return years
    return f"{years} ({catalog.SEASON_LABELS[season]})"


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    return f"{count} {singular if count == 1 else plural_form or singular + 's'}"
