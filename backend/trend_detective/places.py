"""Suggested places to investigate. A blurb says why a place is interesting, never what the
data show: no trend is stated before it has been computed."""

from __future__ import annotations

from trend_detective.models import Place, PlaceKind, PlacesResult, ThemeId


def _place(
    place_id: str,
    name: str,
    country: str,
    lat: float,
    lon: float,
    kind: PlaceKind,
    blurb: str,
    themes: list[ThemeId],
) -> Place:
    return Place(
        id=place_id,
        name=name,
        country=country,
        lat=lat,
        lon=lon,
        kind=kind,
        blurb=blurb,
        suggested_themes=themes,
    )


# fmt: off
PLACES: tuple[Place, ...] = (
    _place("niamey", "Niamey", "Niger", 13.51, 2.11, "grassland",
           "On the edge of the Sahara, where the rains failed in the 1970s and 1980s. "
           "Have they come back?",
           ["water", "soil", "temperature"]),
    _place("manaus", "Manaus", "Brazil", -3.1, -60.0, "rainforest",
           "The heart of the Amazon, where forest and rainfall depend on each other.",
           ["water", "temperature", "air"]),
    _place("tromso", "Tromsø", "Norway", 69.65, 18.96, "polar",
           "Inside the Arctic Circle, a region that scientists say is warming faster than "
           "the rest of the planet.",
           ["temperature", "snow"]),
    _place("delhi", "Delhi", "India", 28.61, 77.21, "city",
           "A megacity under some of the haziest air in the world.",
           ["air", "sunlight", "temperature"]),
    _place("aral", "Aral Sea", "Kazakhstan / Uzbekistan", 45.0, 60.0, "wetland",
           "A sea that shrank to a fraction of its size within one lifetime.",
           ["water", "temperature", "soil"]),
    _place("alps", "Central Alps", "Switzerland", 46.55, 8.0, "mountain",
           "High mountains whose snow and glaciers feed Europe's great rivers.",
           ["snow", "temperature"]),
    _place("central-valley", "Central Valley", "United States", 36.75, -119.77, "farmland",
           "One of the most productive farming regions on Earth, and one of the thirstiest.",
           ["soil", "water", "temperature"]),
    _place("atacama", "Atacama Desert", "Chile", -24.5, -69.25, "desert",
           "The driest non-polar desert on the planet.",
           ["water", "sunlight", "temperature"]),
    _place("venice", "Venice Lagoon", "Italy", 45.44, 12.33, "coast",
           "A city on a tidal lagoon, exposed to every change in sea and sky.",
           ["temperature", "water", "wind"]),
    _place("male", "Malé", "Maldives", 4.17, 73.51, "island",
           "A low coral island in the middle of the warm Indian Ocean.",
           ["temperature", "water", "wind"]),
    _place("tamanrasset", "Tamanrasset", "Algeria", 22.79, 5.52, "desert",
           "An oasis town in the middle of the Sahara, far from any sea.",
           ["temperature", "water", "sunlight"]),
    _place("yakutsk", "Yakutsk", "Russia", 62.03, 129.73, "city",
           "Among the coldest cities on Earth, deep inside the Siberian forest.",
           ["temperature", "snow"]),
    _place("lhasa", "Lhasa", "China", 29.65, 91.1, "mountain",
           "A city on the Tibetan Plateau, 3,600 metres up, where the rivers of Asia begin.",
           ["temperature", "snow", "sunlight"]),
    _place("cairns", "Cairns", "Australia", -16.92, 145.77, "coast",
           "A tropical coast next to the Great Barrier Reef.",
           ["temperature", "water", "wind"]),
    _place("dodge-city", "Dodge City", "United States", 37.75, -100.02, "grassland",
           "The heart of the Great Plains, where the Dust Bowl droughts struck in the 1930s.",
           ["soil", "water", "temperature"]),
    _place("pantanal", "Pantanal", "Brazil", -19.01, -57.65, "wetland",
           "The largest tropical wetland on Earth, flooded and dried out by the seasons.",
           ["water", "soil", "temperature"]),
)
# fmt: on


def build_places() -> PlacesResult:
    return PlacesResult(places=list(PLACES))
