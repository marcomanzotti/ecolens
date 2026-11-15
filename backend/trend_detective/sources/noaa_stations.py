"""NOAA NCEI Global Summary of the Year (GHCN-based): three station records of annual mean
temperature, shipped inside the package (trend_detective/data/noaa_gsoy_tavg.json, built by
scripts/build_witness_data.py from data/noaa/gsoy_stations.json). Nothing is fetched at run time.

A station is used as a witness only when the point lies within MAX_STATION_DISTANCE_KM of it:
about one MERRA-2 cell (0.5 degree is roughly 50 km), beyond which a single thermometer no longer
says much about the cell.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_STATIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "noaa_gsoy_tavg.json"
MAX_STATION_DISTANCE_KM = 50.0
EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class Station:
    key: str
    station_id: str
    name: str
    lat: float
    lon: float
    elevation_m: float
    years: tuple[int, ...]
    tavg: tuple[float | None, ...]  # annual mean air temperature, degrees C


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine); the antimeridian needs no special case."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat, d_lon = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


@lru_cache(maxsize=2)
def load_stations(path: Path | None = None) -> tuple[Station, ...]:
    """Read the station file (cached). FileNotFoundError when it is absent."""
    data = json.loads((path or DEFAULT_STATIONS_PATH).read_text(encoding="utf-8"))
    return tuple(
        Station(
            key=key,
            station_id=raw["station_id"],
            name=raw["station_name"],
            lat=float(raw["lat"]),
            lon=float(raw["lon"]),
            elevation_m=float(raw["elevation_m"]),
            years=tuple(int(y) for y in raw["years"]),
            tavg=tuple(None if v is None else float(v) for v in raw["TAVG_degC"]),
        )
        for key, raw in data["stations"].items()
    )


def nearest_station(
    stations: Sequence[Station],
    lat: float,
    lon: float,
    max_km: float = MAX_STATION_DISTANCE_KM,
) -> tuple[Station, float] | None:
    """The closest station and its distance in km, or None when none is within `max_km`."""
    ranked = sorted(
        ((s, distance_km(lat, lon, s.lat, s.lon)) for s in stations), key=lambda pair: pair[1]
    )
    return ranked[0] if ranked and ranked[0][1] <= max_km else None


def station_series(station: Station, years: Sequence[int]) -> list[float | None]:
    by_year = dict(zip(station.years, station.tavg, strict=True))
    return [by_year.get(year) for year in years]
