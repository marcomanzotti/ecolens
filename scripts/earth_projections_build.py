"""Downloads CMIP6 period means from the public Pangeo cloud stores and writes the 2050 assets.

Run with the backend venv (dev-only tools: zarr, fsspec, aiohttp; see requirements-dev.txt):

    backend/.venv/bin/python scripts/earth_projections_build.py --variables tas pr

or `scripts/build_earth_assets.py --dataset projections`. Period means are cached per model in
`data/raw/cmip6/cache/` (gitignored), so a rerun only downloads what is missing. The logic is in
`earth_projections.py`; output goes to `frontend/public/earth/projections/`.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import earth_projections as ep

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "cmip6"
CACHE = RAW / "cache"
OUT = ROOT / "frontend" / "public" / "earth" / "projections"
CATALOGUE_URL = "https://storage.googleapis.com/cmip6/pangeo-cmip6.csv"
GCS_HTTP = "https://storage.googleapis.com/"
VARIABLES = ("tas", "pr", "mrsos", "hurs", "rsds", "sfcWind", "lai", "clt")
PREFERRED = (
    "GISS-E2-1-G",
    "ACCESS-CM2",
    "CanESM5",
    "CNRM-CM6-1",
    "GFDL-ESM4",
    "IPSL-CM6A-LR",
    "MIROC6",
    "MPI-ESM1-2-LR",
    "MRI-ESM2-0",
    "UKESM1-0-LL",
    "BCC-CSM2-MR",
    "CESM2-WACCM",
    "FGOALS-g3",
    "INM-CM5-0",
    "NorESM2-MM",
    "CNRM-ESM2-1",
    "GFDL-CM4",
    "FIO-ESM-2-0",
    "CMCC-ESM2",
    "MPI-ESM1-2-HR",
    "HadGEM3-GC31-LL",
    "CESM2",
)
UNITS = {
    "tas": "K",
    "pr": "%",
    "mrsos": "%",
    "hurs": "%",
    "rsds": "%",
    "sfcWind": "%",
    "lai": "%",
    "clt": "%",
}
NAMES = {
    "tas": "Near-surface air temperature",
    "pr": "Precipitation",
    "mrsos": "Soil moisture (top 10 cm)",
    "hurs": "Near-surface relative humidity",
    "rsds": "Surface downwelling shortwave radiation (sunlight)",
    "sfcWind": "Near-surface wind speed",
    "lai": "Leaf area index (vegetation)",
    "clt": "Total cloud cover",
}
SCALE = {"tas": 0.01}
DEFAULT_SCALE = 0.1
FILL_THRESHOLD = 1e19
log = logging.getLogger("projections")


def _catalogue() -> list[dict[str, str]]:
    path = RAW / "pangeo-cmip6.csv"
    if not path.exists():
        import urllib.request

        RAW.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(CATALOGUE_URL, path)  # noqa: S310 - fixed public URL
    wanted = set(ep.TABLES.values())
    with path.open(newline="") as handle:
        return [
            r
            for r in csv.DictReader(handle)
            if r["experiment_id"] in ep.EXPERIMENTS and r["table_id"] in wanted
        ]


def _period_field(zstore: str, variable: str, period: tuple[int, int]):  # type: ignore[no-untyped-def]
    import fsspec
    import numpy as np
    import zarr

    group = zarr.open_consolidated(fsspec.get_mapper(zstore.replace("gs://", GCS_HTTP)), mode="r")
    time = group["time"]
    years = ep.decode_years(time[:], time.attrs["units"], time.attrs.get("calendar", "standard"))
    index = np.flatnonzero((years >= period[0]) & (years <= period[1]))
    if index.size == 0:
        raise ValueError(f"{zstore}: no data in {period}")
    data = np.asarray(group[variable][index[0] : index[-1] + 1], dtype=float)
    data = np.where(np.abs(data) >= FILL_THRESHOLD, np.nan, data)
    mean = ep.period_mean(data, years[index[0] : index[-1] + 1], period)
    lat_name = "lat" if "lat" in group else "latitude"
    lon_name = "lon" if "lon" in group else "longitude"
    return mean, np.asarray(group[lat_name][:]), np.asarray(group[lon_name][:])


def _cached_regridded(sel: ep.Selection, variable: str, experiment: str):  # type: ignore[no-untyped-def]
    import numpy as np

    period = ep.BASELINE if experiment == "historical" else ep.FUTURE
    path = CACHE / f"{variable}_{sel.source_id}_{sel.member_id}_{experiment}.npy"
    if not path.exists():
        mean, lat, lon = _period_field(sel.zstores[experiment], variable, period)
        if lat.ndim != 1 or lon.ndim != 1:
            raise ValueError(f"{sel.source_id}: not a regular lat/lon grid")
        CACHE.mkdir(parents=True, exist_ok=True)
        np.save(path, ep.regrid(mean, lat, lon).astype(np.float32))
    return ep.check_field(np.load(path), path.stem)


def _model_fields(sel: ep.Selection, variable: str):  # type: ignore[no-untyped-def]
    try:
        fields = {e: _cached_regridded(sel, variable, e) for e in ep.EXPERIMENTS}
    except Exception as exc:  # noqa: BLE001 - one broken store must not stop the build
        log.warning("skipping %s %s: %s", variable, sel.source_id, exc)
        return None
    log.info("ok %s %s", variable, sel.source_id)
    return fields


def _license(zstore: str) -> str:
    """The store's own `license` attribute (small consolidated-metadata read, cached on disk)."""
    path = CACHE / ("license_" + zstore.replace("gs://", "").replace("/", "_") + ".txt")
    if not path.exists():
        import fsspec

        with fsspec.open(zstore.replace("gs://", GCS_HTTP) + ".zmetadata") as handle:
            attrs = json.load(handle)["metadata"][".zattrs"]
        path.write_text(str(attrs.get("license", "not stated in the store")))
    return path.read_text().split(". Consult")[0]  # the licence sentence, not the boilerplate


