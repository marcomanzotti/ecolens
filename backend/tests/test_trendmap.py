"""Trend map (block B): one cell per grid point, BH across all cells, summary and twin."""

from __future__ import annotations

import pytest

from tests.investigation_helpers import FULL, line, variable, wiggle
from trend_detective import models as m
from trend_detective.errors import NoDataError
from trend_detective.ports import GridSeries
from trend_detective.trendmap import build_trendmap

pytestmark = pytest.mark.usefixtures("fake_stats")

BBOX = m.BBox(lat_min=10, lat_max=12, lon_min=-5, lon_max=-3)
PRECIP = variable("PRECTOTCORR")
LAT_STEP, LON_STEP = 0.5, 0.625


def cell(lat: float, lon: float, step: float, amplitude: float = 0.1) -> GridSeries:
    values = line(10.0, step, noise=lambda i: amplitude * wiggle(i))
    return GridSeries(lat=lat, lon=lon, values=tuple(values))


def empty(lat: float, lon: float) -> GridSeries:
    return GridSeries(lat=lat, lon=lon, values=(None,) * 45)


def six_cells() -> list[GridSeries]:
    """Two rows of three cells, in scrambled order."""
    return [
        cell(10.5, -4.375, -0.1),  # falling, weak
        cell(10.0, -5.0, 0.5),  # rising, strongest
        empty(10.5, -3.75),  # no data
        cell(10.0, -3.75, 0.0, amplitude=3.0),  # flat noise: not significant
        cell(10.5, -5.0, -0.3),  # falling, strongest
        cell(10.0, -4.375, 0.2),  # rising, weaker
    ]


def trendmap(grid: list[GridSeries], season: m.Season = "annual") -> m.TrendMapResult:
    return build_trendmap(PRECIP, BBOX, FULL, season, grid)


def test_cells_are_listed_row_by_row_with_the_grid_coordinates() -> None:
    result = trendmap(six_cells())

    assert [(c.lat, c.lon) for c in result.cells] == [
        (10.0, -5.0),
        (10.0, -4.375),
        (10.0, -3.75),
        (10.5, -5.0),
        (10.5, -4.375),
        (10.5, -3.75),
    ]


def test_grid_spec_comes_from_the_returned_points() -> None:
    result = trendmap(six_cells())

    assert result.grid == m.GridSpec(lat_step=0.5, lon_step=0.625, n_lat=2, n_lon=3)


def test_grid_step_has_no_floating_point_noise() -> None:
    grid = [cell(10.0 + 0.1 * i, -5.0, 0.1) for i in range(3)]
    grid += [cell(10.0 + 0.1 * i, -4.9, 0.1) for i in range(3)]

    result = trendmap(grid)

    assert result.grid.lat_step == 0.1
    assert result.grid.lon_step == pytest.approx(0.1)


def test_single_row_falls_back_to_the_merra2_step() -> None:
    result = trendmap([cell(10.0, -5.0, 0.1), cell(10.0, -4.375, 0.1)])

    assert result.grid == m.GridSpec(lat_step=0.5, lon_step=0.625, n_lat=1, n_lon=2)


def test_cell_carries_sen_slope_direction_and_p_values() -> None:
    result = trendmap(six_cells())
    rising = result.cells[0]
    falling = result.cells[3]

    assert rising.n == 45
    assert rising.direction == "up"
    assert rising.slope_per_decade is not None and rising.slope_per_decade == pytest.approx(
        5.0, rel=0.1
    )
    assert rising.p_value is not None and rising.p_adjusted is not None
    assert rising.p_adjusted >= rising.p_value
    assert rising.significant is True
    assert falling.direction == "down"
    assert falling.slope_per_decade is not None and falling.slope_per_decade < 0


def test_cell_without_data_is_kept_and_empty() -> None:
    result = trendmap(six_cells())
    nodata = result.cells[5]

    assert nodata == m.TrendMapCell(
        lat=10.5,
        lon=-3.75,
        n=0,
        slope_per_decade=None,
        direction=None,
        p_value=None,
        p_adjusted=None,
        significant=False,
    )


def test_benjamini_hochberg_counts_only_cells_with_data() -> None:
    result = trendmap(six_cells())

    assert result.correction.n_tests == 5
    assert result.correction.method == "fdr_bh"
    assert result.summary.n_cells == 6
    assert result.summary.n_valid == 5


