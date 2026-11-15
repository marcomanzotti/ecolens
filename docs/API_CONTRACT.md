# API contract — EcoLens

Agreed on 14/11/2026 (stage 1). Front-end and back-end are built against this document.

## Where the truth lives

| What | File | Edited by hand? |
|---|---|---|
| Response and domain models | `backend/trend_detective/models.py` | **Yes — the single source of truth** |
| Request bodies, envelope, error codes | `backend/api/schemas.py` | Yes |
| Routes | `backend/api/main.py` | Yes |
| OpenAPI schema | `docs/openapi.json` | No, generated |
| TypeScript types | `frontend/lib/api-types.gen.ts` | No, generated |
| Typed client and type aliases | `frontend/lib/api.ts` | Yes |
| One example answer per endpoint | `frontend/fixtures/*.json` | No, generated |

Field-level detail (every field, type and description) is in `models.py` and in
`docs/openapi.json`; this document gives the rules that the schema cannot express.

**Changing the contract:**

```bash
# 1. edit models.py / schemas.py, then
scripts/gen_types.sh                                   # openapi.json + TypeScript types
backend/.venv/bin/python scripts/build_demos.py        # demos + fixtures (live POWER)
cd backend && .venv/bin/python -m pytest               # contract tests
cd ../frontend && npm run typecheck
```

Never edit the generated files by hand: change the models and run the steps above.

## Running against the contract

```bash
# Back-end (stage 1: every route answers with its fixture)
cd backend && .venv/bin/uvicorn api.main:app --reload --port 8000    # docs at /docs

# Front-end without any back-end
cd frontend && npm run dev:fixtures      # NEXT_PUBLIC_USE_FIXTURES=1
# Front-end against a back-end
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Envelope

Every response, success or failure, at every status code:

```json
{ "success": true,  "data": { },  "error": null }
{ "success": false, "data": null, "error": { "code": "no_data", "message": "…", "details": null } }
```

`error.message` is written in English and is safe to show to the user as it is.
`error.details` is an optional list of strings (validation problems).

| `error.code` | HTTP | When |
|---|---|---|
| `validation_error` | 422 | Body or parameters do not match the schema, or `variable_id` is not in the catalog |
| `no_data` | 422 | The request is valid but the source has no usable data there (e.g. snow in the Sahara) |
| `not_found` | 404 | Unknown path or unknown demo id |
| `rate_limited` | 429 | Too many requests from one client |
| `upstream_unavailable` | 502 | NASA POWER answered with an error |
| `upstream_timeout` | 504 | NASA POWER did not answer in time |
| `assistant_unavailable` | 503 | `/ask` called with no Gemini key configured, or Gemini failed |
| `internal_error` | 500 | Anything else. Never leaks stack traces or secrets |

The client adds one code of its own, `network_error`, when the back-end cannot be reached.

## Endpoints

No authentication. JSON in, JSON out. CORS allows only `FRONTEND_ORIGIN`.

| Method and path | Body | `data` | Fixture | Expected time |
|---|---|---|---|---|
| `GET /health` | — | `Health` | `health.json` | instant |
| `GET /catalog` | — | `Catalog` | `catalog.json` | instant |
| `GET /places` | — | `PlacesResult` | `places.json` | instant |
| `POST /case` | `CaseRequest` | `CaseResult` | `case.json` | a few seconds |
| `POST /lineup` | `LineupRequest` | `LineupResult` | `lineup.json` | several seconds |
| `POST /witnesses` | `WitnessesRequest` | `WitnessesResult` | `witnesses.json` | a few seconds |
| `POST /trendmap` | `TrendMapRequest` | `TrendMapResult` | `trendmap.json` | 10 s or more |
| `POST /ask` | `AskRequest` | `AskResult` | `ask.json` | a few seconds |
| `GET /demo` | — | `DemoList` | `demo_list.json` | instant |
| `GET /demo/{id}` | — | `DemoCase` | `demo.json` | instant |

Times are estimates from two manual POWER calls (point: about 2 s; 10° box: about 7 s), not
measurements of the finished API. Every slow call needs a visible loading state.
`error.json` is an example failure for building error states.

### Requests

```jsonc
// POST /case
{ "location": { "lat": 13.51, "lon": 2.11, "label": "Niamey, Niger" },
  "variable_id": "PRECTOTCORR",
  "period": { "start_year": 1981, "end_year": 2025 },   // optional, this is the default
  "season": "annual" }                                   // optional: annual | DJF | MAM | JJA | SON

