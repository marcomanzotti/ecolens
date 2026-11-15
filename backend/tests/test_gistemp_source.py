"""GISTEMP annual grid shipped in the package: lookup of the 2-degree cell and the file itself."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from trend_detective.sources import gistemp

YEARS = tuple(range(1981, 1991))


def _grid() -> gistemp.GistempGrid:
    """Every cell holds its own flat index / 100 + year offset, except one empty cell."""
    base = np.arange(90 * 180, dtype=float).reshape(90, 180) / 1000.0
    annual = np.stack([base + k * 0.1 for k in range(len(YEARS))])
    annual[:, 10, 20] = np.nan
    annual[3, 11, 21] = np.nan
    return gistemp.GistempGrid(years=YEARS, anomaly=annual)


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (0.0, 0.0, (45, 90)),
        (13.51, 2.11, (51, 91)),
        (-89.9, -179.9, (0, 0)),
        (89.9, 179.9, (89, 179)),
        (90.0, 0.0, (89, 90)),  # the pole belongs to the last row
        (-90.0, 0.0, (0, 90)),
        (0.0, 180.0, (45, 0)),  # +180 and -180 are the same meridian
        (0.0, -180.0, (45, 0)),
        (45.4, 12.3, (67, 96)),
    ],
)
def test_cell_index(lat: float, lon: float, expected: tuple[int, int]) -> None:
    assert gistemp.cell_index(lat, lon) == expected


def test_cell_centre_is_inside_the_cell() -> None:
    lat, lon = gistemp.cell_centre(51, 91)
    assert (lat, lon) == (13.0, 3.0)
    assert gistemp.cell_index(lat, lon) == (51, 91)


def test_cell_series_returns_one_value_per_requested_year() -> None:
    series = gistemp.cell_series(_grid(), 13.51, 2.11, [1981, 1982, 1990])

    expected_base = (51 * 180 + 91) / 1000.0
    assert series == pytest.approx([expected_base, expected_base + 0.1, expected_base + 0.9])


def test_cell_series_marks_missing_years_and_years_outside_the_grid() -> None:
    lat, lon = gistemp.cell_centre(11, 21)
    series = gistemp.cell_series(_grid(), lat, lon, [1980, 1984, 1985, 2030])

    assert series[0] is None
    assert series[1] is None  # NaN year in the grid (index 3 -> 1984)
    assert series[2] is not None
    assert series[3] is None


def test_cell_with_no_data_gives_none() -> None:
    lat, lon = gistemp.cell_centre(10, 20)

    assert gistemp.cell_series(_grid(), lat, lon, list(YEARS)) is None


def test_write_then_load_round_trips_to_a_hundredth_of_a_degree(tmp_path: Path) -> None:
    grid = _grid()
    path = tmp_path / "grid.npz"

    gistemp.write_grid(path, grid.years, grid.anomaly)
    loaded = gistemp.load_grid(path)

    assert loaded.years == grid.years
    assert loaded.anomaly.shape == grid.anomaly.shape
    both_nan = np.isnan(loaded.anomaly) & np.isnan(grid.anomaly)
    assert np.array_equal(np.isnan(loaded.anomaly), np.isnan(grid.anomaly))
    diff = np.abs(np.nan_to_num(loaded.anomaly) - np.nan_to_num(grid.anomaly))
    assert diff[~both_nan].max() <= 0.0051


def test_write_grid_refuses_a_wrong_shape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="shape"):
        gistemp.write_grid(tmp_path / "x.npz", (1981,), np.zeros((1, 10, 10)))
    with pytest.raises(ValueError, match="years"):
        gistemp.write_grid(tmp_path / "x.npz", (1981, 1982), np.zeros((1, 90, 180)))


def test_load_grid_with_a_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        gistemp.load_grid(tmp_path / "absent.npz")


# -- the real shipped file ------------------------------------------------------------------------


def test_shipped_file_is_small_and_inside_the_package() -> None:
    path = gistemp.DEFAULT_GRID_PATH

    assert path.exists()
    assert path.stat().st_size <= 2_000_000
    assert "trend_detective" in path.parts


def test_shipped_grid_covers_the_engine_period() -> None:
    grid = gistemp.load_grid()

    assert grid.years[0] == 1981
    assert grid.years[-1] == 2025
    assert grid.anomaly.shape == (45, 90, 180)


def test_shipped_grid_is_warmer_at_the_end_in_niamey_and_has_no_gaps() -> None:
    grid = gistemp.load_grid()

    series = gistemp.cell_series(grid, 13.51, 2.11, list(range(1981, 2026)))

    assert series is not None
    assert all(v is not None for v in series)
    first, last = np.mean(series[:10]), np.mean(series[-10:])  # type: ignore[arg-type]
    assert last - first > 0.3


def test_shipped_grid_values_are_plausible_anomalies() -> None:
    grid = gistemp.load_grid()

    finite = grid.anomaly[np.isfinite(grid.anomaly)]
    assert finite.size > 0.8 * grid.anomaly.size
    assert np.abs(finite).max() < 30
