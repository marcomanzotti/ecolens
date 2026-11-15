"""Tests of the globe's GISTEMP assets (scripts/earth_gistemp.py, scripts/earth_imagery.py).

Small synthetic NetCDF3 files and arrays only: the real 57 MB grid is never read here.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import earth_gistemp as eg  # noqa: E402
import earth_imagery as ei  # noqa: E402

from trend_detective import stats  # noqa: E402

LATS = np.array([-60.0, 0.0, 60.0])
LONS = np.array([-90.0, 0.0, 90.0, 179.0])
FIRST, LAST_FULL = 1981, 2000
FILL = 32767


def _time_axis(last_full: int, extra_months: int) -> list[date]:
    months = [date(y, m, 15) for y in range(FIRST, last_full + 1) for m in range(1, 13)]
    return months + [date(last_full + 1, m, 15) for m in range(1, extra_months + 1)]


def _raw_values(n_time: int, seed: int = 1) -> np.ndarray:
    """int16 centi-K: a warming trend in the northern row, flat noise elsewhere."""
    rng = np.random.default_rng(seed)
    raw = rng.normal(0, 30, size=(n_time, LATS.size, LONS.size))
    years = np.arange(n_time) / 12.0
    raw[:, 2, :] += years[:, None] * 6.0  # +0.6 K per decade
    raw[:, 0, 0] -= years * 6.0  # one cooling cell
    return np.round(raw).astype(np.int16)


def _write_netcdf(path: Path, raw: np.ndarray, times: list[date]) -> None:
    from scipy.io import netcdf_file

    origin = date(1800, 1, 1)
    with netcdf_file(path, "w") as nc:
        nc.createDimension("time", len(times))
        nc.createDimension("lat", LATS.size)
        nc.createDimension("lon", LONS.size)
        t = nc.createVariable("time", "f4", ("time",))
        t[:] = [(d - origin).days for d in times]
        t.units = b"days since 1800-01-01 00:00:00"
        la = nc.createVariable("lat", "f4", ("lat",))
        la[:] = LATS[::-1]  # stored north -> south: the reader must sort it
        lo = nc.createVariable("lon", "f4", ("lon",))
        lo[:] = LONS
        var = nc.createVariable("tempanomaly", "i2", ("time", "lat", "lon"))
        var.scale_factor = np.float32(0.01)
        var._FillValue = np.int16(FILL)
        var[:] = raw[:, ::-1, :]
        nc.history = b"Created 2001-11-10 08:55:39 by SBBX_to_nc 2.0 - ILAND=1200"


@pytest.fixture
def synthetic(tmp_path: Path) -> tuple[Path, np.ndarray, list[date]]:
    times = _time_axis(LAST_FULL, extra_months=10)  # the last year has only 10 months
    raw = _raw_values(len(times))
    raw[5, 1, 1] = FILL  # one missing month: 1981 still has 11 valid months
    for month in range(3):  # 1990 at row 1, column 2: only 9 valid months -> missing year
        raw[(1990 - FIRST) * 12 + month, 1, 2] = FILL
    path = tmp_path / "grid.nc"
    _write_netcdf(path, raw, times)
    return path, raw, times


def test_reader_scales_sorts_and_masks(synthetic):
    path, raw, _ = synthetic
    grid = eg.read_gistemp(path)
    assert list(grid.lat) == list(LATS)
    assert np.isnan(grid.values[5, 1, 1])
    assert grid.values[0, 2, 3] == pytest.approx(raw[0, 2, 3] * 0.01, abs=1e-6)


def test_three_cells_by_hand_against_monthly_means(synthetic):
    path, raw, times = synthetic
    grid = eg.read_gistemp(path)
    years, annual = eg.annual_means(grid, FIRST)
    for year, i, j in [(1981, 1, 1), (1995, 2, 3), (2000, 0, 0)]:
        months = [
            raw[t, i, j] * 0.01
            for t, d in enumerate(times)
            if d.year == year and raw[t, i, j] != FILL
        ]
        expected = sum(months) / len(months)
        assert annual[years.index(year), i, j] == pytest.approx(expected, abs=1e-6)
        assert eg.hand_check(grid, LATS[i], LONS[j], year) == pytest.approx(expected, abs=1e-6)


def test_incomplete_last_year_is_excluded(synthetic):
    grid = eg.read_gistemp(synthetic[0])
    assert eg.complete_years(grid)[-1] == LAST_FULL
    years, _ = eg.annual_means(grid, FIRST)
    assert years[-1] == LAST_FULL
    with pytest.raises(ValueError, match="not complete"):
        eg.annual_means(grid, FIRST, LAST_FULL + 1)


def test_cell_with_missing_year_is_never_filled(synthetic):
    grid = eg.read_gistemp(synthetic[0])
    years, annual = eg.annual_means(grid, FIRST)
    k = years.index(1990)
    assert np.isnan(annual[k, 1, 2])
    decoded = eg.decode_int16(eg.encode_anomaly(annual), annual.shape, eg.CENTI)
    assert np.isnan(decoded[k, 1, 2])
    raw = np.frombuffer(eg.encode_anomaly(annual), dtype="<i2").reshape(annual.shape)
    assert raw[k, 1, 2] == eg.MISSING_INT16
    assert np.isfinite(decoded[k - 1, 1, 2]) and np.isfinite(decoded[k + 1, 1, 2])


def _engine_reference(years: tuple[int, ...], annual: np.ndarray, k: int) -> np.ndarray:
    """The rule written out again with the engine, for one end year."""
    window = list(years[: k + 1])
    flat = annual[: k + 1].reshape(k + 1, -1)
    trends = [
        stats.compute_trend(window, [None if np.isnan(v) else float(v) for v in col], "K")
        for col in flat.T
    ]
    tested = [i for i, t in enumerate(trends) if t is not None]
    expected = np.zeros(flat.shape[1], dtype=np.int8)
    if tested:
        adjusted = stats.benjamini_hochberg([trends[i].mann_kendall.p_value for i in tested])
        for i, p in zip(tested, adjusted, strict=True):
            if p < 0.05:
                expected[i] = int(np.sign(trends[i].sen.slope_per_decade))
    return expected.reshape(annual.shape[1:])


def test_lit_cells_are_exactly_the_bh_significant_ones(synthetic):
    grid = eg.read_gistemp(synthetic[0])
    years, annual = eg.annual_means(grid, FIRST)
    emergence = eg.compute_emergence(years, annual)
    for k in range(len(years)):
        assert np.array_equal(emergence.direction[k], _engine_reference(years, annual, k)), years[k]
    lit = emergence.direction != 0
    assert np.all(emergence.p_adjusted[lit] < 0.05)
    assert not np.any(emergence.p_adjusted[emergence.tested & ~lit] < 0.05)
    # too short windows are never tested
    assert emergence.n_tests[: eg.MIN_YEARS_FOR_TREND - 1] == (0,) * (eg.MIN_YEARS_FOR_TREND - 1)
    assert (emergence.direction[-1, 2] == 1).all() and emergence.direction[-1, 0, 0] == -1


def test_parallel_build_matches_serial(synthetic):
    grid = eg.read_gistemp(synthetic[0])
    years, annual = eg.annual_means(grid, FIRST)
    serial = eg.compute_emergence(years, annual)
    parallel = eg.compute_emergence(years, annual, workers=2)
    assert np.array_equal(serial.direction, parallel.direction)


def test_surface_share_recomputed_from_bins_matches_meta(synthetic):
    grid = eg.read_gistemp(synthetic[0])
    years, annual = eg.annual_means(grid, FIRST)
    emergence = eg.compute_emergence(years, annual)
    shares = eg.surface_shares(emergence, grid.lat)
    emerged = np.frombuffer(eg.encode_emerged(emergence), dtype="i1").reshape(annual.shape)
    weights = np.cos(np.radians(LATS))[:, None] * np.ones(LONS.size)
    for k, row in enumerate(shares):
        assert row["year"] == years[k]
        total = weights[emergence.tested[k]].sum()
        warm = weights[emerged[k] == 1].sum() / total * 100 if total else 0.0
        cool = weights[emerged[k] == -1].sum() / total * 100 if total else 0.0
        assert row["warming_pct"] == pytest.approx(warm, abs=0.01)
        assert row["cooling_pct"] == pytest.approx(cool, abs=0.01)
    assert shares[-1]["warming_pct"] > 0


def test_rate_bin_holds_end_slope_and_direction(synthetic):
    grid = eg.read_gistemp(synthetic[0])
    years, annual = eg.annual_means(grid, FIRST)
    emergence = eg.compute_emergence(years, annual)
    data = eg.encode_rate(emergence)
    cells = LATS.size * LONS.size
    slope = eg.decode_int16(data[: cells * 2], (LATS.size, LONS.size), eg.MILLI)
    direction = np.frombuffer(data[cells * 2 :], dtype="i1").reshape(LATS.size, LONS.size)
    assert np.allclose(slope, emergence.slope_per_decade[-1], atol=1e-3, equal_nan=True)
    assert np.array_equal(direction, emergence.direction[-1])


def test_refuses_blank_or_error_frames():
    with pytest.raises(ei.BlankFrameError):
        ei.check_jpeg(b"<?xml version='1.0'?><ServiceExceptionReport/>")
    with pytest.raises(ei.BlankFrameError):
        ei.check_not_blank(np.zeros((8, 16, 3), dtype=np.uint8))
    with pytest.raises(ei.BlankFrameError):
        ei.check_not_blank(np.zeros((0, 0, 3), dtype=np.uint8))
    mostly_one = np.full((10, 20, 3), 200, dtype=np.uint8)
    mostly_one[0, :5] = 0
    with pytest.raises(ei.BlankFrameError):
        ei.check_not_blank(mostly_one)
    ei.check_jpeg(b"\xff\xd8\xff\xe0rest")
    ei.check_not_blank(np.random.default_rng(0).integers(0, 255, (10, 20, 3), dtype=np.uint8))


def test_ppm_parser_reads_dwebp_output():
    pixels = np.arange(2 * 3 * 3, dtype=np.uint8).reshape(2, 3, 3)
    data = b"P6\n3 2\n255\n" + pixels.tobytes()
    assert np.array_equal(ei.parse_ppm(data), pixels)


def test_wms_url_asks_for_the_whole_earth():
    url = ei.wms_url(2048)
    assert "BBOX=-90%2C-180%2C90%2C180" in url and "WIDTH=2048" in url and "HEIGHT=1024" in url


def test_file_date_comes_from_the_history_attribute(synthetic):
    assert eg.file_created(synthetic[0]) == "2001-11-10"
