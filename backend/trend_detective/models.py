"""Domain models shared by the engine and the API.

This module is the single source of truth for the API contract
(docs/API_CONTRACT.md). The TypeScript types in frontend/lib/api-types.gen.ts
are generated from these models: change them here, then run scripts/gen_types.sh.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

ALPHA = 0.05
MIN_YEAR = 1981
MAX_YEAR = 2025
MIN_YEARS_FOR_TREND = 10
AUTOCORRELATION_THRESHOLD = 0.3
MIN_BBOX_SPAN_DEG = 2.0
MAX_BBOX_SPAN_DEG = 10.0
MAX_QUESTION_LENGTH = 500

Season = Literal["annual", "DJF", "MAM", "JJA", "SON"]
Direction = Literal["up", "down", "flat"]
ThemeId = Literal["temperature", "water", "soil", "snow", "sunlight", "air", "wind"]
SourceKind = Literal["reanalysis", "satellite", "derived", "station", "station_grid"]
PlaceKind = Literal[
    "desert",
    "rainforest",
    "city",
    "coast",
    "mountain",
    "polar",
    "farmland",
    "grassland",
    "island",
    "wetland",
]
# strong  = OLS t-test and Mann-Kendall both significant at ALPHA
# mixed   = only one of the two is significant
# none    = neither is significant
# insufficient = fewer than MIN_YEARS_FOR_TREND valid years
Evidence = Literal["strong", "mixed", "none", "insufficient"]


class Model(BaseModel):
    """Base: immutable, rejects unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------


class Location(Model):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    label: str | None = Field(default=None, max_length=120)


class Period(Model):
    start_year: int = Field(default=MIN_YEAR, ge=MIN_YEAR, le=MAX_YEAR)
    end_year: int = Field(default=MAX_YEAR, ge=MIN_YEAR, le=MAX_YEAR)

    @model_validator(mode="after")
    def _long_enough(self) -> Period:
        if self.end_year - self.start_year + 1 < MIN_YEARS_FOR_TREND:
            raise ValueError(f"period must span at least {MIN_YEARS_FOR_TREND} years")
        return self


class BBox(Model):
    lat_min: float = Field(ge=-90, le=90)
    lat_max: float = Field(ge=-90, le=90)
    lon_min: float = Field(ge=-180, le=180)
    lon_max: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def _valid_span(self) -> BBox:
        spans = (self.lat_max - self.lat_min, self.lon_max - self.lon_min)
        if min(spans) < MIN_BBOX_SPAN_DEG:
            raise ValueError(
                f"bounding box must span at least {MIN_BBOX_SPAN_DEG:g} degrees on each side"
            )
        if max(spans) > MAX_BBOX_SPAN_DEG:
            raise ValueError(
                f"bounding box must span at most {MAX_BBOX_SPAN_DEG:g} degrees on each side"
            )
        return self


class DataSource(Model):
    """Where a variable comes from. `product` is the originating NASA product."""

    provider: str = Field(description="Service the data is fetched from, e.g. 'NASA POWER'")
    product: str = Field(description="Originating product, e.g. 'MERRA-2', 'CERES SYN1deg'")
    kind: SourceKind
    url: str | None = None


class Variable(Model):
    id: str = Field(description="NASA POWER parameter id, e.g. 'T2M'")
    name: str = Field(description="Short human name, e.g. 'Air temperature'")
    definition: str = Field(description="Plain-language definition for non-experts")
    unit: str = Field(description="Display unit, e.g. '°C', 'mm/day'")
    theme: ThemeId
    source: DataSource
    first_year: int = Field(description="First year with data for this variable")
    witness_group: str | None = Field(
        default=None,
        description="Variables sharing a group measure the same quantity from independent sources",
    )


class Theme(Model):
    id: ThemeId
    label: str
    question: str = Field(description="Guided-question wording, e.g. 'Is it getting hotter?'")
    description: str


class Place(Model):
    id: str
    name: str
    country: str
    lat: float
    lon: float
    kind: PlaceKind
    blurb: str = Field(description="One sentence on why this place is worth investigating")
    suggested_themes: list[ThemeId]


