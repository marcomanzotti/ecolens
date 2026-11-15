"""GISTEMP v4 grid -> annual anomalies and the emergence of significant trends, cell by cell.

Pure logic used by `build_earth_assets.py` (the CLI); tested in
`backend/tests/test_build_earth_assets.py`.

Significance rule (the same as Block B, `trend_detective/trendmap.py`): for each end year Y,
every cell is tested with `stats.compute_trend` on its annual means over the window
first_year -> Y (Mann-Kendall with tie correction, Sen slope for the direction; missing years are
dropped, at least MIN_YEARS_FOR_TREND valid years, constant series untested). The Mann-Kendall
p-values of all tested cells of that window are adjusted with `stats.benjamini_hochberg`, and a
cell is significant when p_adjusted < ALPHA. Direction: +1 when the Sen slope is positive, -1
when negative.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from trend_detective import stats
from trend_detective.models import ALPHA, MIN_YEARS_FOR_TREND

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

VARIABLE = "tempanomaly"
MONTHS_PER_YEAR = 12
MIN_VALID_MONTHS = 10
CENTI = 100
MILLI = 1000
MISSING_INT16 = 32767
INT16_LIMIT = 32766
TIME_ORIGIN_PREFIX = "days since "


@dataclass(frozen=True)
class MonthlyGrid:
    """Monthly anomalies in K, NaN where missing. Rows south -> north, columns west -> east."""

    lat: NDArray[np.float64]
    lon: NDArray[np.float64]
    year: NDArray[np.int64]
    month: NDArray[np.int64]
    values: NDArray[np.float64]  # (time, lat, lon)


@dataclass(frozen=True)
class EmergenceGrid:
    """Per end year Y of the window first_year -> Y, per cell."""

    years: tuple[int, ...]
    direction: NDArray[np.int8]  # -1 / 0 / +1, significant cells only
    tested: NDArray[np.bool_]  # cell had a trend test in that window
    slope_per_decade: NDArray[np.float64]  # Sen slope, NaN when untested
    p_adjusted: NDArray[np.float64]  # Benjamini-Hochberg, NaN when untested
    n_tests: tuple[int, ...]


def _decode_time(units: str, days: NDArray[np.float64]) -> tuple[list[int], list[int]]:
    from datetime import date, timedelta

    if not units.startswith(TIME_ORIGIN_PREFIX):
        raise ValueError(f"unexpected time units: {units!r}")
    origin = date.fromisoformat(units.removeprefix(TIME_ORIGIN_PREFIX).split()[0])
    dates = [origin + timedelta(days=float(d)) for d in days]
    return [d.year for d in dates], [d.month for d in dates]


def _text(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def read_gistemp(path: Path) -> MonthlyGrid:
    """Reads an (uncompressed) GISTEMP NetCDF3 file. Values are scaled to K; fill -> NaN."""
    import numpy as np
    from scipy.io import netcdf_file

    with netcdf_file(path, "r", mmap=False) as nc:
        var = nc.variables[VARIABLE]
        raw = np.array(var.data, dtype=np.float64)
        fill = float(getattr(var, "_FillValue", MISSING_INT16))
        scale = float(getattr(var, "scale_factor", 1.0))
        offset = float(getattr(var, "add_offset", 0.0))
        lat = np.array(nc.variables["lat"].data, dtype=np.float64)
        lon = np.array(nc.variables["lon"].data, dtype=np.float64)
        time = nc.variables["time"]
        years, months = _decode_time(_text(time.units), np.array(time.data, dtype=np.float64))
    values = np.where(raw == fill, np.nan, raw * scale + offset)
    lat_order, lon_order = np.argsort(lat), np.argsort(lon)
    return MonthlyGrid(
        lat=lat[lat_order],
        lon=lon[lon_order],
        year=np.array(years, dtype=np.int64),
        month=np.array(months, dtype=np.int64),
        values=values[:, lat_order][:, :, lon_order],
    )


def file_created(path: Path) -> str | None:
    """Creation date from the file's `history` attribute ("Created 2026-11-10 08:55:39 ...")."""
    import re

    from scipy.io import netcdf_file

    with netcdf_file(path, "r", mmap=False) as nc:
        history = _text(getattr(nc, "history", b""))
    match = re.search(r"Created (\d{4}-\d{2}-\d{2})", history)
    return match.group(1) if match else None