// POST /lineup — the whole catalog unless narrowed; variable_ids wins over themes
{ "location": { "lat": 13.51, "lon": 2.11 }, "themes": ["water", "soil"] }

// POST /witnesses — any variable that has a witness_group; its whole group is compared
{ "location": { "lat": 13.51, "lon": 2.11 }, "variable_id": "TQV" }

// POST /trendmap — box between 2 and 10 degrees on each side
{ "variable_id": "PRECTOTCORR",
  "bbox": { "lat_min": 10, "lat_max": 20, "lon_min": -5, "lon_max": 5 } }

// POST /ask — 3 to 500 characters
{ "question": "Is the Sahel getting wetter?" }
```

Unknown fields are rejected (`validation_error`). `location.label` is echoed back and used in
the verdict text; when it is missing the back-end writes the coordinates instead.

## Rules behind the numbers

These bind the engine (BE-1, BE-2) and tell the interface how to word things.

**Series.** One value per year. `season: "annual"` uses the annual mean supplied by POWER (month
key `13`); a season is the mean of its three monthly values, with DJF assigned to the year of its
January. `-999` becomes `null`; a season with a missing month is `null`. Units are converted to the
catalog's display unit before any statistic.

**Significance.** `alpha = 0.05` everywhere, never changed per request. A trend needs at least
10 valid years, otherwise `trend` is `null` and `verdict.evidence` is `"insufficient"`.

| `evidence` | Meaning | `significant` |
|---|---|---|
| `strong` | OLS t-test **and** Mann-Kendall both p < 0.05 (the Hamed-Rao p when `autocorrelation_corrected`) | `true` |
| `mixed` | only one of the two | `false` |
| `none` | neither | `false` |
| `insufficient` | fewer than 10 valid years, or a constant series | — |

**Slopes** are always per decade, in the variable's display unit. `ols.*` is ordinary least squares
on year (two-sided t-test, 95% CI); `mann_kendall.*` uses the tie-corrected variance and continuity
correction; `sen.*` is the Theil-Sen slope with its 95% CI. `direction` follows the sign of Sen's
slope. `total_change` is the OLS slope times the span of the period. `fit` is the OLS line with the
95% confidence band of the mean, one point per year.

**Autocorrelation (P3).** `lag1_autocorrelation` is computed on the detrended residuals.
`mann_kendall.p_value_hamed_rao` is the Mann-Kendall p-value with the Hamed and Rao (1998)
variance correction (Sen-detrended ranks, autocorrelations outside the 95% white-noise band,
n/n\* factor), checked against `pymannkendall.hamed_rao_modification_test` (max abs difference
below 1e-15 on 400 series); it is `null` when the corrected variance is not positive or the series
is a perfect line. When `|lag1_autocorrelation| > 0.3` and it exists, the verdict, `evidence`,
`significant`, `methods_agree` and the Sen interval use it and `autocorrelation_corrected` is
`true`; otherwise they use `mann_kendall.p_value`, which is always the uncorrected one. The OLS
t-test is never corrected. The line-up, the trend map and the emergence years keep the
uncorrected Mann-Kendall p-value (stated in `limitations`).

**Verdict.** Built by fixed rules from `TrendStats` in `verdict.py`. Never by the AI assistant.

**Line-up (block A).** Each variable is tested with Mann-Kendall; p-values are corrected together
with Benjamini-Hochberg (`correction.method = "fdr_bh"`); `significant` means `p_adjusted < alpha`.
Items are ranked by `|standardized_slope|` (Sen's slope divided by the standard deviation of the
series, so that variables in different units can be compared). Variables with no usable data come
last with `status: "no_data"` and `rank: null`. `sparkline` always has one entry per year of the
requested period.

**Emergence (block C).** `running` holds the Mann-Kendall p-value and Sen's slope of the expanding
window from the first year to each `end_year`. `emerged_year` is the first `end_year` from which
the p-value stays below alpha until the end of the record. `years_needed` follows the approach of Weatherhead et
al. (1998), adapted to one value per year:
`n* = [ (3.3 · sqrt(12) · σ / |ω|) · sqrt((1 + φ) / (1 − φ)) ]^(2/3)`, with σ the standard
deviation and φ the lag-1 autocorrelation of the residuals and ω the slope per year. The
`sqrt(12)` is there because the published form is for monthly data; for annual points the variance
of the slope is 12 times larger (derived and checked numerically in `test_emergence.py`). The
paper could not be read (paywalled): the monthly form is quoted from memory and the annual
adaptation is our own derivation. In the interface this number is "a rough estimate", never an
exact prediction. `additional_years` compares it with the span of the record.

**Witnesses (block D).** All variables sharing a `witness_group`, compared over their common
period only. `source.kind` is now `reanalysis | satellite | derived | station | station_grid`:
`station` is a point station record (NOAA GSOY), `station_grid` a gridded analysis of station and
ship records (NASA GISTEMP). Air temperature (`T2M`, group `air_temperature`) is compared with
GISTEMP v4 anywhere on Earth (the 2° cell holding the point, an anomaly from 1951–1980; id
`GISTEMP_ANOMALY`, provider "NASA GISS") and, within 50 km of one of the three NOAA stations,
with that station (id `NOAA_GSOY_<station id>`). Both are annual means: with a season selected
`/witnesses` answers `no_data` and says so. The cell has no data, or the file is missing: the
same error with the reason. `agreement.level`: `agree` (same direction, all significant), `partly` (same
direction), `disagree` (opposite directions), `insufficient`.

**Trend map (block B).** One cell per point of the source grid (MERRA-2: 0.5° latitude × 0.625°
longitude; the 10° sample box has 21 × 17 = 357 cells). Cells are listed row by row; `lat`/`lon`
are the grid points returned by POWER. Benjamini-Hochberg across all cells of the map. Colour
scale: symmetric, from `-summary.max_abs_slope` to `+summary.max_abs_slope`. `opposite_twin` is
the strongest significant rising cell paired with the strongest significant falling cell, or
`null`.

**Assistant.** `/ask` returns only an interpretation, a place and catalog ids. `location` comes
from a geocoder, `variable_ids` are checked against the catalog, and the text never contains
numbers or verdicts. `GET /health` tells the interface whether to show the free-text box
(`assistant_available`).

## About the fixtures

They are built by `scripts/build_demos.py` with the real engine (`TrendInvestigator`) on live
NASA POWER data: the case, line-up and map of the `sahel-rain` demo (Niamey, Niger, 13.51°N,
2.11°E, box 9–19°N, 3°W–7°E) and the column water vapour witnesses at the same place. The same
script writes the saved demos in `backend/api/demo_data/`. `ask.json` and `error.json` are
written by hand. Use the fixtures for shapes, ranges and layout, not as expected values in
engine tests (POWER revises recent years).

## Catalog notes (checked against POWER on 14/11/2026)

- 31 variables in 7 themes; ids are POWER parameter ids. At the three points tried (Niamey,
  Manaus, Tromsø) all return 45 annual values (1981–2025), except those starting in 1984
  (`CLOUD_AMT`, `ALLSKY_SFC_SW_DWN`, `CLRSKY_SFC_SW_DWN`, `ALLSKY_SFC_LW_DWN`) and in 2001
  (`PW`, `AOD_55`, `CLOUD_OD`, `ALLSKY_SFC_UV_INDEX`, `ALLSKY_SRF_ALB`).
- **`IMERG_PRECTOT` (GPM) is listed by POWER but returned only `-999`**, monthly and daily, at
  the two points tried. It is not in the catalog. The witness groups today are `air_temperature` (`T2M` against
  GISTEMP and nearby NOAA stations, see Witnesses) and `column_water_vapour`: `TQV` (MERRA-2, kg/m²) against `PW` (described by POWER as "sourced
  from CERES", cm × 10 = kg/m²). How independent the two really are is not established: the
  interface must not call them independent measurements without that check.
- The `product` labels in the catalog are provisional. BE-2 confirms each one against the POWER
  parameter documentation.
- Request limits of POWER (parameters per call, box size) are not verified beyond the calls
  above: 14 and 20 parameters in one point call worked, one parameter on a 10° box worked.
  BE-1 confirms the limits.