class PeriodPreset(Model):
    id: str
    label: str
    period: Period


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------


class SeriesPoint(Model):
    year: int
    value: float | None = Field(description="Annual or seasonal mean; null when missing")


class FitPoint(Model):
    """OLS trend line with its 95% confidence band for the mean."""

    year: int
    value: float
    ci_low: float
    ci_high: float


class OlsResult(Model):
    slope_per_decade: float
    stderr_per_decade: float
    ci95_low: float = Field(description="Lower bound of the 95% CI of the slope, per decade")
    ci95_high: float
    t_statistic: float
    p_value: float = Field(ge=0, le=1)
    r_squared: float = Field(ge=0, le=1)
    intercept: float = Field(description="Fitted value at the first year of the period")


class MannKendallResult(Model):
    s: float
    z: float
    tau: float = Field(ge=-1, le=1)
    p_value: float = Field(ge=0, le=1)
    p_value_hamed_rao: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description=(
            "Mann-Kendall p-value with the Hamed and Rao (1998) variance correction for "
            "autocorrelation; null when it cannot be computed"
        ),
    )


class SenResult(Model):
    slope_per_decade: float
    ci95_low: float
    ci95_high: float


class TrendStats(Model):
    n: int = Field(description="Number of valid years used")
    n_missing: int
    unit: str
    alpha: float = ALPHA
    direction: Direction
    evidence: Evidence
    significant: bool = Field(description="True only when evidence is 'strong'")
    methods_agree: bool = Field(description="OLS and Mann-Kendall reach the same conclusion")
    total_change: float = Field(description="OLS slope times the length of the period, in `unit`")
    percent_change: float | None = Field(
        description="total_change relative to the period mean; null when the mean is near zero"
    )
    mean: float
    std: float
    lag1_autocorrelation: float
    autocorrelation_corrected: bool = Field(
        default=False,
        description=(
            "True when the verdict used the Hamed-Rao p-value because |lag-1 autocorrelation| > 0.3"
        ),
    )
    ols: OlsResult
    mann_kendall: MannKendallResult
    sen: SenResult


class Verdict(Model):
    """Plain-language verdict built by deterministic rules from TrendStats. Never by an LLM."""

    evidence: Evidence
    headline: str = Field(
        description="One short sentence, e.g. 'Case closed: it is getting warmer.'"
    )
    what: str
    where: str
    how_much: str
    how_sure: str
    caveats: list[str]


class RunningPoint(Model):
    """Trend from the first year up to `end_year` (expanding window)."""

    end_year: int
    slope_per_decade: float
    p_value: float = Field(ge=0, le=1, description="Mann-Kendall p-value")


EmergenceStatus = Literal["emerged", "not_yet", "insufficient"]


class Emergence(Model):
    """Block C. When did the trend become significant, or how long until it could?"""

    status: EmergenceStatus
    emerged_year: int | None = Field(
        description="First end-year from which the trend stays significant to the end of the record"
    )
    years_needed: float | None = Field(
        description="Weatherhead et al. (1998) record length needed to detect the current slope"
    )
    additional_years: int | None = Field(
        description="years_needed minus years available, rounded up; 0 when already emerged"
    )
    noise_std: float = Field(description="Standard deviation of the detrended residuals")
    autocorrelation: float = Field(description="Lag-1 autocorrelation of the residuals")
    running: list[RunningPoint]
    explanation: str


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


class CaseResult(Model):
    location: Location
    variable: Variable
    period: Period
    season: Season
    series: list[SeriesPoint]
    fit: list[FitPoint]
    trend: TrendStats | None = Field(description="null when evidence is 'insufficient'")
    emergence: Emergence | None
    verdict: Verdict
    limitations: list[str]


class Correction(Model):
    method: Literal["fdr_bh"] = "fdr_bh"
    label: str = "Benjamini-Hochberg false discovery rate"
    alpha: float = ALPHA
    n_tests: int


LineupStatus = Literal["ok", "no_data"]


