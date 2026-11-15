"""Trend statistics, cross-checked against numpy, scipy and pymannkendall."""

from __future__ import annotations

import math
import time

import numpy as np
import pymannkendall as pmk
import pytest
from scipy import stats as sps

from tests.engine_series import ar1_noise, noisy_line, with_gaps, year_range
from trend_detective.models import MIN_YEARS_FOR_TREND, TrendStats
from trend_detective.stats import (
    benjamini_hochberg,
    compute_trend,
    fit_line,
    pearson,
)

UNIT = "mm/day"


def _trend(years: list[int], values: list[float | None]) -> TrendStats:
    result = compute_trend(years, values, UNIT)
    assert result is not None
    return result


def _valid(years: list[int], values: list[float | None]) -> tuple[np.ndarray, np.ndarray]:
    pairs = [(y, v) for y, v in zip(years, values, strict=True) if v is not None]
    return np.array([p[0] for p in pairs], float), np.array([p[1] for p in pairs], float)


# --------------------------------------------------------------------------
# OLS
# --------------------------------------------------------------------------


def test_ols_matches_scipy_linregress_on_known_slope() -> None:
    years = year_range(45)
    values = noisy_line(45, slope_per_year=0.03, sigma=0.5, seed=42)

    trend = _trend(years, values)

    ref = sps.linregress(years, values)
    assert trend.ols.slope_per_decade == pytest.approx(ref.slope * 10, rel=1e-9)
    assert trend.ols.stderr_per_decade == pytest.approx(ref.stderr * 10, rel=1e-9)
    assert trend.ols.p_value == pytest.approx(ref.pvalue, rel=1e-7)
    assert trend.ols.r_squared == pytest.approx(ref.rvalue**2, rel=1e-9)
    assert trend.ols.intercept == pytest.approx(ref.intercept + ref.slope * years[0], rel=1e-9)
    assert trend.ols.t_statistic == pytest.approx(ref.slope / ref.stderr, rel=1e-9)
    # the slope is recovered within sampling error
    assert trend.ols.slope_per_decade == pytest.approx(0.3, abs=0.1)


def test_ols_confidence_interval_uses_t_distribution() -> None:
    years = year_range(30)
    values = noisy_line(30, 0.05, 1.0, seed=3)

    trend = _trend(years, values)

    tcrit = sps.t.ppf(0.975, df=28)
    half = tcrit * trend.ols.stderr_per_decade
    assert trend.ols.ci95_low == pytest.approx(trend.ols.slope_per_decade - half, rel=1e-9)
    assert trend.ols.ci95_high == pytest.approx(trend.ols.slope_per_decade + half, rel=1e-9)


def test_ols_with_polyfit_agreement() -> None:
    years = year_range(40)
    values = noisy_line(40, -0.02, 0.4, seed=11)

    trend = _trend(years, values)

    slope, _ = np.polyfit(years, values, 1)
    assert trend.ols.slope_per_decade == pytest.approx(slope * 10, rel=1e-9)


# --------------------------------------------------------------------------
# Mann-Kendall and Sen
# --------------------------------------------------------------------------


def _assert_mk_matches(trend: TrendStats, values: list[float]) -> None:
    ref = pmk.original_test(values)
    assert trend.mann_kendall.s == pytest.approx(ref.s)
    assert trend.mann_kendall.z == pytest.approx(ref.z, rel=1e-9, abs=1e-12)
    assert trend.mann_kendall.p_value == pytest.approx(ref.p, rel=1e-7, abs=1e-12)
    assert trend.mann_kendall.tau == pytest.approx(ref.Tau, rel=1e-9, abs=1e-12)


def test_mann_kendall_matches_pymannkendall_on_trending_series() -> None:
    values = noisy_line(45, 0.03, 0.5, seed=42)
    _assert_mk_matches(_trend(year_range(45), values), values)


def test_mann_kendall_matches_pymannkendall_on_flat_noisy_series() -> None:
    values = noisy_line(45, 0.0, 1.0, seed=7)
    _assert_mk_matches(_trend(year_range(45), values), values)


