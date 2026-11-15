"""Suggested places: coverage, coordinates and consistency with the catalog."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trend_detective import catalog, places

FIXTURE = Path(__file__).resolve().parents[2] / "frontend" / "fixtures" / "places.json"

# Expected hemispheres (lat sign, lon sign) and a rough bounding box per place, written from
# the real geography so that a swapped or mistyped coordinate is caught.
EXPECTED_REGION = {
    "niamey": (10, 16, 0, 5),
    "manaus": (-5, -1, -63, -58),
    "tromso": (68, 71, 17, 21),
    "delhi": (27, 30, 76, 78),
    "aral": (43, 47, 57, 62),
    "alps": (45, 48, 6, 10),
    "central-valley": (35, 38, -121, -118),
    "atacama": (-27, -20, -71, -68),
    "venice": (45, 46, 12, 13),
    "male": (3, 5, 73, 74),
    "tamanrasset": (22, 23, 5, 6),
    "yakutsk": (61, 63, 129, 131),
    "lhasa": (29, 30, 90, 92),
    "cairns": (-18, -16, 145, 146),
    "dodge-city": (37, 38, -101, -99),
    "pantanal": (-20, -18, -58, -57),
}


def test_has_the_ten_reference_places_and_at_most_six_more() -> None:
    result = places.build_places()

    assert 10 <= len(result.places) <= 16
    fixture_ids = [p["id"] for p in json.loads(FIXTURE.read_text())["data"]["places"]]
    assert [p.id for p in result.places] == fixture_ids


def test_ids_are_unique_and_names_not_empty() -> None:
    result = places.build_places()

    assert [i for i, n in Counter(p.id for p in result.places).items() if n > 1] == []
    assert all(p.name and p.country and p.blurb for p in result.places)


def test_coordinates_fall_in_the_expected_region() -> None:
    result = places.build_places()

    assert {p.id for p in result.places} == set(EXPECTED_REGION)
    for place in result.places:
        lat_lo, lat_hi, lon_lo, lon_hi = EXPECTED_REGION[place.id]
        assert lat_lo <= place.lat <= lat_hi, place.id
        assert lon_lo <= place.lon <= lon_hi, place.id


def test_places_cover_every_place_kind_of_the_contract() -> None:
    kinds = {p.kind for p in places.build_places().places}

    assert kinds == {
        "desert",
        "rainforest",
        "city",
        "coast",
        "mountain",
        "polar",
        "farmland",
        "grassland",
        "island",
        "wetland",
    }


def test_suggested_themes_exist_and_are_not_empty() -> None:
    theme_ids = {t.id for t in catalog.build_catalog().themes}

    for place in places.build_places().places:
        assert place.suggested_themes, place.id
        assert set(place.suggested_themes) <= theme_ids, place.id
        assert len(set(place.suggested_themes)) == len(place.suggested_themes)


def test_blurbs_state_no_computed_trend() -> None:
    forbidden = ("is getting", "has increased", "has decreased", "is rising", "is falling")
    for place in places.build_places().places:
        assert not any(phrase in place.blurb.lower() for phrase in forbidden), place.id
