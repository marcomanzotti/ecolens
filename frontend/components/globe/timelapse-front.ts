/**
 * Geometry of the emergence front, from one year of emerged.bin. Pure module: no three.js.
 *
 * - Border: marching squares on the grid of cell centres, threshold 0.5 of the 0/1 field
 *   "significant in this direction". Longitude wraps around; nothing is drawn past the last row.
 * - Glow: the significant cells that touch a non-significant one (4-neighbours): a band exactly
 *   one cell wide just inside the border.
 * - New cells: significant this year and not the year before (each emits one ring).
 */
import type { TimelapseMeta } from "./timelapse-data";

export type Direction = 1 | -1;

export interface GridShape {
  nLat: number;
  nLon: number;
  latFirst: number;
  lonFirst: number;
  step: number;
}

export function gridShape(meta: TimelapseMeta): GridShape {
  const { n_lat, n_lon, lat_first, lon_first, step_deg } = meta.grid;
  return { nLat: n_lat, nLon: n_lon, latFirst: lat_first, lonFirst: lon_first, step: step_deg };
}

/** The year's frame of emerged.bin (no copy). */
export function emergedFrame(emerged: Int8Array, meta: TimelapseMeta, frame: number): Int8Array {
  const cells = meta.grid.n_lat * meta.grid.n_lon;
  return emerged.subarray(frame * cells, (frame + 1) * cells);
}

// Edges of a marching square: 0 bottom, 1 right, 2 top, 3 left (bottom = lower row).
// For each case (bit 0 = lower-left, 1 = lower-right, 2 = upper-right, 3 = upper-left),
// the pairs of edges joined by a segment. Saddles (5, 10) join as two separate corners.
const CASES: readonly (readonly (readonly [number, number])[])[] = [
  [],
  [[3, 0]],
  [[0, 1]],
  [[3, 1]],
  [[1, 2]],
  [[3, 0], [1, 2]],
  [[0, 2]],
  [[3, 2]],
  [[2, 3]],
  [[0, 2]],
  [[0, 1], [2, 3]],
  [[1, 2]],
  [[1, 3]],
  [[0, 1]],
  [[3, 0]],
  [],
];

/** (row, col) offsets of each edge's midpoint inside the square whose lower-left is (r, c). */
const EDGE_MID: readonly (readonly [number, number])[] = [
  [0, 0.5],
  [0.5, 1],
  [1, 0.5],
  [0.5, 0],
];

/** Border segments as [lat, lon, lat, lon, ...] (degrees), two points per segment. */
export function frontSegments(frame: Int8Array, grid: GridShape, direction: Direction): number[] {
  const { nLat, nLon, latFirst, lonFirst, step } = grid;
  const on = (r: number, c: number) => (frame[r * nLon + ((c + nLon) % nLon)] === direction ? 1 : 0);
  const out: number[] = [];
  for (let r = 0; r < nLat - 1; r += 1) {
    for (let c = 0; c < nLon; c += 1) {
      const code = on(r, c) | (on(r, c + 1) << 1) | (on(r + 1, c + 1) << 2) | (on(r + 1, c) << 3);
      for (const [a, b] of CASES[code]) {
        for (const edge of [a, b]) {
          const [dr, dc] = EDGE_MID[edge];
          out.push(latFirst + (r + dr) * step, lonFirst + (c + dc) * step);
        }
      }
    }
  }
  return out;
}

/** RGBA8 texture data (nLon x nLat, rows south to north) for the field shader:
 *  R = warming glow cell, G = cooling glow cell, B = significant warming, A = significant cooling. */
export function frontMask(frame: Int8Array, grid: GridShape): Uint8Array {
  const { nLat, nLon } = grid;
  const out = new Uint8Array(nLat * nLon * 4);
  for (let r = 0; r < nLat; r += 1) {
    for (let c = 0; c < nLon; c += 1) {
      const value = frame[r * nLon + c];
      if (value === 0) continue;
      const same = (rr: number, cc: number) =>
        rr < 0 || rr >= nLat ? true : frame[rr * nLon + ((cc + nLon) % nLon)] === value;
      const edge = !(same(r - 1, c) && same(r + 1, c) && same(r, c - 1) && same(r, c + 1));
      const o = (r * nLon + c) * 4;
      out[o + (value > 0 ? 0 : 1)] = edge ? 255 : 0;
      out[o + (value > 0 ? 2 : 3)] = 255;
    }
  }
  return out;
}

/** Cells (index, direction) significant in `frame` and not in `previous`. */
export function newlyEmerged(frame: Int8Array, previous: Int8Array): { cell: number; direction: number }[] {
  const out: { cell: number; direction: number }[] = [];
  for (let i = 0; i < frame.length; i += 1) {
    if (frame[i] !== 0 && previous[i] !== frame[i]) out.push({ cell: i, direction: frame[i] });
  }
  return out;
}
