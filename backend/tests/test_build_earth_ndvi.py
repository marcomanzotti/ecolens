"""Tests of the globe's vegetation (MODIS NDVI) assets (scripts/earth_ndvi.py).

Small synthetic PNGs, colour maps and arrays only: the real GIBS images are never read here.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import earth_gistemp as eg  # noqa: E402
import earth_ndvi as en  # noqa: E402

from trend_detective import stats  # noqa: E402

COLORMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ColorMaps>
  <ColorMap title="No Data">
    <Entries>
      <ColorMapEntry rgb="0,26,105" transparent="true" sourceValue="[-3000,-2000)"
        value="[-0.3,-0.2)" nodata="true" ref="0"/>
    </Entries>
  </ColorMap>
  <ColorMap title="Vegetation Indices">
    <Entries>
      <ColorMapEntry rgb="225,225,226" transparent="true" sourceValue="[-999,1)"
        value="[-0.0999,0.0001)" ref="2"/>
      <ColorMapEntry rgb="241,236,236" transparent="false" sourceValue="[1,51)"
        value="[0.0001,0.0051)" ref="3"/>
      <ColorMapEntry rgb="160,192,48" transparent="false" sourceValue="[3601,3676)"
        value="[0.3601,0.3676)" ref="80"/>
      <ColorMapEntry rgb="18,110,1" transparent="false" sourceValue="[7501,7601)"
        value="[0.7501,0.7601)" ref="120"/>
    </Entries>
  </ColorMap>
</ColorMaps>
"""


def _png(pixels: np.ndarray, filters: list[int]) -> bytes:
    """Encodes an RGBA uint8 image as PNG with the given filter type per row (0-4)."""
    h, w, _ = pixels.shape
    bpp = 4
    rows = []
    prev = np.zeros(w * bpp, dtype=np.int32)
    for y in range(h):
        line = pixels[y].reshape(-1).astype(np.int32)
        f = filters[y % len(filters)]
        left = np.concatenate([np.zeros(bpp, np.int32), line[:-bpp]])
        upleft = np.concatenate([np.zeros(bpp, np.int32), prev[:-bpp]])
        if f == 0:
            pred = np.zeros_like(line)
        elif f == 1:
            pred = left
        elif f == 2:
            pred = prev
        elif f == 3:
            pred = (left + prev) // 2
        else:
            pa, pb, pc = abs(prev - upleft), abs(left - upleft), abs(left + prev - 2 * upleft)
            pred = np.where((pa <= pb) & (pa <= pc), left, np.where(pb <= pc, prev, upleft))
        rows.append(bytes([f]) + ((line - pred) & 255).astype(np.uint8).tobytes())
        prev = line

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


# --- colour map --------------------------------------------------------------------------------


def test_colormap_maps_each_opaque_colour_to_its_bin_midpoint() -> None:
    cmap = en.parse_colormap(COLORMAP_XML)
    assert cmap.values[(241, 236, 236)] == pytest.approx(0.0026)
    assert cmap.values[(160, 192, 48)] == pytest.approx((0.3601 + 0.3676) / 2)
    assert cmap.values[(18, 110, 1)] == pytest.approx(0.7551)
    # transparent entries (no data, NDVI <= 0) are not values
    assert (0, 26, 105) not in cmap.values
    assert (225, 225, 226) not in cmap.values
    assert cmap.max_half_width == pytest.approx(0.005)


def test_colormap_refuses_a_colour_used_twice() -> None:
    doubled = COLORMAP_XML.replace('rgb="18,110,1"', 'rgb="160,192,48"')
    with pytest.raises(ValueError, match="ambiguous"):
        en.parse_colormap(doubled)


# --- PNG decoding ------------------------------------------------------------------------------


@pytest.mark.parametrize("filters", [[0], [1], [2], [3], [4], [0, 1, 2, 3, 4]])
def test_png_decoder_round_trips_every_filter(filters: list[int]) -> None:
    rng = np.random.default_rng(3)
    pixels = rng.integers(0, 256, size=(5, 7, 4), dtype=np.uint8)
    decoded = en.decode_png(_png(pixels, filters))
    np.testing.assert_array_equal(decoded, pixels)


