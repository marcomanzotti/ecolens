/**
 * Turns the cells of a trend map into flat arrays for one merged mesh.
 * Pure module (no three.js, no DOM): checked in node by geo.check.mts.
 */
import { srgbChannelToLinear, trendAlpha, trendRgb } from "./colors";
import { clamp, latLonToVec3, type Vec3 } from "./geo";

export interface GridCell {
  lat: number;
  lon: number;
  slope_per_decade: number | null;
  significant: boolean;
}

export interface GridStep {
  lat_step: number;
  lon_step: number;
}

export interface TrendGeometryOptions {
  /** Radius of the painted quads. */
  radius: number;
  /** Radius of the outline around the significant cells. */
  outlineRadius: number;
  /** Cells wider than this many degrees are subdivided to follow the sphere. */
  maxQuadDeg: number;
  /** The colour scale runs from -maxAbs to +maxAbs. */
  maxAbs: number;
}

export interface TrendGeometry {
  /** xyz per vertex. */
  positions: Float32Array;
  /** Linear rgb + alpha per vertex. */
  colors: Float32Array;
  indices: Uint32Array;
  /** For every triangle, the index (in the input array) of the cell it belongs to. */
  faceCell: Int32Array;
  /** xyz pairs: line segments around the areas of significant cells. */
  outline: Float32Array;
  paintedCells: number;
}

const MAX_LAT_DEG = 90;
const VERTEX_SIZE = 3;
const COLOR_SIZE = 4;
const TRIANGLE_SIZE = 3;

interface CellBounds {
  south: number;
  north: number;
  west: number;
  east: number;
}

export function cellBounds(cell: { lat: number; lon: number }, step: GridStep): CellBounds {
  return {
    south: clamp(cell.lat - step.lat_step / 2, -MAX_LAT_DEG, MAX_LAT_DEG),
    north: clamp(cell.lat + step.lat_step / 2, -MAX_LAT_DEG, MAX_LAT_DEG),
    west: cell.lon - step.lon_step / 2,
    east: cell.lon + step.lon_step / 2,
  };
}

/** Number of pieces each side of a cell is cut into. */
export function cellSubdivisions(step: GridStep, maxQuadDeg: number): number {
  const largest = Math.max(step.lat_step, step.lon_step);
  return Math.max(1, Math.ceil(largest / maxQuadDeg));
}

/** A cell is painted when it has a slope to show. */
export function isPainted(cell: GridCell): boolean {
  return cell.slope_per_decade !== null && Number.isFinite(cell.slope_per_decade);
}

/** The largest |slope| among the cells: fallback when the summary gives none. */
export function maxAbsSlope(cells: readonly GridCell[]): number {
  return cells.reduce((max, cell) => (isPainted(cell) ? Math.max(max, Math.abs(cell.slope_per_decade ?? 0)) : max), 0);
}

/** The closed outline of a cell (first point repeated at the end), anticlockwise from outside. */
export function cellOutline(
  cell: { lat: number; lon: number },
  step: GridStep,
  radius: number,
  maxQuadDeg: number,
): Vec3[] {
  const { south, north, west, east } = cellBounds(cell, step);
  const n = cellSubdivisions(step, maxQuadDeg);
  const points: Vec3[] = [];
  for (let i = 0; i < n; i += 1) points.push(latLonToVec3(south, west + ((east - west) * i) / n, radius));
  for (let i = 0; i < n; i += 1) points.push(latLonToVec3(south + ((north - south) * i) / n, east, radius));
  for (let i = 0; i < n; i += 1) points.push(latLonToVec3(north, east - ((east - west) * i) / n, radius));
  for (let i = 0; i < n; i += 1) points.push(latLonToVec3(north - ((north - south) * i) / n, west, radius));
  points.push(points[0]);
  return points;
}

function gridKey(row: number, col: number): string {
  return `${row}:${col}`;
}

/** Row/column of every cell on the regular grid, to find neighbours. */
function gridIndexer(cells: readonly GridCell[], step: GridStep) {
  const lat0 = cells.reduce((min, cell) => Math.min(min, cell.lat), Infinity);
  const lon0 = cells.reduce((min, cell) => Math.min(min, cell.lon), Infinity);
  return (cell: { lat: number; lon: number }) => ({
    row: Math.round((cell.lat - lat0) / step.lat_step),
    col: Math.round((cell.lon - lon0) / step.lon_step),
  });
}

