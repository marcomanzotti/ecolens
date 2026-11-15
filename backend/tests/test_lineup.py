"""Line-up (block A): Mann-Kendall per variable, BH correction, ranking by standardized slope."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.investigation_helpers import (
    FULL,
    NIAMEY,
    line,
    make_trend,
    variable,
    wiggle,
)
from trend_detective import models as m
from trend_detective import stats
from trend_detective.lineup import build_lineup

pytestmark = pytest.mark.usefixtures("fake_stats")

Series = dict[str, list[float | None]]


def lineup(
    series: Series, ids: Sequence[str] | None = None, period: m.Period = FULL
) -> m.LineupResult:
    variables = [variable(i) for i in (ids or list(series))]
    return build_lineup(NIAMEY, period, "annual", variables, series)


def noisy(step: float, amplitude: float) -> list[float | None]:
    return line(10.0, step, noise=lambda i: amplitude * wiggle(i))


def test_items_are_ranked_by_absolute_standardized_slope() -> None:
    series = {
        "T2M": noisy(0.5, 6.0),  # up, noisy
        "PRECTOTCORR": noisy(-0.5, 0.1),  # down, nearly a perfect line
        "WS10M": noisy(0.5, 1.5),  # up, a little noisy
    }

    result = lineup(series)

    assert [i.variable.id for i in result.items] == ["PRECTOTCORR", "WS10M", "T2M"]
    assert [i.rank for i in result.items] == [1, 2, 3]
    magnitudes = [abs(i.standardized_slope or 0) for i in result.items]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_item_carries_mann_kendall_sen_and_standardization() -> None:
    result = lineup({"T2M": noisy(0.3, 0.1)})
    item = result.items[0]
    trend = stats.compute_trend(list(range(1981, 2026)), noisy(0.3, 0.1), "°C")
    assert trend is not None

    assert item.status == "ok"
    assert item.n == 45
    assert item.direction == "up"
    assert item.slope_per_decade == pytest.approx(trend.sen.slope_per_decade)
    assert item.standardized_slope == pytest.approx(trend.sen.slope_per_decade / trend.std)
    assert item.tau == trend.mann_kendall.tau
    assert item.p_value == trend.mann_kendall.p_value


def test_negative_slope_keeps_its_sign() -> None:
    item = lineup({"T2M": noisy(-0.3, 0.1)}).items[0]

    assert item.direction == "down"
    assert item.slope_per_decade is not None and item.slope_per_decade < 0
    assert item.standardized_slope is not None and item.standardized_slope < 0


def test_variables_without_data_come_last_with_no_rank() -> None:
    constant: list[float | None] = [0.0] * 45
    series: Series = {
        "SNODP": constant,  # constant: nothing to test
        "T2M": noisy(0.3, 0.1),
        "FRSNO": [None] * 45,  # no value at all
    }

    result = lineup(series, ids=["SNODP", "T2M", "FRSNO", "PS"])  # PS: absent from the source

    assert [i.variable.id for i in result.items][0] == "T2M"
    tail = result.items[1:]
    assert {i.variable.id for i in tail} == {"SNODP", "FRSNO", "PS"}
    for item in tail:
        assert item.status == "no_data"
        assert item.rank is None
        assert item.slope_per_decade is None
        assert item.standardized_slope is None
        assert item.p_value is None and item.p_adjusted is None and item.tau is None
        assert item.direction is None
        assert item.significant is False


def test_no_data_items_keep_catalog_order_and_report_valid_count() -> None:
    sparse: list[float | None] = [1.0, 2.0, 3.0] + [None] * 42

    result = lineup({"FRSNO": [None] * 45, "SNODP": sparse}, ids=["SNODP", "FRSNO", "PS"])

    assert [i.variable.id for i in result.items] == ["SNODP", "FRSNO", "PS"]
    assert [i.n for i in result.items] == [3, 0, 0]


def test_sparkline_has_one_entry_per_year_of_the_period() -> None:
    period = m.Period(start_year=2001, end_year=2025)
    values = line(5.0, 0.1, n=25)
    late_start: list[float | None] = [None] * 5 + line(1.0, 0.1, n=20)

    result = lineup({"T2M": values, "PW": late_start, "PS": [None] * 25}, period=period)

    assert all(len(i.sparkline) == 25 for i in result.items)
    pw = next(i for i in result.items if i.variable.id == "PW")
    assert pw.sparkline[:5] == [None] * 5
    assert pw.sparkline[5:] == late_start[5:]
    assert pw.n == 20


def test_variable_that_starts_late_is_still_tested() -> None:
    late_start: list[float | None] = [None] * 20 + line(1.0, 0.1, n=25)

    item = lineup({"PW": late_start}).items[0]

    assert item.status == "ok"
    assert item.n == 25


def test_too_few_valid_years_is_no_data() -> None:
    few: list[float | None] = [None] * 36 + line(1.0, 0.1, n=9)

    item = lineup({"T2M": few}).items[0]

    assert item.status == "no_data"
    assert item.n == 9


def _fake_with_p(monkeypatch: pytest.MonkeyPatch, p_by_first_value: dict[float, float]) -> None:
    def compute(
        years: Sequence[int], values: Sequence[float | None], unit: str
    ) -> m.TrendStats | None:
        first = next(v for v in values if v is not None)
        p = p_by_first_value[first]
        return make_trend(mk_p=p, ols_p=p, unit=unit, sen_slope=0.5 + first / 1000)

    monkeypatch.setattr(stats, "compute_trend", compute)


def test_significance_uses_the_adjusted_p_value(monkeypatch: pytest.MonkeyPatch) -> None:
    ids = ["T2M", "T2M_MAX", "T2M_MIN", "T2M_RANGE", "TS", "T2MDEW", "FROST_DAYS", "PS"]
    # p = 0.03 is below alpha on its own but not once corrected for 8 tests (0.03 * 8 / 2).
    p_values = [0.03, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0001]
    codes = {float(i): p for i, p in enumerate(p_values)}
    _fake_with_p(monkeypatch, codes)
    series: Series = {vid: line(float(i), 0.1) for i, vid in enumerate(ids)}

    result = lineup(series, ids=ids)

    by_id = {i.variable.id: i for i in result.items}
    weak = by_id["T2M"]
    assert weak.p_value == 0.03
    assert weak.p_adjusted == pytest.approx(0.12)
    assert weak.significant is False
    strong = by_id["PS"]
    assert strong.p_adjusted == pytest.approx(0.0008)
    assert strong.significant is True
    assert result.n_significant == 1
    assert result.correction.n_tests == 8
    assert result.correction.method == "fdr_bh"
    assert result.correction.alpha == m.ALPHA


def test_adjusted_p_is_never_below_raw_p() -> None:
    series = {vid: noisy(0.05 * i, 1.0) for i, vid in enumerate(["T2M", "TS", "PS", "WS10M"])}

    result = lineup(series)

    for item in result.items:
        assert item.p_value is not None and item.p_adjusted is not None
        assert item.p_adjusted >= item.p_value
        assert item.significant == (item.p_adjusted < m.ALPHA)


def test_only_testable_variables_count_as_tests() -> None:
    series: Series = {"T2M": noisy(0.3, 0.1), "TS": noisy(0.2, 0.1), "SNODP": [0.0] * 45}

    result = lineup(series, ids=["T2M", "TS", "SNODP", "PS"])

    assert result.correction.n_tests == 2


def test_summary_counts_significant_and_untestable_variables() -> None:
    series: Series = {"T2M": noisy(0.3, 0.1), "TS": noisy(0.0, 3.0), "SNODP": [0.0] * 45}

    result = lineup(series)

    assert result.n_significant == 1
    assert result.summary == (
        "1 of 2 tested variables shows a significant trend after correcting for the number of "
        "tests. 1 variable had too little data to test."
    )


def test_summary_when_nothing_could_be_tested() -> None:
    result = lineup({"SNODP": [0.0] * 45})

    assert result.n_significant == 0
    assert result.correction.n_tests == 0
    assert result.summary == "No variable had enough data to test for a trend."


def test_result_echoes_request_and_validates() -> None:
    result = lineup({"T2M": noisy(0.3, 0.1)})

    assert result.location == NIAMEY
    assert result.period == FULL
    assert result.season == "annual"
    assert m.LineupResult.model_validate(result.model_dump()) == result


def test_ties_in_standardized_slope_keep_catalog_order() -> None:
    same = line(10.0, 0.5)

    result = lineup({"T2M": same, "TS": list(same)}, ids=["T2M", "TS"])

    assert [i.variable.id for i in result.items] == ["T2M", "TS"]
    assert [i.rank for i in result.items] == [1, 2]