def test_png_decoder_refuses_non_png() -> None:
    with pytest.raises(ValueError, match="PNG"):
        en.decode_png(b"<html>error</html>")


def test_decode_ndvi_reads_values_and_masks_transparent_pixels() -> None:
    cmap = en.parse_colormap(COLORMAP_XML)
    image = np.zeros((1, 3, 4), dtype=np.uint8)
    image[0, 0] = (18, 110, 1, 255)
    image[0, 1] = (0, 0, 0, 0)  # water / no data / NDVI <= 0
    image[0, 2] = (160, 192, 48, 255)
    ndvi = en.decode_ndvi(image, cmap)
    assert ndvi[0, 0] == pytest.approx(0.7551)
    assert np.isnan(ndvi[0, 1])
    assert ndvi[0, 2] == pytest.approx(0.36385)


def test_decode_ndvi_refuses_a_colour_not_in_the_colour_map() -> None:
    cmap = en.parse_colormap(COLORMAP_XML)
    image = np.array([[[1, 2, 3, 255]]], dtype=np.uint8)
    with pytest.raises(ValueError, match="not in the colour map"):
        en.decode_ndvi(image, cmap)


# --- aggregation -------------------------------------------------------------------------------


def test_to_cells_means_valid_pixels_and_flips_rows_south_to_north() -> None:
    # image rows run north -> south; 4 x 8 pixels -> 2 x 4 cells of 2 x 2 pixels
    image = np.full((4, 8), np.nan)
    image[0:2, 0:2] = [[0.2, 0.4], [0.6, np.nan]]  # north-west cell: 3 of 4 valid
    image[2:4, 6:8] = [[0.1, np.nan], [np.nan, np.nan]]  # south-east: 1 of 4 valid
    cells = en.to_cells(image, factor=2)
    assert cells.shape == (2, 4)
    assert cells[1, 0] == pytest.approx(0.4)  # row 1 = north
    assert np.isnan(cells[0, 3])  # fewer than half the pixels valid: missing, not filled
    assert np.isnan(cells[0, 0])


def test_annual_max_needs_min_valid_months_and_never_fills() -> None:
    monthly = np.full((12, 1, 2), np.nan)
    monthly[:, 0, 0] = np.linspace(0.2, 0.6, 12)
    monthly[: en.MIN_VALID_MONTHS - 1, 0, 1] = 0.5  # one month short
    out = en.annual_max(monthly)
    assert out[0, 0] == pytest.approx(0.6)
    assert np.isnan(out[0, 1])


def test_usable_years_exclude_a_year_the_source_does_not_hold_in_full() -> None:
    months = {(y, m) for y in (2001, 2002) for m in range(1, 13)}
    months -= {(2002, 4)}  # one month not published: still usable
    months |= {(2003, m) for m in range(1, 11)}  # ten months: refused
    assert en.usable_years(months, 2001, 2003) == (2001, 2002)


def test_domain_masks_barren_and_short_baseline_cells() -> None:
    years = tuple(range(2001, 2016))
    annual = np.full((len(years), 1, 3), 0.5)
    annual[:, 0, 1] = 0.05  # barren: peak NDVI below the threshold
    annual[:7, 0, 2] = np.nan  # only 3 valid baseline years
    anomaly = en.anomalies(years, annual)
    assert np.all(np.isfinite(anomaly[:, 0, 0]))
    assert np.allclose(anomaly[:, 0, 0], 0.0)
    assert np.all(np.isnan(anomaly[:, 0, 1]))
    assert np.all(np.isnan(anomaly[:, 0, 2]))


