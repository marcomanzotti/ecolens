"""Hamed and Rao (1998) corrected Mann-Kendall, checked against pymannkendall."""

from __future__ import annotations

import numpy as np
import pymannkendall as pmk
import pytest

from tests.engine_series import ar1_noise, noisy_line, with_gaps, year_range
from trend_detective.models import MannKendallResult
from trend_detective.stats import compute_trend, hamed_rao_p_value

TOLERANCE = 1e-9

# pymannkendall itself warns when the corrected variance is negative (it then returns NaN).
pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")


def _ar1_trend(n: int, phi: float, slope: float, seed: int) -> list[float]:
    noise = ar1_noise(n, phi, 1.0, seed)
    return [slope * i + v for i, v in enumerate(noise)]


def _hr(values: list[float]) -> float | None:
    n = len(values)
    return hamed_rao_p_value(np.arange(1981.0, 1981.0 + n), np.array(values, dtype=float))


CASES = {
    "white-noise-flat": noisy_line(45, 0.0, 1.0, seed=1),
    "white-noise-trend": noisy_line(45, 0.05, 1.0, seed=2),
    "ar1-0.6-trend": _ar1_trend(45, 0.6, 0.04, seed=3),
    "ar1-0.85-strong": _ar1_trend(45, 0.85, 0.02, seed=4),
    "ar1-0.85-short": _ar1_trend(20, 0.85, 0.05, seed=5),
    "ar1-minus-0.6": _ar1_trend(45, -0.6, 0.03, seed=6),
    "ar1-minus-0.8-n30": _ar1_trend(30, -0.8, 0.0, seed=7),
    "ties-rounded": [round(v, 0) for v in _ar1_trend(45, 0.7, 0.05, seed=8)],
    "n10": _ar1_trend(10, 0.5, 0.2, seed=9),
    "n12-noisy": noisy_line(12, 0.1, 1.0, seed=10),
    "n25-ar-0.4": _ar1_trend(25, 0.4, 0.06, seed=11),
}


@pytest.mark.parametrize("name", CASES)
def test_matches_pymannkendall(name: str) -> None:
    values = CASES[name]
    reference = pmk.hamed_rao_modification_test(values).p

    ours = _hr(values)

    if np.isnan(reference):
        assert ours is None
    else:
        assert ours is not None
        assert abs(ours - reference) < TOLERANCE


def test_many_random_series_stay_within_tolerance() -> None:
    worst = 0.0
    compared = 0
    for seed in range(400):
        phi = (seed % 9 - 4) / 5.0
        n = 10 + seed % 36
        values = _ar1_trend(n, phi, 0.02 * (seed % 5), seed=seed)
        reference = pmk.hamed_rao_modification_test(values).p
        ours = _hr(values)
        if np.isnan(reference):
            assert ours is None
            continue
        assert ours is not None
        worst = max(worst, abs(ours - reference))
        compared += 1
    assert compared > 300
    assert worst < TOLERANCE


def test_positive_autocorrelation_makes_p_larger_than_uncorrected() -> None:
    years = year_range(45)
    values = _ar1_trend(45, 0.8, 0.03, seed=21)
    trend = compute_trend(years, values, "u")

    assert trend is not None
    assert trend.mann_kendall.p_value_hamed_rao is not None
    assert trend.mann_kendall.p_value_hamed_rao > trend.mann_kendall.p_value


def test_gapped_series_uses_real_years_and_is_finite() -> None:
    values = with_gaps(_ar1_trend(45, 0.5, 0.05, seed=22), [3, 4, 20])
    p = compute_trend(year_range(45), values, "u")

    assert p is not None
    assert p.n == 42
    hr = p.mann_kendall.p_value_hamed_rao
    assert hr is not None and 0.0 <= hr <= 1.0


def test_returns_none_when_corrected_variance_is_not_positive() -> None:
    # strongly alternating ranks: the correction factor is negative (pymannkendall gives NaN)
    values = _ar1_trend(21, -0.4, 0.02, seed=11)
    assert np.isnan(pmk.hamed_rao_modification_test(values).p)

    assert _hr(values) is None


def test_perfect_line_cannot_be_corrected() -> None:
    assert hamed_rao_p_value(np.arange(20.0), np.arange(20.0) * 2.0) is None


def test_result_model_defaults_to_null_and_validates_range() -> None:
    result = MannKendallResult(s=1.0, z=0.5, tau=0.1, p_value=0.5)
    assert result.p_value_hamed_rao is None
    with pytest.raises(ValueError):
        MannKendallResult(s=1.0, z=0.5, tau=0.1, p_value=0.5, p_value_hamed_rao=1.5)


def test_white_noise_series_is_not_corrected_and_flag_is_false() -> None:
    years = year_range(45)
    values = noisy_line(45, 0.05, 1.0, seed=33)
    trend = compute_trend(years, values, "u")

    assert trend is not None
    assert abs(trend.lag1_autocorrelation) <= 0.3
    assert trend.autocorrelation_corrected is False
    assert trend.mann_kendall.p_value_hamed_rao is not None  # still reported


@pytest.mark.parametrize("seed", range(40, 52))
def test_verdict_uses_corrected_p_when_autocorrelation_is_high(seed: int) -> None:
    years = year_range(45)
    values = _ar1_trend(45, 0.85, 0.03, seed=seed)
    trend = compute_trend(years, values, "u")

    assert trend is not None
    hr = trend.mann_kendall.p_value_hamed_rao
    assert abs(trend.lag1_autocorrelation) > 0.3
    assert trend.autocorrelation_corrected is (hr is not None)
    assert hr is not None
    ols_sig = trend.ols.p_value < trend.alpha
    expected = (
        "strong"
        if ols_sig and hr < trend.alpha
        else "mixed"
        if ols_sig or hr < trend.alpha
        else "none"
    )
    assert trend.evidence == expected
    assert trend.methods_agree is (ols_sig == (hr < trend.alpha))


def test_a_trend_significant_only_before_correction_stops_being_strong() -> None:
    years = year_range(45)
    found = []
    for seed in range(200, 260):
        trend = compute_trend(years, _ar1_trend(45, 0.85, 0.03, seed=seed), "u")
        assert trend is not None
        hr = trend.mann_kendall.p_value_hamed_rao
        if hr is not None and trend.mann_kendall.p_value < 0.05 <= hr:
            found.append(trend)
    assert found, "no series changed verdict; widen the seed range"
    assert all(t.evidence != "strong" and not t.significant for t in found)
