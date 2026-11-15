"""Verdict: deterministic plain-English rules from TrendStats."""

from __future__ import annotations

import pytest

from tests.investigation_helpers import FULL, NIAMEY, make_trend, variable
from trend_detective import models as m
from trend_detective.verdict import build_verdict

PRECIP = variable("PRECTOTCORR")


def verdict(
    trend: m.TrendStats | None,
    *,
    var: m.Variable = PRECIP,
    location: m.Location = NIAMEY,
    period: m.Period = FULL,
    season: m.Season = "annual",
    n_valid: int = 0,
) -> m.Verdict:
    return build_verdict(var, location, period, season, trend, n_valid=n_valid)


def test_strong_rise_closes_the_case() -> None:
    result = verdict(make_trend(direction="up", evidence="strong"))

    assert result.evidence == "strong"
    assert result.headline == "Case closed: precipitation is rising."
    assert result.what == "Precipitation is rising."


def test_strong_fall_uses_falling() -> None:
    result = verdict(make_trend(direction="down", evidence="strong", sen_slope=-0.4))

    assert result.headline == "Case closed: precipitation is falling."


def test_where_uses_label_and_period() -> None:
    assert verdict(make_trend()).where == "Niamey, Niger, 1981–2025."


def test_where_falls_back_to_coordinates_without_label() -> None:
    result = verdict(make_trend(), location=m.Location(lat=13.51, lon=-2.11))

    assert result.where == "13.51°N, 2.11°W, 1981–2025."


def test_where_formats_southern_and_eastern_coordinates() -> None:
    result = verdict(make_trend(), location=m.Location(lat=-3.1, lon=60.0))

    assert result.where.startswith("3.10°S, 60.00°E, ")


def test_where_names_the_season() -> None:
    result = verdict(make_trend(), season="JJA")

    assert result.where == "Niamey, Niger, 1981–2025 (June to August)."


def test_how_much_gives_sen_slope_and_total_change() -> None:
    trend = make_trend(sen_slope=0.081, total_change=0.42, percent_change=29.0)

    how_much = verdict(trend).how_much

    assert "+0.0810 mm/day per decade" in how_much
    assert "+0.420 mm/day over the whole period" in how_much
    assert "+29%" in how_much


def test_how_much_omits_percent_when_unavailable() -> None:
    trend = make_trend(percent_change=None)

    assert "%" not in verdict(trend).how_much


def test_how_much_drops_unit_for_dimensionless_variables() -> None:
    var = variable("GWETTOP")
    trend = make_trend(unit="0–1", sen_slope=-0.012, total_change=-0.05, direction="down")

    how_much = verdict(trend, var=var).how_much

    assert "0–1" not in how_much
    assert "−0.0120 per decade" in how_much


def test_how_sure_reports_both_p_values_when_strong() -> None:
    trend = make_trend(ols_p=0.0011, mk_p=0.0039)

    how_sure = verdict(trend).how_sure

    assert "Both tests" in how_sure
    assert "t-test p = 0.0011" in how_sure
    assert "Mann-Kendall p = 0.0039" in how_sure


def test_tiny_p_values_are_floored() -> None:
    trend = make_trend(ols_p=1e-9, mk_p=3e-7)

    assert "p < 0.001" in verdict(trend).how_sure


def test_mixed_evidence_is_inconclusive_not_a_verdict() -> None:
    trend = make_trend(evidence="mixed", ols_p=0.03, mk_p=0.2)

    result = verdict(trend)

    assert result.evidence == "mixed"
    assert result.headline.startswith("Inconclusive")
    assert "Case closed" not in result.headline
    assert "Only one of the two tests" in result.how_sure
    assert any("disagree" in c for c in result.caveats)


def test_no_evidence_says_no_significant_trend() -> None:
    trend = make_trend(evidence="none", ols_p=0.4, mk_p=0.5, sen_slope=0.01)

    result = verdict(trend)

    assert result.evidence == "none"
    assert result.headline == "No significant trend found in precipitation."
    assert "chance" in result.how_sure
    assert "rising" not in result.what


def test_insufficient_without_trend_states_no_numbers() -> None:
    result = verdict(None, n_valid=6)

    assert result.evidence == "insufficient"
    assert result.headline == "Not enough data to judge precipitation."
    assert "6" in result.how_sure
    assert "at least 10" in result.how_sure
    assert result.how_much == "No slope was computed."
    assert result.caveats == []


