/**
 * Colours of the globe and of the trend layer. Pure module (no three.js, no DOM)
 * so the legend can import it without pulling in the 3D bundle.
 */

/** Space Apps brand colours used on the globe (docs/BRAND.md). */
export const GLOBE_COLORS = {
  ocean: "#07173F",
  oceanLight: "#0A2259",
  land: "#16408F",
  coast: "#2E96F5",
  graticule: "rgba(255, 255, 255, 0.07)",
  atmosphere: "#2E96F5",
  marker: "#FFFFFF",
  markerRing: "#07173F",
  selected: "#EAFE07",
  twin: "#EAFE07",
  border: "rgba(46, 150, 245, 0.28)",
  /** Dark line around significant areas: stands out against every colour of the scale. */
  significantOutline: "#07173F",
  rim: "#2E96F5",
} as const;

export interface TrendPaletteStop {
  /** Position on the scale: -1 = strongest decrease, 0 = no change, +1 = strongest increase. */
  readonly t: number;
  readonly color: string;
}

/**
 * Diverging blue ↔ orange/red scale through a light neutral. Blue/orange stays
 * distinguishable with the common colour-vision deficiencies, and both ends are
 * bright enough to read on the dark globe (geo.check.mts measures both). The
 * ends are the brand colours the charts use for falling and rising
 * (Blue Yonder, Rocket Red).
 */
export const TREND_PALETTE: readonly TrendPaletteStop[] = [
  { t: -1, color: "#2E96F5" },
  { t: -0.66, color: "#6DB6F8" },
  { t: -0.33, color: "#B4D9FB" },
  { t: 0, color: "#F1EFE9" },
  { t: 0.33, color: "#FBC49A" },
  { t: 0.66, color: "#F5803C" },
  { t: 1, color: "#E43700" },
];

/** Opacity of cells whose trend passed the significance test. */
export const TREND_ALPHA_SIGNIFICANT = 1;
/** Opacity of cells whose trend did not pass it. */
export const TREND_ALPHA_NOT_SIGNIFICANT = 0.3;

export type Rgb = readonly [r: number, g: number, b: number];

const HEX_RADIX = 16;
const CHANNEL_MAX = 255;

function hexToRgb(hex: string): Rgb {
  const value = Number.parseInt(hex.slice(1), HEX_RADIX);
  return [(value >> 16) & CHANNEL_MAX, (value >> 8) & CHANNEL_MAX, value & CHANNEL_MAX];
}

function rgbToHex([r, g, b]: Rgb): string {
  const channel = (c: number) => Math.round(c).toString(HEX_RADIX).padStart(2, "0");
  return `#${channel(r)}${channel(g)}${channel(b)}`;
}

const PALETTE_RGB: readonly Rgb[] = TREND_PALETTE.map((stop) => hexToRgb(stop.color));

/** Position of a slope on the palette, in [-1, 1]. */
export function trendPosition(slope: number, maxAbs: number): number {
  if (!Number.isFinite(slope) || !Number.isFinite(maxAbs) || maxAbs <= 0) {
    return 0;
  }
  return Math.min(1, Math.max(-1, slope / maxAbs));
}

/** sRGB channels (0..255) of a slope on the scale -maxAbs … +maxAbs. */
export function trendRgb(slope: number, maxAbs: number): Rgb {
  const t = trendPosition(slope, maxAbs);
  const upper = TREND_PALETTE.findIndex((stop) => stop.t >= t);
  if (upper <= 0) {
    return PALETTE_RGB[0];
  }
  const from = TREND_PALETTE[upper - 1];
  const to = TREND_PALETTE[upper];
  const mix = (t - from.t) / (to.t - from.t);
  const a = PALETTE_RGB[upper - 1];
  const b = PALETTE_RGB[upper];
  return [a[0] + (b[0] - a[0]) * mix, a[1] + (b[1] - a[1]) * mix, a[2] + (b[2] - a[2]) * mix];
}

/** CSS hex colour of a slope on the scale -maxAbs … +maxAbs (symmetric around 0). */
export function trendColor(slope: number, maxAbs: number): string {
  return rgbToHex(trendRgb(slope, maxAbs));
}

/** Opacity used for a cell, given whether its trend is significant. */
export function trendAlpha(significant: boolean): number {
  return significant ? TREND_ALPHA_SIGNIFICANT : TREND_ALPHA_NOT_SIGNIFICANT;
}

/** CSS `linear-gradient(...)` of the whole palette, for a legend bar. */
export function trendGradientCss(direction = "to right"): string {
  const stops = TREND_PALETTE.map((stop) => `${stop.color} ${((stop.t + 1) / 2) * 100}%`);
  return `linear-gradient(${direction}, ${stops.join(", ")})`;
}

const SRGB_LINEAR_THRESHOLD = 0.04045;
const SRGB_LINEAR_DIVISOR = 12.92;
const SRGB_OFFSET = 0.055;
const SRGB_GAMMA = 2.4;

/** One sRGB channel (0..255) to linear light (0..1), as vertex colours need it. */
export function srgbChannelToLinear(channel: number): number {
  const c = channel / CHANNEL_MAX;
  return c <= SRGB_LINEAR_THRESHOLD
    ? c / SRGB_LINEAR_DIVISOR
    : ((c + SRGB_OFFSET) / (1 + SRGB_OFFSET)) ** SRGB_GAMMA;
}

const LUMA_WEIGHTS: Rgb = [0.2126, 0.7152, 0.0722];
const CONTRAST_OFFSET = 0.05;

/** WCAG relative luminance (0..1) of an sRGB colour. */
export function relativeLuminance(rgb: Rgb): number {
  return rgb.reduce((sum, channel, i) => sum + LUMA_WEIGHTS[i] * srgbChannelToLinear(channel), 0);
}

/** WCAG contrast ratio (1..21) between two sRGB colours. */
export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  return (Math.max(la, lb) + CONTRAST_OFFSET) / (Math.min(la, lb) + CONTRAST_OFFSET);
}

export function parseHex(hex: string): Rgb {
  return hexToRgb(hex);
}
