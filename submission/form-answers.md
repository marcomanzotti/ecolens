# EcoLens: answers for the submission form

Short answers to paste into the Space Apps project page, field by field. The full text is in
`project-page.md`. `docs/SUBMISSION.md` lists the fields but **no character limits**: if the form
shows a limit, the character count after each answer helps to check it (counted without the
heading). Text in square brackets must be filled by hand.

---

## Project name

EcoLens

## High-level summary

_(885 characters)_
EcoLens turns NASA Earth-science data into investigations a student can follow. Pick any place on Earth (a city, coordinates or a click on a 3D globe) and EcoLens tests 31 variables from NASA POWER (monthly, 1981–2025) for a trend. It answers what is changing, where, by how much, and whether the change is significant: a trend counts only when a t-test and the Mann-Kendall test agree at α = 0.05. It ranks all variables with a correction for multiple testing, checks a second record (NASA GISTEMP, NOAA stations), shows the year the trend became significant, maps where the trend flips direction nearby, and compares with CMIP6 projections for 2041–2060. Every case ends with what it cannot tell you. The same variable can rise in one place and fall close by, and a slope is not a trend until it is tested: EcoLens makes that test visible, in plain words, for free and with no login.

## Project demo

[PUBLIC LINK TO THE SLIDES]

(Seven slides: `submission/slides/index.html`, or the PDF `submission/slides/ecolens-slides.pdf`
uploaded to a public folder. Check the link in a private browser window.)

## Final project

https://ecolens-earth.vercel.app

(Code: https://github.com/marcomanzotti/ecolens)

## Project details

_(2008 characters)_
What it does: choose a place (34,216 cities, coordinates or a click on the globe), a season and the years. EcoLens draws the yearly series with its trend line and 95% band and gives a verdict in plain words: what, where, how much (Sen's slope per decade), how sure (t-test and Mann-Kendall). It shows the year the trend became significant and a rough estimate of the years needed to detect it; a line-up of all 31 variables at that place, corrected for multiple testing (Benjamini-Hochberg); a trend map of a 10°×10° box with the nearest pair of cells moving in opposite directions; witnesses (GISTEMP v4, NOAA stations) where they exist; and the CMIP6 projection for 2041–2060 under SSP2-4.5 and SSP5-8.5. The globe plays a 1981–2025 time-lapse with a trend test in every cell (GISTEMP temperature, MODIS vegetation). Four solved cases and a 30-second guided tour help beginners.

Example (live app): Venice Lagoon air temperature rises +0.41 °C per decade (1981–2025), significant since 2000; GISTEMP agrees (+0.50 °C per decade); CMIP6 projects +1.6 °C (SSP2-4.5) and +2.3 °C (SSP5-8.5) for 2041–2060 vs 1995–2014, 12 of 12 models.

How it works: Python 3.12, FastAPI, numpy and scipy for the statistical engine, tested against numpy, scipy and pymannkendall; Next.js, React, Tailwind and three.js for the interface; hosted on Vercel. NASA POWER is fetched live, with no login. The verdicts come from fixed rules: no AI in the app.

Benefits and impact: built for high-school and college students and a curious public. It starts from a place, not a dataset, explains every variable in one sentence, and teaches the habits of a careful detective: test before you claim, find a second witness, say what you cannot know. Open source (MIT).

Limits, stated in the app: straight-line trends only; a trend is not a cause; the Hamed-Rao autocorrelation correction is used only in the verdict; "years to detect" is approximate; some POWER product labels are provisional; CMIP6 values are scenarios, not forecasts.

## NASA data & resources

_(866 characters)_
NASA POWER (Langley), monthly point and regional API, 1981–2025, fetched live: 31 variables (temperature, rainfall, soil wetness, evaporation, snow, sunlight, clouds, aerosols, wind). Source products named by POWER: MERRA-2 reanalysis (GMAO), CERES SYN1deg, GEWEX SRB; labels not confirmed by POWER are shown as provisional. It drives every verdict, the line-up and the trend maps.
GISTEMP v4 (NASA GISS, file of 10 Nov 2026): annual anomalies 1981–2025 on a 2° grid; globe time-lapse with a trend test in every cell for every year (78% of the measured surface warming significantly by 2025), and temperature witness.
MODIS Terra monthly NDVI (NASA LP DAAC) via NASA GIBS: vegetation time-lapse 2001–2025.
Blue Marble (NASA Earth Observatory) via NASA GIBS: the Earth on the globe.
CMIP6 model GISS-E2-1-G (NASA GISS) is one of the 12 models in the 2050 projections.

## Space Agency Partner & other data / references

_(757 characters)_
Space agency partner data: none.
Other data: CMIP6 multi-model projections (WCRP; 12 models, one run each) via the Pangeo / Google Cloud public dataset, CC BY 4.0; NOAA NCEI Global Summary of the Year station records (Tromsø, Fresno, New York); GeoNames cities15000, CC BY 4.0; Natural Earth coastlines via world-atlas.
Methods: Mann (1945) and Kendall (1975); Sen (1968); Hamed and Rao (1998); Benjamini and Hochberg (1995); Weatherhead et al. (1998), adapted; IPCC AR6 model-agreement approach.
Software: FastAPI, numpy, scipy, pydantic, httpx, pymannkendall (tests), Next.js, React, Tailwind CSS, shadcn, three.js, react-three-fiber, Recharts, d3-geo. Fonts: Fira Sans, Overpass (SIL OFL).
Full credits: README of https://github.com/marcomanzotti/ecolens

## Use of AI

_(642 characters)_
Development: the code, tests, documentation and submission texts were written with the help of an AI coding assistant (Claude, by Anthropic), under the direction and review of the team. The idea, data choices, methods and decisions are the team's. Every statistical method was checked against independent libraries (numpy, scipy, pymannkendall) in automated tests. Declared in the README ("Use of AI").
In the app: no AI. No AI produces any number, verdict or text; all figures come from fixed statistical rules. The app sends nothing to an AI service.
No image, video or audio was generated by AI: the slides use screenshots of the app.

---

## Checklist: to fill or do by hand

- [ ] **Team name:** [TEAM NAME] — also on slide 1 and slide 7 of the deck
      (`submission/slides/index.html`: search for `[TEAM NAME]`), then re-export the PDF.
- [ ] **Member names:** [MEMBER 1], [MEMBER 2] — on slide 1 of the deck. The rules require team
      name and member names on the slides.
- [ ] **Event / location:** [LOCAL EVENT NAME, CITY] or Universal Event. Check that both members
      are registered to the **same** event and not on a waiting list (Universal Event needs at
      least 2 people).
- [ ] **Demo link:** host the slides publicly (for example the PDF on Google Drive with "anyone
      with the link", or the `submission/slides/` folder on GitHub Pages or Vercel) and paste the
      link in "Project demo". Open it in a private window to check there is no login.
- [ ] **Final project link:** confirm https://ecolens-earth.vercel.app opens in a private window
      after the last deployment.
- [ ] **Public repo:** confirm https://github.com/marcomanzotti/ecolens shows the latest code and
      README before submitting.
- [ ] Optional: request a FortiGuard rating for `ecolens-earth.vercel.app`
      (https://www.fortiguard.com/faq/wfratingsubmit, Company Name "N/A") so judges can open it.
- [ ] Tick **Terms and Conditions** and **Confirm All Work is Original**.
- [ ] Click **Submit for Judging** (target 23:00, deadline 23:59 local time) and wait for the
      confirmation banner. Use "Save Progress" often.
