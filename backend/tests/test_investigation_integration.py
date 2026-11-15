"""TrendInvestigator on the real engine and the saved NASA POWER samples (Niamey, Sahel box).

No fakes of the statistics here: these tests check that the results are valid models and
internally consistent, not specific numbers.
"""

from __future__ import annotations

import pytest

from tests.investigation_helpers import (
    FULL,
    NIAMEY,
    FakeSeriesSource,
    load_grid_samples,
    sample_point_source,
)
from trend_detective import catalog, stats
from trend_detective import models as m
from trend_detective.service import TrendInvestigator

BBOX = m.BBox(lat_min=10, lat_max=20, lon_min=-5, lon_max=5)
YEARS = list(range(1981, 2026))
ALL_IDS = [v.id for v in catalog.VARIABLES]


@pytest.fixture
def service() -> TrendInvestigator:
    return TrendInvestigator(sample_point_source())


def roundtrip[M: m.Model](result: M) -> M:
    return type(result).model_validate_json(result.model_dump_json())


# -- case -------------------------------------------------------------------


async def test_case_for_niamey_precipitation(service: TrendInvestigator) -> None:
    result = await service.case(NIAMEY, "PRECTOTCORR", FULL, "annual")

    assert roundtrip(result) == result
    trend = result.trend
    assert trend is not None and result.emergence is not None
    assert trend.n == 45 and trend.n_missing == 0 and trend.unit == "mm/day"
    assert [p.year for p in result.series] == YEARS
    assert [f.year for f in result.fit] == YEARS
    assert result.verdict.evidence == trend.evidence
    assert result.emergence.running[-1].end_year == 2025
    assert all(f.ci_low <= f.value <= f.ci_high for f in result.fit)


async def test_case_evidence_follows_the_two_p_values(service: TrendInvestigator) -> None:
    for variable_id in ("T2M", "PRECTOTCORR", "WS10M", "RH2M", "GWETROOT", "TO3"):
        trend = (await service.case(NIAMEY, variable_id, FULL, "annual")).trend

        assert trend is not None
        ols_sig, mk_sig = trend.ols.p_value < m.ALPHA, trend.mann_kendall.p_value < m.ALPHA
        expected = "strong" if ols_sig and mk_sig else "mixed" if ols_sig or mk_sig else "none"
        assert trend.evidence == expected
        assert trend.significant == (expected == "strong")


async def test_case_agrees_with_an_independent_computation(service: TrendInvestigator) -> None:
    from scipy import stats as sp

    result = await service.case(NIAMEY, "T2M", FULL, "annual")
    values = [p.value for p in result.series]
    assert None not in values
    fit = sp.linregress(YEARS, values)
    sen = sp.theilslopes(values, YEARS)

    assert result.trend is not None
    assert result.trend.ols.slope_per_decade == pytest.approx(fit.slope * 10)
    assert result.trend.ols.p_value == pytest.approx(fit.pvalue)
    assert result.trend.sen.slope_per_decade == pytest.approx(sen.slope * 10)


async def test_case_for_a_variable_that_starts_in_2001(service: TrendInvestigator) -> None:
    result = await service.case(NIAMEY, "PW", FULL, "annual")

    assert len(result.series) == 45
    assert [p.value for p in result.series[:20]] == [None] * 20
    assert result.trend is not None and result.trend.n == 25 and result.trend.n_missing == 20
    assert result.trend.unit == "kg/m²"
    # POWER gives cm; the display unit is kg/m², ten times larger.
    assert 10 < result.trend.mean < 60


async def test_case_for_a_constant_series_is_insufficient(service: TrendInvestigator) -> None:
    result = await service.case(NIAMEY, "FROST_DAYS", FULL, "annual")

    assert result.trend is None and result.emergence is None and result.fit == []
    assert result.verdict.evidence == "insufficient"
    assert roundtrip(result) == result


async def test_case_over_a_shorter_period(service: TrendInvestigator) -> None:
    period = m.Period(start_year=2006, end_year=2025)

    result = await service.case(NIAMEY, "T2M", period, "annual")

    assert [p.year for p in result.series] == list(range(2006, 2026))
    assert result.trend is not None and result.trend.n == 20


# -- lineup -----------------------------------------------------------------


async def test_lineup_of_the_whole_catalog_is_consistent(service: TrendInvestigator) -> None:
    result = await service.lineup(NIAMEY, FULL, "annual")

    assert roundtrip(result) == result
    ok = [i for i in result.items if i.status == "ok"]
    no_data = [i for i in result.items if i.status == "no_data"]
    assert len(ok) + len(no_data) == len(ALL_IDS) == len(result.items)
    assert result.items == [*ok, *no_data]  # no-data variables come last
    assert [i.rank for i in ok] == list(range(1, len(ok) + 1))
    assert all(i.rank is None for i in no_data)
    assert result.correction.n_tests == len(ok) and result.correction.method == "fdr_bh"
    assert result.n_significant == sum(i.significant for i in ok)
    magnitudes = [abs(i.standardized_slope or 0) for i in ok]
    assert magnitudes == sorted(magnitudes, reverse=True)
    assert all(len(i.sparkline) == 45 for i in result.items)


async def test_lineup_p_values_are_corrected_and_monotone(service: TrendInvestigator) -> None:
    result = await service.lineup(NIAMEY, FULL, "annual")
    ok = [i for i in result.items if i.status == "ok"]

    for item in ok:
        assert item.p_value is not None and item.p_adjusted is not None
        assert item.p_value <= item.p_adjusted <= 1.0
        assert item.significant == (item.p_adjusted < m.ALPHA)
    by_raw = sorted(ok, key=lambda i: i.p_value or 0)
    adjusted = [i.p_adjusted or 0 for i in by_raw]
    assert adjusted == sorted(adjusted)  # the correction never reorders the p-values


