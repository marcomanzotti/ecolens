"""MODIS Terra monthly NDVI images (NASA GIBS) -> annual peak NDVI on a 1 degree grid.

Pure logic used by `build_earth_assets.py` (the CLI); tested in
`backend/tests/test_build_earth_ndvi.py`. The trend test and the shares are those of
`earth_gistemp.py` (the engine's rule), applied to these annual values.

How a number is recovered from a coloured image: GIBS publishes the colour map of the layer
(`MODIS_L3_NDVI.xml`), in which every opaque colour is used by exactly one NDVI bin (bins 0.005
to 0.01 wide). Each opaque pixel is mapped back to the midpoint of its bin, so the decoded value
is exact up to half a bin (at most 0.005 NDVI). Transparent pixels (water, no data, and NDVI <= 0,
which the layer does not colour: snow, ice) are missing, never filled. A colour that is not in the
map stops the build.

Pipeline: 0.25 degree image (1440 x 720) -> monthly 1 degree cell mean (at least half of the 16
pixels valid) -> annual maximum of the monthly means (peak greenness; at least MIN_VALID_MONTHS
valid months) -> anomaly vs the BASELINE mean. A cell is measured only when its baseline has at
least MIN_BASELINE_YEARS valid years and a mean peak NDVI of at least BARREN_NDVI; otherwise
all its years are missing (deserts, ice and water are not tested).
"""

from __future__ import annotations

import re
import struct
import warnings
import zlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

LAYER = "MODIS_Terra_L3_NDVI_Monthly"
COLORMAP_URL = "https://gibs.earthdata.nasa.gov/colormaps/v1.3/MODIS_L3_NDVI.xml"
WMS_URL = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
IMAGE_WIDTH, IMAGE_HEIGHT = 1440, 720
CELL_DEG = 1
PIXELS_PER_CELL = IMAGE_WIDTH // (360 // CELL_DEG)
MIN_VALID_MONTHS = 4
MIN_MONTHS_IN_SOURCE = 11
BASELINE = (2001, 2010)
MIN_BASELINE_YEARS = 8
BARREN_NDVI = 0.1
LABELS = ("greening", "browning")
ANOMALY_FACTOR = 1000  # int16 in thousandths of NDVI
RATE_FACTOR = 10000  # int16 in 1e-4 NDVI per decade
MONTHS_PER_YEAR = 12
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RGBA_COLOR_TYPE = 6
BYTES_PER_PIXEL = 4
OPAQUE = 255

_ENTRY = re.compile(r"<ColorMapEntry\b([^>]*)/?>")
_ATTR = re.compile(r'(\w+)="([^"]*)"')
_BIN = re.compile(r"\[\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*\)")


@dataclass(frozen=True)
class Colormap:
    """Opaque colour -> NDVI (midpoint of its bin)."""

    values: dict[tuple[int, int, int], float]
    max_half_width: float


def wms_url(year: int, month: int) -> str:
    from urllib.parse import urlencode

    query = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.3.0",
        "CRS": "EPSG:4326",
        "BBOX": "-90,-180,90,180",
        "STYLES": "",
        "LAYERS": LAYER,
        "FORMAT": "image/png",
        "WIDTH": IMAGE_WIDTH,
        "HEIGHT": IMAGE_HEIGHT,
        "TIME": f"{year}-{month:02d}-01",
    }
    return f"{WMS_URL}?{urlencode(query)}"


def parse_colormap(xml: str) -> Colormap:
    """Reads the GIBS colour map; refuses a colour used by two different bins."""
    values: dict[tuple[int, int, int], float] = {}
    half_widths: list[float] = []
    for match in _ENTRY.finditer(xml):
        attrs = dict(_ATTR.findall(match.group(1)))
        if attrs.get("transparent") == "true" or attrs.get("nodata") == "true":
            continue
        bounds = _BIN.match(attrs["value"])
        if not bounds:
            raise ValueError(f"unexpected bin: {attrs['value']!r}")
        low, high = float(bounds.group(1)), float(bounds.group(2))
        rgb = tuple(int(v) for v in attrs["rgb"].split(","))
        if rgb in values:
            raise ValueError(f"ambiguous colour map: {rgb} is used twice")
        values[rgb] = (low + high) / 2  # type: ignore[index]
        half_widths.append((high - low) / 2)
    if not values:
        raise ValueError("no opaque entry in the colour map")
    return Colormap(values=values, max_half_width=round(max(half_widths), 6))


def _unfilter_row(kind: int, line: bytes, prev: list[int]) -> list[int]:
    bpp = BYTES_PER_PIXEL
    cur = list(line)
    if kind == 0:
        return cur
    if kind == 2:
        return [(c + p) & 255 for c, p in zip(cur, prev, strict=True)]
    for x in range(len(cur)):
        a = cur[x - bpp] if x >= bpp else 0
        b = prev[x]
        if kind == 1:
            pred = a
        elif kind == 3:
            pred = (a + b) // 2
        elif kind == 4:
            c = prev[x - bpp] if x >= bpp else 0
            pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
            pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
        else:
            raise ValueError(f"unknown PNG filter {kind}")
        cur[x] = (cur[x] + pred) & 255
    return cur


def decode_png(data: bytes) -> NDArray[np.uint8]:
    """8-bit RGBA, non-interlaced PNG -> (height, width, 4). Only what GIBS returns."""
    import numpy as np

    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG image (the service may have returned an error page)")
    pos, idat, header = len(PNG_SIGNATURE), bytearray(), None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
    if header is None:
        raise ValueError("PNG without header")
    width, height, depth, color_type, _, _, interlace = header
    if depth != 8 or color_type != RGBA_COLOR_TYPE or interlace:
        raise ValueError(f"unsupported PNG (depth {depth}, colour type {color_type})")
    raw = zlib.decompress(bytes(idat))
    stride = width * BYTES_PER_PIXEL
    out = np.zeros((height, stride), dtype=np.uint8)
    prev = [0] * stride
    for y in range(height):
        start = y * (stride + 1)
        prev = _unfilter_row(raw[start], raw[start + 1 : start + 1 + stride], prev)
        out[y] = prev
    return out.reshape(height, width, BYTES_PER_PIXEL)


