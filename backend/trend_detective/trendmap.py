"""Block B: the trend of one variable in every cell of the source grid.

One Mann-Kendall / Sen analysis per cell, Benjamini-Hochberg across all cells with data.
The map colour scale is symmetric: `max_abs_slope` is the largest |Sen slope| of any cell.
`opposite_twin` pairs the strongest significant rising cell with the strongest significant
falling cell ("strongest" = largest |Sen slope|, smaller p-value on a tie).

`stats` is used through the module so that tests can substitute its functions.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from trend_detective import catalog, stats
from trend_detective.errors import NoDataError
from trend_detective.models import (
    ALPHA,
    BBox,
    Correction,
    GridSpec,
    OppositeTwin,
    Period,
    Season,
    TrendMapCell,
    TrendMapResult,
    TrendMapSummary,
    TrendStats,
    Variable,
)
from trend_detective.ports import GridSeries
from trend_detective.series import valid_count
from trend_detective.wording import format_number, plural, with_unit

# MERRA-2 grid, used when the returned points do not show a step (a single row or column).
DEFAULT_LAT_STEP = 0.5
DEFAULT_LON_STEP = 0.625
STEP_DECIMALS = 4
EARTH_RADIUS_KM = 6371.0088


def _cell(point: GridSeries, trend: TrendStats | None, p_adjusted: float | None) -> TrendMapCell:
    if trend is None or p_adjusted is None:
        return TrendMapCell(
            lat=point.lat,
            lon=point.lon,
            n=valid_count(point.values),
            slope_per_decade=None,
            direction=None,
            p_value=None,
            p_adjusted=None,
            significant=False,
        )
    return TrendMapCell(
        lat=point.lat,
        lon=point.lon,
        n=trend.n,
        slope_per_decade=trend.sen.slope_per_decade,
        direction=trend.direction,
        p_value=trend.mann_kendall.p_value,
        p_adjusted=p_adjusted,
        significant=p_adjusted < ALPHA,
    )


def _step(values: set[float], default: float) -> float:
    ordered = sorted(values)
    gaps = [b - a for a, b in zip(ordered, ordered[1:], strict=False)]
    return round(min(gaps), STEP_DECIMALS) if gaps else default


def _grid_spec(points: Sequence[GridSeries]) -> GridSpec:
    lats, lons = {p.lat for p in points}, {p.lon for p in points}
    return GridSpec(
        lat_step=_step(lats, DEFAULT_LAT_STEP),
        lon_step=_step(lons, DEFAULT_LON_STEP),
        n_lat=len(lats),
        n_lon=len(lons),
    )


def distance_km(a: TrendMapCell, b: TrendMapCell) -> float:
    """Great-circle (haversine) distance between two cells, in kilometres."""
    lat_a, lat_b = math.radians(a.lat), math.radians(b.lat)
    d_lat, d_lon = lat_b - lat_a, math.radians(b.lon - a.lon)
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def _strength(cell: TrendMapCell) -> tuple[float, float]:
    """Sort key, smaller = stronger: large |slope| first, then small p-value."""
    return (-abs(cell.slope_per_decade or 0.0), cell.p_value or 0.0)


def _place(cell: TrendMapCell) -> str:
    return f"{cell.lat:g}, {cell.lon:g}"


def _twin(cells: Sequence[TrendMapCell], variable: Variable) -> OppositeTwin | None:
    rising = [c for c in cells if c.significant and c.direction == "up"]
    falling = [c for c in cells if c.significant and c.direction == "down"]
    if not rising or not falling:
        return None
    up, down = min(rising, key=_strength), min(falling, key=_strength)
    km = round(distance_km(up, down), 1)
    slopes = [
        with_unit(format_number(c.slope_per_decade or 0.0, signed=True), variable.unit)
        for c in (up, down)
    ]
    return OppositeTwin(
        up=up,
        down=down,
        distance_km=km,
        text=(
            f"Same variable, same years, opposite direction: {slopes[0]} per decade at "
            f"({_place(up)}) against {slopes[1]} per decade at ({_place(down)}), {km:g} km apart."
        ),
    )


def _trending(count: int, word: str) -> str:
    return f"{plural(count, 'cell')} {'is' if count == 1 else 'are'} {word} significantly"


def _summary(cells: Sequence[TrendMapCell]) -> TrendMapSummary:
    valid = [c for c in cells if c.slope_per_decade is not None]
    up = sum(1 for c in valid if c.significant and c.direction == "up")
    down = sum(1 for c in valid if c.significant and c.direction == "down")
    return TrendMapSummary(
        n_cells=len(cells),
        n_valid=len(valid),
        n_up_significant=up,
        n_down_significant=down,
        max_abs_slope=max(abs(c.slope_per_decade or 0.0) for c in valid),
        text=(
            f"Of {len(valid)} cells tested, {_trending(up, 'rising')} and "
            f"{_trending(down, 'falling')}."
        ),
    )


def build_trendmap(
    variable: Variable,
    bbox: BBox,
    period: Period,
    season: Season,
    grid: Sequence[GridSeries],
) -> TrendMapResult:
    """`grid` holds display-unit values, one per year of `period`, for each grid point."""
    years = catalog.period_years(period)
    points = sorted(grid, key=lambda p: (p.lat, p.lon))
    trends = [stats.compute_trend(years, p.values, variable.unit) for p in points]
    tested = [i for i, trend in enumerate(trends) if trend is not None]
    if not tested:
        raise NoDataError(
            f"There is no usable data for {variable.name.lower()} in this area and period."
        )
    adjusted = stats.benjamini_hochberg(
        [trend.mann_kendall.p_value for trend in trends if trend is not None]
    )
    by_index = dict(zip(tested, adjusted, strict=True))
    cells = [
        _cell(p, t, by_index.get(i)) for i, (p, t) in enumerate(zip(points, trends, strict=True))
    ]
    return TrendMapResult(
        variable=variable,
        bbox=bbox,
        period=period,
        season=season,
        grid=_grid_spec(points),
        correction=Correction(n_tests=len(tested)),
        cells=cells,
        summary=_summary(cells),
        opposite_twin=_twin(cells, variable),
    )
