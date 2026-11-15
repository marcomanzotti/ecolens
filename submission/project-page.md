# EcoLens: project page text

Text for the NASA Space Apps Challenge 2026 project page, in the order of the submission form.

- **Challenge:** Be An Earth System Trend Detective!
- **Team:** project_nasa (Marco Manzotti, Dario Bottari, Miles McCrudden)
- **Live app (no login):** https://ecolens-earth.vercel.app
- **Code (MIT licence):** https://github.com/marcomanzotti/ecolens
- **Demo (29-second video):** https://github.com/marcomanzotti/ecolens/blob/main/submission/video/ecolens-demo.mp4
- **Slides (7, PDF):** https://github.com/marcomanzotti/ecolens/blob/main/submission/slides/ecolens-slides.pdf

---

## 1. Project name

**EcoLens**. Tagline: *The tool finds the trends. You investigate them.*

## 2. High-level summary

EcoLens turns NASA Earth-science data into investigations that a student can follow. Pick any
place on Earth: a city, a pair of coordinates or a click on a 3D globe. EcoLens fetches 31
Earth-system variables from NASA POWER (monthly, 1981–2025), tests each one for a trend, and
answers the four questions the challenge asks: **what** is changing, **where**, **by how much**,
and **whether the change is statistically significant**. A trend is called "significant" only when
two independent tests agree, a least-squares t-test and the Mann-Kendall test, at α = 0.05.
EcoLens then ranks every variable at that place with a correction for multiple testing, compares
the measurement with a second independent record where one exists, shows the year the trend
became significant, and puts it next to what CMIP6 climate models project for 2041–2060. Every
case ends with what the analysis cannot tell you. It matters because the same variable can rise
in one place and fall a short distance away, and a slope through noisy data is not a trend until
it has been tested. EcoLens makes that test visible, explains it in plain words, and is open to
anyone with a browser.

## 3. Project demo

A 29-second video of the live app, with English captions: https://github.com/marcomanzotti/ecolens/blob/main/submission/video/ecolens-demo.mp4

Also as seven slides (PDF): https://github.com/marcomanzotti/ecolens/blob/main/submission/slides/ecolens-slides.pdf

## 4. Final project

- Live app: https://ecolens-earth.vercel.app
- Source code: https://github.com/marcomanzotti/ecolens

## 5. Project details

### What it does

- **Open a case.** Search 34,216 places (every city above 15,000 inhabitants, from GeoNames),
  type coordinates, or click anywhere on the globe. Choose the whole year or a season
  (DJF, MAM, JJA, SON) and the years to study.
