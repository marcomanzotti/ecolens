/**
 * Stepped diverging scale of the temperature anomaly field (see timelapse-datasets.ts for the
 * vegetation one). Pure module.
 *
 * Bands of 0.5 K from -2 to +4 K, read like contour levels; the same for every year, so a red
 * of 1985 means what a red of 2024 means. Cool arm in the Blue Yonder family, warm arm ending
 * near Rocket Red; the two bands next to 0 are near-neutral. Both arms were checked with the
 * dataviz validator (lightness monotone, visible steps, far ends at least 2:1 against Deep Blue),
 * and the poles are far apart for colour-blind readers (deutan Delta E 29.6). Values outside the
 * scale take the colour of the end band; the legend marks that with an arrow.
 */

export const ANOMALY_MIN_K = -2;
export const ANOMALY_MAX_K = 4;
export const ANOMALY_STEP_K = 0.5;

/** From the coldest band (-2 to -1.5 K) to the warmest (+3.5 to +4 K). */
export const ANOMALY_BANDS: readonly string[] = [
  "#0475D1",
  "#2E96F5",
  "#82B7F3",
  "#B8D8FB",
  "#FEE9E4",
  "#FFCCBE",
  "#FEAD97",
  "#FC8D6F",
  "#F16F4C",
  "#E64E22",
  "#CE3901",
  "#AF2F02",
];

/** Missing cells: grey hatching, never filled with a value. */
export const MISSING_COLOR = "#6B7280";
export const MISSING_HATCH_COLOR = "#9CA3AF";

/** Emergence front of the temperature: line and one-cell glow. Warming / cooling. */
export const FRONT_COLORS = { warming: "#FF5A1F", cooling: "#5CB8FF" } as const;
