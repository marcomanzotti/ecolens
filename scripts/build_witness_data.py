"""Build the two small data files the temperature witnesses read at run time.

Run from the repo root:  backend/.venv/bin/python scripts/build_witness_data.py

Inputs (already downloaded, never fetched here):
  data/raw/gistemp/gistemp1200_GHCNv4_ERSSTv5.nc   GISTEMP v4, 1200 km smoothing (NASA GISS)
  data/noaa/gsoy_stations.json                     three NOAA GSOY station records
Outputs, inside the backend package so that they ship with it:
  backend/trend_detective/data/gistemp_annual.npz  annual anomalies 1981-2025, 2 degree grid
  backend/trend_detective/data/noaa_gsoy_tavg.json annual mean temperature of the stations
The annual means are the ones of the globe (earth_gistemp.annual_means).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

import earth_gistemp as eg  # noqa: E402

from trend_detective.models import MAX_YEAR, MIN_YEAR  # noqa: E402
from trend_detective.sources import gistemp  # noqa: E402

GISTEMP_NC = ROOT / "data" / "raw" / "gistemp" / "gistemp1200_GHCNv4_ERSSTv5.nc"
NOAA_JSON = ROOT / "data" / "noaa" / "gsoy_stations.json"
PACKAGE_DATA = ROOT / "backend" / "trend_detective" / "data"
GRID_OUT = PACKAGE_DATA / "gistemp_annual.npz"
STATIONS_OUT = PACKAGE_DATA / "noaa_gsoy_tavg.json"
STATION_FIELDS = ("station_id", "station_name", "lat", "lon", "elevation_m", "years", "TAVG_degC")


def build_gistemp_grid(nc_path: Path, out: Path) -> tuple[int, ...]:
    """Annual anomalies of the engine's period on the 2 degree grid; returns the years."""
    grid = eg.read_gistemp(nc_path)
    years, annual = eg.annual_means(grid, MIN_YEAR, MAX_YEAR)
    expected = (len(years), gistemp.N_ROWS, gistemp.N_COLS)
    if annual.shape != expected:
        raise SystemExit(f"unexpected GISTEMP grid shape {annual.shape}, wanted {expected}")
    gistemp.write_grid(out, years, annual)
    return years


def build_station_file(source: Path, out: Path) -> list[str]:
    """Keep only what the witness needs: the annual mean temperature of each station."""
    data = json.loads(source.read_text(encoding="utf-8"))
    slim = {
        "source": data["source"],
        "url": data["url"],
        "dataset": data["dataset"],
        "downloaded": data["downloaded"],
        "units": data["units"],
        "stations": {
            key: {field: station[field] for field in STATION_FIELDS}
            for key, station in data["stations"].items()
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(slim, ensure_ascii=False, separators=(",", ":")) + "\n")
    return list(slim["stations"])


def main() -> None:
    years = build_gistemp_grid(GISTEMP_NC, GRID_OUT)
    size_kb = GRID_OUT.stat().st_size / 1024
    sys.stdout.write(f"{GRID_OUT.name}: {years[0]}-{years[-1]}, {size_kb:.0f} KB\n")
    stations = build_station_file(NOAA_JSON, STATIONS_OUT)
    sys.stdout.write(f"{STATIONS_OUT.name}: {', '.join(stations)}\n")


if __name__ == "__main__":
    main()
