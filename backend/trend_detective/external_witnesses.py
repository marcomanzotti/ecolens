"""Witnesses that do not come from NASA POWER, added to a witness group (block D).

Air temperature (group "air_temperature") has two:
- NASA GISTEMP v4 (GISS): station and ship/buoy records on a 2 degree grid, read from a compact
  annual grid shipped in the package (sources/gistemp.py). Available anywhere on Earth where the
  cell has data. Values are anomalies from the 1951-1980 average, in degrees C.
- NOAA NCEI GSOY stations (annual mean temperature): the three stations of the project, used
  only when the point is within MAX_STATION_DISTANCE_KM of one.

Both are annual means: with a season selected there is no external witness, and the reason is
returned instead of raising, so that the caller can say why.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from trend_detective import catalog
from trend_detective.models import DataSource, Location, Period, Season, Variable
from trend_detective.sources import gistemp, noaa_stations

logger = logging.getLogger(__name__)

AIR_TEMPERATURE_GROUP = catalog.AIR_TEMPERATURE_GROUP
GISTEMP_ID = "GISTEMP_ANOMALY"
GISTEMP_URL = "https://data.giss.nasa.gov/gistemp/"
GSOY_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
MSG_ANNUAL_ONLY = (
    "GISTEMP and the NOAA stations are annual means only: choose the annual mean to call the "
    "second temperature sources."
)
MSG_GRID_MISSING = "The GISTEMP data file is not available on this server."
MSG_NO_CELL = "GISTEMP has no data in the 2° cell around this point."

GISTEMP_NOTES = (
    "GISTEMP is an anomaly from the 1951–1980 average, while MERRA-2 is an absolute "
    "temperature: their levels differ, so only trends and year-to-year changes are compared "
    "(slopes are in the same unit, °C per decade).",
    "A GISTEMP cell is 2° wide (about 200 km) and spreads station and ship data up to 1,200 km, "
    "while a MERRA-2 cell is 0.5° (about 50 km): the two describe areas of different sizes.",
)
STATION_GHCN_NOTE = (
    "GISTEMP is built from NOAA's GHCN station records, so the NOAA station and GISTEMP are "
    "not independent of each other."
)


@dataclass(frozen=True)
class ExternalSeries:
    """One external witness: a catalog-like variable, one value per year of the period, and the
    limitations that apply to it."""

    variable: Variable
    values: tuple[float | None, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ExternalWitnesses:
    series: tuple[ExternalSeries, ...] = ()
    unavailable: tuple[str, ...] = ()


def _gistemp_variable() -> Variable:
    return Variable(
        id=GISTEMP_ID,
        name="Air temperature anomaly (GISTEMP)",
        definition=(
            "How much warmer or colder than the 1951–1980 average the air near the ground was, "
            "from land weather stations and ocean ships and buoys, spread over a 2° grid."
        ),
        unit="°C",
        theme="temperature",
        source=DataSource(
            provider="NASA GISS",
            product="GISTEMP v4",
            kind="station_grid",
            url=GISTEMP_URL,
        ),
        first_year=gistemp.load_grid().years[0],
        witness_group=AIR_TEMPERATURE_GROUP,
    )


def _station_variable(station: noaa_stations.Station, km: float) -> Variable:
    return Variable(
        id=f"NOAA_GSOY_{station.station_id}",
        name=f"Air temperature at {station.name.title()}",
        definition=(
            f"Yearly average air temperature measured at the weather station {station.name}, "
            f"{km:.0f} km from the point and {station.elevation_m:.0f} m above sea level."
        ),
        unit="°C",
        theme="temperature",
        source=DataSource(
            provider="NOAA NCEI",
            product="Global Summary of the Year (GHCN)",
            kind="station",
            url=GSOY_URL,
        ),
        first_year=station.years[0],
        witness_group=AIR_TEMPERATURE_GROUP,
    )


def _gistemp_witness(
    location: Location, years: Sequence[int]
) -> tuple[ExternalSeries | None, str | None]:
    try:
        grid = gistemp.load_grid()
    except FileNotFoundError:
        logger.warning("GISTEMP grid file not found: %s", gistemp.DEFAULT_GRID_PATH)
        return None, MSG_GRID_MISSING
    values = gistemp.cell_series(grid, location.lat, location.lon, years)
    if values is None:
        return None, MSG_NO_CELL
    return ExternalSeries(_gistemp_variable(), tuple(values), GISTEMP_NOTES), None


def _station_witness(location: Location, years: Sequence[int]) -> ExternalSeries | None:
    found = noaa_stations.nearest_station(noaa_stations.load_stations(), location.lat, location.lon)
    if found is None:
        return None
    station, km = found
    limit = f"{noaa_stations.MAX_STATION_DISTANCE_KM:.0f} km"
    notes = (
        f"The NOAA record is one weather station ({station.name}, {km:.0f} km from the point, "
        f"{station.elevation_m:.0f} m high), while a MERRA-2 cell averages about 50 km: levels "
        f"and local ups and downs can differ. Stations are used only within {limit} of the point.",
        STATION_GHCN_NOTE,
    )
    values = noaa_stations.station_series(station, years)
    return ExternalSeries(_station_variable(station, km), tuple(values), notes)


def external_witnesses(
    group: str, location: Location, period: Period, season: Season
) -> ExternalWitnesses:
    """External witnesses of `group` at a point, one value per year of `period`."""
    if group != AIR_TEMPERATURE_GROUP:
        return ExternalWitnesses()
    if season != "annual":
        return ExternalWitnesses(unavailable=(MSG_ANNUAL_ONLY,))
    years = catalog.period_years(period)
    gistemp_series, reason = _gistemp_witness(location, years)
    station_series = _station_witness(location, years)
    found = tuple(s for s in (gistemp_series, station_series) if s is not None)
    return ExternalWitnesses(series=found, unavailable=() if reason is None else (reason,))
