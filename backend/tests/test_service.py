"""TrendInvestigator: the use cases on top of a SeriesSource (stats replaced by fakes)."""

from __future__ import annotations

import pytest

from tests.investigation_helpers import (
    FULL,
    NIAMEY,
    FakeSeriesSource,
    line,
    wiggle,
)
from trend_detective import catalog
from trend_detective import models as m
from trend_detective.errors import NoDataError, UnknownVariableError, UpstreamError
from trend_detective.ports import GridSeries
from trend_detective.service import TrendInvestigator

pytestmark = pytest.mark.usefixtures("fake_stats")

N = 45
BBOX = m.BBox(lat_min=10, lat_max=12, lon_min=-5, lon_max=-3)


def rising(start: float = 1.0, step: float = 0.02, amplitude: float = 0.05) -> list[float | None]:
    return line(start, step, noise=lambda i: amplitude * wiggle(i))


def late_series() -> list[float | None]:
    """A series that starts in 2001, like PW (in POWER's cm)."""
    return [None] * 20 + line(2.5, 0.02, n=25, noise=lambda i: 0.05 * wiggle(i))


def investigator(
    points: dict[str, list[float | None]] | None = None,
    grid: list[GridSeries] | None = None,
    error: Exception | None = None,
) -> tuple[TrendInvestigator, FakeSeriesSource]:
    source = FakeSeriesSource(points=points, grid=grid or [], error=error)
    return TrendInvestigator(source), source


# -- reference data ---------------------------------------------------------


def test_catalog_and_places_come_from_the_modules() -> None:
    service, _ = investigator()

    assert service.catalog() == catalog.build_catalog()
    assert len(service.places().places) == 16


# -- case -------------------------------------------------------------------


async def test_case_builds_every_part_of_the_result() -> None:
    service, source = investigator({"PRECTOTCORR": rising()})

    result = await service.case(NIAMEY, "PRECTOTCORR", FULL, "annual")

    assert result.location == NIAMEY
    assert result.variable.id == "PRECTOTCORR"
    assert result.period == FULL and result.season == "annual"
    assert [p.year for p in result.series] == list(range(1981, 2026))
    assert len(result.fit) == 45
    assert result.trend is not None and result.trend.n == 45
    assert result.emergence is not None
    assert result.verdict.evidence == result.trend.evidence
    assert "Niamey, Niger" in result.verdict.where
    assert result.limitations
    assert source.point_calls == [(NIAMEY, ("PRECTOTCORR",), FULL, "annual")]


async def test_case_series_values_are_the_source_values() -> None:
    values = rising()
    service, _ = investigator({"PRECTOTCORR": values})

    result = await service.case(NIAMEY, "PRECTOTCORR", FULL, "annual")

    assert [p.value for p in result.series] == values


async def test_case_converts_to_display_units_before_any_statistic() -> None:
    cm = rising(2.5, 0.02, 0.05)  # PW is distributed in cm of water
    service, _ = investigator({"PW": cm})

    result = await service.case(NIAMEY, "PW", FULL, "annual")

    assert [p.value for p in result.series] == pytest.approx([v * 10 for v in cm if v is not None])
    assert result.trend is not None
    assert result.trend.unit == "kg/m²"
    assert result.trend.mean == pytest.approx(sum(v for v in cm if v is not None) * 10 / 45)
    assert any("centimetres" in text for text in result.limitations)


async def test_case_for_a_variable_that_starts_late_still_works() -> None:
    values: list[float | None] = [None] * 20 + line(
        2.5, 0.02, n=25, noise=lambda i: 0.05 * wiggle(i)
    )
    service, _ = investigator({"PW": values})

    result = await service.case(NIAMEY, "PW", FULL, "annual")

    assert len(result.series) == 45
    assert [p.value for p in result.series[:20]] == [None] * 20
    assert result.trend is not None and result.trend.n == 25 and result.trend.n_missing == 20
    assert any("only start in 2001" in text for text in result.limitations)
    assert any("20 years have no data" in c for c in result.verdict.caveats)


async def test_case_with_too_few_valid_years_is_insufficient_not_an_error() -> None:
    values: list[float | None] = [None] * 39 + line(1.0, 0.1, n=6)
    service, _ = investigator({"PRECTOTCORR": values})

    result = await service.case(NIAMEY, "PRECTOTCORR", FULL, "annual")

    assert result.trend is None
    assert result.fit == []
    assert result.emergence is None
    assert result.verdict.evidence == "insufficient"
    assert "6" in result.verdict.how_sure
    assert len(result.series) == 45


async def test_case_with_a_constant_series_is_insufficient() -> None:
    service, _ = investigator({"SNODP": [0.0] * N})

    result = await service.case(NIAMEY, "SNODP", FULL, "annual")

    assert result.trend is None
    assert result.verdict.evidence == "insufficient"
    assert "same value" in result.verdict.how_sure


