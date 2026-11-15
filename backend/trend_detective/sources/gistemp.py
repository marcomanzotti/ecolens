"""NASA GISTEMP v4 annual temperature anomalies, read from a compact grid inside the package.

The grid is built once from the 1200 km-smoothed monthly file by scripts/build_witness_data.py
(never downloaded at run time). It holds, for 1981-2025, the annual mean anomaly in degrees
relative to 1951-1980 on GISTEMP's 2 degree grid (90 rows from south to north, 180 columns from
the antimeridian eastwards), as int16 hundredths of a degree. Missing = 32767.

A GISTEMP cell is 2 degrees wide and spreads station and ship data up to 1200 km, so it describes
a far larger area than a 0.5 degree reanalysis cell.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

CELL_DEG = 2.0
N_ROWS = 90
N_COLS = 180
SCALE = 100  # stored hundredths of a degree
MISSING = 32767
DEFAULT_GRID_PATH = Path(__file__).resolve().parent.parent / "data" / "gistemp_annual.npz"


@dataclass(frozen=True)
class GistempGrid:
    """Annual anomalies in degrees C (or K), NaN where missing: shape (years, 90, 180)."""

    years: tuple[int, ...]
    anomaly: NDArray[np.float64]


def cell_index(lat: float, lon: float) -> tuple[int, int]:
    """Row and column of the 2 degree cell holding a point. The poles belong to the last row
    on their side, and +180 and -180 are the same meridian (column 0)."""
    row = min(max(math.floor((lat + 90.0) / CELL_DEG), 0), N_ROWS - 1)
    col = math.floor(((lon + 180.0) % 360.0) / CELL_DEG) % N_COLS
    return row, col


def cell_centre(row: int, col: int) -> tuple[float, float]:
    return -90.0 + (row + 0.5) * CELL_DEG, -180.0 + (col + 0.5) * CELL_DEG


def write_grid(path: Path, years: Sequence[int], annual: NDArray[np.float64]) -> None:
    """Store (years, 90, 180) anomalies as compressed int16 hundredths."""
    import numpy as np

    if annual.shape[1:] != (N_ROWS, N_COLS):
        raise ValueError(f"annual grid must have shape (years, {N_ROWS}, {N_COLS})")
    if annual.shape[0] != len(years):
        raise ValueError("years must have one entry per time step")
    finite = np.isfinite(annual)
    scaled = np.where(finite, np.round(np.nan_to_num(annual) * SCALE), MISSING)
    if np.abs(scaled[finite]).max(initial=0) >= MISSING:
        raise ValueError("anomaly too large for int16 hundredths")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path, years=np.asarray(years, dtype="<i2"), anomaly_centi=scaled.astype("<i2")
    )


@lru_cache(maxsize=2)
def load_grid(path: Path | None = None) -> GistempGrid:
    """Read the grid (cached). FileNotFoundError when the file is absent."""
    import numpy as np

    with np.load(path or DEFAULT_GRID_PATH, allow_pickle=False) as data:
        years = tuple(int(y) for y in data["years"])
        raw = data["anomaly_centi"].astype(np.float64)
    return GistempGrid(years=years, anomaly=np.where(raw == MISSING, np.nan, raw / SCALE))


def cell_series(
    grid: GistempGrid, lat: float, lon: float, years: Sequence[int]
) -> list[float | None] | None:
    """Anomaly of the cell holding the point, one value per requested year (None when missing or
    outside the grid). None instead of a list when the cell has no data in any year."""
    import numpy as np

    row, col = cell_index(lat, lon)
    column = grid.anomaly[:, row, col]
    if not np.isfinite(column).any():
        return None
    by_year = dict(zip(grid.years, column, strict=True))
    return [
        float(v) if (v := by_year.get(year)) is not None and math.isfinite(v) else None
        for year in years
    ]
