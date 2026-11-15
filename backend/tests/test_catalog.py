"""Catalog: the 31 variables, 7 themes, seasons, presets and lookup helpers."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from trend_detective import catalog
from trend_detective import models as m
from trend_detective.errors import UnknownVariableError

FIXTURE = Path(__file__).resolve().parents[2] / "frontend" / "fixtures" / "catalog.json"
DATA = Path(__file__).parent / "data"
THEME_IDS = {"temperature", "water", "soil", "snow", "sunlight", "air", "wind"}


def test_catalog_has_31_variables_in_7_themes() -> None:
    built = catalog.build_catalog()

    assert len(built.variables) == 31
    assert {t.id for t in built.themes} == THEME_IDS
    assert {v.theme for v in built.variables} == THEME_IDS


def test_variable_ids_are_unique() -> None:
    ids = [v.id for v in catalog.build_catalog().variables]

    assert [i for i, n in Counter(ids).items() if n > 1] == []


def test_imerg_is_not_listed_because_power_returns_only_fill_values() -> None:
    ids = {v.id for v in catalog.build_catalog().variables}

    assert "IMERG_PRECTOT" not in ids


def test_seasons_and_period_presets() -> None:
    built = catalog.build_catalog()

    assert built.seasons == ["annual", "DJF", "MAM", "JJA", "SON"]
    presets = {p.id: p.period for p in built.period_presets}
    assert presets["full"] == m.Period(start_year=1981, end_year=2025)
    assert presets["satellite"].start_year == 2001
    assert presets["recent"].start_year == 2006
    assert all(p.period.end_year == m.MAX_YEAR for p in built.period_presets)


def test_catalog_constants_follow_the_models() -> None:
    built = catalog.build_catalog()

    assert (built.min_year, built.max_year, built.alpha) == (m.MIN_YEAR, m.MAX_YEAR, m.ALPHA)


def test_every_variable_has_a_plain_english_definition_and_unit() -> None:
    for variable in catalog.build_catalog().variables:
        assert variable.definition.endswith("."), variable.id
        assert len(variable.definition) > 20, variable.id
        assert variable.unit, variable.id
        assert variable.source.provider == "NASA POWER"


@pytest.mark.parametrize(
    ("variable_id", "first_year"),
    [
        ("T2M", 1981),
        ("CLOUD_AMT", 1984),
        ("ALLSKY_SFC_SW_DWN", 1984),
        ("CLRSKY_SFC_SW_DWN", 1984),
        ("ALLSKY_SFC_LW_DWN", 1984),
        ("PW", 2001),
        ("AOD_55", 2001),
        ("CLOUD_OD", 2001),
        ("ALLSKY_SFC_UV_INDEX", 2001),
        ("ALLSKY_SRF_ALB", 2001),
    ],
)
def test_first_years_match_the_checked_power_records(variable_id: str, first_year: int) -> None:
    assert catalog.get_variable(variable_id).first_year == first_year


def test_first_years_match_the_saved_power_samples() -> None:
    """The first year with a real value in the Niamey samples equals first_year."""
    raw: dict[str, dict[str, float]] = {}
    for name in ("power_point_sahel.json", "power_point_sahel_2.json"):
        raw.update(json.loads((DATA / name).read_text())["properties"]["parameter"])
    for variable in catalog.build_catalog().variables:
        annual = {k: v for k, v in raw[variable.id].items() if k.endswith("13") and v != -999.0}
        assert int(min(annual)[:4]) == variable.first_year, variable.id


def test_only_one_witness_group_with_tqv_and_pw() -> None:
    groups = Counter(v.witness_group for v in catalog.build_catalog().variables if v.witness_group)

    assert groups == {"column_water_vapour": 2}
    assert [v.id for v in catalog.witness_group_members("column_water_vapour")] == ["TQV", "PW"]


def test_pw_is_scaled_from_centimetres_to_kg_per_m2() -> None:
    assert catalog.display_scale("PW") == 10.0
    assert catalog.display_scale("T2M") == 1.0
    assert catalog.to_display_units("PW", [0.25, None, 3.0]) == [2.5, None, 30.0]


def test_to_display_units_keeps_missing_values_and_does_not_touch_unscaled() -> None:
    values = [1.5, None, -2.0]

    assert catalog.to_display_units("T2M", values) == values


def test_catalog_texts_never_call_the_water_vapour_pair_independent() -> None:
    for variable in catalog.build_catalog().variables:
        assert "independent" not in variable.definition.lower()


def test_get_variable_raises_for_unknown_id() -> None:
    with pytest.raises(UnknownVariableError):
        catalog.get_variable("NOPE")


def test_select_variables_defaults_to_the_whole_catalog() -> None:
    assert len(catalog.select_variables(None, None)) == 31
    assert len(catalog.select_variables([], [])) == 31


def test_select_variables_by_theme_keeps_catalog_order() -> None:
    selected = catalog.select_variables(["soil", "snow"], None)

    assert [v.id for v in selected] == [
        "GWETTOP",
        "GWETROOT",
        "GWETPROF",
        "SNODP",
        "FRSNO",
        "PRECSNOLAND",
    ]


def test_variable_ids_win_over_themes() -> None:
    selected = catalog.select_variables(["soil"], ["T2M", "PS"])

    assert [v.id for v in selected] == ["T2M", "PS"]


def test_select_variables_rejects_unknown_ids_and_drops_duplicates() -> None:
    with pytest.raises(UnknownVariableError):
        catalog.select_variables(None, ["T2M", "NOPE"])
    assert [v.id for v in catalog.select_variables(None, ["T2M", "T2M"])] == ["T2M"]


def test_witness_group_members_of_unknown_group_is_empty() -> None:
    assert catalog.witness_group_members("nothing") == []


def test_period_years_is_inclusive() -> None:
    assert catalog.period_years(m.Period(start_year=2001, end_year=2010)) == list(range(2001, 2011))


def test_catalog_agrees_with_the_published_fixture_on_ids_and_units() -> None:
    """The fixture was built by the reference script; ids, units and themes must not drift."""
    fixture = json.loads(FIXTURE.read_text())["data"]["variables"]
    built = catalog.build_catalog().variables

    assert [(v["id"], v["unit"], v["theme"], v["first_year"]) for v in fixture] == [
        (v.id, v.unit, v.theme, v.first_year) for v in built
    ]
