"""Block C: expanding-window emergence and the Weatherhead et al. (1998) detection time."""

from __future__ import annotations

import math

import numpy as np
import pymannkendall as pmk
import pytest

from tests.engine_series import (
    ar1_noise,
    exact_slope_series,
    noisy_line,
    round_trip_values,
    with_gaps,
    year_range,
)
from trend_detective.emergence import (
    WEATHERHEAD_COEFFICIENT,
    compute_emergence,
    first_persistent_year,
    weatherhead_years_needed,
)
from trend_detective.models import ALPHA, MIN_YEARS_FOR_TREND, Emergence
from trend_detective.stats import compute_trend


def _emergence(years: list[int], values: list[float | None]) -> Emergence:
    result = compute_emergence(years, values)
    assert result is not None
    return result


# --------------------------------------------------------------------------
# Returns None
# --------------------------------------------------------------------------


def test_none_with_fewer_than_ten_valid_years() -> None:
    values = noisy_line(MIN_YEARS_FOR_TREND - 1, 0.5, 0.1, seed=1)
    assert compute_emergence(year_range(len(values)), values) is None


def test_none_for_constant_series() -> None:
    assert compute_emergence(year_range(30), [2.0] * 30) is None


def test_none_for_empty_input() -> None:
    assert compute_emergence([], []) is None


def test_mismatched_lengths_raise() -> None:
    with pytest.raises(ValueError, match="same length"):
        compute_emergence([1990, 1991], [1.0])


# --------------------------------------------------------------------------
# Running window
# --------------------------------------------------------------------------


def test_running_windows_match_pymannkendall() -> None:
    years = year_range(45)
    values = noisy_line(45, 0.03, 0.5, seed=42)

    result = _emergence(years, values)

    assert len(result.running) == 45 - MIN_YEARS_FOR_TREND + 1
    assert result.running[0].end_year == years[MIN_YEARS_FOR_TREND - 1]
    assert result.running[-1].end_year == years[-1]
    for point in result.running:
        window = values[: point.end_year - years[0] + 1]
        ref = pmk.original_test(window)
        assert point.p_value == pytest.approx(ref.p, rel=1e-7, abs=1e-12)
        assert point.slope_per_decade == pytest.approx(ref.slope * 10)


def test_running_uses_only_years_with_data_and_keeps_real_years() -> None:
    years = year_range(45)
    values = with_gaps(noisy_line(45, 0.05, 0.4, seed=3), [0, 1, 14, 15, 30])

    result = _emergence(years, values)

    valid_years = [y for y, v in zip(years, values, strict=True) if v is not None]
    assert [p.end_year for p in result.running] == valid_years[MIN_YEARS_FOR_TREND - 1 :]
    last = result.running[-1]
    ref = pmk.original_test([v for v in values if v is not None])
    assert last.p_value == pytest.approx(ref.p, rel=1e-7)


def test_final_running_point_equals_full_series_trend() -> None:
    years = year_range(45)
    values = noisy_line(45, 0.03, 0.5, seed=42)
    trend = compute_trend(years, values, "u")
    assert trend is not None

    last = _emergence(years, values).running[-1]

    assert last.p_value == pytest.approx(trend.mann_kendall.p_value)
    assert last.slope_per_decade == pytest.approx(trend.sen.slope_per_decade)


# --------------------------------------------------------------------------
# Emerged year
# --------------------------------------------------------------------------


def test_first_persistent_year_basic() -> None:
    years = [2000, 2001, 2002, 2003, 2004]
    assert first_persistent_year(years, [0.5, 0.04, 0.2, 0.01, 0.01], ALPHA) == 2003


def test_first_persistent_year_when_always_significant() -> None:
    assert first_persistent_year([2000, 2001], [0.01, 0.02], ALPHA) == 2000


def test_first_persistent_year_none_when_last_not_significant() -> None:
    assert first_persistent_year([2000, 2001, 2002], [0.01, 0.01, 0.2], ALPHA) is None


def test_first_persistent_year_p_equal_to_alpha_is_not_significant() -> None:
    assert first_persistent_year([2000, 2001], [0.01, ALPHA], ALPHA) is None


def test_first_persistent_year_empty() -> None:
    assert first_persistent_year([], [], ALPHA) is None


