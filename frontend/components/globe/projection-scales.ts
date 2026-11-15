/**
 * Colour scales of the "2050" layer (CMIP6 median change, 2041–2060 vs 1995–2014). Pure module.
 *
 * Both reuse scales already validated with the dataviz validator for the time-lapse, so the
 * same colour means the same thing across layers:
 * - temperature: the GISTEMP anomaly bands (steps of 0.5 K, −2 to +4 K, red = warmer);
 * - precipitation: the brown↔teal NDVI bands (brown = drier, teal = wetter; red and blue already
 *   mean warmer and cooler), here in steps of 5% from −25% to +25%.
 * Values beyond either end take the end band; the legend marks that with an arrow.
 */
import { NDVI_BANDS, type TimelapseScale } from "./timelapse-datasets";
import { ANOMALY_BANDS, ANOMALY_MAX_K, ANOMALY_MIN_K, ANOMALY_STEP_K } from "./timelapse-palette";

export type ProjectionLayerVariable = "tas" | "pr";

export interface ProjectionLayerSpec {
  id: ProjectionLayerVariable;
  label: string;
  /** Unit as printed. */
  unit: string;
  quantity: string;
  armsInWords: string;
  /** Why some land has no colour, if it can happen. */
  blankNote?: string;
  scale: TimelapseScale;
}

export const PROJECTION_LAYER_ORDER: readonly ProjectionLayerVariable[] = ["tas", "pr"];

export const PROJECTION_LAYERS: Readonly<Record<ProjectionLayerVariable, ProjectionLayerSpec>> = {
  tas: {
    id: "tas",
    label: "Temperature",
    unit: "°C",
    quantity: "Projected temperature change",
    armsInWords: "blue below zero and red above, the same colours as the measured anomaly",
    scale: {
      min: ANOMALY_MIN_K,
      max: ANOMALY_MAX_K,
      step: ANOMALY_STEP_K,
      bands: ANOMALY_BANDS,
      ticks: [-2, -1, 0, 1, 2, 3, 4],
      digits: 1,
      encodeRange: 0,
    },
  },
  pr: {
    id: "pr",
    label: "Precipitation",
    unit: "%",
    quantity: "Projected precipitation change",
    armsInWords: "brown for drier and teal for wetter",
    blankNote: "No colour: almost no rain in 1995–2014 (below 0.1 mm/day), so no % change",
    scale: {
      min: -25,
      max: 25,
      step: 5,
      bands: NDVI_BANDS,
      ticks: [-25, -15, -5, 5, 15, 25],
      digits: 0,
      encodeRange: 0,
    },
  },
};