def test_significance_uses_adjusted_p() -> None:
    result = trendmap(six_cells())

    for c in result.cells:
        if c.p_adjusted is not None:
            assert c.significant == (c.p_adjusted < m.ALPHA)


def test_summary_counts_and_colour_limit() -> None:
    result = trendmap(six_cells())
    slopes = [abs(c.slope_per_decade) for c in result.cells if c.slope_per_decade is not None]

    assert result.summary.n_up_significant == 2
    assert result.summary.n_down_significant == 2
    assert result.summary.max_abs_slope == pytest.approx(max(slopes))
    assert result.summary.text == (
        "Of 5 cells tested, 2 cells are rising significantly and 2 cells are falling significantly."
    )


def test_summary_text_uses_singular_for_one_cell() -> None:
    grid = [cell(10.0, -5.0, 0.5), cell(10.0, -4.375, 0.0, amplitude=3.0)]
    grid += [cell(10.5, -5.0, 0.0, amplitude=3.0), cell(10.5, -4.375, 0.0, amplitude=3.0)]

    text = trendmap(grid).summary.text

    assert "1 cell is rising significantly" in text
    assert "0 cells are falling significantly" in text


def test_twin_pairs_the_strongest_rising_and_falling_cells() -> None:
    result = trendmap(six_cells())
    twin = result.opposite_twin

    assert twin is not None
    assert (twin.up.lat, twin.up.lon) == (10.0, -5.0)
    assert (twin.down.lat, twin.down.lon) == (10.5, -5.0)
    assert twin.up.significant and twin.down.significant
    assert twin.up.slope_per_decade is not None and twin.up.slope_per_decade > 0
    assert twin.down.slope_per_decade is not None and twin.down.slope_per_decade < 0
    assert twin.distance_km == pytest.approx(55.6, abs=0.1)
    assert "opposite direction" in twin.text and "km apart" in twin.text


def test_twin_distance_on_the_equator() -> None:
    grid = [cell(0.0, 0.0, 0.5), cell(0.0, 1.0, -0.5), cell(0.5, 0.0, 0.0, amplitude=3.0)]
    grid += [cell(0.5, 1.0, 0.0, amplitude=3.0)]

    twin = trendmap(grid).opposite_twin

    assert twin is not None
    assert twin.distance_km == pytest.approx(111.2, abs=0.2)


def test_twin_is_null_without_a_significant_falling_cell() -> None:
    grid = [cell(10.0, -5.0, 0.5), cell(10.0, -4.375, 0.4), cell(10.5, -5.0, 0.3)]
    grid += [cell(10.5, -4.375, -0.0, amplitude=3.0)]

    result = trendmap(grid)

    assert result.summary.n_up_significant >= 1
    assert result.summary.n_down_significant == 0
    assert result.opposite_twin is None


def test_twin_ignores_non_significant_cells() -> None:
    grid = [cell(10.0, -5.0, 0.5), cell(10.0, -4.375, -0.001, amplitude=4.0)]
    grid += [cell(10.5, -5.0, 0.0, amplitude=3.0), cell(10.5, -4.375, 0.0, amplitude=3.0)]

    assert trendmap(grid).opposite_twin is None


def test_no_cell_with_data_is_a_no_data_error() -> None:
    with pytest.raises(NoDataError):
        trendmap([empty(10.0, -5.0), empty(10.5, -5.0)])


def test_empty_grid_is_a_no_data_error() -> None:
    with pytest.raises(NoDataError):
        trendmap([])


def test_cells_with_too_few_valid_years_count_as_no_data() -> None:
    sparse = GridSeries(lat=10.0, lon=-5.0, values=(1.0, 2.0, 3.0) + (None,) * 42)

    result = trendmap([sparse, cell(10.0, -4.375, 0.5)])

    assert result.cells[0].n == 3
    assert result.cells[0].slope_per_decade is None
    assert result.summary.n_valid == 1


def test_result_echoes_request_and_validates() -> None:
    result = trendmap(six_cells(), season="MAM")

    assert result.variable == PRECIP
    assert result.bbox == BBOX
    assert result.period == FULL
    assert result.season == "MAM"
    assert m.TrendMapResult.model_validate(result.model_dump()) == result