def _global_mean(field) -> float:  # type: ignore[no-untyped-def]
    import numpy as np

    lat, _ = ep.target_grid()
    weights = np.broadcast_to(np.cos(np.radians(lat))[:, None], field.shape)
    ok = np.isfinite(field)
    return float(np.sum(field[ok] * weights[ok]) / np.sum(weights[ok]))


def build_variable(rows, variable: str, max_models: int, workers: int):  # type: ignore[no-untyped-def]
    import numpy as np

    selections = ep.select_models(rows, variable, PREFERRED, max_models)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda s: _model_fields(s, variable), selections))
    used = [(s, f) for s, f in zip(selections, results, strict=True) if f is not None]
    if len(used) < ep.MIN_MODELS:
        raise RuntimeError(f"{variable}: only {len(used)} models")
    scale = SCALE.get(variable, DEFAULT_SCALE)
    entry: dict[str, object] = {
        "name": NAMES[variable],
        "cmip6_id": variable,
        "table": ep.TABLES[variable],
        "unit": UNITS[variable],
        "scale": scale,
        "change": "future - baseline"
        if variable in ep.ABSOLUTE
        else "100 * (future - baseline) / baseline",
        "models": [
            {
                "source_id": s.source_id,
                "institution_id": s.institution_id,
                "member_id": s.member_id,
                "grid_label": s.grid_label,
                "versions": dict(s.versions),
                "zstores": dict(s.zstores),
                "license_attribute_in_store": _license(s.zstores["ssp245"]),
            }
            for s, _ in used
        ],
        "files": {},
        "global_mean_median": {},
    }
    if variable not in ep.ABSOLUTE:
        entry["baseline_floor_native_units"] = ep.PERCENT_FLOOR[variable]
    for scenario in ep.SCENARIOS:
        changes = np.stack(
            [ep.model_change(f["historical"], f[scenario], variable) for _, f in used]
        )
        stats = ep.ensemble(changes)
        name = f"{variable}_{scenario}.bin"
        (OUT / name).write_bytes(ep.encode(stats, scale))
        entry["files"][scenario] = name  # type: ignore[index]
        entry["global_mean_median"][scenario] = round(_global_mean(stats["median"]), 3)  # type: ignore[index]
    return entry


def _meta(variables: dict[str, object]) -> dict[str, object]:
    return {
        "format_version": 1,
        "built": datetime.now(UTC).date().isoformat(),
        "source": {
            "name": "CMIP6 multi-model projections (WCRP), Pangeo / Google Cloud public dataset",
            "catalogue": CATALOGUE_URL,
            "license": "CC BY 4.0 for all CMIP6 models since October 2022 (PCMDI CMIP6 Terms of "
            "Use, which supersede the older license attribute kept per model below); cite each "
            "model's institution and acknowledge WCRP CMIP6",
            "terms_of_use": "https://pcmdi.llnl.gov/CMIP6/TermsOfUse/TermsOfUse6-2.html",
        },
        "baseline": list(ep.BASELINE),
        "future": list(ep.FUTURE),
        "scenarios": {
            "ssp245": "SSP2-4.5 (moderate emissions)",
            "ssp585": "SSP5-8.5 (high emissions)",
        },
        "grid": {
            "n_lat": 90,
            "n_lon": 180,
            "lat_first": -89.0,
            "lon_first": -179.0,
            "step_deg": ep.GRID_STEP,
            "order": "lat (south to north), lon (west to east); cell centres",
        },
        "regridding": "bilinear from each model's native grid; "
        "cells next to a missing value stay missing",
        "file_layout": {
            "parts": [
                "median int16 LE",
                "p10 int16 LE",
                "p90 int16 LE",
                "agreement uint8 (% of models with the sign of the median)",
                "count uint8 (models)",
            ],
            "shape": [90, 180],
            "value": "int16 * scale",
            "missing_int16": ep.I16_MISSING,
            "missing_uint8": ep.U8_MISSING,
        },
        "statistics": "per model mean of annual means per 20-year period; across models median, "
        "10th and 90th percentile; a cell needs at least "
        f"{ep.MIN_MODELS} models",
        "agreement_rule": "share of models whose change has the sign of the median; "
        "robust if >= 80% "
        "(IPCC AR6 simple approach)",
        "caveats": [
            "Scenario projections, not forecasts.",
            "Model resolution is about 1-2.5 degrees; no bias correction or downscaling.",
            "Projections know nothing about the local trends measured by the app.",
        ],
        "variables": variables,
    }


def build_all(variables, max_models: int = 12, workers: int = 8) -> None:  # type: ignore[no-untyped-def]
    """Builds the variables in order; meta.json is rewritten after each variable."""
    rows = _catalogue()
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = OUT / "meta.json"
    built = json.loads(meta_path.read_text())["variables"] if meta_path.exists() else {}
    for variable in variables:
        built[variable] = build_variable(rows, variable, max_models, workers)
        meta_path.write_text(json.dumps(_meta(built), indent=1))
        log.info("%s done: %s", variable, built[variable]["global_mean_median"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--variables", nargs="+", choices=VARIABLES, default=list(VARIABLES))
    parser.add_argument("--max-models", type=int, default=12)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stderr)
    build_all(args.variables, args.max_models, args.workers)


if __name__ == "__main__":
    main()
