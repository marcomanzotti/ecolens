/**
 * Search among every city of the world above 15,000 inhabitants (GeoNames cities15000,
 * CC BY 4.0). Pure functions only: the file is fetched by `place-index-loader.ts`.
 */

/** One row of `public/places/cities.json`: name, ASCII name ("" if redundant), country code, lat, lon. */
export type PlaceRow = readonly [string, string, string, number, number];

export interface PlaceIndexFile {
  countries: Readonly<Record<string, string>>;
  /** Sorted by population, largest first: the row index is the rank. */
  places: readonly PlaceRow[];
}

export interface WorldPlace {
  name: string;
  country: string;
  countryCode: string;
  lat: number;
  lon: number;
  /** 0 is the most populous city of the list. */
  rank: number;
  /** Folded name and ASCII name, matched against the folded query. */
  keys: readonly string[];
}

// Letters that Unicode does not decompose into a base letter plus an accent.
const SPECIAL_LETTERS: Readonly<Record<string, string>> = {
  ł: "l",
  ø: "o",
  đ: "d",
  ð: "d",
  ħ: "h",
  ı: "i",
  æ: "ae",
  œ: "oe",
  ß: "ss",
  þ: "th",
};
const SPECIAL_PATTERN = new RegExp(`[${Object.keys(SPECIAL_LETTERS).join("")}]`, "g");
const COMBINING_MARKS = /\p{M}/gu;
const SEPARATORS = /[\s\-'’.()/]+/;

/** Lower case, no accents, special letters spelled out: "Reykjavík" and "reykjavik" match. */
export function foldText(text: string): string {
  return text
    .normalize("NFD")
    .replace(COMBINING_MARKS, "")
    .toLowerCase()
    .replace(SPECIAL_PATTERN, (letter) => SPECIAL_LETTERS[letter] ?? letter)
    .trim();
}

export function buildPlaceIndex(file: PlaceIndexFile): readonly WorldPlace[] {
  return file.places.map(([name, ascii, countryCode, lat, lon], rank) => {
    const keys = ascii === "" ? [foldText(name)] : [foldText(name), foldText(ascii)];
    return { name, country: file.countries[countryCode] ?? countryCode, countryCode, lat, lon, rank, keys };
  });
}

/** 0: the name is the query; 1: the name starts with it; 2: a later word does; -1: no match. */
function nameTier(keys: readonly string[], needle: string): number {
  let best = -1;
  for (const key of keys) {
    if (key === needle) return 0;
    if (key.startsWith(needle)) best = 1;
    else if (best === -1 && key.split(SEPARATORS).some((word, i) => i > 0 && word.startsWith(needle))) best = 2;
  }
  return best;
}

function countryMatches(place: WorldPlace, filter: string): boolean {
  if (filter === "") return true;
  return place.countryCode.toLowerCase() === filter || foldText(place.country).startsWith(filter);
}

/**
 * Places whose name (or a word of it) starts with the query, accents ignored.
 * "springfield, us" narrows by country name or code. Exact names first, then names that
 * start with the query, then later words; inside each group the most populous first.
 */
export function searchPlaces(index: readonly WorldPlace[], query: string, limit = 8): WorldPlace[] {
  const [rawName = "", rawCountry = ""] = query.split(",", 2);
  const needle = foldText(rawName);
  const countryFilter = foldText(rawCountry);
  if (needle === "") return [];

  const tiers: WorldPlace[][] = [[], [], []];
  for (const place of index) {
    const tier = nameTier(place.keys, needle);
    if (tier === -1 || tiers[tier].length >= limit || !countryMatches(place, countryFilter)) continue;
    tiers[tier] = [...tiers[tier], place];
    if (tiers[0].length >= limit) break;
  }
  return tiers.flat().slice(0, limit);
}

export function worldPlaceLabel(place: WorldPlace): string {
  return `${place.name}, ${place.country}`;
}
