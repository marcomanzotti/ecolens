# EcoLens

**The tool finds the trends. You investigate them.**

EcoLens is our answer to the NASA Space Apps Challenge 2026 challenge
*Be An Earth System Trend Detective!*. Pick any place on Earth, and it questions 31 Earth-system
variables from [NASA POWER](https://power.larc.nasa.gov/) (1981–2025) and tells you **what** is
changing, **where**, **by how much**, and **how sure** we can be that the change is real.

## What it does

- **Open a case**: three guided questions (what, where, when) or a click on the 3D globe.
- **Verdict and evidence**: the yearly series with its trend line and 95% confidence band, the
  slope per decade, a t-test on the fitted line, the Mann-Kendall test and Sen's slope, then a
  verdict in plain words. "Significant" means both tests agree at α = 0.05.
- **When the case cracked**: the year the trend became significant and stayed so, and a rough
  estimate of how many years of data a trend of that size needs.
- **The line-up**: every variable questioned at the same place, ranked by the size of the trend
  relative to its year-to-year noise, with p-values corrected for multiple testing
  (Benjamini-Hochberg).
- **Where it flips**: the same test on every grid point of a 10° × 10° box, drawn on the globe,
  with the closest pair of cells that change in opposite directions (the "opposite twin").
- **Witnesses**: where a second product measures the same quantity, both are compared.
- **Limitations**: every case ends with what it cannot tell you.
- **Solved cases**: four saved investigations (Sahel rainfall, Delhi sunlight, Pantanal
  rainfall, Venice temperature), built with the same engine on live data.

## How it is built

```
backend/   Python 3.12 · FastAPI · numpy/scipy
  trend_detective/   the engine: statistics, emergence, line-up, map, verdict (no web code)
  api/               routes, validation, cache, rate limits, CORS, saved demos
frontend/  Next.js · React · Tailwind · three.js globe
scripts/   type generation, demo and fixture builder
docs/      API contract and OpenAPI schema
```

The API contract is in [docs/API_CONTRACT.md](docs/API_CONTRACT.md). Every response is
`{success, data, error}`. The only live data dependency is NASA POWER, which needs no login.

## Run it locally

```bash
# Back-end (http://localhost:8000)
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
FRONTEND_ORIGIN=http://localhost:3000 .venv/bin/uvicorn api.main:app --port 8000

# Front-end (http://localhost:3000), in a second terminal
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

`npm run dev:fixtures` runs the interface alone, on saved answers. Tests:
`cd backend && .venv/bin/python -m pytest` and `cd frontend && npm run typecheck && npm run lint`.

## Data and method

- **Data**: NASA POWER monthly point and regional API, community AG. Products named by POWER:
  MERRA-2 reanalysis, CERES SYN1deg and GEWEX SRB. Where POWER does not state the source
  product of a variable, the app labels it "provisional".
- **Statistics**: annual or seasonal means; ordinary least squares with a t-test and 95%
  interval; Mann-Kendall with tie correction; Sen's slope; Benjamini-Hochberg across the line-up
  and the map; at least 10 valid years. Checked in tests against numpy, scipy and pymannkendall.
- **Years needed to detect a trend**: a rough estimate adapted from Weatherhead et al. (1998)
  to yearly data. It is an approximation, not a prediction.
- **Known limits**: the verdict switches to the Hamed-Rao autocorrelation-corrected
  Mann-Kendall test only when year-to-year autocorrelation is high (|r| > 0.3); the time-lapse
  maps use the uncorrected test; only straight-line trends are tested; a trend says that a value
  changed, not why.

## Use of AI

- **In development**: the code, tests and documentation were written with the help of an AI
  coding assistant (Claude, by Anthropic), under the direction and review of the team. Every
  statistical method was checked against independent libraries in automated tests.
- **In the app**: no AI produces any number or verdict. All figures and verdicts come from
  fixed statistical rules in `backend/trend_detective/`. The public app has no AI assistant and
  sends nothing to an AI service.

## Credits

Data: NASA POWER (NASA Langley Research Center). Coastlines: Natural Earth via `world-atlas`.

Static files shipped with the app (`frontend/public/`, `backend/trend_detective/data/`, `data/`):

- **Earth image**: Blue Marble, NASA Earth Observatory, via NASA GIBS.
- **Temperature time-lapse and witness**: GISTEMP v4, NASA Goddard Institute for Space Studies
  (GISS Surface Temperature Analysis).
- **Vegetation time-lapse**: MODIS Terra monthly NDVI (NASA LP DAAC), via NASA GIBS.
- **2050 projections**: CMIP6 multi-model ensemble (WCRP), through the Pangeo / Google Cloud
  public dataset, licensed CC BY 4.0. Models and members are listed in
  `frontend/public/earth/projections/meta.json`. We thank the climate modelling groups for
  producing and making available their model output.
- **Weather-station witnesses**: NOAA NCEI Global Summary of the Year (GHCN).
- **Place search**: GeoNames (`cities15000`), licensed CC BY 4.0, https://www.geonames.org/.

NASA data are used under NASA's open data policy. EcoLens is an independent project for the
NASA Space Apps Challenge 2026 and is not endorsed by NASA, NOAA or WCRP.

## License

Code: MIT, see `LICENSE`. Data files keep the licences listed in Credits.
