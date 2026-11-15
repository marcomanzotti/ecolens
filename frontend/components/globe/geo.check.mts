/**
 * Assertions for geo.ts and colors.ts. Run from frontend/ with:
 *   node components/globe/geo.check.mts
 * (Node 22.18+ strips the TypeScript types by itself.)
 *
 * Also proves that the lat/lon convention matches the UVs of three's
 * SphereGeometry (so an equirectangular texture is neither mirrored nor shifted)
 * and that the suggested places fall on land in the Natural Earth data.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as nodeModule from "node:module";

// The modules import each other without a file extension (as the bundler wants):
// teach node to try ".ts" for those.
// (module.registerHooks exists since Node 22.15; the project's @types/node is older.)
type NextResolve = (specifier: string, context: unknown) => unknown;
const { registerHooks } = nodeModule as unknown as {
  registerHooks: (hooks: { resolve: (specifier: string, context: unknown, next: NextResolve) => unknown }) => void;
};
const { createRequire } = nodeModule;
registerHooks({
  resolve(specifier, context, nextResolve) {
    const isBareRelative = specifier.startsWith(".") && !/\.[cm]?[jt]sx?$|\.json$/.test(specifier);
    return nextResolve(isBareRelative ? `${specifier}.ts` : specifier, context);
  },
});

const geoUrl = new URL("./geo.ts", import.meta.url).href;
const colorsUrl = new URL("./colors.ts", import.meta.url).href;
const geo = (await import(geoUrl)) as typeof import("./geo");
const colors = (await import(colorsUrl)) as typeof import("./colors");
const trendUrl = new URL("./trend-geometry.ts", import.meta.url).href;
const trend = (await import(trendUrl)) as typeof import("./trend-geometry");
const summaryUrl = new URL("./trend-summary.ts", import.meta.url).href;
const summary = (await import(summaryUrl)) as typeof import("./trend-summary");

const EPSILON = 1e-9;
const require = createRequire(import.meta.url);

function assertVec(actual: readonly number[], expected: readonly number[], label: string): void {
  actual.forEach((value, i) => {
    assert.ok(Math.abs(value - expected[i]) < EPSILON, `${label}: axis ${i} is ${value}, expected ${expected[i]}`);
  });
}

// Known points.
assertVec(geo.latLonToVec3(0, 0), [1, 0, 0], "(0,0)");
assertVec(geo.latLonToVec3(90, 0), [0, 1, 0], "(90,0)");
assertVec(geo.latLonToVec3(-90, 0), [0, -1, 0], "(-90,0)");
assertVec(geo.latLonToVec3(0, 90), [0, 0, -1], "(0,90)");
assertVec(geo.latLonToVec3(0, -90), [0, 0, 1], "(0,-90)");
assertVec(geo.latLonToVec3(45, 180), [-Math.SQRT1_2, Math.SQRT1_2, 0], "(45,180)");
assertVec(geo.latLonToVec3(0, 0, 2), [2, 0, 0], "radius");

// East is to the right of an observer above (0,0) with north up: right = forward × up = -Z.
assert.ok(geo.latLonToVec3(0, 10)[2] < 0, "east must be towards -Z");

// Round trips.
const SAMPLES: readonly (readonly [number, number])[] = [
  [0, 0],
  [0, 90],
  [0, -90],
  [45, 180],
  [-33.87, 151.21],
  [13.51, 2.11],
  [69.65, 18.96],
  [-3.1, -60],
  [28.61, 77.21],
  [-77.85, 166.67],
  [10, -179.5],
];
for (const [lat, lon] of SAMPLES) {
  const [x, y, z] = geo.latLonToVec3(lat, lon, 1.7);
  const back = geo.vec3ToLatLon(x, y, z);
  assert.ok(Math.abs(back.lat - lat) < 1e-9, `round trip lat ${lat},${lon}`);
  assert.ok(Math.abs(geo.normalizeLon(back.lon - lon)) < 1e-9, `round trip lon ${lat},${lon}`);
}
assert.equal(geo.vec3ToLatLon(0, 3, 0).lat, 90);
assert.deepEqual(geo.vec3ToLatLon(0, 0, 0), { lat: 0, lon: 0 });

// Rounding to 2 decimals.
const sydney = geo.latLonToVec3(-33.8688, 151.2093);
assert.deepEqual(geo.vec3ToRoundedLatLon(...sydney), { lat: -33.87, lon: 151.21 });
assert.equal(geo.normalizeLon(180), -180);
assert.equal(geo.normalizeLon(190), -170);
assert.equal(geo.normalizeLon(-190), 170);
assert.equal(geo.roundCoord(-0.001), 0);

// UVs: left edge 180°W, centre Greenwich, top north.
assert.deepEqual(geo.latLonToUv(0, 0), [0.5, 0.5]);
assert.deepEqual(geo.latLonToUv(90, -180), [0, 1]);
assert.deepEqual(geo.latLonToUv(-90, 90), [0.75, 0]);

// The same convention as three's SphereGeometry UVs, vertex by vertex.
const three = require("three") as typeof import("three");
const sphere = new three.SphereGeometry(1, 48, 24);
const positions = sphere.getAttribute("position");
const uvs = sphere.getAttribute("uv");
let compared = 0;
for (let i = 0; i < positions.count; i += 1) {
  const x = positions.getX(i);
  const y = positions.getY(i);
  const z = positions.getZ(i);
  const u = uvs.getX(i);
  const v = uvs.getY(i);
  const isPole = Math.abs(y) > 0.999;
  const isSeam = u < 0.001 || u > 0.999;
  if (isPole || isSeam) continue;
  const { lat, lon } = geo.vec3ToLatLon(x, y, z);
  const [eu, ev] = geo.latLonToUv(lat, lon);
  assert.ok(Math.abs(eu - u) < 1e-5, `u mismatch at vertex ${i}: ${eu} vs ${u}`);
  assert.ok(Math.abs(ev - v) < 1e-5, `v mismatch at vertex ${i}: ${ev} vs ${v}`);
  compared += 1;
}
assert.ok(compared > 1000, "sphere vertices compared");

// Places are on land, open ocean is not (Natural Earth via world-atlas).
const d3 = require("d3-geo") as typeof import("d3-geo");
const topojson = require("topojson-client") as typeof import("topojson-client");
const atlasPath = require.resolve("world-atlas/land-50m.json");
const atlas = JSON.parse(readFileSync(atlasPath, "utf8")) as import("topojson-specification").Topology;
const land = topojson.feature(atlas, atlas.objects.land);
const ON_LAND: Record<string, readonly [lon: number, lat: number]> = {
  Niamey: [2.11, 13.51],
  "Tromsø (mainland nearby)": [19.5, 69.3],
  Manaus: [-60, -3.1],
  Delhi: [77.21, 28.61],
};
for (const [name, point] of Object.entries(ON_LAND)) {
  assert.ok(d3.geoContains(land, [point[0], point[1]]), `${name} should be on land`);
}
assert.ok(!d3.geoContains(land, [-30, 0]), "mid-Atlantic should be ocean");
assert.ok(!d3.geoContains(land, [-150, 20]), "mid-Pacific should be ocean");

// Box helpers and arcs.
const box = { lat_min: 10, lat_max: 20, lon_min: -5, lon_max: 5 };
assert.deepEqual(geo.boxCenter(box), { lat: 15, lon: 0 });
assert.ok(Math.abs(geo.boxAngularRadius(box) - geo.degToRad(5)) < 1e-9);
const arc = geo.greatCircleArc({ lat: 0, lon: 0 }, { lat: 0, lon: 90 }, 10, 1, 0.2);
assert.equal(arc.length, 11);
assertVec(arc[0], [1, 0, 0], "arc start");
assertVec(arc[10], [0, 0, -1], "arc end");
assert.ok(Math.abs(Math.hypot(...arc[5]) - 1.2) < 1e-9, "arc apex lifted");

// Colours: symmetric scale, clamped, neutral at zero.
assert.equal(colors.trendColor(0, 0.31), "#f1efe9");
assert.equal(colors.trendColor(0.31, 0.31), "#e43700");
assert.equal(colors.trendColor(-0.31, 0.31), "#2e96f5");
assert.equal(colors.trendColor(5, 0.31), "#e43700");
assert.equal(colors.trendColor(-5, 0.31), "#2e96f5");
assert.equal(colors.trendColor(0.2, 0), "#f1efe9");
assert.ok(colors.trendAlpha(true) > colors.trendAlpha(false) * 2);
assert.ok(colors.trendGradientCss().startsWith("linear-gradient(to right, #2E96F5 0%"));

// Camera helpers.
const view = { lat: 0, lon: 0 };
geo.writeInterpolatedView(view, { lat: 10, lon: 170 }, { lat: 30, lon: -170 }, 0.5);
assert.ok(Math.abs(view.lat - 20) < EPSILON && Math.abs(view.lon + 180) < EPSILON, "short way across the antimeridian");
geo.writeInterpolatedView(view, { lat: -20, lon: -60 }, { lat: 40, lon: 20 }, 1);
assert.deepEqual(view, { lat: 40, lon: 20 });
assert.equal(geo.shortestLonDelta(170, -170), 20);
assert.equal(geo.shortestLonDelta(-170, 170), -20);
assert.equal(geo.easeInOutCubic(0), 0);
assert.equal(geo.easeInOutCubic(0.5), 0.5);
assert.equal(geo.easeInOutCubic(1), 1);
assert.equal(geo.easeInOutCubic(7), 1);
const out: [number, number, number] = [0, 0, 0];
assertVec(geo.writeLatLonToVec3(out, -33.87, 151.21, 1.7), geo.latLonToVec3(-33.87, 151.21, 1.7), "write = pure");

// The whole unit sphere fits: its silhouette half-angle is asin(1/d).
const FOV = 40;
const fitWide = geo.fitDistance(FOV, 16 / 9, 1);
assert.ok(Math.abs(Math.asin(1 / fitWide) - geo.degToRad(FOV / 2)) < EPSILON, "fit, landscape");
const fitTall = geo.fitDistance(FOV, 0.5, 1);
assert.ok(fitTall > fitWide, "a narrow view needs more distance");
assert.ok(Math.abs(Math.tan(Math.asin(1 / fitTall)) - Math.tan(geo.degToRad(FOV / 2)) * 0.5) < EPSILON, "fit, portrait");
// A 5° cap seen from capViewDistance spans `fill` of the half view.
const capRadius = geo.degToRad(5);
const capDistance = geo.capViewDistance(capRadius, FOV, 2, 0.6);
const capTan = Math.sin(capRadius) / (capDistance - Math.cos(capRadius));
assert.ok(Math.abs(capTan - 0.6 * Math.tan(geo.degToRad(FOV / 2))) < EPSILON, "cap fills the asked share");
assert.ok(Math.abs(geo.angularDistance({ lat: 0, lon: 0 }, { lat: 0, lon: 90 }) - Math.PI / 2) < EPSILON);
assert.ok(geo.isOnNearSide(1, 0, 0, 3, 0, 0), "facing the camera");
assert.ok(!geo.isOnNearSide(-1, 0, 0, 3, 0, 0), "behind the globe");
assert.ok(!geo.isOnNearSide(0, 1, 0, 3, 0, 0), "on the limb, just hidden");

// Click → lat/lon: a ray from an off-centre camera towards a place first meets the sphere at that place.
function raySphere(origin: readonly number[], target: readonly number[]): [number, number, number] {
  const d = target.map((v, i) => v - origin[i]);
  const dLen = Math.hypot(...d);
  const dir = d.map((v) => v / dLen);
  const b = origin.reduce((sum, v, i) => sum + v * dir[i], 0);
  const c = origin.reduce((sum, v) => sum + v * v, 0) - 1;
  const t = -b - Math.sqrt(b * b - c);
  return [origin[0] + dir[0] * t, origin[1] + dir[1] * t, origin[2] + dir[2] * t];
}
for (const [lat, lon] of SAMPLES) {
  const camera = geo.latLonToVec3(lat + 3, lon - 4, 2.6);
  const aim = geo.latLonToVec3(lat, lon, 1);
  const hit = raySphere(camera, aim);
  const picked = geo.vec3ToRoundedLatLon(...hit);
  assert.ok(Math.abs(picked.lat - geo.roundCoord(lat)) <= 0.01, `click lat ${lat},${lon}: ${picked.lat}`);
  assert.ok(Math.abs(geo.normalizeLon(picked.lon - lon)) <= 0.011, `click lon ${lat},${lon}: ${picked.lon}`);
}

// Trend cells: bounds, winding, colours, face → cell lookup, outline.
const STEP = { lat_step: 0.5, lon_step: 0.625 };
assert.deepEqual(trend.cellBounds({ lat: 10, lon: -5 }, STEP), { south: 9.75, north: 10.25, west: -5.3125, east: -4.6875 });
assert.equal(trend.cellBounds({ lat: 90, lon: 0 }, STEP).north, 90);
assert.equal(trend.cellSubdivisions(STEP, 2), 1);
assert.equal(trend.cellSubdivisions({ lat_step: 5, lon_step: 5 }, 2), 3);
const CELLS = [
  { lat: 10, lon: 0, slope_per_decade: 0.3, significant: true },
  { lat: 10, lon: 0.625, slope_per_decade: 0.2, significant: true },
  { lat: 10.5, lon: 0, slope_per_decade: null, significant: false },
  { lat: 10.5, lon: 0.625, slope_per_decade: -0.3, significant: false },
];
const OPTIONS = { radius: 1.002, outlineRadius: 1.003, maxQuadDeg: 2, maxAbs: 0.3 };
const built = trend.buildTrendGeometry(CELLS, STEP, OPTIONS);
assert.equal(built.paintedCells, 3, "the cell without a slope is not painted");
assert.equal(built.positions.length, 3 * 4 * 3);
assert.equal(built.colors.length, 3 * 4 * 4);
assert.equal(built.indices.length, 3 * 2 * 3);
assert.deepEqual([...built.faceCell], [0, 0, 1, 1, 3, 3], "faces point back at the input cells");
for (let t = 0; t < built.indices.length; t += 3) {
  const [a, b, c] = [0, 1, 2].map((k) => {
    const v = built.indices[t + k] * 3;
    return [built.positions[v], built.positions[v + 1], built.positions[v + 2]];
  });
  const ab = b.map((v, i) => v - a[i]);
  const ac = c.map((v, i) => v - a[i]);
  const normal = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]];
  assert.ok(normal[0] * a[0] + normal[1] * a[1] + normal[2] * a[2] > 0, `triangle ${t / 3} faces outwards`);
  assert.ok(Math.abs(Math.hypot(...a) - 1.002) < 1e-6, "vertices on the trend radius");
}
// First cell: strongest rise, significant → Rocket Red, opaque. Last: strongest fall, muted.
const rocket = colors.parseHex("#E43700").map(colors.srgbChannelToLinear);
[0, 1, 2].forEach((k) => assert.ok(Math.abs(built.colors[k] - rocket[k]) < 1e-6, "rising colour"));
assert.equal(built.colors[3], colors.TREND_ALPHA_SIGNIFICANT);
assert.ok(Math.abs(built.colors[built.colors.length - 1] - colors.TREND_ALPHA_NOT_SIGNIFICANT) < 1e-6, "muted alpha");
// Two significant neighbours: one rectangle, the shared edge is not drawn → 6 segments.
assert.equal(built.outline.length, 6 * 2 * 3);
const lone = trend.buildTrendGeometry([CELLS[0]], STEP, OPTIONS);
assert.equal(lone.outline.length, 4 * 2 * 3);
assert.equal(trend.buildTrendGeometry([], STEP, OPTIONS).positions.length, 0);
assert.equal(trend.maxAbsSlope(CELLS), 0.3);
const ring = trend.cellOutline({ lat: 10, lon: 0 }, { lat_step: 5, lon_step: 5 }, 1.006, 2);
assert.equal(ring.length, 4 * 3 + 1);
assertVec(ring[0], ring[ring.length - 1], "outline is closed");
assertVec(ring[0], geo.latLonToVec3(7.5, -2.5, 1.006), "outline starts at the south-west corner");
// A large cell is subdivided and still hugs the sphere.
const big = trend.buildTrendGeometry([{ lat: 0, lon: 0, slope_per_decade: 1, significant: true }], { lat_step: 10, lon_step: 10 }, { ...OPTIONS, maxAbs: 1 });
assert.equal(big.indices.length / 3, 2 * 5 * 5);

// The fixture (built by scripts/build_demos.py from live data, so its numbers change when it is
// rebuilt): every valid cell painted, the mesh starts at the box's south-west corner, and the
// text alternative repeats the counts and the twin.
const fixture = (JSON.parse(readFileSync(new URL("../../fixtures/trendmap.json", import.meta.url), "utf8")) as { data: import("@/lib/api").TrendMapResult }).data;
const fixtureGeometry = trend.buildTrendGeometry(fixture.cells, fixture.grid, { ...OPTIONS, maxAbs: fixture.summary.max_abs_slope });
const validCells = fixture.cells.filter((c) => c.slope_per_decade !== null).length;
assert.ok(validCells > 0, "the fixture has cells to paint");
assert.equal(fixtureGeometry.paintedCells, validCells);
assert.equal(fixtureGeometry.faceCell.length, validCells * 2);
const firstCell = fixture.cells.find((c) => c.slope_per_decade !== null)!;
const firstVertex = geo.vec3ToLatLon(fixtureGeometry.positions[0], fixtureGeometry.positions[1], fixtureGeometry.positions[2]);
assert.ok(
  Math.abs(firstVertex.lat - (firstCell.lat - fixture.grid.lat_step / 2)) < 1e-4 &&
    Math.abs(firstVertex.lon - (firstCell.lon - fixture.grid.lon_step / 2)) < 1e-4,
  "mesh starts at the south-west corner of the first cell",
);

// Text alternative of the trend map.
const twin = fixture.opposite_twin;
assert.ok(twin, "the Sahel fixture has an opposite twin");
const text = summary.trendMapSummary(fixture, twin);
assert.ok(text.includes(`${fixture.summary.n_valid} cells`), text);
assert.ok(text.includes(`${fixture.summary.n_up_significant} rising`) && text.includes(`${fixture.summary.n_down_significant} falling`), text);
assert.ok(text.includes("Precipitation") && text.includes("1981–2025"), text);
assert.ok(text.includes(`${Math.round(twin.distance_km)} km`), text);
assert.ok(!summary.trendMapSummary(fixture, null).includes("twin"), "no twin, no twin sentence");
const down = twin.down;
assert.ok(
  summary.cellLabel(down, "mm/day").startsWith(`${Math.abs(down.lat).toFixed(2)}°${down.lat >= 0 ? "N" : "S"}, ${Math.abs(down.lon).toFixed(2)}°${down.lon >= 0 ? "E" : "W"}: −`),
  summary.cellLabel(down, "mm/day"),
);
assert.ok(summary.cellLabel(down, "mm/day").endsWith("mm/day per decade, significant"));

// The palette for people with a colour-vision deficiency (Viénot et al. 1999 dichromat
// matrices on linear RGB): the two ends must stay far apart, and every stop must stand
// out from the land and the ocean.
const CVD: Record<string, readonly (readonly number[])[]> = {
  protanopia: [[0.11238, 0.88762, 0], [0.11238, 0.88762, 0], [0.00401, -0.00401, 1]],
  deuteranopia: [[0.29275, 0.70725, 0], [0.29275, 0.70725, 0], [-0.02234, 0.02234, 1]],
  tritanopia: [[1, 0.14461, -0.14461], [0, 0.85924, 0.14076], [0, 0.85924, 0.14076]],
};
function simulate(rgb: readonly number[], matrix: readonly (readonly number[])[]): number[] {
  const linear = rgb.map(colors.srgbChannelToLinear);
  return matrix.map((row) => Math.min(1, Math.max(0, row[0] * linear[0] + row[1] * linear[1] + row[2] * linear[2])));
}
const fallingEnd = colors.parseHex(colors.TREND_PALETTE[0].color);
const risingEnd = colors.parseHex(colors.TREND_PALETTE[colors.TREND_PALETTE.length - 1].color);
for (const [name, matrix] of Object.entries(CVD)) {
  const a = simulate(fallingEnd, matrix);
  const b = simulate(risingEnd, matrix);
  const distance = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  assert.ok(distance > 0.3, `${name}: the two ends of the scale are too close (${distance.toFixed(3)})`);
}
const ocean = colors.parseHex(colors.GLOBE_COLORS.ocean);
const landRgb = colors.parseHex(colors.GLOBE_COLORS.land);
for (const stop of colors.TREND_PALETTE) {
  const rgb = colors.parseHex(stop.color);
  assert.ok(colors.contrastRatio(rgb, ocean) >= 3, `${stop.color} on the ocean: ${colors.contrastRatio(rgb, ocean).toFixed(2)}`);
  assert.ok(colors.contrastRatio(rgb, landRgb) >= 2, `${stop.color} on land: ${colors.contrastRatio(rgb, landRgb).toFixed(2)}`);
}
// Lightness falls steadily from the neutral middle to each end (magnitude is not hue alone).
const lum = colors.TREND_PALETTE.map((stop) => colors.relativeLuminance(colors.parseHex(stop.color)));
const mid = (lum.length - 1) / 2;
for (let i = 0; i < mid; i += 1) {
  assert.ok(lum[i] < lum[i + 1], "falling side gets lighter towards zero");
  assert.ok(lum[lum.length - 1 - i] < lum[lum.length - 2 - i], "rising side gets lighter towards zero");
}

// Time-lapse datasets: both sets of static files load, match meta.json, and read the same way.
const datasetsUrl = new URL("./timelapse-datasets.ts", import.meta.url).href;
const datasets = (await import(datasetsUrl)) as typeof import("./timelapse-datasets");
const dataUrl = new URL("./timelapse-data.ts", import.meta.url).href;
const tdata = (await import(dataUrl)) as typeof import("./timelapse-data");
const publicDir = new URL("../../public", import.meta.url);
const diskFetch = async (url: string): Promise<Response> =>
  new Response(readFileSync(new URL(`.${url}`, `${publicDir.href}/`)));

for (const id of datasets.DATASET_ORDER) {
  const dataset = datasets.TIMELAPSE_DATASETS[id];
  const loaded = await tdata.loadTimelapse(dataset, diskFetch);
  const { meta } = loaded;
  assert.equal(loaded.dataset.id, id);
  assert.equal(meta.unit, dataset.unit, `${id}: unit`);
  assert.equal(meta.labels?.up, dataset.labels.up, `${id}: labels`);
  for (const row of meta.shares) {
    assert.ok(row.up_pct >= 0 && row.up_pct <= 100 && row.down_pct >= 0, `${id} ${row.year}: shares`);
    assert.ok(row.up_cells + row.down_cells <= row.tested_cells, `${id} ${row.year}: cells`);
  }
  // The scale: one band per step, ticks inside, 0 on a band boundary (neutral pair either side).
  const { scale } = dataset;
  assert.equal(Math.round((scale.max - scale.min) / scale.step), scale.bands.length, `${id}: bands`);
  assert.equal(datasets.scaleBandIndex(scale, -scale.step / 2) + 1, datasets.scaleBandIndex(scale, scale.step / 2));
  assert.equal(datasets.scaleBandIndex(scale, scale.max * 10), scale.bands.length - 1);
}

// Vegetation: 1-degree grid, 2001-2025, India greening and the open ocean never measured.
const ndvi = await tdata.loadTimelapse(datasets.TIMELAPSE_DATASETS.vegetation, diskFetch);
assert.equal(ndvi.meta.grid.step_deg, 1);
assert.deepEqual([ndvi.meta.years[0], ndvi.meta.years.at(-1)], [2001, 2025]);
const punjab = tdata.cellDetail(ndvi, 30.6, 75.4, 2025);
assert.deepEqual([punjab.lat, punjab.lon], [30.5, 75.5], "cell centre of a 1-degree grid");
assert.equal(punjab.direction, 1, "Punjab greening");
const pacific = tdata.cellDetail(ndvi, 0, -140, 2025);
assert.equal(pacific.anomaly, null);
assert.ok(pacific.series.every((v) => v === null), "open ocean never measured");

process.stdout.write(`geo.check: all assertions passed (${compared} sphere vertices compared)\n`);