function pushSegments(target: number[], from: readonly [number, number], to: readonly [number, number], n: number, radius: number): void {
  for (let i = 0; i < n; i += 1) {
    const a = latLonToVec3(from[0] + ((to[0] - from[0]) * i) / n, from[1] + ((to[1] - from[1]) * i) / n, radius);
    const b = latLonToVec3(from[0] + ((to[0] - from[0]) * (i + 1)) / n, from[1] + ((to[1] - from[1]) * (i + 1)) / n, radius);
    target.push(a[0], a[1], a[2], b[0], b[1], b[2]);
  }
}

/** Line segments along the edges where a significant cell meets a cell that is not. */
function buildOutline(cells: readonly GridCell[], step: GridStep, n: number, radius: number): Float32Array {
  const indexOf = gridIndexer(cells, step);
  const significant = new Set<string>();
  for (const cell of cells) {
    if (isPainted(cell) && cell.significant) {
      const { row, col } = indexOf(cell);
      significant.add(gridKey(row, col));
    }
  }
  const segments: number[] = [];
  for (const cell of cells) {
    if (!isPainted(cell) || !cell.significant) continue;
    const { row, col } = indexOf(cell);
    const { south, north, west, east } = cellBounds(cell, step);
    if (!significant.has(gridKey(row - 1, col))) pushSegments(segments, [south, west], [south, east], n, radius);
    if (!significant.has(gridKey(row + 1, col))) pushSegments(segments, [north, west], [north, east], n, radius);
    if (!significant.has(gridKey(row, col - 1))) pushSegments(segments, [south, west], [north, west], n, radius);
    if (!significant.has(gridKey(row, col + 1))) pushSegments(segments, [south, east], [north, east], n, radius);
  }
  return new Float32Array(segments);
}

/** One merged, vertex-coloured mesh for all the cells that have a slope. */
export function buildTrendGeometry(
  cells: readonly GridCell[],
  step: GridStep,
  options: TrendGeometryOptions,
): TrendGeometry {
  const n = cellSubdivisions(step, options.maxQuadDeg);
  const painted = cells.reduce((count, cell) => count + (isPainted(cell) ? 1 : 0), 0);
  const verticesPerCell = (n + 1) * (n + 1);
  const trianglesPerCell = 2 * n * n;
  const positions = new Float32Array(painted * verticesPerCell * VERTEX_SIZE);
  const colors = new Float32Array(painted * verticesPerCell * COLOR_SIZE);
  const indices = new Uint32Array(painted * trianglesPerCell * TRIANGLE_SIZE);
  const faceCell = new Int32Array(painted * trianglesPerCell);

  let vertex = 0;
  let triangle = 0;
  cells.forEach((cell, cellIndex) => {
    if (!isPainted(cell)) return;
    const { south, north, west, east } = cellBounds(cell, step);
    const rgb = trendRgb(cell.slope_per_decade ?? 0, options.maxAbs);
    const alpha = trendAlpha(cell.significant);
    const base = vertex;
    for (let i = 0; i <= n; i += 1) {
      for (let j = 0; j <= n; j += 1) {
        const point = latLonToVec3(south + ((north - south) * i) / n, west + ((east - west) * j) / n, options.radius);
        positions.set(point, vertex * VERTEX_SIZE);
        colors.set(
          [srgbChannelToLinear(rgb[0]), srgbChannelToLinear(rgb[1]), srgbChannelToLinear(rgb[2]), alpha],
          vertex * COLOR_SIZE,
        );
        vertex += 1;
      }
    }
    for (let i = 0; i < n; i += 1) {
      for (let j = 0; j < n; j += 1) {
        const sw = base + i * (n + 1) + j;
        const se = sw + 1;
        const nw = sw + (n + 1);
        const ne = nw + 1;
        // Anticlockwise seen from outside (north up, east to the right).
        indices.set([sw, se, ne, sw, ne, nw], triangle * TRIANGLE_SIZE);
        faceCell[triangle] = cellIndex;
        faceCell[triangle + 1] = cellIndex;
        triangle += 2;
      }
    }
  });

  return {
    positions,
    colors,
    indices,
    faceCell,
    outline: buildOutline(cells, step, n, options.outlineRadius),
    paintedCells: painted,
  };
}
