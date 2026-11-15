"""Trend statistics (BE-1).

Rules: docs/API_CONTRACT.md, section "Rules behind the numbers".
`years` and `values` always have the same length; None marks a missing year.

Design notes
- Missing years (None, NaN, +-inf) are dropped; the real year values stay as x, so a gap is a
  gap in time, not a shift of the series.
- Mann-Kendall and Theil-Sen are vectorised over all pairs of points: O(n^2) memory, meant for
  annual series (tens to a few hundred points), not for long daily records.
- The lag-1 autocorrelation of the detrended residuals is reported. When its absolute value is
  above AUTOCORRELATION_THRESHOLD the Mann-Kendall p-value of the verdict is the one with the
  Hamed and Rao (1998) variance correction; the OLS t-test is never corrected (there is no
  pre-whitening). The uncorrected Mann-Kendall p-value is always reported next to it.
- numpy / scipy are imported lazily, inside the functions that use them.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from trend_detective.models import (
    ALPHA,
    AUTOCORRELATION_THRESHOLD,
    MIN_YEARS_FOR_TREND,
    FitPoint,
    MannKendallResult,
    OlsResult,
    SenResult,
    TrendStats,
)

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

    FloatArray = NDArray[np.float64]

YEARS_PER_DECADE = 10.0
CONFIDENCE_LEVEL = 0.95
# percent_change is null when |mean| is below this fraction of the standard deviation.
PERCENT_MIN_MEAN_OVER_STD = 0.1
# Units whose zero is arbitrary: a percentage of the mean has no meaning on them.
INTERVAL_SCALE_UNITS = frozenset({"°C"})
# t statistic reported for a perfect fit (zero residual), so that the value stays finite in JSON.
PERFECT_FIT_T = 1e9
MIN_PEARSON_PAIRS = 3


@dataclass(frozen=True)
class Sample:
    """Valid observations only, sorted by year."""

    x: FloatArray
    y: FloatArray
    n_missing: int


@dataclass(frozen=True)
class OlsFit:
    """Ordinary least squares on year, with everything needed for bands and tests."""

    slope: float
    intercept: float  # value at x = 0
    x_mean: float
    sxx: float
    sse: float
    sst: float
    df: int
    stderr: float
    residuals: FloatArray


@dataclass(frozen=True)
class MannKendall:
    s: float
    var_s: float
    z: float
    tau: float
    p_value: float


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------


def clean_sample(years: Sequence[int], values: Sequence[float | None]) -> Sample | None:
    """Drop missing years. None when there are too few valid years or the series is constant."""
    import numpy as np

    if len(years) != len(values):
        raise ValueError("years and values must have the same length")
    y_all = np.array([math.nan if v is None else v for v in values], dtype=float)
    keep = np.isfinite(y_all)
    if int(keep.sum()) < MIN_YEARS_FOR_TREND:
        return None
    x = np.asarray(years, dtype=float)[keep]
    y = y_all[keep]
    order = np.argsort(x, kind="stable")
    x, y = x[order], y[order]
    if np.any(np.diff(x) <= 0):
        raise ValueError("years must be unique")
    if float(np.ptp(y)) == 0.0:
        return None
    return Sample(x=x, y=y, n_missing=len(values) - len(y))


# --------------------------------------------------------------------------
# Ordinary least squares
# --------------------------------------------------------------------------


def ols_fit(x: FloatArray, y: FloatArray) -> OlsFit:
    import numpy as np

    n = len(y)
    x_mean = float(x.mean())
    xc = x - x_mean
    sxx = float(xc @ xc)
    slope = float(xc @ (y - y.mean())) / sxx
    intercept = float(y.mean()) - slope * x_mean
    residuals = y - (intercept + slope * x)
    sse = float(residuals @ residuals)
    sst = float(np.sum((y - y.mean()) ** 2))
    df = n - 2
    stderr = math.sqrt(sse / df / sxx)
    return OlsFit(slope, intercept, x_mean, sxx, sse, sst, df, stderr, residuals)


def _t_critical(df: int) -> float:
    from scipy.special import stdtrit

    return float(stdtrit(df, 1.0 - (1.0 - CONFIDENCE_LEVEL) / 2.0))


def _ols_result(fit: OlsFit, first_x: float) -> OlsResult:
    from scipy.special import stdtr

    if fit.stderr > 0:
        t_stat = fit.slope / fit.stderr
        p_value = min(1.0, 2.0 * float(stdtr(fit.df, -abs(t_stat))))
    else:
        t_stat = math.copysign(PERFECT_FIT_T, fit.slope)
        p_value = 0.0
    half = _t_critical(fit.df) * fit.stderr
    per_decade = YEARS_PER_DECADE
    return OlsResult(
        slope_per_decade=fit.slope * per_decade,
        stderr_per_decade=fit.stderr * per_decade,
        ci95_low=(fit.slope - half) * per_decade,
        ci95_high=(fit.slope + half) * per_decade,
        t_statistic=t_stat,
        p_value=p_value,
        r_squared=min(1.0, max(0.0, 1.0 - fit.sse / fit.sst)),
        intercept=fit.intercept + fit.slope * first_x,
    )


# --------------------------------------------------------------------------
# Mann-Kendall and Theil-Sen
# --------------------------------------------------------------------------


@lru_cache(maxsize=64)
def _pair_indices(n: int) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    import numpy as np

    return np.triu_indices(n, k=1)


def _two_sided_p(s: float, var_s: float) -> float:
    """Normal-approximation p-value of the Mann-Kendall score, with continuity correction."""
    z = 0.0 if var_s <= 0 or s == 0 else (s - math.copysign(1.0, s)) / math.sqrt(var_s)
    return min(1.0, math.erfc(abs(z) / math.sqrt(2.0)))


def mann_kendall(y: FloatArray) -> MannKendall:
    """Mann-Kendall test: tie-corrected variance, continuity correction, two-sided p."""
    import numpy as np

    n = len(y)
    i, j = _pair_indices(n)
    s = float(np.sign(y[j] - y[i]).sum())
    _, counts = np.unique(y, return_counts=True)
    ties = float(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    var_s = (n * (n - 1) * (2 * n + 5) - ties) / 18.0
    z = 0.0 if var_s <= 0 or s == 0 else (s - math.copysign(1.0, s)) / math.sqrt(var_s)
    return MannKendall(
        s=s,
        var_s=var_s,
        z=z,
        tau=s / (0.5 * n * (n - 1)),
        p_value=_two_sided_p(s, var_s),
    )


def hamed_rao_factor(x: FloatArray, y: FloatArray) -> float | None:
    """Hamed and Rao (1998) variance inflation n/n*: the Mann-Kendall variance is multiplied by it.

    The series is detrended with Sen's slope, replaced by its ranks, and the autocorrelations
    of the ranks at every lag whose value lies outside the 95% band of white noise are summed.
    None when the factor is not positive (the corrected variance would be undefined).
    """
    import numpy as np
    from scipy.stats import rankdata

    n = len(y)
    # Time runs 1, 2, 3, ... as in pymannkendall: the Sen-detrended values always contain exact
    # ties (the median pair), and float rounding decides whether they are seen as ties.
    steps = x - x[0] + 1.0
    ranks = rankdata(y - sen_slope(x, y) * steps)
    centred = ranks - ranks.mean()
    acov = np.correlate(centred, centred, "full")[n - 1 :] / n
    if acov[0] == 0.0:  # every detrended value ties: a perfect line, nothing to estimate
        return None
    acf = acov[1:] / acov[0]
    lags = np.arange(1, n, dtype=float)
    outside = np.abs(acf) > _z_two_sided() / math.sqrt(n)
    weights = (n - lags) * (n - lags - 1) * (n - lags - 2)
    factor = 1.0 + 2.0 / (n * (n - 1) * (n - 2)) * float(np.sum((weights * acf)[outside]))
    return factor if factor > 0 else None


def hamed_rao_p_value(x: FloatArray, y: FloatArray) -> float | None:
    """Mann-Kendall p-value with the Hamed and Rao (1998) correction for autocorrelation.
    Same as pymannkendall.hamed_rao_modification_test. None when it cannot be computed."""
    mk = mann_kendall(y)
    factor = hamed_rao_factor(x, y)
    return None if factor is None else _two_sided_p(mk.s, mk.var_s * factor)


def pair_slopes(x: FloatArray, y: FloatArray) -> FloatArray:
    """All pairwise slopes (y_j - y_i) / (x_j - x_i), sorted. x must be strictly increasing."""
    import numpy as np

    i, j = _pair_indices(len(y))
    return np.sort((y[j] - y[i]) / (x[j] - x[i]))


def sen_slope(x: FloatArray, y: FloatArray) -> float:
    """Theil-Sen slope per unit of x."""
    import numpy as np

    return float(np.median(pair_slopes(x, y)))


def _sen_interval(sorted_slopes: FloatArray, var_s: float) -> tuple[float, float]:
    """Sen (1968) confidence interval for the slope (same rank rule as scipy.theilslopes)."""
    import numpy as np

    z = _z_two_sided()
    n_slopes = len(sorted_slopes)
    sigma = math.sqrt(max(var_s, 0.0))
    upper = min(int(np.round((n_slopes + z * sigma) / 2.0)), n_slopes - 1)
    lower = max(int(np.round((n_slopes - z * sigma) / 2.0)) - 1, 0)
    return float(sorted_slopes[lower]), float(sorted_slopes[upper])


def _z_two_sided() -> float:
    from scipy.special import ndtri

    return -float(ndtri((1.0 - CONFIDENCE_LEVEL) / 2.0))


# --------------------------------------------------------------------------
# Autocorrelation
# --------------------------------------------------------------------------


def lag1_autocorrelation(residuals: FloatArray) -> float:
    """Lag-1 autocorrelation of zero-mean residuals; consecutive valid values are paired."""
    denominator = float(residuals @ residuals)
    if denominator == 0.0:
        return 0.0
    return float(residuals[:-1] @ residuals[1:]) / denominator


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def _evidence(ols_p: float, mk_p: float) -> tuple[str, bool]:
    ols_sig, mk_sig = ols_p < ALPHA, mk_p < ALPHA
    if ols_sig and mk_sig:
        return "strong", True
    if ols_sig or mk_sig:
        return "mixed", False
    return "none", False


def _direction(sen_per_year: float) -> str:
    if sen_per_year > 0:
        return "up"
    if sen_per_year < 0:
        return "down"
    return "flat"


def _percent_change(total_change: float, mean: float, std: float, unit: str) -> float | None:
    if unit in INTERVAL_SCALE_UNITS or abs(mean) <= PERCENT_MIN_MEAN_OVER_STD * std:
        return None
    return total_change / abs(mean) * 100.0


def compute_trend(
    years: Sequence[int], values: Sequence[float | None], unit: str
) -> TrendStats | None:
    """Full trend analysis. None with fewer than 10 valid years or a constant series."""
    import numpy as np

    sample = clean_sample(years, values)
    if sample is None:
        return None
    x, y = sample.x, sample.y
    fit = ols_fit(x, y)
    ols = _ols_result(fit, float(x[0]))
    mk = mann_kendall(y)
    lag1 = lag1_autocorrelation(fit.residuals)
    factor = hamed_rao_factor(x, y)
    p_hr = None if factor is None else _two_sided_p(mk.s, mk.var_s * factor)
    corrected = p_hr is not None and abs(lag1) > AUTOCORRELATION_THRESHOLD
    mk_p_used = p_hr if corrected and p_hr is not None else mk.p_value
    var_for_interval = mk.var_s * factor if corrected and factor is not None else mk.var_s
    slopes = pair_slopes(x, y)
    sen_year = float(np.median(slopes))
    low, high = _sen_interval(slopes, var_for_interval)
    evidence, significant = _evidence(ols.p_value, mk_p_used)
    mean, std = float(y.mean()), float(y.std(ddof=1))
    total_change = fit.slope * float(x[-1] - x[0])
    return TrendStats(
        n=len(y),
        n_missing=sample.n_missing,
        unit=unit,
        alpha=ALPHA,
        direction=_direction(sen_year),
        evidence=evidence,
        significant=significant,
        methods_agree=(ols.p_value < ALPHA) == (mk_p_used < ALPHA),
        total_change=total_change,
        percent_change=_percent_change(total_change, mean, std, unit),
        mean=mean,
        std=std,
        lag1_autocorrelation=lag1,
        autocorrelation_corrected=corrected,
        ols=ols,
        mann_kendall=MannKendallResult(
            s=mk.s, z=mk.z, tau=mk.tau, p_value=mk.p_value, p_value_hamed_rao=p_hr
        ),
        sen=SenResult(
            slope_per_decade=sen_year * YEARS_PER_DECADE,
            ci95_low=low * YEARS_PER_DECADE,
            ci95_high=high * YEARS_PER_DECADE,
        ),
    )


def fit_line(years: Sequence[int], values: Sequence[float | None]) -> list[FitPoint]:
    """OLS line with the 95% confidence band of the mean, one point per year from the first
    to the last valid year. Empty when compute_trend would return None."""
    import numpy as np

    sample = clean_sample(years, values)
    if sample is None:
        return []
    fit = ols_fit(sample.x, sample.y)
    grid = np.arange(sample.x[0], sample.x[-1] + 1.0)
    center = fit.intercept + fit.slope * grid
    se_mean = math.sqrt(fit.sse / fit.df) * np.sqrt(
        1.0 / len(sample.y) + (grid - fit.x_mean) ** 2 / fit.sxx
    )
    half = _t_critical(fit.df) * se_mean
    return [
        FitPoint(year=int(year), value=float(c), ci_low=float(c - h), ci_high=float(c + h))
        for year, c, h in zip(grid, center, half, strict=True)
    ]


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """Adjusted p-values (false discovery rate), in the order given, monotone, capped at 1."""
    import numpy as np

    p = np.asarray(p_values, dtype=float)
    if p.size == 0:
        return []
    if not np.all(np.isfinite(p)) or p.min() < 0.0 or p.max() > 1.0:
        raise ValueError("p-values must be numbers between 0 and 1")
    m = p.size
    order = np.argsort(p, kind="stable")
    scaled = p[order] * m / np.arange(1, m + 1)
    adjusted_sorted = np.minimum(np.minimum.accumulate(scaled[::-1])[::-1], 1.0)
    adjusted = np.empty(m)
    adjusted[order] = adjusted_sorted
    return [float(v) for v in adjusted]


def pearson(a: Sequence[float | None], b: Sequence[float | None]) -> float | None:
    """Pearson correlation over the years where both are present; None with fewer than 3."""
    import numpy as np

    if len(a) != len(b):
        raise ValueError("a and b must have the same length")
    pairs = [
        (u, v)
        for u, v in zip(a, b, strict=True)
        if u is not None and v is not None and math.isfinite(u) and math.isfinite(v)
    ]
    if len(pairs) < MIN_PEARSON_PAIRS:
        return None
    arr = np.array(pairs, dtype=float)
    u, v = arr[:, 0] - arr[:, 0].mean(), arr[:, 1] - arr[:, 1].mean()
    denominator = math.sqrt(float(u @ u) * float(v @ v))
    if denominator == 0.0:
        return None
    return min(1.0, max(-1.0, float(u @ v) / denominator))
