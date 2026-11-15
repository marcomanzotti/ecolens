"""Standing caveats that go with every case and every witness comparison.

They describe how the data are made and what the tests can and cannot show; they never
say what the data show.
"""

from __future__ import annotations

from collections.abc import Sequence

from trend_detective import catalog
from trend_detective.models import Period, Season, Variable

STRAIGHT_LINE_NOTE = (
    "Only straight-line trends are tested. A change that speeds up, slows down or reverses "
    "is not captured."
)
AUTOCORRELATION_NOTE = (
    "Years that resemble the one before them make the tests over-confident. When the lag-1 "
    "autocorrelation is above 0.3 in absolute value, the verdict uses the Mann-Kendall "
    "p-value corrected for it (Hamed and Rao, 1998); the t-test p-value is never corrected."
)
OTHER_BLOCKS_NOTE = (
    "The line-up, the trend map and the emergence year use the Mann-Kendall p-value without "
    "the autocorrelation correction."
)
POWER_PROVIDER = "NASA POWER"
TEMPERATURE_INDEPENDENCE_NOTE = (
    "The witnesses are built differently (a reanalysis, a gridded record of stations and ships, "
    "single stations), but they may rely on some of the same observations. How independent "
    "they are has not been fully established, so agreement between them is not proof."
)
CAUSE_NOTE = "A trend shows that a value changed, not why it changed."
SEASON_NOTE = (
    "A season is the mean of its three monthly values; December to February belongs to the "
    "year of its January."
)
INDEPENDENCE_NOTE = (
    "The witnesses are all distributed by NASA POWER and may share inputs or methods. How "
    "independent they are has not been established, so agreement between them is not proof."
)
CORRELATION_NOTE = (
    "The correlation includes any trend the series share, so it can be high even when their "
    "year-to-year ups and downs do not match."
)
MERRA2_GRID_KM = 50
COARSE_GRID_KM = 100


def _grid_note(variable: Variable) -> str:
    product = variable.source.product
    km = MERRA2_GRID_KM if "MERRA" in product else COARSE_GRID_KM
    kind = {
        "reanalysis": "a global reanalysis (a weather model corrected with observations)",
        "satellite": "a satellite-based product",
        "derived": "a derived product",
        "station": "a weather station record",
        "station_grid": "a gridded analysis of station and ship records",
    }[variable.source.kind]
    return (
        f"Values come from {product}, {kind}, on a grid of roughly {km} km: they describe the "
        "area around the point, not the exact spot."
    )


def _unit_note(variable: Variable) -> list[str]:
    note = catalog.POWER_UNIT_NOTES.get(variable.id)
    return [] if note is None else [note]


def _late_start_note(variable: Variable, period: Period) -> list[str]:
    if variable.first_year <= period.start_year:
        return []
    return [
        f"Data for this variable only start in {variable.first_year}, so the trend covers a "
        "shorter period than the one requested."
    ]


def case_limitations(variable: Variable, period: Period, season: Season) -> list[str]:
    return [
        _grid_note(variable),
        STRAIGHT_LINE_NOTE,
        AUTOCORRELATION_NOTE,
        OTHER_BLOCKS_NOTE,
        CAUSE_NOTE,
        *_unit_note(variable),
        *([SEASON_NOTE] if season != "annual" else []),
        *_late_start_note(variable, period),
    ]


def _independence_note(members: Sequence[Variable]) -> str:
    only_power = all(member.source.provider == POWER_PROVIDER for member in members)
    return INDEPENDENCE_NOTE if only_power else TEMPERATURE_INDEPENDENCE_NOTE


def witness_limitations(
    members: Sequence[Variable],
    common_period: Period,
    season: Season,
    extra_notes: Sequence[str] = (),
) -> list[str]:
    """`members` are all the witnesses compared; `extra_notes` come with the external ones."""
    return [
        _independence_note(members),
        f"The witnesses are compared over their common period only "
        f"({common_period.start_year}–{common_period.end_year}), so these trends can differ "
        "from the ones over each record's full length.",
        CORRELATION_NOTE,
        STRAIGHT_LINE_NOTE,
        AUTOCORRELATION_NOTE,
        *extra_notes,
        *(note for member in members for note in _unit_note(member)),
        *([SEASON_NOTE] if season != "annual" else []),
    ]
