/**
 * The time-lapse datasets: where the files are, and how to colour and name their numbers.
 * Pure module (no three.js, no DOM). Each dataset is built by scripts/build_earth_assets.py.
 *
 * Every scale is stepped and diverging, the same for every year, with a near-neutral pair of
 * bands around 0. Both arms of each scale were checked with the dataviz validator against Deep
 * Blue (#07173F): lightness monotone, visible steps, far ends at least 3:1 (NDVI) / 2:1 (K).
 * The NDVI scale uses brown and teal on purpose: red and blue already mean warming and cooling.
 */
import { ANOMALY_BANDS, ANOMALY_MAX_K, ANOMALY_MIN_K, ANOMALY_STEP_K, FRONT_COLORS } from "./timelapse-palette";

export type TimelapseDatasetId = "temperature" | "vegetation";

export interface TimelapseScale {
  min: number;
  max: number;
  step: number;
  /** One colour per step, from `min` to `max`. */
  bands: readonly string[];
  /** Values written under the legend bar. */
  ticks: readonly number[];
  /** Decimals used to print a value of this unit. */
  digits: number;
  /** Encoded range of the anomaly texture (beyond the colour scale on purpose). */
  encodeRange: number;
}

export interface TimelapseDataset {
  id: TimelapseDatasetId;
  /** Name in the dataset switch. */
  label: string;
  baseUrl: string;
  /** Unit of the anomaly, as printed. */
  unit: string;
  /** What is coloured, for the legend title: "Annual temperature anomaly". */
  quantity: string;
  /** Words for a significant rising / falling trend. */
  labels: { up: string; down: string };
  /** Colours of the emergence front, glow and rings. */
  frontColors: { up: string; down: string };
  /** The colours of the two arms, in words, for the text alternative. */
  armsInWords: string;
  /** "measured surface" / "measured land". */
  denominator: string;
  /** Source credit under the legend. */
  credit: string;
  scale: TimelapseScale;
}

/** Browning (lowest band) to greening (highest band), steps of 0.02 NDVI. */
export const NDVI_BANDS: readonly string[] = [
  "#A0560E",
  "#C98228",
  "#E0AE5E",
  "#EFD29C",
  "#F8EEDB",
  "#DDF1EA",
  "#AEE0CF",
  "#6FC7AE",
  "#22A085",
  "#00785F",
];

export const NDVI_FRONT_COLORS = { up: "#3DDBB0", down: "#FFA630" } as const;

export const TIMELAPSE_DATASETS: Readonly<Record<TimelapseDatasetId, TimelapseDataset>> = {
  temperature: {
    id: "temperature",
    label: "Temperature",
    baseUrl: "/earth/gistemp",
    unit: "K",
    quantity: "Annual temperature anomaly",
    labels: { up: "warming", down: "cooling" },
    frontColors: { up: FRONT_COLORS.warming, down: FRONT_COLORS.cooling },
    armsInWords: "blue below zero and red above",
    denominator: "measured surface",
    credit: "GISTEMP v4, NASA GISS",
    scale: {
      min: ANOMALY_MIN_K,
      max: ANOMALY_MAX_K,
      step: ANOMALY_STEP_K,
      bands: ANOMALY_BANDS,
      ticks: [-2, -1, 0, 1, 2, 3, 4],
      digits: 2,
      encodeRange: 6,
    },
  },
  vegetation: {
    id: "vegetation",
    label: "Vegetation",
    baseUrl: "/earth/ndvi",
    unit: "NDVI",
    quantity: "Annual peak greenness anomaly",
    labels: { up: "greening", down: "browning" },
    frontColors: NDVI_FRONT_COLORS,
    armsInWords: "brown below zero and teal above",
    denominator: "measured land",
    credit: "MODIS Terra NDVI, NASA LP DAAC / GIBS",
    scale: {
      min: -0.1,
      max: 0.1,
      step: 0.02,
      bands: NDVI_BANDS,
      ticks: [-0.1, -0.05, 0, 0.05, 0.1],
      digits: 3,
      encodeRange: 0.5,
    },
  },
};

export const DEFAULT_DATASET: TimelapseDatasetId = "temperature";
export const DATASET_ORDER: readonly TimelapseDatasetId[] = ["temperature", "vegetation"];

/** Index of the band a value falls in; out-of-range values take the end band. */
export function scaleBandIndex(scale: TimelapseScale, value: number): number {
  const index = Math.floor((value - scale.min) / scale.step + 1e-9);
  return Math.min(scale.bands.length - 1, Math.max(0, index));
}

/** CSS hard-stop gradient of the bands, for the legend bar. */
export function scaleGradientCss(scale: TimelapseScale, direction = "to right"): string {
  const width = 100 / scale.bands.length;
  const stops = scale.bands.map((color, i) => `${color} ${i * width}% ${(i + 1) * width}%`);
  return `linear-gradient(${direction}, ${stops.join(", ")})`;
}
