/**
 * Assertions for place-search.ts on the real GeoNames index. Run from frontend/ with:
 *   node lib/place-search.check.mts
 * (Node 22.18+ strips the TypeScript types by itself.)
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import type { PlaceIndexFile } from "./place-search";

// Loaded by URL with its extension, as node needs; typed from the module as the bundler sees it.
const searchUrl = new URL("./place-search.ts", import.meta.url).href;
const { buildPlaceIndex, foldText, searchPlaces } = (await import(searchUrl)) as typeof import("./place-search");

const file = JSON.parse(readFileSync(new URL("../public/places/cities.json", import.meta.url), "utf8")) as PlaceIndexFile;
const index = buildPlaceIndex(file);
const names = (query: string, limit?: number) => searchPlaces(index, query, limit).map((p) => `${p.name}/${p.countryCode}`);

// Folding: accents, case and letters that do not decompose.
assert.equal(foldText("Reykjavík"), "reykjavik");
assert.equal(foldText("  ŁÓDŹ "), "lodz");
assert.equal(foldText("São Paulo"), "sao paulo");
assert.equal(foldText("Tromsø"), "tromso");

// A city outside the 16 suggested places, typed without accents.
assert.equal(names("reykjavik")[0], "Reykjavík/IS");
assert.equal(names("Ouagadougou")[0], "Ouagadougou/BF");
const ouaga = searchPlaces(index, "ouaga")[0];
assert.equal(ouaga.country, "Burkina Faso");
assert.ok(Math.abs(ouaga.lat - 12.37) < 0.01 && Math.abs(ouaga.lon + 1.53) < 0.01);

// Exact name before longer prefixes, then the most populous: "Paris" in France first.
assert.equal(names("paris")[0], "Paris/FR");
// A prefix ranks by population: the first "lon" is London.
assert.equal(names("lon")[0], "London/GB");
// A later word matches after names that start with the query: "york" finds New York.
assert.ok(names("york", 20).includes("New York City/US"));
// Country filter after a comma, by name or by code.
assert.ok(names("springfield, us").every((n) => n.endsWith("/US")));
assert.ok(names("springfield, united").every((n) => n.endsWith("/US") || n.endsWith("/GB")));
assert.ok(names("paris, us").length > 0 && names("paris, us").every((n) => n.endsWith("/US")));
// Limits and empty queries.
assert.equal(names("a", 5).length, 5);
assert.deepEqual(names("   "), []);
assert.deepEqual(names("zzzzqqq"), []);
// Every row is usable: finite coordinates in range and a country name.
assert.ok(index.length > 30000);
assert.ok(index.every((p) => Math.abs(p.lat) <= 90 && Math.abs(p.lon) <= 180 && p.country.length > 0));

process.stdout.write(`place-search checks passed (${index.length} places)\n`);
