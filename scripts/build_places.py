"""Builds the place search index of the front-end from GeoNames.

Source: GeoNames "cities15000" (every city above 15,000 inhabitants) and "countryInfo.txt",
https://download.geonames.org/export/dump/, licence CC BY 4.0 (credit GeoNames).

Download once into data/raw/geonames/ (the folder is not committed):

    curl -LO https://download.geonames.org/export/dump/cities15000.zip
    curl -LO https://download.geonames.org/export/dump/countryInfo.txt

Then run from the repository root:

    python3 -I scripts/build_places.py data/raw/geonames frontend/public/places/cities.json

Output: one compact JSON, places sorted by population (largest first), each row
[name, ascii name or "" when it adds nothing to an accent-free search, country code,
latitude, longitude]. The population is used only for the order (the row index is the rank),
so the file stays small. Coordinates are rounded to 0.01° (about 1 km), well below
the 0.5° grid of NASA POWER.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import unicodedata
import zipfile
from pathlib import Path

CITIES_ZIP = "cities15000.zip"
CITIES_TXT = "cities15000.txt"
COUNTRY_INFO = "countryInfo.txt"
COORD_DECIMALS = 2

# Columns of the GeoNames "geoname" table.
COL_NAME, COL_ASCII, COL_LAT, COL_LON, COL_COUNTRY, COL_POPULATION = 1, 2, 4, 5, 8, 14


def fold(text: str) -> str:
    """Lower case without accents: the same folding the front-end search applies."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def read_countries(path: Path) -> dict[str, str]:
    countries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        countries[fields[0]] = fields[4]
    return countries


def read_cities(path: Path) -> list[list[object]]:
    with zipfile.ZipFile(path) as archive:
        raw = archive.read(CITIES_TXT).decode("utf-8")
    rows: list[list[object]] = []
    for fields in csv.reader(io.StringIO(raw), delimiter="\t", quoting=csv.QUOTE_NONE):
        name = fields[COL_NAME]
        ascii_name = fields[COL_ASCII]
        rows.append(
            [
                name,
                "" if fold(ascii_name) == fold(name) else ascii_name,
                fields[COL_COUNTRY],
                round(float(fields[COL_LAT]), COORD_DECIMALS),
                round(float(fields[COL_LON]), COORD_DECIMALS),
                int(fields[COL_POPULATION] or 0),
            ]
        )
    rows.sort(key=lambda row: (-int(row[5]), str(row[0])))
    return [row[:5] for row in rows]


def main(source_dir: str, output: str) -> None:
    source = Path(source_dir)
    countries = read_countries(source / COUNTRY_INFO)
    cities = read_cities(source / CITIES_ZIP)
    used = sorted({str(row[2]) for row in cities})
    payload = {
        "source": "GeoNames cities15000, CC BY 4.0, https://www.geonames.org/",
        "fields": ["name", "ascii", "country", "lat", "lon"],
        "order": "population, largest first",
        "countries": {code: countries.get(code, code) for code in used},
        "places": cities,
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(cities)} places, {len(used)} countries, {target.stat().st_size} bytes -> {target}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: build_places.py <geonames dir> <output json>")
    main(sys.argv[1], sys.argv[2])
