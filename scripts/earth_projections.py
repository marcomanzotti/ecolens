"""CMIP6 climate model projections -> 2041-2060 change vs 1995-2014 on the 2 degree GISTEMP grid.

Pure logic used by `earth_projections_build.py` (download and CLI); tested in
`backend/tests/test_build_earth_projections.py`.

Method (IPCC AR6 style, simple approach):
- one member per model (r1i1p1f1 if complete, else the first complete member), only models
  that publish `historical`, `ssp245` and `ssp585` for the variable;
- per model: mean of the annual means over each 20-year period, bilinear regridding of the
  model's own grid to the 2 degree grid (cells next to a missing value stay missing);
- change = future - baseline (K for `tas`; % of the baseline for the others, masked where the
  baseline is close to zero);
- across models per cell: median, 10th and 90th percentile, model count, and sign agreement =
  share of models whose change has the sign of the median ("robust" if >= 80%).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray

EXPERIMENTS = ("historical", "ssp245", "ssp585")
SCENARIOS = ("ssp245", "ssp585")
BASELINE = (1995, 2014)
FUTURE = (2041, 2060)
PREFERRED_MEMBER = "r1i1p1f1"
TABLES = {
    "tas": "Amon",
    "pr": "Amon",
    "hurs": "Amon",
    "rsds": "Amon",
    "sfcWind": "Amon",
    "clt": "Amon",
    "mrsos": "Lmon",
    "lai": "Lmon",
}
ABSOLUTE = frozenset({"tas"})
# Baselines below these values (native units) are too small for a meaningful % change.
PERCENT_FLOOR = {
    "pr": 0.1 / 86400,  # 0.1 mm/day in kg m-2 s-1
    "mrsos": 1.0,  # kg m-2
    "lai": 0.1,
    "hurs": 1.0,  # %
    "rsds": 1.0,  # W m-2
    "sfcWind": 0.1,  # m s-1
    "clt": 1.0,  # %
}
MIN_MODELS = 3
ROBUST_AGREEMENT = 0.8
GRID_STEP = 2.0
I16_MISSING = 32767
U8_MISSING = 255
MONTHS = 12
DAYS_PER_YEAR = {
    "noleap": 365.0,
    "365_day": 365.0,
    "360_day": 360.0,
    "all_leap": 366.0,
    "366_day": 366.0,
    "julian": 365.25,
}
GREGORIAN_YEAR = 365.2425
SECONDS_PER = {"days": 1.0, "hours": 1 / 24, "minutes": 1 / 1440, "seconds": 1 / 86400}
_UNITS = re.compile(r"(\w+) since (\d+)-(\d+)-(\d+)")


@dataclass(frozen=True)
class Selection:
    """One model member with a store for each experiment."""

    source_id: str
    institution_id: str
    member_id: str
    grid_label: str
    zstores: Mapping[str, str]
    versions: Mapping[str, str]


def _member_key(member: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", member))


def select_models(
    rows: Iterable[Mapping[str, str]], variable: str, preferred: Iterable[str], max_models: int
) -> list[Selection]:
    """Picks, in the preferred order, models with all three experiments for one member."""
    table = TABLES[variable]
    found: dict[tuple[str, str, str], dict[str, tuple[str, str, str]]] = {}
    for row in rows:
        if row["variable_id"] != variable or row["table_id"] != table:
            continue
        if row["experiment_id"] not in EXPERIMENTS:
            continue
        key = (row["source_id"], row["member_id"], row["grid_label"])
        by_exp = found.setdefault(key, {})
        current = by_exp.get(row["experiment_id"])
        entry = (row["version"], row["zstore"], row["institution_id"])
        if current is None or entry[0] > current[0]:
            by_exp[row["experiment_id"]] = entry
    picked: list[Selection] = []
    for source in preferred:
        complete = [k for k, v in found.items() if k[0] == source and len(v) == len(EXPERIMENTS)]
        if not complete:
            continue
        complete.sort(key=lambda k: (k[1] != PREFERRED_MEMBER, k[2] != "gn", _member_key(k[1])))
        key = complete[0]
        by_exp = found[key]
        picked.append(
            Selection(
                source_id=source,
                institution_id=by_exp["historical"][2],
                member_id=key[1],
                grid_label=key[2],
                zstores={e: by_exp[e][1] for e in EXPERIMENTS},
                versions={e: by_exp[e][0] for e in EXPERIMENTS},
            )
        )
        if len(picked) == max_models:
            break
    return picked


def decode_years(values: NDArray, units: str, calendar: str) -> NDArray:
    """Calendar year of each time value (CF 'X since Y-M-D'); exact enough for mid-month steps."""
    import numpy as np

    match = _UNITS.match(units.strip())
    if not match or match.group(1) not in SECONDS_PER:
        raise ValueError(f"unsupported time units: {units!r}")
    year_len = DAYS_PER_YEAR.get(calendar.lower(), GREGORIAN_YEAR)
    ref_year, ref_month, ref_day = (int(match.group(i)) for i in (2, 3, 4))
    ref_offset = (ref_month - 1) * year_len / MONTHS + (ref_day - 1)
    days = np.asarray(values, dtype=float) * SECONDS_PER[match.group(1)]
    return (ref_year + np.floor((days + ref_offset) / year_len)).astype(int)


def period_mean(data: NDArray, years: NDArray, period: tuple[int, int]) -> NDArray:
    """Mean of the annual means; every year of the period must have its 12 months."""
    import numpy as np

    first, last = period
    annual = []
    for year in range(first, last + 1):
        months = data[years == year]
        if months.shape[0] != MONTHS:
            raise ValueError(f"incomplete years: {year} has {months.shape[0]} months")
        annual.append(months.mean(axis=0))
    return np.mean(annual, axis=0)


def target_grid() -> tuple[NDArray, NDArray]:
    """Cell centres of the GISTEMP grid: latitude south to north, longitude west to east."""
    import numpy as np

    half = GRID_STEP / 2
    lat = np.arange(-90 + half, 90, GRID_STEP)
    lon = np.arange(-180 + half, 180, GRID_STEP)
    return lat, lon


def regrid(field: NDArray, src_lat: NDArray, src_lon: NDArray) -> NDArray:
    """Bilinear interpolation of a regular lat/lon field onto the target grid (NaN propagates)."""
    import numpy as np
    from scipy.interpolate import RegularGridInterpolator

    lat_order = np.argsort(src_lat)
    lat = np.asarray(src_lat, dtype=float)[lat_order]
    values = np.asarray(field, dtype=float)[lat_order]
    lon = (np.asarray(src_lon, dtype=float) + 180) % 360 - 180
    lon_order = np.argsort(lon)
    lon, values = lon[lon_order], values[:, lon_order]
    # periodic in longitude, edge rows repeated at the poles
    lon = np.concatenate([lon[-1:] - 360, lon, lon[:1] + 360])
    values = np.concatenate([values[:, -1:], values, values[:, :1]], axis=1)
    if lat[0] > -90:
        lat, values = np.concatenate([[-90.0], lat]), np.concatenate([values[:1], values])
    if lat[-1] < 90:
        lat, values = np.concatenate([lat, [90.0]]), np.concatenate([values, values[-1:]])
    interp = RegularGridInterpolator((lat, lon), values, method="linear")
    tlat, tlon = target_grid()
    glat, glon = np.meshgrid(tlat, tlon, indexing="ij")
    return interp(np.stack([glat, glon], axis=-1))


def check_field(field: NDArray, label: str) -> NDArray:
    """Refuses a period mean with no value at all (e.g. a store with missing chunks)."""
    import numpy as np

    if not np.isfinite(field).any():
        raise ValueError(f"{label}: no valid value (incomplete store?)")
    return field


def model_change(baseline: NDArray, future: NDArray, variable: str) -> NDArray:
    """Future minus baseline: absolute for temperature, % of the baseline otherwise."""
    import numpy as np

    base = np.asarray(baseline, dtype=float)
    fut = np.asarray(future, dtype=float)
    if variable in ABSOLUTE:
        return fut - base
    floor = PERCENT_FLOOR[variable]
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = 100.0 * (fut - base) / base
    return np.where(base >= floor, pct, np.nan)


def ensemble(changes: NDArray) -> dict[str, NDArray]:
    """Median, 10th/90th percentile, model count and sign agreement across models (axis 0)."""
    import numpy as np

    stack = np.asarray(changes, dtype=float)
    count = np.isfinite(stack).sum(axis=0)
    enough = count >= MIN_MODELS
    filled = np.where(enough[None], stack, 0.0)  # all-missing cells: no empty-slice warnings
    median = np.where(enough, np.nanmedian(filled, axis=0), np.nan)
    p10 = np.where(enough, np.nanpercentile(filled, 10, axis=0), np.nan)
    p90 = np.where(enough, np.nanpercentile(filled, 90, axis=0), np.nan)
    direction = np.sign(median)
    same = (np.sign(stack) == direction[None]) & (direction[None] != 0) & np.isfinite(stack)
    agreement = np.where(enough, same.sum(axis=0) / np.maximum(count, 1), np.nan)
    return {"median": median, "p10": p10, "p90": p90, "count": count, "agreement": agreement}


def encode(stats: Mapping[str, NDArray], scale: float) -> bytes:
    """int16 LE median, p10, p90 (value / scale) then uint8 agreement (%) and model count."""
    import numpy as np

    parts = []
    for name in ("median", "p10", "p90"):
        values = np.asarray(stats[name], dtype=float)
        scaled = np.clip(np.round(values / scale), -32000, 32000)
        parts.append(np.where(np.isfinite(values), scaled, I16_MISSING).astype("<i2").tobytes())
    agreement = np.asarray(stats["agreement"], dtype=float)
    pct = np.where(np.isfinite(agreement), np.round(agreement * 100), U8_MISSING)
    parts.append(pct.astype(np.uint8).tobytes())
    parts.append(np.clip(stats["count"], 0, 254).astype(np.uint8).tobytes())
    return b"".join(parts)


def decode(blob: bytes, shape: tuple[int, int], scale: float) -> dict[str, NDArray]:
    """Inverse of `encode` (used by tests and the build's hand checks)."""
    import numpy as np

    n = shape[0] * shape[1]
    out: dict[str, NDArray] = {}
    for i, name in enumerate(("median", "p10", "p90")):
        raw = np.frombuffer(blob, dtype="<i2", count=n, offset=2 * n * i).reshape(shape)
        out[name] = np.where(raw == I16_MISSING, np.nan, raw * scale)
    out["agreement"] = np.frombuffer(blob, dtype=np.uint8, count=n, offset=6 * n).reshape(shape)
    out["count"] = np.frombuffer(blob, dtype=np.uint8, count=n, offset=7 * n).reshape(shape)
    return out
