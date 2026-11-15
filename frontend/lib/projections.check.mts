/**
 * Assertions for projections.ts on the real files in public/earth/projections. Run from frontend/ with:
 *   node lib/projections.check.mts
 * (Node 22.18+ strips the TypeScript types by itself.)
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import type { ProjectionMeta } from "./projections";

const moduleUrl = new URL("./projections.ts", import.meta.url).href;
const lib = (await import(moduleUrl)) as typeof import("./projections");

const dir = new URL("../public/earth/projections/", import.meta.url);
const meta = JSON.parse(readFileSync(new URL("meta.json", dir), "utf8")) as ProjectionMeta;
const field = (variable: string, scenario: "ssp245" | "ssp585") => {
  const bytes = readFileSync(new URL(meta.variables[variable].files[scenario], dir));
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  return lib.parseProjectionField(meta, variable, scenario, buffer);
};

// Grid: same cells and order as GISTEMP (rows south to north, columns west to east).
assert.equal(lib.projectionCellIndex(meta, -89.5, -179.5), 0);
assert.equal(lib.projectionCellIndex(meta, -89.5, 179.5), meta.grid.n_lon - 1);
assert.equal(lib.projectionCellIndex(meta, 89.5, 179.5), meta.grid.n_lat * meta.grid.n_lon - 1);
assert.equal(lib.projectionCellIndex(meta, 0.5, 180.5), lib.projectionCellIndex(meta, 0.5, -179.5));

// Variable mapping: only physically matching pairs.
assert.equal(lib.cmip6VariableFor("T2M"), "tas");
assert.equal(lib.cmip6VariableFor("PRECTOTCORR"), "pr");
assert.equal(lib.cmip6VariableFor("GWETROOT"), "mrsos");
assert.equal(lib.cmip6VariableFor("AOD_55"), null);
assert.equal(lib.cmip6VariableFor(null), null);

// Temperature: warmer everywhere on land, more in SSP5-8.5 and in the Arctic.
const tas245 = field("tas", "ssp245");
const tas585 = field("tas", "ssp585");
const venice245 = lib.projectionAt(meta, tas245, 45.44, 12.33);
const venice585 = lib.projectionAt(meta, tas585, 45.44, 12.33);
assert.ok(venice245 && venice585);
assert.ok(venice245.median > 0.8 && venice245.median < 4, `Venice SSP2-4.5 ${venice245.median}`);
assert.ok(venice585.median > venice245.median);
assert.ok(venice245.p10 <= venice245.median && venice245.median <= venice245.p90);
assert.ok(venice245.robust && venice245.agreeing === venice245.count);
const svalbard = lib.projectionAt(meta, tas245, 78.2, 15.6);
assert.ok(svalbard && svalbard.median > venice245.median, "Arctic amplification");
assert.match(lib.agreementSentence("tas", venice245), /^\d+ of \d+ models project warmer conditions\.$/);

// Precipitation: a % change with a 10-90% range and a sentence.
const niamey = lib.projectionAt(meta, field("pr", "ssp245"), 13.51, 2.11);
assert.ok(niamey);
assert.ok(niamey.p10 <= niamey.median && niamey.median <= niamey.p90);
assert.ok(niamey.count >= 3 && niamey.agreeing <= niamey.count);
assert.match(lib.agreementSentence("pr", niamey), /models project (wetter|drier) conditions\.$/);

// Wrong-size files are refused.
assert.throws(() => lib.parseProjectionField(meta, "tas", "ssp245", new ArrayBuffer(10)));

process.stdout.write("projections.check: all assertions passed\n");