async def test_case_passes_period_and_season_to_the_source() -> None:
    period = m.Period(start_year=2001, end_year=2025)
    service, source = investigator({"PRECTOTCORR": rising()})

    result = await service.case(NIAMEY, "PRECTOTCORR", period, "JJA")

    assert source.point_calls[0][2:] == (period, "JJA")
    assert result.period == period and result.season == "JJA"
    assert [p.year for p in result.series] == list(range(2001, 2026))
    assert "June to August" in result.verdict.where


async def test_case_uses_coordinates_when_the_label_is_missing() -> None:
    service, _ = investigator({"PRECTOTCORR": rising()})

    result = await service.case(m.Location(lat=13.51, lon=2.11), "PRECTOTCORR", FULL, "annual")

    assert result.verdict.where.startswith("13.51°N, 2.11°E")


async def test_case_unknown_variable_is_rejected_before_calling_the_source() -> None:
    service, source = investigator({"PRECTOTCORR": rising()})

    with pytest.raises(UnknownVariableError):
        await service.case(NIAMEY, "NOPE", FULL, "annual")

    assert source.point_calls == []


async def test_case_without_any_value_is_a_no_data_error() -> None:
    absent, _ = investigator({})
    all_missing, _ = investigator({"SNODP": [None] * N})

    with pytest.raises(NoDataError, match="snow depth"):
        await absent.case(NIAMEY, "SNODP", FULL, "annual")
    with pytest.raises(NoDataError):
        await all_missing.case(NIAMEY, "SNODP", FULL, "annual")


async def test_source_errors_pass_through() -> None:
    service, _ = investigator(error=UpstreamError("down"))

    with pytest.raises(UpstreamError, match="down"):
        await service.case(NIAMEY, "PRECTOTCORR", FULL, "annual")


async def test_series_of_the_wrong_length_is_an_upstream_error() -> None:
    class ShortSource(FakeSeriesSource):
        async def point_series(self, location, variable_ids, period, season):  # type: ignore[no-untyped-def]
            return {"PRECTOTCORR": [1.0] * 10}

    with pytest.raises(UpstreamError):
        await TrendInvestigator(ShortSource()).case(NIAMEY, "PRECTOTCORR", FULL, "annual")


# -- lineup -----------------------------------------------------------------


async def test_lineup_of_the_whole_catalog_makes_one_source_call() -> None:
    service, source = investigator({"T2M": rising(20, 0.03), "PRECTOTCORR": rising()})

    result = await service.lineup(NIAMEY, FULL, "annual")

    assert len(source.point_calls) == 1
    assert list(source.point_calls[0][1]) == [v.id for v in catalog.VARIABLES]
    assert len(result.items) == len(catalog.VARIABLES)
    assert {i.variable.id for i in result.items if i.status == "ok"} == {"T2M", "PRECTOTCORR"}
    assert sum(1 for i in result.items if i.status == "no_data") == len(catalog.VARIABLES) - 2


async def test_lineup_themes_narrow_the_variables() -> None:
    service, source = investigator({"T2M": rising(20, 0.03), "PRECTOTCORR": rising()})

    result = await service.lineup(NIAMEY, FULL, "annual", themes=["temperature"])

    expected = [v.id for v in catalog.VARIABLES if v.theme == "temperature"]
    assert list(source.point_calls[0][1]) == expected
    assert {i.variable.id for i in result.items} == set(expected)


async def test_lineup_variable_ids_win_over_themes() -> None:
    service, source = investigator({"T2M": rising(20, 0.03), "PRECTOTCORR": rising()})

    result = await service.lineup(
        NIAMEY, FULL, "annual", themes=["temperature"], variable_ids=["PRECTOTCORR", "T2M"]
    )

    assert list(source.point_calls[0][1]) == ["PRECTOTCORR", "T2M"]
    assert len(result.items) == 2


async def test_lineup_converts_units_and_tests_late_variables() -> None:
    late = late_series()
    service, _ = investigator({"PW": late})

    result = await service.lineup(NIAMEY, FULL, "annual", variable_ids=["PW"])

    item = result.items[0]
    assert item.status == "ok" and item.n == 25
    assert item.sparkline[20] == pytest.approx(late[20] * 10)  # type: ignore[operator]
    assert len(item.sparkline) == 45


async def test_lineup_unknown_variable_is_rejected() -> None:
    service, source = investigator({})

    with pytest.raises(UnknownVariableError):
        await service.lineup(NIAMEY, FULL, "annual", variable_ids=["T2M", "NOPE"])

    assert source.point_calls == []


