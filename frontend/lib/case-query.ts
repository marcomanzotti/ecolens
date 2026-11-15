import type { BBox, Location, Period, Season, ThemeId } from "@/lib/api";

/** Everything that identifies a case. It lives in the URL so a case can be shared. */
export interface CaseQuery {
  location: Location | null;
  variableId: string | null;
  period: Period;
  season: Season;
  themes: readonly ThemeId[];
  demoId: string | null;
}

/** Route of the case page. The landing page lives at "/". */
export const CASE_PATH = "/case";

export const DEFAULT_PERIOD: Period = { start_year: 1981, end_year: 2025 };
export const SEASONS: readonly Season[] = ["annual", "DJF", "MAM", "JJA", "SON"];
export const THEME_IDS: readonly ThemeId[] = [
  "temperature",
  "water",
  "soil",
  "snow",
  "sunlight",
  "air",
  "wind",
];

const MIN_YEAR = 1981;
const MAX_YEAR = 2100;
const MAX_LABEL_LENGTH = 80;
const VARIABLE_ID_PATTERN = /^[A-Z0-9_]{1,40}$/;
const DEMO_ID_PATTERN = /^[a-z0-9-]{1,60}$/;
const MAP_BOX_HALF_SIDE = 5;

interface ParamReader {
  get(name: string): string | null;
}

function readNumber(raw: string | null, min: number, max: number): number | null {
  if (raw === null || raw.trim() === "") return null;
  const value = Number(raw);
  return Number.isFinite(value) && value >= min && value <= max ? value : null;
}

function readYear(raw: string | null): number | null {
  const value = readNumber(raw, MIN_YEAR, MAX_YEAR);
  return value !== null && Number.isInteger(value) ? value : null;
}

export function isSeason(value: string | null): value is Season {
  return value !== null && (SEASONS as readonly string[]).includes(value);
}

export function isThemeId(value: string): value is ThemeId {
  return (THEME_IDS as readonly string[]).includes(value);
}

/** Reads a case from URL parameters. Anything malformed falls back to the default. */
export function parseCaseQuery(params: ParamReader): CaseQuery {
  const lat = readNumber(params.get("lat"), -90, 90);
  const lon = readNumber(params.get("lon"), -180, 180);
  const label = params.get("label")?.trim().slice(0, MAX_LABEL_LENGTH) || null;
  const start = readYear(params.get("start"));
  const end = readYear(params.get("end"));
  const season = params.get("season");
  const variable = params.get("variable");
  const demo = params.get("demo");
  const hasPeriod = start !== null && end !== null && start < end;

  return {
    location: lat !== null && lon !== null ? { lat, lon, label } : null,
    variableId: variable !== null && VARIABLE_ID_PATTERN.test(variable) ? variable : null,
    period: hasPeriod ? { start_year: start, end_year: end } : DEFAULT_PERIOD,
    season: isSeason(season) ? season : "annual",
    themes: (params.get("themes") ?? "").split(",").filter(isThemeId),
    demoId: demo !== null && DEMO_ID_PATTERN.test(demo) ? demo : null,
  };
}

/** Builds the URL of a case. Defaults are left out to keep links short. */
export function caseHref(query: CaseQuery): string {
  const params = new URLSearchParams();
  if (query.demoId) {
    params.set("demo", query.demoId);
    return `${CASE_PATH}?${params.toString()}`;
  }
  if (query.location) {
    params.set("lat", String(Number(query.location.lat.toFixed(4))));
    params.set("lon", String(Number(query.location.lon.toFixed(4))));
    if (query.location.label) params.set("label", query.location.label);
  }
  if (query.variableId) params.set("variable", query.variableId);
  const isDefaultPeriod =
    query.period.start_year === DEFAULT_PERIOD.start_year &&
    query.period.end_year === DEFAULT_PERIOD.end_year;
  if (!isDefaultPeriod) {
    params.set("start", String(query.period.start_year));
    params.set("end", String(query.period.end_year));
  }
  if (query.season !== "annual") params.set("season", query.season);
  if (query.themes.length > 0) params.set("themes", query.themes.join(","));
  const text = params.toString();
  return text ? `${CASE_PATH}?${text}` : CASE_PATH;
}

/** The same case, investigating another variable (leaves any demo). */
export function withVariable(query: CaseQuery, location: Location, variableId: string): CaseQuery {
  return { ...query, location, variableId, demoId: null };
}

export const EMPTY_QUERY: CaseQuery = {
  location: null,
  variableId: null,
  period: DEFAULT_PERIOD,
  season: "annual",
  themes: [],
  demoId: null,
};

/** A 10° × 10° box centred on the place, kept inside the valid range. */
export function boxAround(location: Location): BBox {
  const lat = Math.min(
    Math.max(Math.round(location.lat), -90 + MAP_BOX_HALF_SIDE),
    90 - MAP_BOX_HALF_SIDE,
  );
  const lon = Math.min(
    Math.max(Math.round(location.lon), -180 + MAP_BOX_HALF_SIDE),
    180 - MAP_BOX_HALF_SIDE,
  );
  return {
    lat_min: lat - MAP_BOX_HALF_SIDE,
    lat_max: lat + MAP_BOX_HALF_SIDE,
    lon_min: lon - MAP_BOX_HALF_SIDE,
    lon_max: lon + MAP_BOX_HALF_SIDE,
  };
}
