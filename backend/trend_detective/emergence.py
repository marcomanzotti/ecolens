"""Block C: when a trend became significant, and how long until it could be (BE-1).

Expanding window from the first valid year, minimum window MIN_YEARS_FOR_TREND valid years.
`emerged_year` is the first end-year from which the Mann-Kendall p-value stays below ALPHA to the
end of the record. `years_needed` follows Weatherhead et al. (1998), J. Geophys. Res. 103(D14),
17149-17161, eq. 3:

    n* = [ (3.3 * sigma / |omega|) * sqrt((1 + phi) / (1 - phi)) ] ** (2/3)

with sigma the standard deviation and phi the lag-1 autocorrelation of the residuals and omega
the trend per year. That form assumes monthly data, where Var(omega_hat) ~ sigma^2 / n^3 (n in
years). Our series have one point per year, where Var(omega_hat) = 12 sigma^2 / n^3 (checked
numerically in the tests), so the bracket is multiplied by sqrt(12): `compute_emergence` calls
`weatherhead_years_needed(..., annual_resolution=True)`.

STATUS: the paper itself could not be read (paywalled). The monthly formula is quoted from memory;
the annual version rests on our own derivation of the variance of an OLS slope, with the same
3.3 factor (95% confidence, 90% probability of detection).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from trend_detective.models import ALPHA, MIN_YEARS_FOR_TREND, Emergence, RunningPoint
from trend_detective.stats import (
    YEARS_PER_DECADE,
    clean_sample,
    lag1_autocorrelation,
    mann_kendall,
    ols_fit,
    sen_slope,
)

WEATHERHEAD_COEFFICIENT = 3.3
WEATHERHEAD_EXPONENT = 2.0 / 3.0
# |phi| is clamped to this value so that sqrt((1 + phi) / (1 - phi)) stays finite.
MAX_ABS_AUTOCORRELATION = 0.99
# Below this slope-to-noise ratio the slope counts as zero.
ZERO_SLOPE_RATIO = 1e-12
# Detection times above this are described as "more than ..." in the explanation.
EXPLANATION_YEARS_CAP = 200


def weatherhead_years_needed(
    sigma: float,
    slope_per_year: float,
    phi: float,
    *,
    annual_resolution: bool = False,
) -> float | None:
    """Record length (years) needed to detect `slope_per_year` against noise of std `sigma`.

    None when the slope is zero (no finite answer). `annual_resolution` multiplies the bracket
    by sqrt(12), see the module docstring.
    """
    if abs(slope_per_year) <= ZERO_SLOPE_RATIO * max(sigma, 1e-300):
        return None
    phi = max(-MAX_ABS_AUTOCORRELATION, min(MAX_ABS_AUTOCORRELATION, phi))
    bracket = WEATHERHEAD_COEFFICIENT * sigma / abs(slope_per_year)
    bracket *= math.sqrt((1.0 + phi) / (1.0 - phi))
    if annual_resolution:
        bracket *= math.sqrt(12.0)
    return bracket**WEATHERHEAD_EXPONENT


def first_persistent_year(
    end_years: Sequence[int], p_values: Sequence[float], alpha: float
) -> int | None:
    """First end-year from which every later p-value (itself included) is below `alpha`."""
    emerged: int | None = None
    for year, p_value in zip(reversed(end_years), reversed(p_values), strict=True):
        if p_value >= alpha:
            break
        emerged = year
    return emerged


def _running(x: Sequence[float], y: Sequence[float]) -> list[RunningPoint]:
    import numpy as np

    xs, ys = np.asarray(x), np.asarray(y)
    return [
        RunningPoint(
            end_year=int(xs[end - 1]),
            slope_per_decade=sen_slope(xs[:end], ys[:end]) * YEARS_PER_DECADE,
            p_value=mann_kendall(ys[:end]).p_value,
        )
        for end in range(MIN_YEARS_FOR_TREND, len(ys) + 1)
    ]


def _years_phrase(years: float) -> str:
    if years > EXPLANATION_YEARS_CAP:
        return f"more than {EXPLANATION_YEARS_CAP}"
    return f"about {math.ceil(years)}"


def _explanation(
    emerged_year: int | None,
    window_years: int | None,
    years_needed: float | None,
    additional_years: int | None,
) -> str:
    if emerged_year is not None:
        return (
            f"The trend first became statistically clear in {emerged_year}, when the record was "
            f"{window_years} years long, and it has stayed clear ever since."
        )
    if years_needed is None:
        return (
            "The record shows no overall rise or fall, so we cannot say how long it would take "
            "to see a trend."
        )
    if not additional_years:
        return (
            "The trend is still hidden by the ups and downs from year to year. By a rough rule "
            "the record should already be long enough, so the signal is probably very weak."
        )
    return (
        "The trend is not yet statistically clear because the ups and downs from year to year "
        "are large compared with the slow change. At this rate we would need "
        f"{_years_phrase(years_needed)} years of records, which is {additional_years} more years "
        "than we have."
    )


def compute_emergence(years: Sequence[int], values: Sequence[float | None]) -> Emergence | None:
    """Expanding-window significance and the Weatherhead et al. (1998) detection time.

    None with fewer than 10 valid years or a constant series.
    """
    import numpy as np

    sample = clean_sample(years, values)
    if sample is None:
        return None
    fit = ols_fit(sample.x, sample.y)
    noise_std = math.sqrt(fit.sse / fit.df)
    phi = lag1_autocorrelation(fit.residuals)
    running = _running(sample.x, sample.y)
    emerged_year = first_persistent_year(
        [p.end_year for p in running], [p.p_value for p in running], ALPHA
    )
    years_needed = weatherhead_years_needed(noise_std, fit.slope, phi, annual_resolution=True)
    record_years = int(sample.x[-1] - sample.x[0]) + 1
    additional = _additional_years(emerged_year, years_needed, record_years)
    window = None if emerged_year is None else int(np.sum(sample.x <= emerged_year))
    return Emergence(
        status="emerged" if emerged_year is not None else "not_yet",
        emerged_year=emerged_year,
        years_needed=years_needed,
        additional_years=additional,
        noise_std=noise_std,
        autocorrelation=phi,
        running=running,
        explanation=_explanation(emerged_year, window, years_needed, additional),
    )


def _additional_years(
    emerged_year: int | None, years_needed: float | None, record_years: int
) -> int | None:
    if emerged_year is not None:
        return 0
    if years_needed is None:
        return None
    return max(0, math.ceil(years_needed - record_years))
