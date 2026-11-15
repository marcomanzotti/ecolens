"""NOAA GSOY station records shipped in the package, and the nearest-station rule."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trend_detective.sources import noaa_stations as ns


def _stations() -> list[ns.Station]:
    years = tuple(range(1981, 1991))
    return [
        ns.Station(
            key="a",
            station_id="X1",
            name="A, XX",
            lat=69.65,
            lon=18.93,
            elevation_m=100.0,
            years=years,
            tavg=tuple(float(i) for i in range(10)),
        ),
        ns.Station(
            key="b",
            station_id="X2",
            name="B, YY",
            lat=40.78,
            lon=-73.97,
            elevation_m=42.7,
            years=years,
            tavg=tuple(None if i == 2 else 10.0 + i for i in range(10)),
        ),
    ]


def test_haversine_one_degree_of_latitude_is_about_111_km() -> None:
    assert ns.distance_km(10.0, 20.0, 11.0, 20.0) == pytest.approx(111.2, abs=0.3)


def test_haversine_is_zero_for_the_same_point_and_wraps_the_antimeridian() -> None:
    assert ns.distance_km(5.0, 5.0, 5.0, 5.0) == 0.0
    assert ns.distance_km(0.0, 179.5, 0.0, -179.5) == pytest.approx(111.2, abs=0.3)


def test_nearest_station_within_the_threshold() -> None:
    found = ns.nearest_station(_stations(), 69.7, 19.0)

    assert found is not None
    station, km = found
    assert station.key == "a"
    assert km < 10


def test_nearest_station_beyond_the_threshold_is_none() -> None:
    assert ns.nearest_station(_stations(), 45.4, 12.3) is None
    # Brooklyn-ish but 60 km out of Central Park: beyond the default 50 km
    assert ns.nearest_station(_stations(), 41.4, -73.97) is None


def test_nearest_station_threshold_is_the_documented_one() -> None:
    assert ns.MAX_STATION_DISTANCE_KM == 50.0
    inside = ns.nearest_station(_stations(), 41.2, -73.97)  # about 49 km north of the station
    assert inside is not None


def test_station_series_aligns_to_requested_years_with_none_for_gaps() -> None:
    station = _stations()[1]

    series = ns.station_series(station, [1980, 1981, 1983, 1990])

    assert series == [None, 10.0, None, 19.0]


def test_load_stations_reads_the_package_file_and_has_the_three_stations() -> None:
    stations = ns.load_stations()

    assert {s.key for s in stations} == {"tromso", "central-valley", "new-york"}
    for s in stations:
        assert len(s.years) == len(s.tavg) == 45
        assert s.years[0] == 1981 and s.years[-1] == 2025


def test_load_stations_with_a_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ns.load_stations(tmp_path / "none.json")


def test_load_stations_maps_null_to_none(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text(
        json.dumps(
            {
                "stations": {
                    "k": {
                        "station_id": "Z",
                        "station_name": "Z, ZZ",
                        "lat": 1.0,
                        "lon": 2.0,
                        "elevation_m": 3.0,
                        "years": [1981, 1982],
                        "TAVG_degC": [1.5, None],
                    }
                }
            }
        )
    )

    (station,) = ns.load_stations(path)

    assert station.tavg == (1.5, None)
    assert station.key == "k"


def test_tromso_station_is_found_for_tromso_and_not_for_venice() -> None:
    stations = ns.load_stations()

    assert ns.nearest_station(stations, 69.6492, 18.9553) is not None
    assert ns.nearest_station(stations, 45.44, 12.32) is None
