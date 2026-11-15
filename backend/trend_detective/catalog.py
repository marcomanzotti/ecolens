"""The catalog: 31 NASA POWER variables in 7 themes, seasons, period presets and lookups.

Ids are NASA POWER parameter ids. Units, definitions and the two product labels that
POWER documents itself (MERRA-2 for PRECTOTCORR and TQV, CERES for PW) were checked
against the POWER parameter metadata on 14/11/2026. The other product labels follow
POWER's published data sources and the first year each variable returns data; the
metadata endpoint does not state them.

Everything here is immutable. Definitions are written for high-school students.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from trend_detective.errors import UnknownVariableError
from trend_detective.models import (
    Catalog,
    DataSource,
    Period,
    PeriodPreset,
    Season,
    SourceKind,
    Theme,
    ThemeId,
    Variable,
)

POWER_URL = "https://power.larc.nasa.gov/"
SEASONS: tuple[Season, ...] = ("annual", "DJF", "MAM", "JJA", "SON")
SEASON_LABELS: Mapping[Season, str] = MappingProxyType(
    {
        "annual": "annual mean",
        "DJF": "December to February",
        "MAM": "March to May",
        "JJA": "June to August",
        "SON": "September to November",
    }
)

# POWER unit -> display unit. PW is distributed in cm of water; 1 cm over 1 m² weighs 10 kg.
DISPLAY_SCALE: Mapping[str, float] = MappingProxyType({"PW": 10.0})
POWER_UNIT_NOTES: Mapping[str, str] = MappingProxyType(
    {"PW": "PW is distributed by POWER in centimetres of water and shown here in kg/m² (x 10)."}
)
AIR_TEMPERATURE_GROUP = "air_temperature"
WITNESS_QUANTITIES: Mapping[str, str] = MappingProxyType(
    {
        "column_water_vapour": "Water vapour in the air column",
        AIR_TEMPERATURE_GROUP: "Air temperature",
    }
)


def _source(product: str, kind: SourceKind) -> DataSource:
    return DataSource(
        provider="NASA POWER",
        product=product,
        kind=kind,
        url=POWER_URL,
    )


_MERRA2 = _source("MERRA-2", "reanalysis")
_CERES = _source("CERES SYN1deg", "satellite")
_SRB = _source("GEWEX SRB + CERES SYN1deg", "satellite")


def _var(
    var_id: str,
    name: str,
    unit: str,
    theme: ThemeId,
    source: DataSource,
    first_year: int,
    definition: str,
    witness_group: str | None = None,
) -> Variable:
    return Variable(
        id=var_id,
        name=name,
        unit=unit,
        theme=theme,
        source=source,
        first_year=first_year,
        definition=definition,
        witness_group=witness_group,
    )


# fmt: off
VARIABLES: tuple[Variable, ...] = (
    _var("T2M", "Air temperature", "°C", "temperature", _MERRA2, 1981,
         "How warm the air is about 2 metres above the ground, averaged over day and night.",
         AIR_TEMPERATURE_GROUP),
    _var("T2M_MAX", "Hottest temperature", "°C", "temperature", _MERRA2, 1981,
         "How hot the hottest hour of the day gets, 2 metres above the ground, on average."),
    _var("T2M_MIN", "Coldest temperature", "°C", "temperature", _MERRA2, 1981,
         "How cold the coldest hour of the day gets, 2 metres above the ground, on average."),
    _var("T2M_RANGE", "Temperature swing", "°C", "temperature", _MERRA2, 1981,
         "The gap between the hottest and the coldest hour of the day, on average."),
    _var("TS", "Ground surface temperature", "°C", "temperature", _MERRA2, 1981,
         "How warm the surface of the land or sea itself is, not the air above it."),
    _var("T2MDEW", "Dew point", "°C", "temperature", _MERRA2, 1981,
         "The temperature at which the air would become saturated and dew or frost would "
         "form. Higher means muggier air."),
    _var("FROST_DAYS", "Frost days", "days", "temperature", _MERRA2, 1981,
         "How many days were cold enough for frost to form (air below 0 °C)."),
    _var("PRECTOTCORR", "Precipitation", "mm/day", "water", _MERRA2, 1981,
         "How much water falls from the sky as rain or snow, on an average day."),
    _var("EVLAND", "Evaporation from land", "mm/day", "water", _MERRA2, 1981,
         "How much water leaves the land surface and goes back into the air."),
    _var("RH2M", "Relative humidity", "%", "water", _MERRA2, 1981,
         "How full of water vapour the air is, compared with the most it could hold."),
    _var("QV2M", "Moisture in the air", "g/kg", "water", _MERRA2, 1981,
         "Grams of water vapour in each kilogram of air near the ground."),
    _var("TQV", "Water vapour in the air column (model)", "kg/m²", "water", _MERRA2, 1981,
         "All the water vapour in the air above one square metre of ground, from a global "
         "weather model.",
         "column_water_vapour"),
    _var("PW", "Water vapour in the air column (CERES)", "kg/m²", "water", _CERES, 2001,
         "All the water vapour in the air above one square metre of ground, from the CERES "
         "satellite data product.",
         "column_water_vapour"),
    _var("CLOUD_AMT", "Cloud cover", "%", "water", _SRB, 1984,
         "The share of the sky covered by clouds."),
    _var("GWETTOP", "Topsoil wetness", "0–1", "soil", _MERRA2, 1981,
         "How wet the top 5 cm of soil is, from 0 (completely dry) to 1 (soaked)."),
    _var("GWETROOT", "Root-zone soil wetness", "0–1", "soil", _MERRA2, 1981,
         "How wet the top metre of soil is, where plant roots drink. 0 is dry, 1 is soaked."),
    _var("GWETPROF", "Deep soil wetness", "0–1", "soil", _MERRA2, 1981,
         "How wet the whole soil layer is, from the surface down to bedrock. 0 is dry, "
         "1 is soaked."),
    _var("SNODP", "Snow depth", "cm", "snow", _MERRA2, 1981,
         "How deep the snow lying on the ground is."),
    _var("FRSNO", "Snow cover", "0–1", "snow", _MERRA2, 1981,
         "The share of the land covered by snow, from 0 (none) to 1 (all)."),
    _var("PRECSNOLAND", "Snowfall", "mm/day", "snow", _MERRA2, 1981,
         "How much water falls as snow over land, on an average day."),
    _var("ALLSKY_SFC_SW_DWN", "Sunlight reaching the ground", "MJ/m²/day", "sunlight", _SRB,
         1984, "The energy from the Sun that reaches the ground, clouds included."),
    _var("CLRSKY_SFC_SW_DWN", "Sunlight under a clear sky", "MJ/m²/day", "sunlight", _SRB,
         1984,
         "The energy from the Sun that would reach the ground if there were no clouds. "
         "It changes when the air gets hazier or cleaner."),
    _var("ALLSKY_SFC_LW_DWN", "Heat radiated down by the sky", "MJ/m²/day", "sunlight", _SRB,
         1984,
         "The invisible heat radiation that the air and clouds send down to the ground."),
    _var("ALLSKY_SFC_UV_INDEX", "UV index", "index", "sunlight", _CERES, 2001,
         "How strong the Sun's skin-burning ultraviolet rays are at the ground."),
    _var("ALLSKY_SRF_ALB", "Surface brightness (albedo)", "0–1", "sunlight", _CERES, 2001,
         "The share of sunlight the ground reflects back. Snow and sand are bright, "
         "forests and oceans are dark."),
    _var("AOD_55", "Haze (aerosol optical depth)", "unitless", "air", _CERES, 2001,
         "How much dust, smoke and pollution particles in the air block sunlight. "
         "Higher means hazier air."),
    _var("CLOUD_OD", "Cloud thickness", "unitless", "air", _CERES, 2001,
         "How much the clouds block light passing through them. Higher means thicker clouds."),
    _var("TO3", "Ozone layer", "Dobson units", "air", _MERRA2, 1981,
         "The total amount of ozone in the air above, the gas that shields us from "
         "ultraviolet rays."),
    _var("PS", "Air pressure", "kPa", "air", _MERRA2, 1981,
         "The weight of the air pressing down on the ground."),
    _var("WS10M", "Wind speed", "m/s", "wind", _MERRA2, 1981,
         "How fast the air moves 10 metres above the ground."),
    _var("WS50M", "Wind speed higher up", "m/s", "wind", _MERRA2, 1981,
         "How fast the air moves 50 metres above the ground, the height of a wind turbine."),
)

THEMES: tuple[Theme, ...] = (
    Theme(id="temperature", label="Heat", question="Is it getting hotter or colder?",
          description="Air and ground temperatures, extremes and frost."),
    Theme(id="water", label="Water in the air", question="Is it getting wetter or drier?",
          description="Rain, evaporation, humidity and clouds."),
    Theme(id="soil", label="Soil", question="Is the ground drying out?",
          description="How much water the soil holds."),
    Theme(id="snow", label="Snow", question="Is the snow disappearing?",
          description="Snowfall, snow depth and snow cover."),
    Theme(id="sunlight", label="Sunlight", question="Is more or less sunlight getting through?",
          description="Solar energy at the ground, UV and surface brightness."),
    Theme(id="air", label="Air", question="Is the air changing?",
          description="Haze, ozone, cloud thickness and pressure."),
    Theme(id="wind", label="Wind", question="Is it getting windier?",
          description="Wind speed near the ground."),
)
# fmt: on

PERIOD_PRESETS: tuple[PeriodPreset, ...] = (
    PeriodPreset(id="full", label="Full record (1981–2025)", period=Period()),
    PeriodPreset(id="satellite", label="Satellite era (2001–2025)", period=Period(start_year=2001)),
    PeriodPreset(id="recent", label="Last 20 years (2006–2025)", period=Period(start_year=2006)),
)

_BY_ID: Mapping[str, Variable] = MappingProxyType({v.id: v for v in VARIABLES})


def build_catalog() -> Catalog:
    return Catalog(
        variables=list(VARIABLES),
        themes=list(THEMES),
        seasons=list(SEASONS),
        period_presets=list(PERIOD_PRESETS),
    )


def get_variable(variable_id: str) -> Variable:
    variable = _BY_ID.get(variable_id)
    if variable is None:
        raise UnknownVariableError(f"'{variable_id}' is not a variable in the catalog.")
    return variable


def select_variables(
    themes: Sequence[ThemeId] | None, variable_ids: Sequence[str] | None
) -> list[Variable]:
    """Variables for a line-up. `variable_ids` wins over `themes`; neither means all."""
    if variable_ids:
        return [get_variable(i) for i in dict.fromkeys(variable_ids)]
    if themes:
        return [v for v in VARIABLES if v.theme in themes]
    return list(VARIABLES)


def witness_group_members(group: str) -> list[Variable]:
    return [v for v in VARIABLES if v.witness_group == group]


def display_scale(variable_id: str) -> float:
    return DISPLAY_SCALE.get(variable_id, 1.0)


def to_display_units(variable_id: str, values: Sequence[float | None]) -> list[float | None]:
    """Convert POWER values to the catalog's display unit; missing values stay missing."""
    scale = display_scale(variable_id)
    if scale == 1.0:
        return list(values)
    return [None if v is None else v * scale for v in values]


def period_years(period: Period) -> list[int]:
    return list(range(period.start_year, period.end_year + 1))