def decode_ndvi(image: NDArray[np.uint8], cmap: Colormap) -> NDArray[np.float64]:
    """RGBA image -> NDVI (bin midpoints), NaN where transparent. Unknown colours stop the build."""
    import numpy as np

    rgb = image[..., :3].astype(np.int64)
    key = (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    opaque = image[..., 3] == OPAQUE
    partial = (image[..., 3] != 0) & ~opaque
    if partial.any():
        raise ValueError("semi-transparent pixels: the image was resampled, values are not exact")
    lookup = {(r << 16) | (g << 8) | b: v for (r, g, b), v in cmap.values.items()}
    keys, inverse = np.unique(key[opaque], return_inverse=True)
    unknown = [int(k) for k in keys if int(k) not in lookup]
    if unknown:
        first = unknown[0]
        raise ValueError(
            f"{len(unknown)} colours not in the colour map, e.g. "
            f"{(first >> 16, (first >> 8) & 255, first & 255)}"
        )
    out = np.full(key.shape, np.nan)
    out[opaque] = np.array([lookup[int(k)] for k in keys])[inverse]
    return out


def has_data(image: NDArray[np.uint8]) -> bool:
    """False for the blank image the WMS returns for a month it does not hold."""
    return bool((image[..., 3] == OPAQUE).any())


def to_cells(ndvi: NDArray[np.float64], factor: int = PIXELS_PER_CELL) -> NDArray[np.float64]:
    """Image (rows north -> south) -> cell means (rows south -> north). A cell needs at least
    half of its pixels valid; otherwise it is missing."""
    import numpy as np

    h, w = ndvi.shape
    blocks = ndvi.reshape(h // factor, factor, w // factor, factor)
    valid = np.isfinite(blocks).sum(axis=(1, 3))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells: masked just below
        mean = np.nanmean(blocks, axis=(1, 3))
    cells = np.where(valid * 2 >= factor * factor, mean, np.nan)
    return cells[::-1]


def annual_max(monthly: NDArray[np.float64]) -> NDArray[np.float64]:
    """(months, lat, lon) of one year -> peak NDVI; NaN with fewer than MIN_VALID_MONTHS."""
    import numpy as np

    valid = np.isfinite(monthly).sum(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        peak = np.nanmax(monthly, axis=0)
    return np.where(valid >= MIN_VALID_MONTHS, peak, np.nan)


def usable_years(months: Iterable[tuple[int, int]], first: int, last: int) -> tuple[int, ...]:
    """Years from `first` to `last` for which the source holds at least MIN_MONTHS_IN_SOURCE
    monthly images. The count stops at the first refused year (no gaps in the series)."""
    held = set(months)
    years: list[int] = []
    for year in range(first, last + 1):
        count = sum((year, m) in held for m in range(1, MONTHS_PER_YEAR + 1))
        if count < MIN_MONTHS_IN_SOURCE:
            break
        years.append(year)
    return tuple(years)


def baseline_mask(
    years: tuple[int, ...], annual: NDArray[np.float64]
) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    """(baseline mean, measured) per cell. Measured: enough baseline years and not barren."""
    import numpy as np

    start, end = BASELINE
    rows = [k for k, y in enumerate(years) if start <= y <= end]
    block = annual[rows]
    count = np.isfinite(block).sum(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(block, axis=0)
    measured = (count >= MIN_BASELINE_YEARS) & (mean >= BARREN_NDVI)
    return mean, measured


def anomalies(years: tuple[int, ...], annual: NDArray[np.float64]) -> NDArray[np.float64]:
    """Annual peak NDVI minus the baseline mean; every year missing outside the measured cells."""
    import numpy as np

    mean, measured = baseline_mask(years, annual)
    return np.where(measured[None], annual - mean[None], np.nan)


def hand_check(monthly_images: list[NDArray[np.float64]], lat: float, lon: float) -> float | None:
    """Peak NDVI of one cell recomputed the slow way from the decoded images of one year."""
    import math

    row = int((90 - lat) // CELL_DEG) * PIXELS_PER_CELL
    col = int((lon + 180) // CELL_DEG) * PIXELS_PER_CELL
    means: list[float] = []
    for image in monthly_images:
        block = [
            float(image[r, c])
            for r in range(row, row + PIXELS_PER_CELL)
            for c in range(col, col + PIXELS_PER_CELL)
        ]
        valid = [v for v in block if not math.isnan(v)]
        if 2 * len(valid) >= len(block):
            means.append(sum(valid) / len(valid))
    return max(means) if len(means) >= MIN_VALID_MONTHS else None


STATISTIC_TEXT = (
    "Annual peak NDVI: the maximum of the twelve monthly 1-degree means (each the mean of the "
    "valid 0.25-degree pixels, at least half of them valid); a year needs at least "
    f"{MIN_VALID_MONTHS} valid months. Peak greenness is used instead of the annual mean because "
    "the layer leaves snow-covered months uncoloured, which would bias an annual mean."
)
MASK_TEXT = (
    f"Measured cells: at least {MIN_BASELINE_YEARS} valid years in {BASELINE[0]}-{BASELINE[1]} and "
    f"a baseline peak NDVI of at least {BARREN_NDVI} (deserts, ice and water are not tested). "
    "Missing values are never filled."
)