def test_mann_kendall_tie_correction_matches_pymannkendall() -> None:
    rng = np.random.default_rng(5)
    values = [float(v) for v in np.round(rng.normal(0, 1.2, 45) + np.arange(45) * 0.03)]
    assert len(set(values)) < 12  # many ties

    trend = _trend(year_range(45), values)

    _assert_mk_matches(trend, values)
    # without the tie correction the variance (and so z) would differ
    n = 45
    naive_sd = math.sqrt(n * (n - 1) * (2 * n + 5) / 18)
    s = trend.mann_kendall.s
    naive_z = (s - math.copysign(1, s)) / naive_sd
    assert trend.mann_kendall.z != pytest.approx(naive_z, rel=1e-3)


def test_mann_kendall_applies_continuity_correction() -> None:
    values = [float(v) for v in range(12)]
    trend = _trend(year_range(12), values)
    # s = 66, var = 12*11*29/18 = 212.667 -> z = (66 - 1) / sqrt(var)
    assert trend.mann_kendall.s == 66
    assert trend.mann_kendall.z == pytest.approx(65 / math.sqrt(212 + 2 / 3))


def test_sen_slope_and_ci_match_scipy_theilslopes() -> None:
    years = year_range(45)
    values = noisy_line(45, 0.03, 0.5, seed=42)

    trend = _trend(years, values)

    slope, _, low, high = sps.theilslopes(values, years, alpha=0.95)
    assert trend.sen.slope_per_decade == pytest.approx(slope * 10, rel=1e-9)
    assert trend.sen.ci95_low == pytest.approx(low * 10, rel=1e-6)
    assert trend.sen.ci95_high == pytest.approx(high * 10, rel=1e-6)
    assert trend.sen.ci95_low <= trend.sen.slope_per_decade <= trend.sen.ci95_high


def test_sen_slope_matches_pymannkendall() -> None:
    values = noisy_line(45, -0.04, 0.6, seed=21)
    trend = _trend(year_range(45), values)
    assert trend.sen.slope_per_decade == pytest.approx(pmk.original_test(values).slope * 10)


# --------------------------------------------------------------------------
# Gaps, constant and short series
# --------------------------------------------------------------------------


def test_gaps_are_dropped_and_real_years_are_kept_as_x() -> None:
    years = year_range(45)
    raw = noisy_line(45, 0.04, 0.6, seed=9)
    values = with_gaps(raw, [0, 5, 6, 20, 21, 22, 44])

    trend = _trend(years, values)

    x, y = _valid(years, values)
    ref = sps.linregress(x, y)
    assert trend.n == 38
    assert trend.n_missing == 7
    assert trend.ols.slope_per_decade == pytest.approx(ref.slope * 10, rel=1e-9)
    assert trend.ols.p_value == pytest.approx(ref.pvalue, rel=1e-7)
    assert trend.ols.intercept == pytest.approx(ref.intercept + ref.slope * x[0], rel=1e-9)
    _assert_mk_matches(trend, [float(v) for v in y])
    sen, _, low, high = sps.theilslopes(y, x, alpha=0.95)
    assert trend.sen.slope_per_decade == pytest.approx(sen * 10, rel=1e-9)
    assert trend.sen.ci95_low == pytest.approx(low * 10, rel=1e-6)
    assert trend.sen.ci95_high == pytest.approx(high * 10, rel=1e-6)


def test_nan_and_infinity_count_as_missing() -> None:
    values: list[float | None] = list(noisy_line(20, 0.05, 0.3, seed=1))
    values[3] = math.nan
    values[4] = math.inf

    trend = _trend(year_range(20), values)

    assert trend.n == 18
    assert trend.n_missing == 2


def test_constant_series_returns_none() -> None:
    assert compute_trend(year_range(30), [3.5] * 30, UNIT) is None


def test_constant_series_with_gaps_returns_none() -> None:
    values = with_gaps([2.0] * 30, [4, 9])
    assert compute_trend(year_range(30), values, UNIT) is None


