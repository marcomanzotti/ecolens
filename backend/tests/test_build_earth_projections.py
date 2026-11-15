"""Tests of the globe's 2050 projection assets (scripts/earth_projections.py).

Synthetic catalogue rows and arrays only: the CMIP6 cloud stores are never read here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import earth_projections as ep  # noqa: E402


def _row(source, exp, member="r1i1p1f1", var="tas", table="Amon", version="20190101"):
    return {
        "activity_id": "CMIP" if exp == "historical" else "ScenarioMIP",
        "institution_id": "INST",
        "source_id": source,
        "experiment_id": exp,
        "member_id": member,
        "table_id": table,
        "variable_id": var,
        "grid_label": "gn",
        "zstore": f"gs://cmip6/{source}/{exp}/{member}/{var}/v{version}/",
        "version": version,
    }


# --- catalogue -----------------------------------------------------------------------------


def test_selection_keeps_only_models_with_all_three_experiments():
    rows = [_row("A", e) for e in ep.EXPERIMENTS]
    rows += [_row("B", "historical"), _row("B", "ssp245")]  # no ssp585
    rows += [_row("C", e) for e in ep.EXPERIMENTS]
    picked = ep.select_models(rows, "tas", preferred=("C", "A", "B"), max_models=5)
    assert [p.source_id for p in picked] == ["C", "A"]
    assert set(picked[0].zstores) == set(ep.EXPERIMENTS)


def test_selection_prefers_r1i1p1f1_then_first_member_in_natural_order():
    rows = [_row("A", e, member="r10i1p1f1") for e in ep.EXPERIMENTS]
    rows += [_row("A", e, member="r2i1p1f2") for e in ep.EXPERIMENTS]
    rows += [_row("B", e, member=m) for e in ep.EXPERIMENTS for m in ("r3i1p1f1", "r1i1p1f1")]
    picked = {p.source_id: p.member_id for p in ep.select_models(rows, "tas", ("A", "B"), 5)}
    assert picked == {"A": "r2i1p1f2", "B": "r1i1p1f1"}


def test_selection_member_must_have_all_experiments_and_latest_version_wins():
    rows = [_row("A", "historical", member="r1i1p1f1")]  # r1 incomplete
    rows += [_row("A", e, member="r2i1p1f1") for e in ep.EXPERIMENTS]
    rows += [_row("A", "ssp585", member="r2i1p1f1", version="20210101")]
    (pick,) = ep.select_models(rows, "tas", ("A",), 5)
    assert pick.member_id == "r2i1p1f1"
    assert "20210101" in pick.zstores["ssp585"]


def test_selection_uses_the_variable_table_and_caps_the_count():
    rows = [_row(s, e, var="lai", table="Lmon") for s in "ABC" for e in ep.EXPERIMENTS]
    rows += [_row("D", e, var="lai", table="Amon") for e in ep.EXPERIMENTS]  # wrong table
    picked = ep.select_models(rows, "lai", ("D", "A", "B", "C"), max_models=2)
    assert [p.source_id for p in picked] == ["A", "B"]


# --- time and period means -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("units", "calendar", "value", "year"),
    [
        ("days since 1850-01-01", "noleap", 365 * 145 + 15, 1995),
        ("days since 1850-01-01 00:00:00", "standard", 52960.5, 1995),
        ("days since 2015-01-01", "360_day", 360 * 26 + 345, 2041),
        ("hours since 2015-01-01", "proleptic_gregorian", 24 * 15, 2015),
    ],
)
def test_decode_years(units, calendar, value, year):
    assert ep.decode_years(np.array([value]), units, calendar)[0] == year


def test_period_mean_is_mean_of_annual_means_and_needs_complete_years():
    years = np.repeat(np.arange(2000, 2004), 12)
    data = np.repeat(np.array([1.0, 2.0, 3.0, 10.0]), 12)[:, None, None] * np.ones((1, 2, 2))
    out = ep.period_mean(data, years, (2000, 2002))
    assert np.allclose(out, 2.0)
    with pytest.raises(ValueError, match="years"):
        ep.period_mean(data[:30], years[:30], (2000, 2003))


# --- regridding ------------------------------------------------------------------------------


def test_target_grid_matches_gistemp_orientation():
    lat, lon = ep.target_grid()
    assert lat.shape == (90,) and lon.shape == (180,)
    assert lat[0] == -89.0 and lat[-1] == 89.0
    assert lon[0] == -179.0 and lon[-1] == 179.0


def test_regrid_handles_0_360_longitudes_and_north_to_south_latitudes():
    src_lat = np.linspace(90, -90, 91)  # north to south
    src_lon = np.arange(0, 360, 2.0)  # 0..358
    field = src_lat[:, None] + np.cos(np.radians(src_lon))[None, :]
    out = ep.regrid(field, src_lat, src_lon)
    lat, lon = ep.target_grid()

    def expected(i, j):
        return lat[i] + np.cos(np.radians(lon[j]))

    assert out.shape == (90, 180)
    assert out[0, 90] == pytest.approx(expected(0, 90), abs=1e-3)
    assert out[89, 0] == pytest.approx(expected(89, 0), abs=1e-3)
    assert out[45, 179] == pytest.approx(expected(45, 179), abs=1e-3)
    assert out[60, 120] > out[30, 120]  # north is the last row


def test_regrid_propagates_missing_cells():
    src_lat = np.linspace(-90, 90, 46)
    src_lon = np.arange(-180, 180, 4.0)
    field = np.ones((46, 90))
    field[:23] = np.nan  # southern half missing (e.g. ocean for a land variable)
    out = ep.regrid(field, src_lat, src_lon)
    assert np.isnan(out[0]).all() and np.isfinite(out[-1]).all()


def test_check_field_refuses_an_all_missing_period_mean():
    assert ep.check_field(np.array([np.nan, 1.0]), "x")[1] == 1.0
    with pytest.raises(ValueError, match="no valid value"):
        ep.check_field(np.full((2, 2), np.nan), "pr_GFDL")


# --- change and ensemble statistics ---------------------------------------------------------


def test_absolute_change_for_temperature():
    assert ep.model_change(np.array([280.0]), np.array([282.5]), "tas")[0] == 2.5


def test_percent_change_masks_dry_baseline():
    dry = ep.PERCENT_FLOOR["pr"] / 2
    base = np.array([1e-4, dry, 0.0])
    fut = np.array([1.2e-4, dry * 3, 1e-5])
    out = ep.model_change(base, fut, "pr")
    assert out[0] == pytest.approx(20.0)
    assert np.isnan(out[1:]).all()


def test_ensemble_median_percentiles_and_agreement():
    changes = np.array([1.0, 2.0, 3.0, 4.0, -1.0])[:, None, None] * np.ones((1, 1, 2))
    changes[:, 0, 1] = [1.0, -1.0, 2.0, -2.0, np.nan]
    stats = ep.ensemble(changes)
    assert stats["median"][0, 0] == 2.0
    assert stats["p10"][0, 0] == pytest.approx(np.percentile([1, 2, 3, 4, -1], 10))
    assert stats["p90"][0, 0] == pytest.approx(np.percentile([1, 2, 3, 4, -1], 90))
    assert stats["count"][0, 0] == 5 and stats["count"][0, 1] == 4
    assert stats["agreement"][0, 0] == pytest.approx(0.8)
    assert stats["agreement"][0, 1] == pytest.approx(0.0)  # median 0: no direction


def test_ensemble_leaves_cells_with_too_few_models_missing():
    changes = np.full((5, 1, 1), np.nan)
    changes[:2, 0, 0] = [1.0, 2.0]
    stats = ep.ensemble(changes)
    assert np.isnan(stats["median"][0, 0]) and stats["count"][0, 0] == 2


def test_encode_round_trips_and_marks_missing():
    stats = ep.ensemble(np.array([[[1.234, np.nan]], [[1.5, np.nan]], [[2.0, np.nan]]]))
    blob = ep.encode(stats, scale=0.01)
    decoded = ep.decode(blob, shape=(1, 2), scale=0.01)
    assert decoded["median"][0, 0] == pytest.approx(1.5)
    assert np.isnan(decoded["median"][0, 1])
    assert decoded["agreement"][0, 0] == 100 and decoded["agreement"][0, 1] == ep.U8_MISSING
    assert decoded["count"][0, 0] == 3