async def test_lineup_matches_the_case_of_the_same_variable(service: TrendInvestigator) -> None:
    lineup = await service.lineup(NIAMEY, FULL, "annual", variable_ids=["T2M", "PRECTOTCORR"])

    for item in lineup.items:
        case = await service.case(NIAMEY, item.variable.id, FULL, "annual")
        assert case.trend is not None
        assert item.p_value == pytest.approx(case.trend.mann_kendall.p_value)
        assert item.slope_per_decade == pytest.approx(case.trend.sen.slope_per_decade)
        assert item.standardized_slope == pytest.approx(
            case.trend.sen.slope_per_decade / case.trend.std
        )
        assert item.direction == case.trend.direction


async def test_lineup_handles_late_and_constant_variables(service: TrendInvestigator) -> None:
    result = await service.lineup(NIAMEY, FULL, "annual")
    by_id = {i.variable.id: i for i in result.items}

    assert by_id["PW"].status == "ok" and by_id["PW"].n == 25
    assert by_id["PW"].sparkline[:20] == [None] * 20
    assert by_id["FROST_DAYS"].status == "no_data"
    assert by_id["T2M"].status == "ok" and by_id["T2M"].n == 45


async def test_lineup_with_a_theme_and_a_period(service: TrendInvestigator) -> None:
    period = m.Period(start_year=2001, end_year=2025)

    result = await service.lineup(NIAMEY, period, "annual", themes=["temperature"])

    assert {i.variable.theme for i in result.items} == {"temperature"}
    assert all(len(i.sparkline) == 25 for i in result.items)


# -- witnesses --------------------------------------------------------------


async def test_witnesses_for_water_vapour(service: TrendInvestigator) -> None:
    result = await service.witnesses(NIAMEY, "TQV", FULL, "annual")

    assert roundtrip(result) == result
    assert result.common_period == m.Period(start_year=2001, end_year=2025)
    assert [w.variable.id for w in result.witnesses] == ["TQV", "PW"]
    trends = [w.trend for w in result.witnesses]
    assert all(t is not None and t.n == 25 for t in trends)
    assert all(len(w.series) == 25 and len(w.fit) == 25 for w in result.witnesses)
    agreement = result.agreement
    directions = {t.direction for t in trends if t}
    assert agreement.same_direction == (len(directions) == 1)
    assert agreement.all_significant == all(t.significant for t in trends if t)
    assert agreement.level == (
        "disagree"
        if not agreement.same_direction
        else "agree"
        if agreement.all_significant
        else "partly"
    )
    assert agreement.correlation is not None and -1 <= agreement.correlation <= 1


async def test_witnesses_correlation_is_pearson_over_the_common_period(
    service: TrendInvestigator,
) -> None:
    result = await service.witnesses(NIAMEY, "PW", FULL, "annual")
    a, b = ([p.value for p in w.series] for w in result.witnesses)

    assert result.agreement.correlation == pytest.approx(stats.pearson(a, b))


# -- trend map --------------------------------------------------------------


@pytest.fixture
def map_service() -> TrendInvestigator:
    return TrendInvestigator(FakeSeriesSource(grid=load_grid_samples(FULL)))


async def test_trendmap_of_the_sahel_box_is_consistent(map_service: TrendInvestigator) -> None:
    result = await map_service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")

    assert roundtrip(result) == result
    assert len(result.cells) == 357
    assert result.grid == m.GridSpec(lat_step=0.5, lon_step=0.625, n_lat=21, n_lon=17)
    assert [(c.lat, c.lon) for c in result.cells] == sorted((c.lat, c.lon) for c in result.cells)
    assert result.correction.n_tests == result.summary.n_valid == 357
    for cell in result.cells:
        assert cell.p_value is not None and cell.p_adjusted is not None
        assert cell.p_value <= cell.p_adjusted <= 1.0
        assert cell.significant == (cell.p_adjusted < m.ALPHA)
        assert cell.n == 45
        assert (cell.direction == "up") == ((cell.slope_per_decade or 0) > 0)


async def test_trendmap_summary_matches_the_cells(map_service: TrendInvestigator) -> None:
    result = await map_service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")
    cells, summary = result.cells, result.summary

    assert summary.n_cells == len(cells)
    assert summary.n_up_significant == sum(c.significant and c.direction == "up" for c in cells)
    assert summary.n_down_significant == sum(c.significant and c.direction == "down" for c in cells)
    assert summary.max_abs_slope == max(abs(c.slope_per_decade or 0) for c in cells)


async def test_trendmap_twin_cells_have_opposite_signs(map_service: TrendInvestigator) -> None:
    twin = (await map_service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")).opposite_twin

    assert twin is not None
    assert twin.up.significant and twin.down.significant
    assert (twin.up.slope_per_decade or 0) > 0 > (twin.down.slope_per_decade or 0)
    assert 0 < twin.distance_km < 1600  # the box is 10 degrees wide (about 1100 km)


async def test_trendmap_cell_matches_a_direct_computation(map_service: TrendInvestigator) -> None:
    grid = load_grid_samples(FULL)
    result = await map_service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")
    point = grid[100]
    direct = stats.compute_trend(YEARS, list(point.values), "mm/day")
    cell = next(c for c in result.cells if (c.lat, c.lon) == (point.lat, point.lon))

    assert direct is not None
    assert cell.slope_per_decade == pytest.approx(direct.sen.slope_per_decade)
    assert cell.p_value == pytest.approx(direct.mann_kendall.p_value)
