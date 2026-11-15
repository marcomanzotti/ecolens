/** Text alternatives of the trend map. Pure module: no three.js, no DOM. */
import type { OppositeTwin, TrendMapCell, TrendMapResult } from "@/lib/api";
import type { TimelapseMeta } from "./timelapse-data";
import type { TimelapseDataset } from "./timelapse-datasets";

const MINUS = "−";
const SLOPE_DIGITS = 2;
const COORD_DIGITS = 2;

function coordinates(lat: number, lon: number): string {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(COORD_DIGITS)}°${ns}, ${Math.abs(lon).toFixed(COORD_DIGITS)}°${ew}`;
}

/** "+0.31", "−0.17", "0". */
export function signedSlope(value: number): string {
  const rounded = Number(value.toPrecision(SLOPE_DIGITS));
  if (rounded === 0) return "0";
  return rounded > 0 ? `+${rounded}` : `${MINUS}${Math.abs(rounded)}`;
}

/** One cell in words: where, how much, and whether the trend is significant. */
export function cellLabel(cell: TrendMapCell, unit: string): string {
  const where = coordinates(cell.lat, cell.lon);
  if (cell.slope_per_decade === null) return `${where}: no data`;
  const significance = cell.significant ? "significant" : "not significant";
  return `${where}: ${signedSlope(cell.slope_per_decade)} ${unit} per decade, ${significance}`;
}

/** The trend map in one paragraph, for people who cannot see the globe. */
export function trendMapSummary(map: TrendMapResult, twin: OppositeTwin | null | undefined): string {
  const { summary, variable, period, bbox, correction } = map;
  const sentences = [
    `Trend map of ${variable.name} (${variable.unit} per decade), ${period.start_year}–${period.end_year}, ` +
      `between ${coordinates(bbox.lat_min, bbox.lon_min)} and ${coordinates(bbox.lat_max, bbox.lon_max)}: ` +
      `${summary.n_cells} cells, ${summary.n_valid} with enough data.`,
    `${summary.n_up_significant} rising and ${summary.n_down_significant} falling significantly ` +
      `(${correction.label}, alpha ${correction.alpha}).`,
  ];
  if (twin) {
    sentences.push(
      `Opposite twin, ${Math.round(twin.distance_km)} km apart: rising at ${cellLabel(twin.up, variable.unit)}; ` +
        `falling at ${cellLabel(twin.down, variable.unit)}.`,
    );
  }
  return sentences.join(" ");
}

/** A time-lapse in words: the significant share of the measured area, year by year. */
export function timelapseSummary(meta: TimelapseMeta, dataset: TimelapseDataset): string {
  const first = meta.years[0];
  const { up, down } = dataset.labels;
  const rows = meta.shares
    .filter((row) => row.tested_cells > 0)
    .map((row) => `${row.year}: ${row.up_pct}% ${up}, ${row.down_pct}% ${down}`);
  return (
    `${dataset.label} time-lapse from ${dataset.credit}, ${dataset.quantity.toLowerCase()} (${dataset.unit}) ` +
    `vs ${meta.baseline} on a ${meta.grid.step_deg}° grid, ${meta.years[0]}–${meta.years[meta.years.length - 1]}. ` +
    `For each year, the share of the ${dataset.denominator} (area-weighted) with a significant trend since ${first} ` +
    `(Mann-Kendall, ${meta.test.correction}, alpha ${meta.test.alpha}): ${rows.join("; ")}.`
  );
}
