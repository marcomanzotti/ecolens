/**
 * CMIP6 climate model projections (2041–2060 vs 1995–2014), read from the static files written by
 * scripts/earth_projections_build.py (public/earth/projections). Pure module: no DOM, no React
 * (fetch is passed in). Nothing is computed here beyond reading a cell: every number is in the files.
 */

export type ScenarioId = "ssp245" | "ssp585";
export const SCENARIOS: readonly ScenarioId[] = ["ssp245", "ssp585"];
export const SCENARIO_LABELS: Readonly<Record<ScenarioId, string>> = {
  ssp245: "SSP2-4.5",
  ssp585: "SSP5-8.5",
};
export const SCENARIO_WORDS: Readonly<Record<ScenarioId, string>> = {
  ssp245: "moderate emissions",
  ssp585: "high emissions",
};
/** IPCC AR6 simple approach: a change is robust where at least 80% of models agree on its sign. */
export const ROBUST_AGREEMENT_PCT = 80;
export const PROJECTIONS_BASE_URL = "/earth/projections";

export interface ProjectionModel {
  source_id: string;
  institution_id: string;
  member_id: string;
}

export interface ProjectionVariable {
  name: string;
  cmip6_id: string;
  /** "K" (absolute change) or "%" (change relative to the baseline). */
  unit: string;
  scale: number;
  models: ProjectionModel[];
  files: Record<ScenarioId, string>;
}

export interface ProjectionMeta {
  baseline: [number, number];
  future: [number, number];
  grid: { n_lat: number; n_lon: number; lat_first: number; lon_first: number; step_deg: number };
  file_layout: { missing_int16: number; missing_uint8: number };
  agreement_rule: string;
  regridding: string;
  caveats: string[];
  variables: Record<string, ProjectionVariable>;
}

export interface ProjectionField {
  variableId: string;
  scenario: ScenarioId;
  median: Int16Array;
  p10: Int16Array;
  p90: Int16Array;
  /** % of models with the sign of the median; `missing_uint8` = no value. */
  agreement: Uint8Array;
  count: Uint8Array;
}

export interface ProjectionCell {
  median: number;
  p10: number;
  p90: number;
  agreementPct: number;
  /** Models with a value in this cell. */
  count: number;
  /** Models agreeing with the sign of the median. */
  agreeing: number;
  robust: boolean;
}

/** POWER variable id -> CMIP6 variable (only physically matching pairs). */
const POWER_TO_CMIP6: Readonly<Record<string, string>> = {
  T2M: "tas",
  PRECTOTCORR: "pr",
  GWETTOP: "mrsos",
  GWETROOT: "mrsos",
  RH2M: "hurs",
  ALLSKY_SFC_SW_DWN: "rsds",
  WS10M: "sfcWind",
  CLOUD_AMT: "clt",
};

/** Words for a rise / fall of each CMIP6 variable: "11 of 13 models project drier conditions". */
const DIRECTION_WORDS: Readonly<Record<string, { up: string; down: string }>> = {
  tas: { up: "warmer conditions", down: "cooler conditions" },
  pr: { up: "wetter conditions", down: "drier conditions" },
  mrsos: { up: "wetter soils", down: "drier soils" },
  hurs: { up: "more humid air", down: "drier air" },
  rsds: { up: "more sunlight", down: "less sunlight" },
  sfcWind: { up: "windier conditions", down: "calmer conditions" },
  clt: { up: "cloudier skies", down: "clearer skies" },
  lai: { up: "greener vegetation", down: "less green vegetation" },
};

export function cmip6VariableFor(powerId: string | null | undefined): string | null {
  return powerId ? (POWER_TO_CMIP6[powerId] ?? null) : null;
}

type Fetcher = (url: string) => Promise<Response>;

async function fetchOk(fetcher: Fetcher, url: string): Promise<Response> {
  const response = await fetcher(url);
  if (!response.ok) throw new Error(`Could not load ${url} (HTTP ${response.status})`);
  return response;
}

export async function loadProjectionMeta(fetcher: Fetcher = fetch): Promise<ProjectionMeta> {
  return (await (await fetchOk(fetcher, `${PROJECTIONS_BASE_URL}/meta.json`)).json()) as ProjectionMeta;
}

/** Splits a file: int16 median, p10, p90, then uint8 agreement and count (see meta.file_layout). */
export function parseProjectionField(
  meta: ProjectionMeta,
  variableId: string,
  scenario: ScenarioId,
  buffer: ArrayBuffer,
): ProjectionField {
  const cells = meta.grid.n_lat * meta.grid.n_lon;
  if (buffer.byteLength !== cells * 8) throw new Error("The projection file does not match meta.json");
  return {
    variableId,
    scenario,
    median: new Int16Array(buffer, 0, cells),
    p10: new Int16Array(buffer, cells * 2, cells),
    p90: new Int16Array(buffer, cells * 4, cells),
    agreement: new Uint8Array(buffer, cells * 6, cells),
    count: new Uint8Array(buffer, cells * 7, cells),
  };
}

export async function loadProjectionField(
  meta: ProjectionMeta,
  variableId: string,
  scenario: ScenarioId,
  fetcher: Fetcher = fetch,
): Promise<ProjectionField> {
  const variable = meta.variables[variableId];
  if (!variable) throw new Error(`No projection for ${variableId}`);
  const response = await fetchOk(fetcher, `${PROJECTIONS_BASE_URL}/${variable.files[scenario]}`);
  return parseProjectionField(meta, variableId, scenario, await response.arrayBuffer());
}

/** Index of the grid cell containing a point (rows south to north, columns west to east). */
export function projectionCellIndex(meta: ProjectionMeta, lat: number, lon: number): number {
  const { n_lat, n_lon, lat_first, lon_first, step_deg } = meta.grid;
  const half = step_deg / 2;
  const row = Math.min(n_lat - 1, Math.max(0, Math.floor((lat - (lat_first - half)) / step_deg)));
  const wrapped = ((((lon - (lon_first - half)) % 360) + 360) % 360) / step_deg;
  return row * n_lon + Math.min(n_lon - 1, Math.floor(wrapped));
}

/** The values of one cell, or null where the models give no value (e.g. sea for a land variable). */
export function projectionAt(
  meta: ProjectionMeta,
  field: ProjectionField,
  lat: number,
  lon: number,
): ProjectionCell | null {
  const cell = projectionCellIndex(meta, lat, lon);
  const { scale } = meta.variables[field.variableId];
  const raw = field.median[cell];
  const agreementPct = field.agreement[cell];
  if (raw === meta.file_layout.missing_int16 || agreementPct === meta.file_layout.missing_uint8) return null;
  const count = field.count[cell];
  return {
    median: raw * scale,
    p10: field.p10[cell] * scale,
    p90: field.p90[cell] * scale,
    agreementPct,
    count,
    agreeing: Math.round((agreementPct * count) / 100),
    robust: agreementPct >= ROBUST_AGREEMENT_PCT,
  };
}

/** "11 of 13 models project drier conditions." */
export function agreementSentence(variableId: string, cell: ProjectionCell): string {
  const words = DIRECTION_WORDS[variableId] ?? { up: "an increase", down: "a decrease" };
  if (cell.median === 0) return `The ${cell.count} models do not agree on a direction.`;
  const direction = cell.median > 0 ? words.up : words.down;
  return `${cell.agreeing} of ${cell.count} models project ${direction}.`;
}
