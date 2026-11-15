/**
 * Pure geographic helpers for the globe. No three.js, no DOM: safe to test in node.
 *
 * Convention (matches the UVs of three's SphereGeometry with an equirectangular
 * texture whose left edge is 180°W and whose top edge is 90°N):
 *   +Y = north pole, +X = (0°N, 0°E), -Z = (0°N, 90°E), +Z = (0°N, 90°W).
 * Seen from outside with north up, east is to the right: the map is not mirrored.
 */

export type Vec3 = readonly [x: number, y: number, z: number];

export interface LatLon {
  lat: number;
  lon: number;
}

export interface GeoBox {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
}

const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;
const COORD_DECIMALS = 2;
const FULL_TURN_DEG = 360;
const HALF_TURN_DEG = 180;
const MAX_LAT_DEG = 90;

export function degToRad(degrees: number): number {
  return degrees * DEG_TO_RAD;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Wraps a longitude into [-180, 180). */
export function normalizeLon(lon: number): number {
  const wrapped = ((((lon + HALF_TURN_DEG) % FULL_TURN_DEG) + FULL_TURN_DEG) % FULL_TURN_DEG) - HALF_TURN_DEG;
  return Object.is(wrapped, -0) ? 0 : wrapped;
}

/** Latitude/longitude in degrees to a point on a sphere of the given radius. */
export function latLonToVec3(lat: number, lon: number, radius = 1): Vec3 {
  const phi = lat * DEG_TO_RAD;
  const lambda = lon * DEG_TO_RAD;
  const cosPhi = Math.cos(phi);
  return [
    radius * cosPhi * Math.cos(lambda),
    radius * Math.sin(phi),
    -radius * cosPhi * Math.sin(lambda),
  ];
}

/** Any non-zero point in space to the latitude/longitude (degrees) below it. */
export function vec3ToLatLon(x: number, y: number, z: number): LatLon {
  const length = Math.hypot(x, y, z);
  if (length === 0) {
    return { lat: 0, lon: 0 };
  }
  const lat = Math.asin(clamp(y / length, -1, 1)) * RAD_TO_DEG;
  const lon = Math.atan2(-z, x) * RAD_TO_DEG;
  return { lat, lon: normalizeLon(lon) };
}

export function roundCoord(value: number): number {
  const factor = 10 ** COORD_DECIMALS;
  const rounded = Math.round(value * factor) / factor;
  return Object.is(rounded, -0) ? 0 : rounded;
}

/** The point the user picked, rounded the way the API expects it. */
export function vec3ToRoundedLatLon(x: number, y: number, z: number): LatLon {
  const { lat, lon } = vec3ToLatLon(x, y, z);
  return {
    lat: clamp(roundCoord(lat), -MAX_LAT_DEG, MAX_LAT_DEG),
    // Round last: wrapping adds and subtracts 180, which brings back float noise.
    lon: roundCoord(normalizeLon(roundCoord(lon))),
  };
}

/** Texture coordinates (u to the east, v to the north, both 0..1) of a lat/lon. */
export function latLonToUv(lat: number, lon: number): readonly [u: number, v: number] {
  return [(normalizeLon(lon) + HALF_TURN_DEG) / FULL_TURN_DEG, (lat + MAX_LAT_DEG) / HALF_TURN_DEG];
}

export function boxCenter(box: GeoBox): LatLon {
  return {
    lat: (box.lat_min + box.lat_max) / 2,
    lon: normalizeLon((box.lon_min + box.lon_max) / 2),
  };
}

/**
 * Half of the angle (radians) the box spans as seen from the Earth's centre,
 * taking the larger of its north-south and east-west extents.
 */
export function boxAngularRadius(box: GeoBox): number {
  const center = boxCenter(box);
  const latSpan = Math.abs(box.lat_max - box.lat_min);
  const lonSpan = Math.abs(box.lon_max - box.lon_min) * Math.cos(center.lat * DEG_TO_RAD);
  return (Math.max(latSpan, lonSpan) / 2) * DEG_TO_RAD;
}

/** Points along the great circle from a to b, lifted in the middle by `lift` radii. */
export function greatCircleArc(
  from: LatLon,
  to: LatLon,
  segments: number,
  baseRadius: number,
  lift: number,
): Vec3[] {
  const a = latLonToVec3(from.lat, from.lon);
  const b = latLonToVec3(to.lat, to.lon);
  const dot = clamp(a[0] * b[0] + a[1] * b[1] + a[2] * b[2], -1, 1);
  const omega = Math.acos(dot);
  const sinOmega = Math.sin(omega);
  const points: Vec3[] = [];
  for (let i = 0; i <= segments; i += 1) {
    const t = i / segments;
    const wa = sinOmega < 1e-6 ? 1 - t : Math.sin((1 - t) * omega) / sinOmega;
    const wb = sinOmega < 1e-6 ? t : Math.sin(t * omega) / sinOmega;
    const x = wa * a[0] + wb * b[0];
    const y = wa * a[1] + wb * b[1];
    const z = wa * a[2] + wb * b[2];
    const length = Math.hypot(x, y, z) || 1;
    const radius = baseRadius + lift * Math.sin(Math.PI * t);
    points.push([(x / length) * radius, (y / length) * radius, (z / length) * radius]);
  }
  return points;
}

/** Mutable triple used as an out-parameter in the render loop (no per-frame garbage). */
export type MutableVec3 = [x: number, y: number, z: number];

/** Same as latLonToVec3, written into `out` so the render loop allocates nothing. */
export function writeLatLonToVec3(out: MutableVec3, lat: number, lon: number, radius = 1): MutableVec3 {
  const phi = lat * DEG_TO_RAD;
  const lambda = lon * DEG_TO_RAD;
  const cosPhi = Math.cos(phi);
  out[0] = radius * cosPhi * Math.cos(lambda);
  out[1] = radius * Math.sin(phi);
  out[2] = -radius * cosPhi * Math.sin(lambda);
  return out;
}

/** Signed shortest way (degrees, in [-180, 180)) from one longitude to another. */
export function shortestLonDelta(fromLon: number, toLon: number): number {
  return normalizeLon(toLon - fromLon);
}

/**
 * A view between two views, moving latitude and longitude linearly and taking
 * the short way round in longitude. Unlike a great circle it never crosses a
 * pole, so a camera with a fixed "north is up" never flips. Written into `out`.
 */
export function writeInterpolatedView(out: LatLon, from: LatLon, to: LatLon, t: number): LatLon {
  out.lat = from.lat + (to.lat - from.lat) * t;
  out.lon = normalizeLon(from.lon + shortestLonDelta(from.lon, to.lon) * t);
  return out;
}

export function easeInOutCubic(t: number): number {
  const x = clamp(t, 0, 1);
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;
}

/** Tangent of half of the narrower of the vertical and horizontal fields of view. */
function tanHalfNarrowFov(verticalFovDeg: number, aspect: number): number {
  const tanHalfVertical = Math.tan((verticalFovDeg * DEG_TO_RAD) / 2);
  return tanHalfVertical * Math.min(1, aspect);
}

/**
 * Distance from the centre of a unit sphere at which the whole sphere fits the
 * view in both directions. `margin` 1 touches the edges, larger leaves room.
 */
export function fitDistance(verticalFovDeg: number, aspect: number, margin: number): number {
  const halfAngle = Math.atan(tanHalfNarrowFov(verticalFovDeg, aspect));
  return margin / Math.sin(halfAngle);
}

/**
 * Distance from the centre of a unit sphere at which a cap of the given angular
 * radius fills the share `fill` (0..1) of the narrower side of the view.
 */
export function capViewDistance(
  angularRadius: number,
  verticalFovDeg: number,
  aspect: number,
  fill: number,
): number {
  const tanHalf = tanHalfNarrowFov(verticalFovDeg, aspect);
  return Math.cos(angularRadius) + Math.sin(angularRadius) / (fill * tanHalf);
}

/** Angle (radians) between two places as seen from the Earth's centre. */
export function angularDistance(a: LatLon, b: LatLon): number {
  const va = latLonToVec3(a.lat, a.lon);
  const vb = latLonToVec3(b.lat, b.lon);
  return Math.acos(clamp(va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2], -1, 1));
}

/**
 * Whether a point on the unit sphere can be seen from a camera at `camera`
 * (it is on the near side of the horizon). Takes plain numbers: no allocation.
 */
export function isOnNearSide(
  pointX: number,
  pointY: number,
  pointZ: number,
  cameraX: number,
  cameraY: number,
  cameraZ: number,
): boolean {
  return pointX * cameraX + pointY * cameraY + pointZ * cameraZ > 1;
}
