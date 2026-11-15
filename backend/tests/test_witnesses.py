"""Witnesses (block D): variables of one witness group over their common period."""

from __future__ import annotations

import pytest

from tests.investigation_helpers import NIAMEY, line, wiggle
from trend_detective import catalog
from trend_detective import models as m
from trend_detective.errors import NoDataError
from trend_detective.witnesses import build_witnesses

pytestmark = pytest.mark.usefixtures("fake_stats")

GROUP = catalog.witness_group_members("column_water_vapour")  # TQV, PW
FULL = m.Period()
N = 45


def noisy(start: float, step: float, amplitude: float, n: int = N) -> list[float | None]:
    return line(start, step, n=n, noise=lambda i: amplitude * wiggle(i))


def late(values: list[float | None], first_index: int) -> list[float | None]:
    """The series with its first `first_index` years missing, like PW before 2001."""
    return [None] * first_index + values[first_index:]


def witnesses(
    tqv: list[float | None],
    pw: list[float | None],
    period: m.Period = FULL,
    season: m.Season = "annual",
) -> m.WitnessesResult:
    return build_witnesses(
        NIAMEY, period, season, "column_water_vapour", GROUP, {"TQV": tqv, "PW": pw}
    )


def test_group_is_the_water_vapour_pair() -> None:
    assert [v.id for v in GROUP] == ["TQV", "PW"]


def test_only_the_common_period_is_compared() -> None:
    result = witnesses(noisy(25, 0.1, 0.5), late(noisy(20, 0.1, 0.5), 20))

    assert result.common_period == m.Period(start_year=2001, end_year=2025)
    for witness in result.witnesses:
        assert [p.year for p in witness.series] == list(range(2001, 2026))
        assert witness.trend is not None
        assert witness.trend.n == 25


def test_series_is_cut_to_the_common_period_not_resampled() -> None:
    tqv = noisy(25, 0.1, 0.5)

    result = witnesses(tqv, late(noisy(20, 0.1, 0.5), 20))

    assert [p.value for p in result.witnesses[0].series] == tqv[20:]


def test_common_period_uses_the_latest_start_and_earliest_end() -> None:
    tqv: list[float | None] = [*noisy(25, 0.1, 0.5)[:40], None, None, None, None, None]
    pw = late(noisy(20, 0.1, 0.5), 18)

    result = witnesses(tqv, pw)

    assert result.common_period == m.Period(start_year=1999, end_year=2020)


def test_witnesses_follow_catalog_order_and_carry_fit_and_trend() -> None:
    result = witnesses(noisy(25, 0.1, 0.5), noisy(20, 0.1, 0.5))

    assert [w.variable.id for w in result.witnesses] == ["TQV", "PW"]
    for witness in result.witnesses:
        assert len(witness.fit) == len(witness.series)
        assert witness.trend is not None
        assert witness.trend.unit == "kg/m²"


def test_quantity_and_echoed_request() -> None:
    result = witnesses(noisy(25, 0.1, 0.5), noisy(20, 0.1, 0.5), season="JJA")

    assert result.quantity == "Water vapour in the air column"
    assert result.location == NIAMEY
    assert result.season == "JJA"


def test_agree_when_same_direction_and_all_significant() -> None:
    result = witnesses(noisy(25, 0.2, 0.3), noisy(20, 0.2, 0.3))
    agreement = result.agreement

    assert agreement.level == "agree"
    assert agreement.same_direction is True
    assert agreement.all_significant is True
    assert agreement.correlation is not None and agreement.correlation > 0.9
    assert "same way" in agreement.text


def test_partly_when_same_direction_but_one_not_significant() -> None:
    result = witnesses(noisy(25, 0.2, 0.3), noisy(20, 0.02, 3.0))
    agreement = result.agreement

    assert [w.trend.direction for w in result.witnesses if w.trend] == ["up", "up"]
    assert agreement.level == "partly"
    assert agreement.same_direction is True
    assert agreement.all_significant is False
    assert "not" in agreement.text


def test_disagree_when_directions_are_opposite() -> None:
    result = witnesses(noisy(25, 0.2, 0.3), noisy(40, -0.2, 0.3))
    agreement = result.agreement

    assert agreement.level == "disagree"
    assert agreement.same_direction is False
    assert agreement.correlation is not None and agreement.correlation < 0
    assert "different directions" in agreement.text


def test_disagree_even_when_only_one_trend_is_significant() -> None:
    result = witnesses(noisy(25, 0.2, 0.3), noisy(30, -0.01, 3.0))

    assert result.agreement.level == "disagree"
    assert result.agreement.all_significant is False


def test_insufficient_when_a_witness_cannot_be_tested() -> None:
    constant: list[float | None] = [27.0] * N

    result = witnesses(noisy(25, 0.2, 0.3), constant)
    agreement = result.agreement

    assert agreement.level == "insufficient"
    assert agreement.same_direction is None
    assert agreement.all_significant is None
    assert result.witnesses[1].trend is None
    assert result.witnesses[1].fit == []
    assert agreement.correlation is None


def test_witness_without_any_data_is_a_no_data_error() -> None:
    with pytest.raises(NoDataError, match="water vapour in the air column \\(CERES\\)"):
        witnesses(noisy(25, 0.2, 0.3), [None] * N)


def test_common_period_shorter_than_ten_years_is_a_no_data_error() -> None:
    period = m.Period(start_year=1981, end_year=2005)

    with pytest.raises(NoDataError, match="at least 10"):
        witnesses(noisy(25, 0.2, 0.3, n=25), late(noisy(20, 0.2, 0.3, n=25), 20), period=period)


def test_no_overlap_at_all_is_a_no_data_error() -> None:
    early = noisy(25, 0.2, 0.3)[:15] + [None] * 30
    only_late = late(noisy(20, 0.2, 0.3), 30)

    with pytest.raises(NoDataError, match="no years in common"):
        witnesses(early, only_late)


def test_limitations_state_independence_is_not_established() -> None:
    result = witnesses(noisy(25, 0.2, 0.3), late(noisy(20, 0.2, 0.3), 20))
    text = " ".join(result.limitations)

    assert "independent" in text and "not been established" in text
    assert "2001–2025" in text
    assert "correlation" in text
    assert "centimetres" in text  # the PW unit conversion is disclosed


def test_result_is_a_valid_model() -> None:
    result = witnesses(noisy(25, 0.2, 0.3), noisy(20, 0.2, 0.3))

    assert m.WitnessesResult.model_validate(result.model_dump()) == result