def complete_years(grid: MonthlyGrid) -> list[int]:
    """Years for which the file holds all twelve monthly time steps."""
    import numpy as np

    years, counts = np.unique(grid.year, return_counts=True)
    return [int(y) for y, c in zip(years, counts, strict=True) if c == MONTHS_PER_YEAR]


def annual_means(
    grid: MonthlyGrid, first_year: int, last_year: int | None = None
) -> tuple[tuple[int, ...], NDArray[np.float64]]:
    """Annual mean per cell; NaN when fewer than MIN_VALID_MONTHS months are valid.

    `last_year` defaults to the last complete year of the file. A year the file does not hold
    in full (e.g. the current one) is refused.
    """
    import numpy as np

    full = complete_years(grid)
    end = max(full) if last_year is None else last_year
    years = tuple(range(first_year, end + 1))
    missing = [y for y in years if y not in full]
    if missing:
        raise ValueError(f"years not complete in the file: {missing}")
    out = np.full((len(years), grid.lat.size, grid.lon.size), np.nan)
    for k, year in enumerate(years):
        block = grid.values[grid.year == year]
        valid = np.isfinite(block).sum(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells: masked just below
            mean = np.nanmean(block, axis=0)
        out[k] = np.where(valid >= MIN_VALID_MONTHS, mean, np.nan)
    return years, out


def _test_window(
    args: tuple[Sequence[int], NDArray[np.float64], str],
) -> list[tuple[float, float] | None]:
    """(Mann-Kendall p, Sen slope per decade) per cell of a flattened window, None if untested."""
    import numpy as np

    years, block, unit = args
    out: list[tuple[float, float] | None] = []
    for column in block.T:
        values = [None if not np.isfinite(v) else float(v) for v in column]
        trend = stats.compute_trend(years, values, unit)
        out.append(
            None if trend is None else (trend.mann_kendall.p_value, trend.sen.slope_per_decade)
        )
    return out


def compute_emergence(
    years: Sequence[int], annual: NDArray[np.float64], workers: int = 1, unit: str = "K"
) -> EmergenceGrid:
    """Expanding-window trend test per cell, BH across all tested cells of each window."""
    import numpy as np

    n_years, n_lat, n_lon = annual.shape
    flat = annual.reshape(n_years, n_lat * n_lon)
    jobs = [(list(years[: k + 1]), flat[: k + 1], unit) for k in range(n_years)]
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_test_window, jobs))
    else:
        results = [_test_window(job) for job in jobs]

    shape = (n_years, n_lat * n_lon)
    direction = np.zeros(shape, dtype=np.int8)
    tested = np.zeros(shape, dtype=bool)
    slope = np.full(shape, np.nan)
    p_adj = np.full(shape, np.nan)
    n_tests: list[int] = []
    for k, cells in enumerate(results):
        index = [i for i, c in enumerate(cells) if c is not None]
        n_tests.append(len(index))
        if not index:
            continue
        p_raw = [cells[i][0] for i in index]  # type: ignore[index]
        adjusted = np.array(stats.benjamini_hochberg(p_raw))
        sen = np.array([cells[i][1] for i in index])  # type: ignore[index]
        tested[k, index] = True
        slope[k, index] = sen
        p_adj[k, index] = adjusted
        significant = adjusted < ALPHA
        direction[k, index] = np.where(significant, np.sign(sen), 0).astype(np.int8)

    def grid(a: NDArray) -> NDArray:  # type: ignore[type-arg]
        return a.reshape(n_years, n_lat, n_lon)

    return EmergenceGrid(
        years=tuple(years),
        direction=grid(direction),
        tested=grid(tested),
        slope_per_decade=grid(slope),
        p_adjusted=grid(p_adj),
        n_tests=tuple(n_tests),
    )