def test_strong_trend_emerges_and_matches_definition() -> None:
    years = year_range(45)
    result = _emergence(years, noisy_line(45, 0.1, 0.5, seed=4))

    assert result.status == "emerged"
    assert result.emerged_year is not None
    from_emergence = [p for p in result.running if p.end_year >= result.emerged_year]
    assert all(p.p_value < ALPHA for p in from_emergence)
    before = [p for p in result.running if p.end_year < result.emerged_year]
    assert not before or before[-1].p_value >= ALPHA
    assert result.additional_years == 0


def test_flat_noise_has_not_emerged() -> None:
    result = _emergence(year_range(45), noisy_line(45, 0.0, 1.0, seed=7))
    assert result.status == "not_yet"
    assert result.emerged_year is None


def test_trend_that_fades_by_the_end_is_not_emerged() -> None:
    values = [float(v) for v in np.arange(25) * 1.0] + round_trip_values(20, top=24.0)
    result = _emergence(year_range(45), values)
    assert any(p.p_value < ALPHA for p in result.running)  # it was significant at some point
    assert result.running[-1].p_value >= ALPHA
    assert result.status == "not_yet"
    assert result.emerged_year is None


# --------------------------------------------------------------------------
# Weatherhead et al. (1998)
# --------------------------------------------------------------------------


def test_weatherhead_coefficient_is_3_3() -> None:
    assert WEATHERHEAD_COEFFICIENT == 3.3


def test_weatherhead_hand_worked_white_noise() -> None:
    # n* = (3.3 * 1 / 0.1) ** (2/3) = 33 ** (2/3)
    assert weatherhead_years_needed(1.0, 0.1, 0.0) == pytest.approx(33 ** (2 / 3))
    assert weatherhead_years_needed(1.0, 0.1, 0.0) == pytest.approx(10.2883, abs=1e-3)


def test_weatherhead_hand_worked_with_autocorrelation() -> None:
    # sqrt((1 + .5) / (1 - .5)) = sqrt(3)
    expected = (33 * math.sqrt(3)) ** (2 / 3)
    assert weatherhead_years_needed(1.0, 0.1, 0.5) == pytest.approx(expected)


def test_weatherhead_symmetric_in_slope_sign() -> None:
    assert weatherhead_years_needed(1.0, -0.1, 0.3) == weatherhead_years_needed(1.0, 0.1, 0.3)


def test_weatherhead_more_noise_or_memory_needs_longer_records() -> None:
    base = weatherhead_years_needed(1.0, 0.1, 0.0)
    assert weatherhead_years_needed(2.0, 0.1, 0.0) > base
    assert weatherhead_years_needed(1.0, 0.1, 0.5) > base
    assert weatherhead_years_needed(1.0, 0.2, 0.0) < base


def test_weatherhead_zero_slope_has_no_finite_answer() -> None:
    assert weatherhead_years_needed(1.0, 0.0, 0.2) is None


def test_weatherhead_extreme_autocorrelation_is_clamped_and_finite() -> None:
    result = weatherhead_years_needed(1.0, 0.1, 1.0)
    assert result is not None
    assert math.isfinite(result)


def test_weatherhead_annual_resolution_factor_is_cube_root_of_twelve() -> None:
    literal = weatherhead_years_needed(1.0, 0.1, 0.0)
    annual = weatherhead_years_needed(1.0, 0.1, 0.0, annual_resolution=True)
    assert literal is not None and annual is not None
    assert annual / literal == pytest.approx(12 ** (1 / 3))


def test_slope_variance_derivation_behind_the_resolution_factor() -> None:
    """Var(slope) = sigma^2 / Sxx: n^3/12 for yearly points, n^3 for monthly points."""
    n = 60
    yearly = np.arange(n, dtype=float)
    monthly = np.arange(12 * n, dtype=float) / 12.0
    sxx_yearly = float(np.sum((yearly - yearly.mean()) ** 2))
    sxx_monthly = float(np.sum((monthly - monthly.mean()) ** 2))
    assert sxx_yearly / (n**3 / 12) == pytest.approx(1.0, rel=1e-3)
    assert sxx_monthly / n**3 == pytest.approx(1.0, rel=1e-3)


def test_years_needed_uses_ols_slope_residual_noise_and_lag1() -> None:
    years = year_range(45)
    noise = ar1_noise(45, 0.5, 0.8, seed=12)
    values = [10 + 0.02 * i + e for i, e in enumerate(noise)]

    result = _emergence(years, values)

    slope, intercept = np.polyfit(years, values, 1)
    resid = np.array(values) - (slope * np.array(years) + intercept)
    sigma = math.sqrt(float(np.sum(resid**2)) / 43)
    phi = float(np.sum(resid[:-1] * resid[1:]) / np.sum(resid**2))
    assert result.noise_std == pytest.approx(sigma)
    assert result.autocorrelation == pytest.approx(phi)
    assert result.years_needed == pytest.approx(
        weatherhead_years_needed(sigma, slope, phi, annual_resolution=True)
    )