class LineupItem(Model):
    rank: int | None = Field(description="1 = strongest trend; null when status is 'no_data'")
    variable: Variable
    status: LineupStatus
    n: int
    direction: Direction | None
    slope_per_decade: float | None = Field(description="Sen's slope, in the variable's unit")
    standardized_slope: float | None = Field(
        description="Sen's slope divided by the series standard deviation (sigma per decade)"
    )
    tau: float | None
    p_value: float | None = Field(description="Mann-Kendall p-value, uncorrected")
    p_adjusted: float | None = Field(description="p-value after multiple-testing correction")
    significant: bool = Field(description="p_adjusted < alpha")
    sparkline: list[float | None] = Field(description="Annual values, one per year of the period")


class LineupResult(Model):
    location: Location
    period: Period
    season: Season
    correction: Correction
    items: list[LineupItem]
    n_significant: int
    summary: str


class Witness(Model):
    variable: Variable
    series: list[SeriesPoint]
    fit: list[FitPoint]
    trend: TrendStats | None


class WitnessAgreement(Model):
    level: Literal["agree", "partly", "disagree", "insufficient"]
    same_direction: bool | None
    all_significant: bool | None
    correlation: float | None = Field(
        description="Pearson r between the witnesses over the common period"
    )
    text: str


class WitnessesResult(Model):
    """Block D. The same quantity seen by independent sources over their common period."""

    location: Location
    quantity: str = Field(description="e.g. 'Water vapour in the air column'")
    season: Season
    common_period: Period
    witnesses: list[Witness]
    agreement: WitnessAgreement
    limitations: list[str]


class TrendMapCell(Model):
    lat: float
    lon: float
    n: int
    slope_per_decade: float | None = Field(
        description="Sen's slope; null when the cell has no data"
    )
    direction: Direction | None
    p_value: float | None
    p_adjusted: float | None
    significant: bool


class GridSpec(Model):
    lat_step: float
    lon_step: float
    n_lat: int
    n_lon: int


class OppositeTwin(Model):
    """Two significant cells of the same map trending in opposite directions."""

    up: TrendMapCell
    down: TrendMapCell
    distance_km: float
    text: str


class TrendMapSummary(Model):
    n_cells: int
    n_valid: int
    n_up_significant: int
    n_down_significant: int
    max_abs_slope: float = Field(description="Use as the symmetric limit of the colour scale")
    text: str


class TrendMapResult(Model):
    """Block B. Slope per grid cell over a box of up to 10 x 10 degrees."""

    variable: Variable
    bbox: BBox
    period: Period
    season: Season
    grid: GridSpec
    correction: Correction
    cells: list[TrendMapCell]
    summary: TrendMapSummary
    opposite_twin: OppositeTwin | None


class AskResult(Model):
    """Free-text question parsed by the AI assistant. Contains no numbers and no verdicts."""

    understood: bool = Field(description="False when no place or topic could be extracted")
    interpretation: str = Field(
        description="One sentence restating the question as an investigation"
    )
    location: Location | None = Field(description="From the geocoder, never from the LLM")
    themes: list[ThemeId]
    variable_ids: list[str] = Field(description="Subset of the catalog, never invented ids")
    period: Period | None
    season: Season | None


class Catalog(Model):
    variables: list[Variable]
    themes: list[Theme]
    seasons: list[Season]
    period_presets: list[PeriodPreset]
    min_year: int = MIN_YEAR
    max_year: int = MAX_YEAR
    alpha: float = ALPHA


class PlacesResult(Model):
    places: list[Place]


class DemoSummary(Model):
    id: str
    title: str
    blurb: str
    place_name: str
    variable_id: str


class DemoList(Model):
    demos: list[DemoSummary]


class DemoCase(Model):
    """A saved investigation the user can replay without waiting for live data."""

    id: str
    title: str
    blurb: str
    narrative: list[str] = Field(description="Short steps of the investigation, in order")
    case: CaseResult
    lineup: LineupResult | None
    witnesses: WitnessesResult | None
    trendmap: TrendMapResult | None


class Health(Model):
    status: Literal["ok"] = "ok"
    version: str
    assistant_available: bool = Field(description="False when no Gemini key is configured")