- **Verdict and evidence.** The yearly series with its trend line and 95% confidence band,
  the slope per decade (Sen's slope and least squares), the t-test on the fitted line, the
  Mann-Kendall test, and a verdict in plain words: what, where, how much, how sure.
- **When the case cracked.** The test is repeated on a record that grows one year at a time.
  The app shows the year the trend became significant and stayed so, and a rough estimate of
  how many years of data a trend of that size needs to be detected.
- **The line-up.** All 31 variables are questioned at the same place and years, ranked by the
  size of their trend relative to their own year-to-year noise, with p-values corrected for the
  number of tests (Benjamini-Hochberg).
- **Where it flips.** The same test on every grid cell of a 10° × 10° box, drawn on the globe,
  with the closest pair of cells that change significantly in opposite directions (the
  "opposite twin").
- **Witnesses.** Where a second record measures the same quantity, both are compared. For air
  temperature: NASA GISTEMP v4 everywhere and NOAA weather stations where one lies within
  50 km; for water vapour: two products inside NASA POWER (MERRA-2 and CERES).
- **The future.** What 12 CMIP6 climate models project for 2041–2060 compared with 1995–2014,
  under a moderate (SSP2-4.5) and a high (SSP5-8.5) emission scenario, with the share of models
  that agree on the direction. Shown as scenarios, never as a forecast.
- **The planet.** The home page globe plays a time-lapse from 1981 to 2025, computed by us from
  NASA GISTEMP v4: for every year and every 2° cell, the same trend test, with the cells where
  warming or cooling has become significant outlined. A second layer does the same for
  vegetation (MODIS NDVI, 2001–2025), and a third shows the CMIP6 projections for 2050.
- **Solved cases and guided tour.** Four saved investigations built with the same engine on real
  data (Sahel rainfall, Delhi sunlight, Pantanal rainfall, Venice temperature) and a guided tour
  of about 30 seconds per case.
- **Limitations.** Every case lists what it cannot tell you (see "Honest limits" below).

### A real example (Venice Lagoon, air temperature, 1981–2025, from the live app)

- Rising by **+0.41 °C per decade** (Sen's slope; 95% interval +0.29 to +0.51); the fitted line
  changes by +1.78 °C over the period. t-test and Mann-Kendall both p < 0.001.
- The trend became significant in **2000**, when the record was 20 years long, and has stayed so.
  A trend of this size against this noise needs about 25 years of data (rough estimate).
- Witness: GISTEMP v4 gives **+0.50 °C per decade** in the same 2° cell; both rise significantly,
  correlation 0.96.
- Line-up: **13 of 31** variables show a significant trend after the Benjamini-Hochberg
  correction. Map: all 336 cells of the 10° × 10° box around Venice warm significantly.
- CMIP6, 2041–2060 vs 1995–2014: **+1.6 °C** under SSP2-4.5 and **+2.3 °C** under SSP5-8.5
  (median of 12 models); 12 of 12 models project warming.

The guided tour shows the "opposite twin" at Delhi: sunlight reaching the ground falls by
−0.61 MJ/m²/day per decade at the city, and in the 10° × 10° box around it 84 cells fall and 7
rise significantly; the nearest pair of cells moving in opposite directions is 455 km apart.

### How it works

- **Back-end:** Python 3.12, FastAPI, numpy and scipy. The statistical engine
  (`backend/trend_detective/`) has no web code. NASA POWER is the only live data source; it needs
  no login. Responses are cached and rate-limited.
- **Statistics:** annual or seasonal means from monthly data; at least 10 valid years;
  ordinary least squares with a t-test and 95% interval; Mann-Kendall with tie correction; Sen's
  slope with its interval; lag-1 autocorrelation, and the Hamed-Rao (1998) variance correction of
  the Mann-Kendall test used in the verdict when the autocorrelation exceeds 0.3 in absolute value;
  Benjamini-Hochberg false discovery rate across the line-up and the map. Checked in automated
  tests against numpy, scipy and pymannkendall (about 600 tests in the back-end).
- **Verdict:** written by fixed rules from the test results. No AI is involved.
- **Front-end:** Next.js, React, Tailwind CSS and three.js (react-three-fiber) for the globe,
  Recharts for the charts. Keyboard navigation, text alternatives for the globe and the charts,
  data tables behind every chart, and reduced-motion support.
- **Static layers:** built once by scripts in `scripts/` and served as files: the GISTEMP and
  MODIS time-lapses, the CMIP6 projections, the Blue Marble Earth image and the place list.
- **Hosting:** Vercel (front-end and a Python function for the API).

### Benefits

- Starts from a place, not from a dataset: no need to know variable codes or data portals.
- Explains every variable in one plain sentence and every verdict in words, with the numbers
  behind it one click away.
- Shows that "significant" is a result of a test, and that a trend may need more years of data
  to be detected.
- Makes the challenge's key point visible: the same variable can trend in opposite directions
  in nearby places.
- Free, open source and with no login.

### Intended impact

The challenge names high-school and college students and members of the public with some
scientific background as the audience. EcoLens is meant for a classroom or a curious reader: open
the place you live in, see what has changed since 1981, check how sure we can be, and learn the
habits of a careful data detective: test before you claim, look for a second witness, say what
you cannot know. The engine is separate from the interface and documented by an API contract,
so other variables or data sources can be added.

### Tools, languages and hardware

Python 3.12 (FastAPI, numpy, scipy, pydantic, httpx); TypeScript (Next.js, React, Tailwind CSS,
three.js, react-three-fiber, Recharts, d3-geo, topojson-client); pytest and pymannkendall for
testing; Vercel for hosting; GitHub. No special hardware: the team used personal laptops.

## 6. NASA data and resources

- **NASA POWER** (NASA Langley Research Center), https://power.larc.nasa.gov/ — monthly point and
  regional API, community AG, 1981–2025, fetched live when a case is opened. 31 variables on
  temperature, water, soil, snow, sunlight, air and wind. The source products named by POWER are
  the **MERRA-2** reanalysis (NASA GMAO), **CERES SYN1deg** and **GEWEX SRB**. POWER confirms the
  product only for some variables (MERRA-2 for precipitation and column water vapour, CERES for
  precipitable water); for the others the app marks the product label as "provisional".
- **GISTEMP v4** (NASA Goddard Institute for Space Studies),
  `gistemp1200_GHCNv4_ERSSTv5.nc.gz`, file of 10 November 2026: annual anomalies 1981–2025 on a
  2° grid. Used for the globe time-lapse (a trend test in every cell for every year) and as the
  temperature witness. In 2025, 78% of the measured surface shows a significant warming trend
  since 1981.
- **MODIS Terra monthly NDVI** (NASA LP DAAC), through **NASA GIBS** (layer
  `MODIS_Terra_L3_NDVI_Monthly`): 300 monthly images 2001–2025 converted back to NDVI values with
  the colour map published by GIBS (error at most ±0.005). Used for the vegetation time-lapse
  ("greening" and "browning").
- **Blue Marble** shaded relief and bathymetry (NASA Earth Observatory), through **NASA GIBS**:
  the Earth image on the globe, at 2K, 4K and 8K.
- **CMIP6 model GISS-E2-1-G** (NASA GISS) is one of the 12 models in the 2050 projections.

NASA data are used under NASA's open data policy and credited in the app and in the README.
No NASA logo, insignia or mission identifier is used.

## 7. Space agency partner data, other data and references

**Space agency partner data:** none used.

**Other data**
- **CMIP6** multi-model projections (WCRP), through the Pangeo / Google Cloud public dataset,
  licensed CC BY 4.0 (PCMDI CMIP6 Terms of Use). 12 models, one run each: GISS-E2-1-G,
  ACCESS-CM2, CanESM5, CNRM-CM6-1, GFDL-ESM4, IPSL-CM6A-LR, MIROC6, MPI-ESM1-2-LR, MRI-ESM2-0,
  UKESM1-0-LL, BCC-CSM2-MR, CESM2-WACCM. We thank the climate modelling groups for producing and
  making available their model output.
- **NOAA NCEI Global Summary of the Year** (GHCN) station records, used as temperature witnesses
  at Tromsø, Fresno and New York Central Park.
- **GeoNames** `cities15000`, CC BY 4.0, https://www.geonames.org/: place search.
- **Natural Earth** coastlines through the `world-atlas` package.

**Methods**
- Mann, H. B. (1945) and Kendall, M. G. (1975): Mann-Kendall trend test.
- Sen, P. K. (1968): slope estimator.
- Hamed, K. H. and Rao, A. R. (1998): Mann-Kendall test for autocorrelated data.
- Benjamini, Y. and Hochberg, Y. (1995): false discovery rate.
- Weatherhead, E. C. et al. (1998): number of years needed to detect a trend (adapted, see limits).
- IPCC AR6 simple approach for model agreement (at least 80% of models agree on the sign).

**Software:** FastAPI, numpy, scipy, pydantic, httpx, pymannkendall (tests only), Next.js,
React, Tailwind CSS, shadcn, three.js, react-three-fiber, drei, Recharts, d3-geo,
topojson-client. Fonts: Fira Sans and Overpass (SIL Open Font License), as in the Space Apps
brand guide.

## 8. Use of AI

- **In development:** the code, tests, documentation and these submission texts were written
  with the help of an AI coding assistant (Claude, by Anthropic), under the direction and review
  of the team. The idea, the choice of data and methods and the decisions were the team's. Every
  statistical method was checked against independent libraries (numpy, scipy, pymannkendall) in
  automated tests. The README declares this in a "Use of AI" section.
- **In the app:** no AI. No AI produces any number, verdict or text in the app: all figures and
  verdicts come from fixed statistical rules in `backend/trend_detective/`. The app sends nothing
  to an AI service.
- **Images and video:** the slides contain only screenshots of the app, and the demo video is a screen recording of the live app, driven by an automated browser script, with captions and title cards written with the help of the AI coding assistant and reviewed by the team. Its background music is original, synthesised note by note by a small script (no samples, no AI model). No image, video or audio was generated by an AI model.

## Honest limits

These are stated in the app, in each case's "Limitations" panel or next to the figure.

- **Straight lines only.** The tests detect monotonic or straight-line trends; a change that
  speeds up, slows down or reverses is not captured. A trend shows that a value changed, not why.
- **Autocorrelation.** When the lag-1 autocorrelation of a series exceeds 0.3 in absolute value,
  the verdict uses the Mann-Kendall p-value with the Hamed-Rao correction. The t-test p-value is
  never corrected, and the line-up, the trend map, the emergence year and the globe time-lapses
  use the Mann-Kendall p-value without this correction.
- **"Years to detect"** is a rough estimate adapted from Weatherhead et al. (1998) to yearly data.
  The original paper is behind a paywall and was not re-read: the formula was adapted by us and
  checked numerically in tests. It is an approximation, not a prediction.
- **Product labels.** NASA POWER does not state the source product for every variable. Labels
  are confirmed only for precipitation and column water vapour (MERRA-2) and precipitable water
  (CERES); the others are shown as "provisional".
- **Grid scale.** Values describe a grid cell of roughly 50 km (MERRA-2) or about 100 km (CERES
  products), not the exact spot. GISTEMP cells are 2° and spread station data up to 1,200 km.
- **Witnesses are not fully independent.** GISTEMP also uses NOAA station data; the two products
  inside POWER may share inputs. Agreement between witnesses is not proof.
- **CMIP6 projections** are scenarios, not forecasts. Models resolve about 1–2.5°, are read at
  the 2° cell that contains the place, are not bias-corrected or downscaled, and know nothing
  about the local trend measured by the app.
- **Coverage.** Some POWER variables start in 1984 or 2001; the app says so and tests the shorter
  period. NOAA station witnesses exist only at three places.
- **NDVI time-lapse.** Values are recovered from colour images (error at most ±0.005); the yearly
  value is the peak month; April 2025 is missing on GIBS.