def test_anomaly_is_relative_to_the_baseline_mean_and_keeps_gaps() -> None:
    years = tuple(range(2001, 2016))
    annual = np.full((len(years), 1, 1), np.nan)
    annual[:, 0, 0] = 0.30 + 0.01 * np.arange(len(years))
    annual[12, 0, 0] = np.nan
    anomaly = en.anomalies(years, annual)
    baseline = 0.30 + 0.01 * np.arange(10).mean()
    assert anomaly[0, 0, 0] == pytest.approx(0.30 - baseline)
    assert np.isnan(anomaly[12, 0, 0])


# --- end to end on a synthetic grid ------------------------------------------------------------


@pytest.fixture(scope="module")
def synthetic() -> tuple[tuple[int, ...], np.ndarray, np.ndarray, eg.EmergenceGrid]:
    rng = np.random.default_rng(7)
    years = tuple(range(2001, 2026))
    lat = np.array([-30.5, 10.5, 50.5])
    n = len(years)
    annual = 0.5 + rng.normal(0, 0.01, size=(n, 3, 4))
    annual[:, 0, :] += 0.004 * np.arange(n)[:, None]  # greening row
    annual[:, 2, 0] -= 0.004 * np.arange(n)  # one browning cell
    annual[:, 1, 3] = 0.03  # barren
    annual[5, 1, 1] = np.nan  # one missing year
    anomaly = en.anomalies(years, annual)
    emergence = eg.compute_emergence(years, anomaly, unit="NDVI")
    return years, lat, anomaly, emergence


def test_lit_cells_are_exactly_the_bh_significant_ones(synthetic) -> None:  # type: ignore[no-untyped-def]
    years, _lat, anomaly, emergence = synthetic
    k = len(years) - 1
    flat = anomaly[: k + 1].reshape(k + 1, -1)
    p_raw, cells = [], []
    for c in range(flat.shape[1]):
        values = [None if not np.isfinite(v) else float(v) for v in flat[:, c]]
        trend = stats.compute_trend(list(years), values, "NDVI")
        if trend is not None:
            p_raw.append(trend.mann_kendall.p_value)
            cells.append(c)
    adjusted = stats.benjamini_hochberg(p_raw)
    expected = {c for c, p in zip(cells, adjusted, strict=True) if p < 0.05}
    lit = set(np.flatnonzero(emergence.direction[k].reshape(-1) != 0).tolist())
    assert lit == expected
    assert emergence.direction[k, 0, :].tolist() == [1, 1, 1, 1]
    assert emergence.direction[k, 2, 0] == -1


def test_barren_cell_is_never_tested(synthetic) -> None:  # type: ignore[no-untyped-def]
    _years, _lat, _anomaly, emergence = synthetic
    assert not emergence.tested[:, 1, 3].any()


def test_missing_year_stays_missing_in_the_encoded_anomaly(synthetic) -> None:  # type: ignore[no-untyped-def]
    years, _lat, anomaly, _emergence = synthetic
    decoded = eg.decode_int16(
        eg.encode_anomaly(anomaly, en.ANOMALY_FACTOR), anomaly.shape, en.ANOMALY_FACTOR
    )
    assert np.isnan(decoded[5, 1, 1])
    assert np.isfinite(decoded[4, 1, 1])
    assert len(years) == decoded.shape[0]


def test_shares_use_the_vegetation_labels_and_match_a_recount(synthetic) -> None:  # type: ignore[no-untyped-def]
    years, lat, _anomaly, emergence = synthetic
    rows = eg.surface_shares(emergence, lat, labels=en.LABELS)
    last = rows[-1]
    assert set(last) >= {"greening_pct", "browning_pct", "greening_cells", "browning_cells"}
    weights = np.cos(np.radians(lat))[:, None] * np.ones((1, 4))
    tested = emergence.tested[-1]
    up = emergence.direction[-1] > 0
    assert last["greening_pct"] == pytest.approx(
        round(100 * weights[up].sum() / weights[tested].sum(), 2)
    )
    assert rows[0]["tested_cells"] == 0  # one year: no test yet
    assert last["year"] == years[-1]
