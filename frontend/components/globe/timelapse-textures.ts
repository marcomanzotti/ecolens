/**
 * Data textures of the time-lapse (one texel per grid cell, rows south to north, so they map
 * straight onto the sphere's UVs: see geo.ts).
 *
 * Anomaly frame, RGBA8 with linear filtering: G = 1 where the cell has a value, R = encoded value
 * times G, B = 1 where the cell is measured in at least one year of the dataset. The shader
 * divides the filtered R by the filtered G, so bilinear interpolation only mixes cells that have
 * data (a missing cell is never filled): a measured cell without a value that year is hatched; a
 * cell the dataset never measures (sea and ice for vegetation) stays transparent.
 */
import {
  ClampToEdgeWrapping,
  DataTexture,
  LinearFilter,
  NearestFilter,
  RepeatWrapping,
  RGBAFormat,
  SRGBColorSpace,
  UnsignedByteType,
  type Texture,
} from "three";

import type { TimelapseData } from "./timelapse-data";
const BYTE_MAX = 255;
const RGBA = 4;

function configure<T extends Texture>(texture: T, filter: typeof LinearFilter | typeof NearestFilter): T {
  texture.magFilter = filter;
  texture.minFilter = filter;
  texture.wrapS = RepeatWrapping; // longitude wraps around the date line
  texture.wrapT = ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

/** Cells with a value in at least one year (computed once per dataset). */
const measuredCache = new WeakMap<TimelapseData, Uint8Array>();

export function measuredCells(data: TimelapseData): Uint8Array {
  const hit = measuredCache.get(data);
  if (hit) return hit;
  const { n_lat, n_lon } = data.meta.grid;
  const { missing } = data.meta.files["anomaly.bin"];
  const cells = n_lat * n_lon;
  const measured = new Uint8Array(cells);
  for (let i = 0; i < data.anomaly.length; i += 1) {
    if (data.anomaly[i] !== missing) measured[i % cells] = 1;
  }
  measuredCache.set(data, measured);
  return measured;
}

export function anomalyFrameTexture(data: TimelapseData, frame: number): DataTexture {
  const { n_lat, n_lon } = data.meta.grid;
  const { scale, missing } = data.meta.files["anomaly.bin"];
  const range = data.dataset.scale.encodeRange;
  const measured = measuredCells(data);
  const cells = n_lat * n_lon;
  const bytes = new Uint8Array(cells * RGBA);
  const offset = frame * cells;
  for (let i = 0; i < cells; i += 1) {
    bytes[i * RGBA + 2] = measured[i] * BYTE_MAX;
    bytes[i * RGBA + 3] = BYTE_MAX;
    const raw = data.anomaly[offset + i];
    if (raw === missing) continue;
    const value = Math.min(range, Math.max(-range, raw * scale));
    bytes[i * RGBA] = Math.round(((value + range) / (2 * range)) * BYTE_MAX);
    bytes[i * RGBA + 1] = BYTE_MAX;
  }
  return configure(new DataTexture(bytes, n_lon, n_lat, RGBAFormat, UnsignedByteType), LinearFilter);
}

/** Front mask (see timelapse-front.ts): nearest filtering, so the glow is exactly one cell. */
export function frontMaskTexture(mask: Uint8Array, nLon: number, nLat: number): DataTexture {
  return configure(new DataTexture(mask, nLon, nLat, RGBAFormat, UnsignedByteType), NearestFilter);
}

/** The colour bands as an n x 1 texture: the shader reads band i at u = (i + 0.5) / n. */
export function paletteTexture(bands: readonly string[]): DataTexture {
  const bytes = new Uint8Array(bands.length * RGBA);
  bands.forEach((hex, i) => {
    const value = Number.parseInt(hex.slice(1), 16);
    bytes.set([(value >> 16) & BYTE_MAX, (value >> 8) & BYTE_MAX, value & BYTE_MAX, BYTE_MAX], i * RGBA);
  });
  const texture = new DataTexture(bytes, bands.length, 1, RGBAFormat, UnsignedByteType);
  texture.colorSpace = SRGBColorSpace;
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}
