"""The builder of the witness data files (scripts/build_witness_data.py)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_witness_data as bwd  # noqa: E402

from trend_detective.sources import noaa_stations  # noqa: E402


def test_station_file_keeps_only_annual_temperature_and_metadata(tmp_path: Path) -> None:
    source = tmp_path / "in.json"
    source.write_text(
        json.dumps(
            {
                "source": "S",
                "url": "U",
                "dataset": "D",
                "downloaded": "2026-11-14",
                "units": "metric",
                "stations": {
                    "k": {
                        "station_id": "Z",
                        "station_name": "Z, ZZ",
                        "lat": 1.0,
                        "lon": 2.0,
                        "elevation_m": 3.0,
                        "years": [1981, 1982],
                        "TAVG_degC": [1.5, 2.5],
                        "PRCP_mm_per_year": [1.0, 2.0],
                    }
                },
            }
        )
    )
    out = tmp_path / "out.json"

    keys = bwd.build_station_file(source, out)

    written = json.loads(out.read_text())
    assert keys == ["k"]
    assert "PRCP_mm_per_year" not in written["stations"]["k"]
    assert written["stations"]["k"]["TAVG_degC"] == [1.5, 2.5]
    (station,) = noaa_stations.load_stations(out)
    assert station.tavg == (1.5, 2.5)


def test_shipped_station_file_matches_the_source_data() -> None:
    source = json.loads(bwd.NOAA_JSON.read_text())
    shipped = noaa_stations.load_stations()

    for station in shipped:
        original = source["stations"][station.key]
        assert list(station.tavg) == original["TAVG_degC"]
        assert station.station_id == original["station_id"]