def area_weights(lat: NDArray[np.float64], n_lon: int) -> NDArray[np.float64]:
    """cos(latitude) of each cell centre, broadcast to (lat, lon)."""
    import numpy as np

    return np.repeat(np.cos(np.radians(lat))[:, None], n_lon, axis=1)


def surface_shares(
    emergence: EmergenceGrid,
    lat: NDArray[np.float64],
    labels: tuple[str, str] = ("warming", "cooling"),
) -> list[dict[str, float | int]]:
    """Per end year: area-weighted share (%) of the tested surface with a significant rising
    (labels[0], e.g. warming) or falling (labels[1]) trend. Years with no tested cell have share 0
    and `tested_cells` 0."""
    rise, fall = labels
    weights = area_weights(lat, emergence.direction.shape[2])
    rows: list[dict[str, float | int]] = []
    for k, year in enumerate(emergence.years):
        tested = emergence.tested[k]
        total = float(weights[tested].sum())
        up = emergence.direction[k] > 0
        down = emergence.direction[k] < 0
        rows.append(
            {
                "year": year,
                "tested_cells": int(tested.sum()),
                f"{rise}_cells": int(up.sum()),
                f"{fall}_cells": int(down.sum()),
                f"{rise}_pct": round(100 * float(weights[up].sum()) / total, 2) if total else 0.0,
                f"{fall}_pct": round(100 * float(weights[down].sum()) / total, 2) if total else 0.0,
            }
        )
    return rows


def to_int16(values: NDArray[np.float64], factor: int) -> NDArray[np.int16]:
    """values * factor rounded, clipped to +-INT16_LIMIT; NaN -> MISSING_INT16."""
    import numpy as np

    scaled = np.clip(np.round(np.nan_to_num(values, nan=0.0) * factor), -INT16_LIMIT, INT16_LIMIT)
    return np.where(np.isfinite(values), scaled, MISSING_INT16).astype("<i2")


def encode_anomaly(annual: NDArray[np.float64], factor: int = CENTI) -> bytes:
    return to_int16(annual, factor).tobytes()


def encode_emerged(emergence: EmergenceGrid) -> bytes:
    return emergence.direction.astype("i1").tobytes()


def encode_rate(emergence: EmergenceGrid, factor: int = MILLI) -> bytes:
    """Sen slope at the end of the series (Int16, unit/factor per decade; milli-K for GISTEMP)
    then its direction (Int8)."""
    slope = to_int16(emergence.slope_per_decade[-1], factor).tobytes()
    return slope + emergence.direction[-1].astype("i1").tobytes()


def decode_int16(data: bytes, shape: tuple[int, ...], factor: int) -> NDArray[np.float64]:
    import numpy as np

    raw = np.frombuffer(data, dtype="<i2").reshape(shape).astype(np.float64)
    return np.where(raw == MISSING_INT16, np.nan, raw / factor)


def hand_check(grid: MonthlyGrid, lat: float, lon: float, year: int) -> float | None:
    """Annual mean of one cell recomputed the slow way, for the build log and the tests."""
    i = int(abs(grid.lat - lat).argmin())
    j = int(abs(grid.lon - lon).argmin())
    months = [float(v) for v, y in zip(grid.values[:, i, j], grid.year, strict=True) if y == year]
    valid = [v for v in months if not math.isnan(v)]
    return sum(valid) / len(valid) if len(valid) >= MIN_VALID_MONTHS else None


RULE_TEXT = (
    "For each end year Y, every cell is tested on its annual mean anomalies over the window "
    "first_year->Y with the engine's compute_trend (Mann-Kendall with tie correction; Sen slope "
    f"gives the direction; missing years dropped; at least {MIN_YEARS_FOR_TREND} valid years; "
    "constant series untested). Benjamini-Hochberg is applied to the Mann-Kendall p-values of all "
    f"tested cells of that window; a cell is significant when p_adjusted < {ALPHA}. Same rule as "
    "the trend map (Block B). No correction for autocorrelation."
)
