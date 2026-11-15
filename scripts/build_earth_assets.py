"""Build the static assets of the globe: the Earth image and the two time-lapses.

Run from the repo root:  backend/.venv/bin/python scripts/build_earth_assets.py

Downloads (once, into data/raw/, gitignored):
  GISTEMP v4 1200 km grid (NASA GISS), the Blue Marble shaded-relief image (NASA GIBS WMS),
  the MODIS Terra monthly NDVI images 2001-2025 and their colour map (NASA GIBS WMS).
Writes:
  frontend/public/earth/bluemarble-{2048,4096,8192}.webp
  frontend/public/earth/gistemp/{anomaly.bin, emerged.bin, rate.bin, meta.json}
  frontend/public/earth/ndvi/{anomaly.bin, emerged.bin, rate.bin, meta.json}
The statistics are in earth_gistemp.py and earth_ndvi.py (tested in
backend/tests/test_build_earth_assets.py and test_build_earth_ndvi.py).
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

import earth_gistemp as eg  # noqa: E402
import earth_imagery as ei  # noqa: E402
import earth_ndvi as en  # noqa: E402

from trend_detective.models import ALPHA, MIN_YEARS_FOR_TREND  # noqa: E402

GISTEMP_URL = "https://data.giss.nasa.gov/pub/gistemp/gistemp1200_GHCNv4_ERSSTv5.nc.gz"
RAW = ROOT / "data" / "raw"
GISTEMP_GZ = RAW / "gistemp" / "gistemp1200_GHCNv4_ERSSTv5.nc.gz"
EARTH_OUT = ROOT / "frontend" / "public" / "earth"
GISTEMP_OUT = EARTH_OUT / "gistemp"
NDVI_OUT = EARTH_OUT / "ndvi"
NDVI_RAW = RAW / "ndvi"
NDVI_FIRST_YEAR, NDVI_LAST_YEAR = 2001, 2025
NDVI_DOWNLOADS = 6
# Cells checked against the decoded images in the build log: Punjab, Sahel (Niger), Amazon.
NDVI_HAND_CHECKS = ((30.5, 75.5), (14.5, 2.5), (-3.5, -60.5))
IMAGE_WIDTHS = (2048, 4096, 8192)
FIRST_YEAR = 1981
HTTP_TIMEOUT_S = 300
# Cells checked against the monthly file in the build log: Niamey, Venice, Southern Ocean.
HAND_CHECKS = ((13.5, 2.1), (45.4, 12.3), (-65.0, -121.0))
FORMAT_VERSION = 1


def _download(url: str, target: Path) -> Path:
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "trend-detective-build"})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:  # noqa: S310
        data = response.read()
    target.write_bytes(data)
    return target


def build_images() -> dict[str, int]:
    sizes: dict[str, int] = {}
    scratch = RAW / "gibs"
    for width in IMAGE_WIDTHS:
        jpeg = _download(ei.wms_url(width), scratch / f"bluemarble_{width}.jpg")
        ei.check_jpeg(jpeg.read_bytes())
        target = EARTH_OUT / f"bluemarble-{width}.webp"
        ei.jpeg_to_webp(jpeg, target, scratch)
        sizes[target.name] = target.stat().st_size
    return sizes


def _file_date() -> str:
    created = eg.file_created(GISTEMP_GZ.with_suffix(""))
    if created:
        return created
    stamp = GISTEMP_GZ.stat().st_mtime
    return datetime.fromtimestamp(stamp, tz=UTC).date().isoformat()


def _nc_path() -> Path:
    _download(GISTEMP_URL, GISTEMP_GZ)
    nc = GISTEMP_GZ.with_suffix("")
    if not nc.exists():
        with gzip.open(GISTEMP_GZ, "rb") as source, nc.open("wb") as target:
            shutil.copyfileobj(source, target)
    return nc


def build_gistemp() -> dict[str, object]:
    grid = eg.read_gistemp(_nc_path())
    years, annual = eg.annual_means(grid, FIRST_YEAR)
    emergence = eg.compute_emergence(years, annual, workers=os.cpu_count() or 1)
    shares = eg.surface_shares(emergence, grid.lat)
    GISTEMP_OUT.mkdir(parents=True, exist_ok=True)
    (GISTEMP_OUT / "anomaly.bin").write_bytes(eg.encode_anomaly(annual))
    (GISTEMP_OUT / "emerged.bin").write_bytes(eg.encode_emerged(emergence))
    (GISTEMP_OUT / "rate.bin").write_bytes(eg.encode_rate(emergence))
    checks = [
        {
            "lat": lat,
            "lon": lon,
            "year": years[-1],
            "annual_mean_k": eg.hand_check(grid, lat, lon, years[-1]),
        }
        for lat, lon in HAND_CHECKS
    ]
    meta = _meta(grid, years, shares, emergence.n_tests, checks)
    (GISTEMP_OUT / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def _meta(grid, years, shares, n_tests, checks) -> dict[str, object]:  # type: ignore[no-untyped-def]
    n_lat, n_lon = grid.lat.size, grid.lon.size
    return {
        "format_version": FORMAT_VERSION,
        "built": datetime.now(tz=UTC).date().isoformat(),
        "source": {
            "name": "GISTEMP v4 (GHCNv4 + ERSSTv5, 1200 km smoothing), NASA GISS",
            "url": GISTEMP_URL,
            "file_date": _file_date(),
        },
        "baseline": "1951-1980",
        "unit": "K",
        "years": list(years),
        "grid": {
            "n_lat": n_lat,
            "n_lon": n_lon,
            "lat_first": float(grid.lat[0]),
            "lon_first": float(grid.lon[0]),
            "step_deg": float(grid.lat[1] - grid.lat[0]),
            "order": "year, lat (south to north), lon (west to east); cell centres",
        },
        "files": {
            "anomaly.bin": {
                "type": "int16 little-endian",
                "shape": [len(years), n_lat, n_lon],
                "scale": 1 / eg.CENTI,
                "unit": "K",
                "missing": eg.MISSING_INT16,
                "content": (
                    f"annual mean anomaly; a year needs at least {eg.MIN_VALID_MONTHS} valid months"
                ),
            },
            "emerged.bin": {
                "type": "int8",
                "shape": [len(years), n_lat, n_lon],
                "content": (
                    "significant trend over the window first year -> year: "
                    "+1 warming, -1 cooling, 0 not significant or untested"
                ),
            },
            "rate.bin": {
                "parts": [
                    {
                        "type": "int16 little-endian",
                        "shape": [n_lat, n_lon],
                        "scale": 1 / eg.MILLI,
                        "unit": "K per decade",
                        "missing": eg.MISSING_INT16,
                        "content": f"Sen slope {years[0]}-{years[-1]}",
                    },
                    {
                        "type": "int8",
                        "shape": [n_lat, n_lon],
                        "offset_bytes": n_lat * n_lon * 2,
                        "content": (
                            "significance at the end of the series "
                            f"(same as emerged.bin {years[-1]})"
                        ),
                    },
                ],
            },
        },
        "test": {
            "rule": eg.RULE_TEXT,
            "alpha": ALPHA,
            "correction": "Benjamini-Hochberg",
            "min_years": MIN_YEARS_FOR_TREND,
            "area_weight": "cos(latitude)",
            "share_denominator": "area of the cells tested in that window",
            "n_tests": list(n_tests),
        },
        "shares": shares,
        "hand_checks": checks,
    }


def _ndvi_image(year: int, month: int) -> Path:
    return _download(en.wms_url(year, month), NDVI_RAW / f"ndvi_{year}-{month:02d}.png")


def _decode_month(args: tuple[Path, en.Colormap]):  # type: ignore[no-untyped-def]
    path, cmap = args
    image = en.decode_png(path.read_bytes())
    if not en.has_data(image):
        return None
    return en.to_cells(en.decode_ndvi(image, cmap))


def _ndvi_monthly(cmap: en.Colormap):  # type: ignore[no-untyped-def]
    """{(year, month): 1-degree cell means} for every month the layer holds."""
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

    months = [
        (y, m) for y in range(NDVI_FIRST_YEAR, NDVI_LAST_YEAR + 1) for m in range(1, 13)
    ]
    with ThreadPoolExecutor(max_workers=NDVI_DOWNLOADS) as pool:
        paths = list(pool.map(lambda ym: _ndvi_image(*ym), months))
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 1) as pool:
        cells = list(pool.map(_decode_month, [(p, cmap) for p in paths]))
    return {ym: c for ym, c in zip(months, cells, strict=True) if c is not None}


def build_ndvi() -> dict[str, object]:
    import numpy as np

    xml = _download(en.COLORMAP_URL, NDVI_RAW / "MODIS_L3_NDVI.xml").read_text()
    cmap = en.parse_colormap(xml)
    monthly = _ndvi_monthly(cmap)
    years = en.usable_years(monthly, NDVI_FIRST_YEAR, NDVI_LAST_YEAR)
    shape = next(iter(monthly.values())).shape
    annual = np.stack(
        [
            en.annual_max(
                np.stack([monthly.get((y, m), np.full(shape, np.nan)) for m in range(1, 13)])
            )
            for y in years
        ]
    )
    anomaly = en.anomalies(years, annual)
    emergence = eg.compute_emergence(years, anomaly, workers=os.cpu_count() or 1, unit="NDVI")
    lat = -90 + en.CELL_DEG / 2 + en.CELL_DEG * np.arange(shape[0])
    shares = eg.surface_shares(emergence, lat, labels=en.LABELS)
    NDVI_OUT.mkdir(parents=True, exist_ok=True)
    (NDVI_OUT / "anomaly.bin").write_bytes(eg.encode_anomaly(anomaly, en.ANOMALY_FACTOR))
    (NDVI_OUT / "emerged.bin").write_bytes(eg.encode_emerged(emergence))
    (NDVI_OUT / "rate.bin").write_bytes(eg.encode_rate(emergence, en.RATE_FACTOR))
    missing_months = sorted(
        f"{y}-{m:02d}" for y in years for m in range(1, 13) if (y, m) not in monthly
    )
    meta = _ndvi_meta(shape, years, shares, emergence.n_tests, cmap, missing_months)
    meta["hand_checks"] = _ndvi_hand_checks(cmap, years[-1], annual, lat)
    (NDVI_OUT / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def _ndvi_hand_checks(cmap, year, annual, lat):  # type: ignore[no-untyped-def]
    images = []
    for month in range(1, 13):
        image = en.decode_png(_ndvi_image(year, month).read_bytes())
        if en.has_data(image):
            images.append(en.decode_ndvi(image, cmap))
    checks = []
    for la, lo in NDVI_HAND_CHECKS:
        row = int(abs(lat - la).argmin())
        col = int(lo + 180)
        built = annual[-1, row, col]
        checks.append(
            {
                "lat": la,
                "lon": lo,
                "year": year,
                "peak_ndvi_slow": en.hand_check(images, la, lo),
                "peak_ndvi_built": None if built != built else round(float(built), 4),
            }
        )
    return checks


def _ndvi_meta(shape, years, shares, n_tests, cmap, missing_months):  # type: ignore[no-untyped-def]
    n_lat, n_lon = shape
    rise, fall = en.LABELS
    return {
        "format_version": FORMAT_VERSION,
        "built": datetime.now(tz=UTC).date().isoformat(),
        "source": {
            "name": "MODIS Terra L3 monthly NDVI, NASA LP DAAC, via NASA GIBS (decoded colour map)",
            "url": en.WMS_URL + "?LAYERS=" + en.LAYER,
            "colormap": en.COLORMAP_URL,
            "file_date": datetime.now(tz=UTC).date().isoformat(),
            "missing_months": missing_months,
        },
        "baseline": f"{en.BASELINE[0]}-{en.BASELINE[1]}",
        "unit": "NDVI",
        "labels": {"up": rise, "down": fall},
        "statistic": en.STATISTIC_TEXT,
        "mask": en.MASK_TEXT,
        "quantisation": {
            "max_error": cmap.max_half_width,
            "content": (
                "each pixel is the midpoint of its colour-map bin (bins 0.005-0.01 NDVI wide); "
                f"error at most {cmap.max_half_width} NDVI before averaging"
            ),
        },
        "years": list(years),
        "grid": {
            "n_lat": n_lat,
            "n_lon": n_lon,
            "lat_first": -90 + en.CELL_DEG / 2,
            "lon_first": -180 + en.CELL_DEG / 2,
            "step_deg": en.CELL_DEG,
            "order": "year, lat (south to north), lon (west to east); cell centres",
        },
        "files": {
            "anomaly.bin": {
                "type": "int16 little-endian",
                "shape": [len(years), n_lat, n_lon],
                "scale": 1 / en.ANOMALY_FACTOR,
                "unit": "NDVI",
                "missing": eg.MISSING_INT16,
                "content": f"annual peak NDVI minus its {en.BASELINE[0]}-{en.BASELINE[1]} mean",
            },
            "emerged.bin": {
                "type": "int8",
                "shape": [len(years), n_lat, n_lon],
                "content": (
                    "significant trend over the window first year -> year: "
                    f"+1 {rise}, -1 {fall}, 0 not significant or untested"
                ),
            },
            "rate.bin": {
                "parts": [
                    {
                        "type": "int16 little-endian",
                        "shape": [n_lat, n_lon],
                        "scale": 1 / en.RATE_FACTOR,
                        "unit": "NDVI per decade",
                        "missing": eg.MISSING_INT16,
                        "content": f"Sen slope {years[0]}-{years[-1]}",
                    },
                    {
                        "type": "int8",
                        "shape": [n_lat, n_lon],
                        "offset_bytes": n_lat * n_lon * 2,
                        "content": (
                            "significance at the end of the series "
                            f"(same as emerged.bin {years[-1]})"
                        ),
                    },
                ],
            },
        },
        "test": {
            "rule": eg.RULE_TEXT.replace("annual mean anomalies", "annual peak NDVI anomalies"),
            "alpha": ALPHA,
            "correction": "Benjamini-Hochberg",
            "min_years": MIN_YEARS_FOR_TREND,
            "area_weight": "cos(latitude)",
            "share_denominator": "area of the cells tested in that window (measured land)",
            "n_tests": list(n_tests),
        },
        "shares": shares,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--skip-images", action="store_true", help="do not rebuild the Earth image")
    parser.add_argument(
        "--dataset", choices=("gistemp", "ndvi", "all"), default="all", help="time-lapse to build"
    )
    args = parser.parse_args()
    EARTH_OUT.mkdir(parents=True, exist_ok=True)
    if not args.skip_images:
        for name, size in build_images().items():
            print(f"{name}: {size / 1e6:.2f} MB")  # noqa: T201
    builders = {"gistemp": build_gistemp, "ndvi": build_ndvi}
    for name in ("gistemp", "ndvi") if args.dataset == "all" else (args.dataset,):
        meta = builders[name]()
        for row in meta["shares"]:  # type: ignore[union-attr]
            if row["year"] % 5 == 0:
                print(name, row)  # noqa: T201
        print(name, meta["hand_checks"])  # noqa: T201


if __name__ == "__main__":
    main()
