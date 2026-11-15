import type { Direction, Location, Period, Season } from "@/lib/api";

const MINUS = "−";

/** Rounds to `digits` significant digits and trims trailing zeros. */
export function formatNumber(value: number, digits = 3): string {
  if (!Number.isFinite(value)) return "n/a";
  if (value === 0) return "0";
  const rounded = Number(value.toPrecision(digits));
  const text = Math.abs(rounded) >= 10000 ? rounded.toLocaleString("en-US") : String(rounded);
  return text.replace("-", MINUS);
}

/** Like formatNumber, with an explicit plus sign for positive values. */
export function formatSigned(value: number, digits = 2): string {
  const text = formatNumber(value, digits);
  return value > 0 ? `+${text}` : text;
}

export function formatSlope(value: number | null, unit: string): string {
  if (value === null) return "no data";
  return `${formatSigned(value)} ${unit} per decade`;
}

/** "p = 0.004", "p < 0.001". */
export function formatP(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "p n/a";
  if (value < 0.001) return "p < 0.001";
  if (value >= 0.995) return "p = 1";
  return `p = ${value < 0.01 ? value.toFixed(3) : value.toFixed(2)}`;
}

export function formatInterval(low: number, high: number): string {
  return `${formatSigned(low)} to ${formatSigned(high)}`;
}

export function formatCoordinates(lat: number, lon: number): string {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}°${ns}, ${Math.abs(lon).toFixed(2)}°${ew}`;
}

export function placeName(location: Location): string {
  return location.label?.trim() || formatCoordinates(location.lat, location.lon);
}

export function formatPeriod(period: Period): string {
  return `${period.start_year}–${period.end_year}`;
}

const SEASON_LABELS: Record<Season, string> = {
  annual: "Whole year",
  DJF: "Dec–Feb",
  MAM: "Mar–May",
  JJA: "Jun–Aug",
  SON: "Sep–Nov",
};

export function seasonLabel(season: Season): string {
  return SEASON_LABELS[season];
}

const DIRECTION_WORDS: Record<Direction, string> = {
  up: "Rising",
  down: "Falling",
  flat: "Flat",
};

export function directionWord(direction: Direction | null): string {
  return direction ? DIRECTION_WORDS[direction] : "No data";
}
