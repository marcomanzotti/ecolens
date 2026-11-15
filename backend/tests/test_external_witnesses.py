"""External temperature witnesses: GISTEMP (2 degree grid) and the three NOAA stations."""

from __future__ import annotations

import pytest

from trend_detective import external_witnesses as ew
from trend_detective import models as m

FULL = m.Period()
GROUP = "air_temperature"
NIAMEY = m.Location(lat=13.51, lon=2.11, label="Niamey, Niger")
VENICE = m.Location(lat=45.44, lon=12.32)
TROMSO = m.Location(lat=69.6492, lon=18.9553)
PACIFIC = m.Location(lat=0.0, lon=-140.0)
DATELINE = m.Location(lat=-17.7, lon=179.9)


def ids(result: ew.ExternalWitnesses) -> list[str]:
    return [s.variable.id for s in result.series]


def test_other_groups_have_no_external_witnesses() -> None:
    result = ew.external_witnesses("column_water_vapour", NIAMEY, FULL, "annual")

    assert result.series == ()
    assert result.unavailable == ()


def test_gistemp_witness_is_a_station_grid_nasa_giss_product() -> None:
    result = ew.external_witnesses(GROUP, NIAMEY, FULL, "annual")

    (gistemp,) = result.series
    variable = gistemp.variable
    assert variable.source.kind == "station_grid"
    assert variable.source.product == "GISTEMP v4"
    assert variable.source.provider == "NASA GISS"
    assert variable.unit == "°C"
    assert variable.witness_group == GROUP
    assert len(gistemp.values) == 45
    assert all(v is not None for v in gistemp.values)


def test_gistemp_notes_state_anomaly_baseline_and_grid_sizes() -> None:
    (gistemp,) = ew.external_witnesses(GROUP, NIAMEY, FULL, "annual").series

    text = " ".join(gistemp.notes)
    assert "1951–1980" in text
    assert "2°" in text and "1,200 km" in text and "0.5°" in text


def test_values_follow_the_requested_period() -> None:
    period = m.Period(start_year=2001, end_year=2020)

    (gistemp,) = ew.external_witnesses(GROUP, NIAMEY, period, "annual").series

    assert len(gistemp.values) == 20


def test_station_witness_is_added_within_the_distance_threshold() -> None:
    result = ew.external_witnesses(GROUP, TROMSO, FULL, "annual")

    assert ids(result)[0] == "GISTEMP_ANOMALY"
    station = result.series[1]
    assert station.variable.source.kind == "station"
    assert station.variable.source.provider == "NOAA NCEI"
    assert "TROMSO" in station.variable.definition or "Tromso" in station.variable.definition
    assert len(station.values) == 45
    note = " ".join(station.notes)
    assert "50 km" in note
    assert "GHCN" in note


def test_no_station_witness_far_from_a_station() -> None:
    assert ids(ew.external_witnesses(GROUP, VENICE, FULL, "annual")) == ["GISTEMP_ANOMALY"]


def test_antimeridian_point_gets_a_gistemp_cell() -> None:
    result = ew.external_witnesses(GROUP, DATELINE, FULL, "annual")

    assert ids(result) == ["GISTEMP_ANOMALY"]


def test_mid_pacific_point_has_a_gistemp_cell() -> None:
    result = ew.external_witnesses(GROUP, PACIFIC, FULL, "annual")

    assert ids(result) == ["GISTEMP_ANOMALY"]


@pytest.mark.parametrize("lat", [90.0, -90.0])
def test_poles_do_not_crash(lat: float) -> None:
    result = ew.external_witnesses(GROUP, m.Location(lat=lat, lon=0.0), FULL, "annual")

    assert len(result.series) + len(result.unavailable) >= 1


@pytest.mark.parametrize("season", ["DJF", "MAM", "JJA", "SON"])
def test_seasons_have_no_external_witness_and_say_why(season: str) -> None:
    result = ew.external_witnesses(GROUP, TROMSO, FULL, season)  # type: ignore[arg-type]

    assert result.series == ()
    assert len(result.unavailable) == 1
    assert "annual" in result.unavailable[0]


def test_cell_without_data_is_reported_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ew.gistemp, "cell_series", lambda *args, **kwargs: None)

    result = ew.external_witnesses(GROUP, NIAMEY, FULL, "annual")

    assert result.series == ()
    assert "GISTEMP has no data" in result.unavailable[0]


def test_missing_grid_file_is_reported_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("gone")

    monkeypatch.setattr(ew.gistemp, "load_grid", boom)

    result = ew.external_witnesses(GROUP, NIAMEY, FULL, "annual")

    assert result.series == ()
    assert "not available" in result.unavailable[0]


def test_stations_are_attempted_even_when_gistemp_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ew.gistemp, "cell_series", lambda *args, **kwargs: None)

    result = ew.external_witnesses(GROUP, TROMSO, FULL, "annual")

    assert ids(result) == [result.series[0].variable.id]
    assert result.series[0].variable.source.kind == "station"
    assert result.unavailable
