/**
 * Time-lapse data: the static files written by scripts/build_earth_assets.py
 * (public/earth/gistemp, public/earth/ndvi). Pure module: no three.js, no DOM (fetch is passed in).
 * Every number the time-lapse shows comes from these files; nothing is computed in a shader.
 */
import { TIMELAPSE_DATASETS, type TimelapseDataset } from "./timelapse-datasets";

/** Share of the measured area with a significant rising (up) or falling (down) trend. */
export interface TimelapseShare {
  year: number;
  tested_cells: number;
  up_cells: number;
  down_cells: number;
  up_pct: number;
  down_pct: number;
}

/** A row of `shares` as written in meta.json: keys named after the labels (warming_pct, ...). */
type RawShare = { year: number; tested_cells: number } & Record<string, number>;

export interface TimelapseMeta {
  format_version: number;
  source: { name: string; url: string; file_date: string; missing_months?: string[] };
  baseline: string;
  unit: string;
  /** Names of a rising / falling trend; GISTEMP's file predates the field (warming / cooling). */
  labels?: { up: string; down: string };
  quantisation?: { max_error: number; content: string };
  years: number[];
  grid: { n_lat: number; n_lon: number; lat_first: number; lon_first: number; step_deg: number };
  files: { "anomaly.bin": { scale: number; missing: number }; "rate.bin": { parts: [{ scale: number }, unknown] } };
  test: { rule: string; alpha: number; correction: string; min_years: number; area_weight: string };
  shares: TimelapseShare[];
}

export interface TimelapseData {
  dataset: TimelapseDataset;
  meta: TimelapseMeta;
  /** Int16 centi-K, years x lat x lon, rows south to north; `meta.files["anomaly.bin"].missing` = no data. */
  anomaly: Int16Array;
  /** -1 / 0 / +1 per year per cell: significant trend over the window first year -> year. */
  emerged: Int8Array;
  /** Sen slope at the end of the series, Int16 milli-K per decade. */
  rateSlope: Int16Array;
  /** Significance at the end of the series (-1 / 0 / +1). */
  rateDirection: Int8Array;
}

export interface CellDetail {
  lat: number;
  lon: number;
  year: number;
  /** In the dataset's unit, null when the year has no valid annual value. */
  anomaly: number | null;
  /** Unit per decade over the whole series, null when the cell was never tested. */
  slopePerDecade: number | null;
  /** -1 / 0 / +1 at the end of the series. */
  direction: number;
  /** First end year from which the trend stays significant to the end; null if it never does. */
  emergedYear: number | null;
  /** Annual anomalies (null = missing), one per year of `meta.years`. */
  series: (number | null)[];
}

type Fetcher = (url: string) => Promise<Response>;

async function fetchOk(fetcher: Fetcher, url: string): Promise<Response> {
  const response = await fetcher(url);
  if (!response.ok) throw new Error(`Could not load ${url} (HTTP ${response.status})`);
  return response;
}

/** meta.json rows (warming_pct, greening_pct, ...) -> the generic up / down shape. */
export function normaliseShares(rows: readonly RawShare[], labels: { up: string; down: string }): TimelapseShare[] {
  return rows.map((row) => ({
    year: row.year,
    tested_cells: row.tested_cells,
    up_cells: row[`${labels.up}_cells`] ?? 0,
    down_cells: row[`${labels.down}_cells`] ?? 0,
    up_pct: row[`${labels.up}_pct`] ?? 0,
    down_pct: row[`${labels.down}_pct`] ?? 0,
  }));
}

export async function loadTimelapse(
  dataset: TimelapseDataset = TIMELAPSE_DATASETS.temperature,
  fetcher: Fetcher = fetch,
): Promise<TimelapseData> {
  const base = dataset.baseUrl;
  const raw = (await (await fetchOk(fetcher, `${base}/meta.json`)).json()) as TimelapseMeta & { shares: RawShare[] };
  const labels = raw.labels ?? dataset.labels;
  const meta: TimelapseMeta = { ...raw, labels, shares: normaliseShares(raw.shares, labels) };
  const buffers = await Promise.all(
    ["anomaly.bin", "emerged.bin", "rate.bin"].map(async (name) => (await fetchOk(fetcher, `${base}/${name}`)).arrayBuffer()),
  );
  const cells = meta.grid.n_lat * meta.grid.n_lon;
  const frames = meta.years.length * cells;
  const [anomaly, emerged, rate] = buffers;
  if (anomaly.byteLength !== frames * 2 || emerged.byteLength !== frames || rate.byteLength !== cells * 3) {
    throw new Error("The time-lapse files do not match their description in meta.json");
  }
  return {
    dataset,
    meta,
    anomaly: new Int16Array(anomaly),
    emerged: new Int8Array(emerged),
    rateSlope: new Int16Array(rate, 0, cells),
    rateDirection: new Int8Array(rate, cells * 2, cells),
  };
}

export function yearIndex(meta: TimelapseMeta, year: number): number {
  const index = year - meta.years[0];
  return Math.min(meta.years.length - 1, Math.max(0, index));
}

/** Grid cell (row south to north, column west to east) containing a point. */
export function cellOf(meta: TimelapseMeta, lat: number, lon: number): { row: number; col: number } {
  const { n_lat, n_lon, lat_first, lon_first, step_deg } = meta.grid;
  const half = step_deg / 2;
  const row = Math.floor((lat - (lat_first - half)) / step_deg);
  const wrapped = ((((lon - (lon_first - half)) % 360) + 360) % 360) / step_deg;
  return { row: Math.min(n_lat - 1, Math.max(0, row)), col: Math.min(n_lon - 1, Math.floor(wrapped)) };
}

export function shareFor(meta: TimelapseMeta, year: number): TimelapseShare {
  return meta.shares[yearIndex(meta, year)];
}

function anomalyAt(data: TimelapseData, frame: number, cell: number): number | null {
  const { scale, missing } = data.meta.files["anomaly.bin"];
  const raw = data.anomaly[frame * data.meta.grid.n_lat * data.meta.grid.n_lon + cell];
  return raw === missing ? null : raw * scale;
}

/** First end year from which the cell stays significant in the same direction to the end. */
export function emergedYear(data: TimelapseData, cell: number): number | null {
  const { years, grid } = data.meta;
  const cells = grid.n_lat * grid.n_lon;
  const last = data.emerged[(years.length - 1) * cells + cell];
  if (last === 0) return null;
  let first = years.length - 1;
  while (first > 0 && data.emerged[(first - 1) * cells + cell] === last) first -= 1;
  return years[first];
}

export function cellDetail(data: TimelapseData, lat: number, lon: number, year: number): CellDetail {
  const { meta } = data;
  const { row, col } = cellOf(meta, lat, lon);
  const cell = row * meta.grid.n_lon + col;
  const slopeRaw = data.rateSlope[cell];
  return {
    lat: meta.grid.lat_first + row * meta.grid.step_deg,
    lon: meta.grid.lon_first + col * meta.grid.step_deg,
    year,
    anomaly: anomalyAt(data, yearIndex(meta, year), cell),
    slopePerDecade:
      slopeRaw === meta.files["anomaly.bin"].missing ? null : slopeRaw * meta.files["rate.bin"].parts[0].scale,
    direction: data.rateDirection[cell],
    emergedYear: emergedYear(data, cell),
    series: meta.years.map((_, k) => anomalyAt(data, k, cell)),
  };
}