def test_additional_years_is_years_needed_minus_available_rounded_up() -> None:
    years = year_range(45)
    result = _emergence(years, exact_slope_series(45, 0.005, 1.0, seed=5))
    assert result.status == "not_yet"
    assert result.years_needed is not None
    assert result.additional_years == math.ceil(result.years_needed - 45)
    assert result.additional_years > 0


def test_additional_years_never_negative_when_formula_says_long_enough() -> None:
    years = year_range(45)
    result = _emergence(years, noisy_line(45, 0.0, 1.0, seed=7))
    assert result.additional_years is None or result.additional_years >= 0


def test_available_years_span_includes_gaps() -> None:
    years = year_range(45)
    values = with_gaps(exact_slope_series(45, 0.005, 1.0, seed=5), [0, 1, 2])
    result = _emergence(years, values)
    assert result.status == "not_yet"
    assert result.years_needed is not None
    assert result.additional_years == math.ceil(result.years_needed - 42)


# --------------------------------------------------------------------------
# Explanation
# --------------------------------------------------------------------------


def _sentences(text: str) -> int:
    return len([s for s in text.replace("?", ".").split(". ") if s.strip()])


def test_explanation_when_emerged_names_the_year() -> None:
    result = _emergence(year_range(45), noisy_line(45, 0.1, 0.5, seed=4))
    assert str(result.emerged_year) in result.explanation
    assert 1 <= _sentences(result.explanation) <= 2


def test_explanation_when_not_yet_mentions_years_still_needed() -> None:
    result = _emergence(year_range(45), exact_slope_series(45, 0.005, 1.0, seed=5))
    assert result.status == "not_yet"
    assert "more years" in result.explanation
    assert 1 <= _sentences(result.explanation) <= 2


def test_explanation_for_a_slope_of_exactly_zero() -> None:
    half = [1.0, 2.0, 1.5, 3.0, 2.0, 1.0, 2.5, 2.0, 1.0, 3.0]
    values = half + half[::-1]  # palindrome: the OLS slope is zero up to rounding
    result = _emergence(year_range(20), values)
    assert result.years_needed is None
    assert result.additional_years is None
    assert "no overall" in result.explanation
    assert _sentences(result.explanation) <= 2


def test_explanation_for_an_enormous_detection_time_is_capped() -> None:
    values = exact_slope_series(45, 1e-5, 1.0, seed=5)
    result = _emergence(year_range(45), values)
    assert "200" in result.explanation
    assert result.years_needed is not None and result.years_needed > 200


def test_explanation_has_no_statistical_jargon() -> None:
    for slope, seed in ((0.1, 4), (0.002, 5), (0.0, 7)):
        text = _emergence(year_range(45), noisy_line(45, slope, 1.0, seed)).explanation
        for word in ("Mann-Kendall", "p-value", "autocorrelation", "Weatherhead", "sigma"):
            assert word not in text


# --------------------------------------------------------------------------
# Performance
# --------------------------------------------------------------------------


def test_compute_emergence_is_fast() -> None:
    import time

    years = year_range(45)
    values = noisy_line(45, 0.03, 0.5, seed=42)
    compute_emergence(years, values)
    start = time.perf_counter()
    for _ in range(50):
        compute_emergence(years, values)
    assert (time.perf_counter() - start) / 50 < 0.05


def test_literal_contract_formula_understates_detection_time_for_annual_points() -> None:
    """With yearly points the slope is detectable (omega / se = 3.3) only at the longer record.

    se(slope) = sigma / sqrt(Sxx) with Sxx = n (n^2 - 1) / 12 for n yearly points, white noise.
    """
    sigma, omega = 1.0, 0.1

    def signal_to_noise(n_years: float) -> float:
        sxx = n_years * (n_years**2 - 1) / 12
        return omega / (sigma / math.sqrt(sxx))

    literal = weatherhead_years_needed(sigma, omega, 0.0)
    annual = weatherhead_years_needed(sigma, omega, 0.0, annual_resolution=True)
    assert literal is not None and annual is not None
    assert signal_to_noise(annual) == pytest.approx(3.3, rel=0.02)
    assert signal_to_noise(literal) < 1.0
