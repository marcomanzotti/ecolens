import type { AskResult, Location, Period, Place, Season, ThemeId } from "@/lib/api";
import { DEFAULT_PERIOD, type CaseQuery } from "@/lib/case-query";
import { foldText } from "@/lib/place-search";

/** What the visitor has chosen so far on the landing page. */
export interface OpenerState {
  themes: readonly ThemeId[];
  /** null: let the line-up pick the strongest trend. */
  variableId: string | null;
  location: Location | null;
  period: Period;
  season: Season;
}

export type OpenerAction =
  | { type: "toggleTheme"; theme: ThemeId; on: boolean }
  | { type: "setVariable"; variableId: string | null }
  | { type: "setLocation"; location: Location | null }
  | { type: "setPeriod"; period: Period }
  | { type: "setSeason"; season: Season }
  | { type: "applyAsk"; result: AskResult };

export const INITIAL_OPENER: OpenerState = {
  themes: [],
  variableId: null,
  location: null,
  period: DEFAULT_PERIOD,
  season: "annual",
};

export function openerReducer(state: OpenerState, action: OpenerAction): OpenerState {
  switch (action.type) {
    case "toggleTheme": {
      const themes = action.on
        ? [...state.themes.filter((t) => t !== action.theme), action.theme]
        : state.themes.filter((t) => t !== action.theme);
      return { ...state, themes };
    }
    case "setVariable":
      return { ...state, variableId: action.variableId };
    case "setLocation":
      return { ...state, location: action.location };
    case "setPeriod":
      return { ...state, period: action.period };
    case "setSeason":
      return { ...state, season: action.season };
    case "applyAsk":
      return applyAsk(state, action.result);
  }
}

/** Fills the guided questions with what the assistant understood; keeps the rest. */
function applyAsk(state: OpenerState, result: AskResult): OpenerState {
  return {
    themes: result.themes.length > 0 ? result.themes : state.themes,
    variableId: result.variable_ids[0] ?? state.variableId,
    location: result.location ?? state.location,
    period: result.period ?? state.period,
    season: result.season ?? state.season,
  };
}

export function toCaseQuery(state: OpenerState): CaseQuery {
  return {
    location: state.location,
    variableId: state.variableId,
    period: state.period,
    season: state.season,
    themes: state.themes,
    demoId: null,
  };
}

export function samePeriod(a: Period, b: Period): boolean {
  return a.start_year === b.start_year && a.end_year === b.end_year;
}

/** The label used for a suggested place everywhere in the app. */
export function placeLabel(place: Place): string {
  return `${place.name}, ${place.country}`;
}

export function placeToLocation(place: Place): Location {
  return { lat: place.lat, lon: place.lon, label: placeLabel(place) };
}

/** The globe labels markers with the bare name; add the country when we know the place. */
export function enrichLocation(location: Location, places: readonly Place[]): Location {
  const match = places.find((p) => p.lat === location.lat && p.lon === location.lon);
  return match ? placeToLocation(match) : location;
}

const COORDINATES_PATTERN = /^\s*(-?\d{1,2}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/;

/** Reads "13.5, 2.1" typed in the place search. Returns null when it is not a valid pair. */
export function parseCoordinates(text: string): Location | null {
  const match = COORDINATES_PATTERN.exec(text);
  if (!match) return null;
  const lat = Number(match[1]);
  const lon = Number(match[2]);
  const valid = Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
  return valid ? { lat, lon, label: null } : null;
}

/** Suggested places: any part of the name, country or kind, accents and case ignored. */
export function matchesPlace(place: Place, query: string): boolean {
  const needle = foldText(query);
  if (needle === "") return true;
  return foldText(`${place.name} ${place.country} ${place.kind}`).includes(needle);
}