@pytest.mark.parametrize("n_valid", [0, 1, 5, MIN_YEARS_FOR_TREND - 1])
def test_too_short_series_returns_none(n_valid: int) -> None:
    values = noisy_line(n_valid, 0.5, 0.1, seed=2)
    assert compute_trend(year_range(n_valid), values, UNIT) is None


def test_ten_valid_years_is_enough() -> None:
    values = noisy_line(10, 0.5, 0.1, seed=2)
    assert compute_trend(year_range(10), values, UNIT) is not None


def test_many_years_but_fewer_than_ten_valid_returns_none() -> None:
    values = with_gaps(noisy_line(45, 0.1, 0.2, seed=2), list(range(9, 45)))
    assert compute_trend(year_range(45), values, UNIT) is None


def test_mismatched_lengths_raise() -> None:
    with pytest.raises(ValueError, match="same length"):
        compute_trend([1990, 1991], [1.0], UNIT)


def test_empty_input_returns_none() -> None:
    assert compute_trend([], [], UNIT) is None


# --------------------------------------------------------------------------
# Verdict fields
# --------------------------------------------------------------------------


def test_strong_evidence_when_both_tests_significant() -> None:
    trend = _trend(year_range(45), noisy_line(45, 0.05, 0.4, seed=4))
    assert trend.evidence == "strong"
    assert trend.significant is True
    assert trend.methods_agree is True
    assert trend.direction == "up"


def test_no_evidence_on_flat_noise() -> None:
    trend = _trend(year_range(45), noisy_line(45, 0.0, 1.0, seed=7))
    assert trend.evidence == "none"
    assert trend.significant is False
    assert trend.methods_agree is True


def test_mixed_when_only_ols_is_significant() -> None:
    rng = np.random.default_rng(29)
    values = [float(v) for v in rng.normal(0, 1, 30)]
    values[-1] += 9.0

    trend = _trend(year_range(30), values)

    assert trend.ols.p_value < 0.05 <= trend.mann_kendall.p_value
    assert trend.evidence == "mixed"
    assert trend.significant is False
    assert trend.methods_agree is False


def test_mixed_when_only_mann_kendall_is_significant() -> None:
    rng = np.random.default_rng(0)
    values = [float(v) for v in np.arange(30) * 0.1 + rng.normal(0, 0.25, 30)]
    values[-1] -= 15.0

    trend = _trend(year_range(30), values)

    assert trend.mann_kendall.p_value < 0.05 <= trend.ols.p_value
    assert trend.evidence == "mixed"
    assert trend.methods_agree is False


def test_direction_follows_sign_of_sen_slope() -> None:
    down = _trend(year_range(30), noisy_line(30, -0.1, 0.2, seed=1))
    assert down.direction == "down"
    assert down.sen.slope_per_decade < 0


def test_direction_is_flat_when_sen_slope_is_zero() -> None:
    values = [1.0, 2.0] * 6
    trend = _trend(year_range(12), values)
    assert trend.sen.slope_per_decade == 0
    assert trend.direction == "flat"


def test_total_change_is_ols_slope_times_span() -> None:
    years = year_range(45)
    trend = _trend(years, noisy_line(45, 0.03, 0.5, seed=42))
    expected = trend.ols.slope_per_decade / 10 * (years[-1] - years[0])
    assert trend.total_change == pytest.approx(expected)


def test_total_change_span_uses_first_and_last_valid_year() -> None:
    years = year_range(45)
    values = with_gaps(noisy_line(45, 0.03, 0.5, seed=42), [0, 1, 44])
    trend = _trend(years, values)
    expected = trend.ols.slope_per_decade / 10 * (years[43] - years[2])
    assert trend.total_change == pytest.approx(expected)


def test_percent_change_relative_to_mean() -> None:
    trend = _trend(year_range(45), noisy_line(45, 0.03, 0.5, seed=42))
    assert trend.percent_change == pytest.approx(trend.total_change / abs(trend.mean) * 100)


def test_percent_change_is_none_when_mean_is_near_zero() -> None:
    values = [v - 10.0 for v in noisy_line(45, 0.03, 1.0, seed=42)]
    shift = float(np.mean(values))
    values = [v - shift for v in values]
    trend = _trend(year_range(45), values)
    assert abs(trend.mean) < 1e-9
    assert trend.percent_change is None