def test_insufficient_constant_series_is_explained() -> None:
    result = verdict(None, n_valid=45)

    assert "same value" in result.how_sure


def test_high_positive_autocorrelation_warns_of_overconfidence() -> None:
    result = verdict(make_trend(lag1=0.42))

    caveat = next(c for c in result.caveats if "autocorrelation" in c)
    assert "+0.42" in caveat
    assert "over-confident" in caveat


def test_high_negative_autocorrelation_does_not_claim_overconfidence() -> None:
    result = verdict(make_trend(lag1=-0.45))

    caveat = next(c for c in result.caveats if "autocorrelation" in c)
    assert "-0.45" in caveat
    assert "over-confident" not in caveat


@pytest.mark.parametrize("lag1", [0.3, -0.3, 0.0, 0.2999])
def test_autocorrelation_at_or_below_threshold_has_no_caveat(lag1: float) -> None:
    result = verdict(make_trend(lag1=lag1))

    assert not any("autocorrelation" in c for c in result.caveats)


def test_missing_years_are_mentioned() -> None:
    result = verdict(make_trend(n=42, n_missing=3))

    assert any("3 years have no data" in c and "42" in c for c in result.caveats)


def test_single_missing_year_is_singular() -> None:
    result = verdict(make_trend(n=44, n_missing=1))

    assert any("1 year has no data" in c for c in result.caveats)


def test_short_record_is_flagged() -> None:
    result = verdict(make_trend(n=12))

    assert any("Short record" in c and "12" in c for c in result.caveats)


def test_long_clean_record_has_no_caveats() -> None:
    assert verdict(make_trend(n=45, n_missing=0, lag1=0.05)).caveats == []


def test_flat_direction_is_worded_as_flat() -> None:
    result = verdict(make_trend(direction="flat", evidence="none", sen_slope=0.0))

    assert "rising" not in result.what and "falling" not in result.what


def test_name_with_leading_acronym_keeps_its_capitals() -> None:
    result = verdict(make_trend(), var=variable("ALLSKY_SFC_UV_INDEX"))

    assert result.headline == "Case closed: UV index is rising."


def test_verdict_is_deterministic() -> None:
    trend = make_trend()

    assert verdict(trend) == verdict(trend)


def test_mixed_evidence_with_a_flat_direction_makes_no_claim_of_motion() -> None:
    result = verdict(make_trend(direction="flat", evidence="mixed", sen_slope=0.0))

    assert result.what == "Precipitation shows mixed signals."


def test_insufficient_with_no_valid_year_does_not_cite_a_count() -> None:
    result = verdict(None, n_valid=0)

    assert result.how_sure == "A trend test needs at least 10 years with data."


def test_not_established_slope_is_labelled_as_such() -> None:
    result = verdict(make_trend(evidence="none", ols_p=0.4, mk_p=0.5))

    assert "not statistically established" in result.how_much


def test_corrected_caveat_says_mann_kendall_was_corrected_and_t_test_was_not() -> None:
    result = verdict(make_trend(lag1=0.42, corrected=True, mk_p_hr=0.03, mk_p=0.001))

    caveat = next(c for c in result.caveats if "autocorrelation" in c)
    assert "+0.42" in caveat
    assert "Hamed" in caveat
    assert "t-test" in caveat
    assert "over-confident" not in caveat


def test_corrected_how_sure_quotes_the_corrected_p_value() -> None:
    result = verdict(
        make_trend(
            evidence="strong", ols_p=0.001, mk_p=0.0001, mk_p_hr=0.02, lag1=0.5, corrected=True
        )
    )

    assert "corrected for autocorrelation" in result.how_sure
    assert "0.02" in result.how_sure
    assert "0.0001" not in result.how_sure


def test_uncorrected_how_sure_has_no_correction_wording() -> None:
    result = verdict(make_trend(evidence="strong", lag1=0.1))

    assert "corrected" not in result.how_sure


def test_high_autocorrelation_without_hamed_rao_keeps_the_overconfidence_caveat() -> None:
    result = verdict(make_trend(lag1=0.42, corrected=False))

    caveat = next(c for c in result.caveats if "autocorrelation" in c)
    assert "over-confident" in caveat
