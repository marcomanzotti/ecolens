"""Synthetic series and recorded NASA POWER payloads shared by the engine tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

DATA_DIR = Path(__file__).parent / "data"
FIRST_YEAR = 1981


def year_range(n: int, start: int = FIRST_YEAR) -> list[int]:
    return list(range(start, start + n))


def noisy_line(
    n: int, slope_per_year: float, sigma: float, seed: int, intercept: float = 10.0
) -> list[float]:
    """Straight line plus seeded Gaussian noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    return [float(v) for v in intercept + slope_per_year * t + rng.normal(0.0, sigma, n)]


def ar1_noise(n: int, phi: float, sigma: float, seed: int) -> list[float]:
    """Seeded AR(1) noise with innovation standard deviation `sigma`."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    out = np.zeros(n)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + eps[i]
    return [float(v) for v in out]


def with_gaps(values: list[float], gap_indices: list[int]) -> list[float | None]:
    return [None if i in set(gap_indices) else v for i, v in enumerate(values)]


def load_json(name: str) -> dict[str, Any]:
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def point_payload() -> dict[str, Any]:
    """Recorded POWER point response (14 parameters, Niamey, 1981-2025)."""
    return load_json("power_point_sahel.json")


def region_payload() -> dict[str, Any]:
    """Recorded POWER regional response (PRECTOTCORR, 10-20N, 5W-5E)."""
    return load_json("power_regional_sahel.json")


def round_trip_values(n: int, top: float) -> list[float]:
    """Straight descent from `top` to 0 over n points (used to build a fading trend)."""
    return [float(v) for v in np.linspace(top, 0.0, n)]


def exact_slope_series(
    n: int, slope_per_year: float, sigma: float, seed: int, intercept: float = 10.0
) -> list[float]:
    """Seeded noise with its own OLS trend removed, plus an exact slope.

    The OLS slope of the result is `slope_per_year` (up to rounding), so tests can reason about
    years_needed without depending on the noise realisation.
    """
    t = np.arange(n, dtype=float)
    noise = np.random.default_rng(seed).normal(0.0, sigma, n)
    slope, level = np.polyfit(t, noise, 1)
    detrended = noise - (slope * t + level)
    return [float(v) for v in intercept + slope_per_year * t + detrended]


def _years_of(key: str) -> int:
    return int(key[:4])


def _restrict(monthly: dict[str, float], start: int, end: int) -> dict[str, float]:
    return {k: v for k, v in monthly.items() if start <= _years_of(k) <= end}


def recorded_point_response(parameters: list[str], start: int, end: int) -> dict[str, Any]:
    """A POWER point answer built from the two recorded payloads (34 parameters, Niamey).

    Unknown parameter ids are left out, like POWER does for ids it does not return.
    """
    pool = {
        **point_payload()["properties"]["parameter"],
        **load_json("power_point_sahel_2.json")["properties"]["parameter"],
    }
    chosen = {p: _restrict(pool[p], start, end) for p in parameters if p in pool}
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [2.11, 13.51, 241.58]},
        "properties": {"parameter": chosen},
    }


def recorded_region_response(start: int, end: int) -> dict[str, Any]:
    """The recorded regional answer (PRECTOTCORR, 357 cells) restricted to start..end."""
    payload = region_payload()
    features = [
        {
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "parameter": {
                    name: _restrict(monthly, start, end)
                    for name, monthly in f["properties"]["parameter"].items()
                }
            },
        }
        for f in payload["features"]
    ]
    return {"type": "FeatureCollection", "features": features}