def test_mean_std_unit_alpha_and_counts() -> None:
    values = noisy_line(45, 0.03, 0.5, seed=42)
    trend = _trend(year_range(45), values)
    assert trend.mean == pytest.approx(float(np.mean(values)))
    assert trend.std == pytest.approx(float(np.std(values, ddof=1)))
    assert trend.unit == UNIT
    assert trend.alpha == 0.05
    assert (trend.n, trend.n_missing) == (45, 0)


# --------------------------------------------------------------------------
# Autocorrelation
# --------------------------------------------------------------------------


def test_lag1_autocorrelation_of_detrended_residuals() -> None:
    years = year_range(45)
    noise = ar1_noise(45, phi=0.6, sigma=1.0, seed=8)
    values = [10 + 0.05 * i + e for i, e in enumerate(noise)]

    trend = _trend(years, values)

    slope, intercept = np.polyfit(years, values, 1)
    resid = np.array(values) - (slope * np.array(years) + intercept)
    expected = float(np.sum(resid[:-1] * resid[1:]) / np.sum(resid**2))
    assert trend.lag1_autocorrelation == pytest.approx(expected, rel=1e-9)
    assert trend.lag1_autocorrelation > 0.3


def test_lag1_autocorrelation_is_small_for_white_noise() -> None:
    trend = _trend(year_range(45), noisy_line(45, 0.02, 1.0, seed=99))
    assert abs(trend.lag1_autocorrelation) < 0.3


# --------------------------------------------------------------------------
# fit_line
# --------------------------------------------------------------------------


def test_fit_line_matches_polyfit_and_confidence_band() -> None:
    years = year_range(45)
    values = noisy_line(45, 0.03, 0.5, seed=42)

    fit = fit_line(years, values)

    slope, intercept = np.polyfit(years, values, 1)
    x = np.array(years, float)
    resid = np.array(values) - (slope * x + intercept)
    s = math.sqrt(np.sum(resid**2) / 43)
    half = (
        sps.t.ppf(0.975, 43)
        * s
        * np.sqrt(1 / 45 + (x - x.mean()) ** 2 / np.sum((x - x.mean()) ** 2))
    )
    assert [p.year for p in fit] == years
    assert [p.value for p in fit] == pytest.approx(list(slope * x + intercept))
    assert [p.ci_high - p.value for p in fit] == pytest.approx(list(half))
    assert [p.value - p.ci_low for p in fit] == pytest.approx(list(half))


def test_fit_line_covers_first_to_last_valid_year_including_gaps() -> None:
    years = year_range(45)
    values = with_gaps(noisy_line(45, 0.03, 0.5, seed=42), [0, 1, 20, 44])

    fit = fit_line(years, values)

    assert [p.year for p in fit] == years[2:44]


def test_fit_line_is_consistent_with_trend_intercept() -> None:
    years = year_range(45)
    values = noisy_line(45, 0.03, 0.5, seed=42)
    fit = fit_line(years, values)
    assert fit[0].value == pytest.approx(_trend(years, values).ols.intercept)


def test_fit_line_is_empty_when_there_is_no_trend() -> None:
    assert fit_line(year_range(30), [1.0] * 30) == []
    assert fit_line(year_range(5), [1.0, 2.0, 3.0, 4.0, 5.0]) == []


# --------------------------------------------------------------------------
# Benjamini-Hochberg
# --------------------------------------------------------------------------