async def test_lineup_with_nothing_testable_is_a_no_data_error() -> None:
    service, _ = investigator({"SNODP": [0.0] * N})

    with pytest.raises(NoDataError):
        await service.lineup(NIAMEY, FULL, "annual", variable_ids=["SNODP", "FRSNO"])


async def test_lineup_source_errors_pass_through() -> None:
    service, _ = investigator(error=UpstreamError("down"))

    with pytest.raises(UpstreamError):
        await service.lineup(NIAMEY, FULL, "annual")


# -- witnesses --------------------------------------------------------------


def vapour_points() -> dict[str, list[float | None]]:
    pw: list[float | None] = [None] * 20 + line(2.5, 0.03, n=25, noise=lambda i: 0.05 * wiggle(i))
    return {"TQV": rising(25, 0.1, 0.3), "PW": pw}


@pytest.mark.parametrize("asked", ["TQV", "PW"])
async def test_witnesses_compare_the_whole_group_from_either_member(asked: str) -> None:
    service, source = investigator(vapour_points())

    result = await service.witnesses(NIAMEY, asked, FULL, "annual")

    assert list(source.point_calls[0][1]) == ["TQV", "PW"]
    assert [w.variable.id for w in result.witnesses] == ["TQV", "PW"]
    assert result.common_period == m.Period(start_year=2001, end_year=2025)
    assert result.quantity == "Water vapour in the air column"
    assert result.agreement.level in {"agree", "partly", "disagree"}


async def test_witnesses_convert_pw_to_kg_per_m2() -> None:
    service, _ = investigator(vapour_points())

    result = await service.witnesses(NIAMEY, "TQV", FULL, "annual")

    pw = result.witnesses[1]
    assert pw.series[0].value == pytest.approx(vapour_points()["PW"][20] * 10)  # type: ignore[operator]


async def test_witnesses_variable_without_group_is_rejected() -> None:
    service, source = investigator({})

    with pytest.raises(UnknownVariableError, match="witness"):
        await service.witnesses(NIAMEY, "T2M", FULL, "annual")
    with pytest.raises(UnknownVariableError):
        await service.witnesses(NIAMEY, "NOPE", FULL, "annual")

    assert source.point_calls == []


async def test_witnesses_with_a_missing_witness_is_a_no_data_error() -> None:
    service, _ = investigator({"TQV": rising(25, 0.1, 0.3)})

    with pytest.raises(NoDataError):
        await service.witnesses(NIAMEY, "TQV", FULL, "annual")


# -- trendmap ---------------------------------------------------------------


def grid() -> list[GridSeries]:
    return [
        GridSeries(lat=10.0, lon=-5.0, values=tuple(rising(1.0, 0.05, 0.05))),
        GridSeries(lat=10.5, lon=-5.0, values=tuple(rising(3.0, -0.05, 0.05))),
        GridSeries(lat=10.0, lon=-4.375, values=(None,) * N),
    ]


async def test_trendmap_asks_the_source_for_the_box() -> None:
    service, source = investigator(grid=grid())

    result = await service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")

    assert source.region_calls == [(BBOX, "PRECTOTCORR", FULL, "annual")]
    assert result.variable.id == "PRECTOTCORR"
    assert result.summary.n_cells == 3 and result.summary.n_valid == 2
    assert result.opposite_twin is not None


async def test_trendmap_converts_units() -> None:
    cm = [GridSeries(lat=10.0, lon=-5.0, values=tuple(rising(2.5, 0.05, 0.05)))]
    cm.append(GridSeries(lat=10.5, lon=-5.0, values=tuple(rising(2.5, 0.05, 0.05))))
    service, _ = investigator(grid=cm)

    result = await service.trendmap("PW", BBOX, FULL, "annual")

    assert result.cells[0].slope_per_decade == pytest.approx(5.0, rel=0.1)  # 0.5 cm -> 5 kg/m²


async def test_trendmap_unknown_variable_is_rejected() -> None:
    service, source = investigator(grid=grid())

    with pytest.raises(UnknownVariableError):
        await service.trendmap("NOPE", BBOX, FULL, "annual")

    assert source.region_calls == []


async def test_trendmap_without_data_is_a_no_data_error() -> None:
    service, _ = investigator(grid=[])

    with pytest.raises(NoDataError):
        await service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")


async def test_trendmap_cells_of_the_wrong_length_are_an_upstream_error() -> None:
    service, _ = investigator(grid=[GridSeries(lat=10.0, lon=-5.0, values=(1.0, 2.0))])

    with pytest.raises(UpstreamError):
        await service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")


async def test_trendmap_source_errors_pass_through() -> None:
    service, _ = investigator(error=UpstreamError("down"))

    with pytest.raises(UpstreamError):
        await service.trendmap("PRECTOTCORR", BBOX, FULL, "annual")