def test_benjamini_hochberg_hand_worked_example() -> None:
    # sorted: .005 .01 .03 .04 -> raw .02 .02 .04 .04 -> already monotone
    assert benjamini_hochberg([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_benjamini_hochberg_enforces_monotonicity() -> None:
    # sorted .001 .04 .041 -> raw .003 .06 .041 -> running minimum .003 .041 .041
    assert benjamini_hochberg([0.041, 0.001, 0.04]) == pytest.approx([0.041, 0.003, 0.041])


def test_benjamini_hochberg_caps_at_one() -> None:
    assert benjamini_hochberg([0.9, 0.95, 0.99]) == pytest.approx([0.99, 0.99, 0.99])
    assert benjamini_hochberg([0.8, 1.0]) == pytest.approx([1.0, 1.0])


def test_benjamini_hochberg_matches_scipy() -> None:
    rng = np.random.default_rng(0)
    p = [float(v) for v in np.concatenate([rng.uniform(0, 0.02, 40), rng.uniform(0, 1, 360)])]
    ref = sps.false_discovery_control(p, method="bh")
    assert benjamini_hochberg(p) == pytest.approx(list(ref))


def test_benjamini_hochberg_handles_ties() -> None:
    p = [0.02, 0.02, 0.5, 0.02]
    assert benjamini_hochberg(p) == pytest.approx(list(sps.false_discovery_control(p)))


def test_benjamini_hochberg_edge_cases() -> None:
    assert benjamini_hochberg([]) == []
    assert benjamini_hochberg([0.03]) == [0.03]


@pytest.mark.parametrize("bad", [[-0.1, 0.2], [0.2, 1.5], [0.1, math.nan]])
def test_benjamini_hochberg_rejects_invalid_p_values(bad: list[float]) -> None:
    with pytest.raises(ValueError, match="p-values"):
        benjamini_hochberg(bad)


# --------------------------------------------------------------------------
# Pearson
# --------------------------------------------------------------------------


def test_pearson_matches_numpy() -> None:
    a = noisy_line(40, 0.1, 1.0, seed=1)
    b = [x * 0.5 + e for x, e in zip(a, noisy_line(40, 0, 0.5, seed=2), strict=True)]
    assert pearson(a, b) == pytest.approx(float(np.corrcoef(a, b)[0, 1]))


def test_pearson_uses_only_years_where_both_are_present() -> None:
    a: list[float | None] = [1.0, 2.0, None, 4.0, 5.0, 7.0]
    b: list[float | None] = [2.0, None, 3.0, 5.0, 4.0, 9.0]
    expected = float(np.corrcoef([1.0, 4.0, 5.0, 7.0], [2.0, 5.0, 4.0, 9.0])[0, 1])
    assert pearson(a, b) == pytest.approx(expected)


def test_pearson_none_with_fewer_than_three_pairs() -> None:
    assert pearson([1.0, 2.0, None], [1.0, 3.0, 4.0]) is None
    assert pearson([], []) is None


def test_pearson_none_when_one_series_is_constant() -> None:
    assert pearson([1.0, 1.0, 1.0, 1.0], [1.0, 2.0, 3.0, 4.0]) is None


def test_pearson_perfect_correlation_is_bounded() -> None:
    r = pearson([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0])
    assert r is not None
    assert -1.0 <= r <= 1.0
    assert r == pytest.approx(1.0)


def test_pearson_mismatched_lengths_raise() -> None:
    with pytest.raises(ValueError, match="same length"):
        pearson([1.0, 2.0], [1.0])


# --------------------------------------------------------------------------
# Performance
# --------------------------------------------------------------------------


def test_compute_trend_is_fast_enough_for_the_trend_map() -> None:
    years = year_range(45)
    values = noisy_line(45, 0.03, 0.5, seed=42)
    compute_trend(years, values, UNIT)  # warm-up (imports)

    runs = 200
    start = time.perf_counter()
    for _ in range(runs):
        compute_trend(years, values, UNIT)
    per_call_ms = (time.perf_counter() - start) / runs * 1000

    assert per_call_ms < 10.0  # target is well under 5 ms; loose bound avoids flakiness


def test_duplicate_years_raise() -> None:
    years = year_range(12)
    years[5] = years[4]
    with pytest.raises(ValueError, match="unique"):
        compute_trend(years, noisy_line(12, 0.1, 0.3, seed=1), UNIT)


def test_unsorted_years_give_the_same_result_as_sorted() -> None:
    years = year_range(20)
    values = noisy_line(20, 0.1, 0.5, seed=6)
    shuffled = list(reversed(range(20)))
    a = _trend(years, values)
    b = _trend([years[i] for i in shuffled], [values[i] for i in shuffled])
    assert a == b
