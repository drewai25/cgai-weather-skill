# Weather Forecast Skill Assessment — Barbados
## Assessment Protocol

**Prepared for:** Barbados Light & Power Company Ltd., via Mottley Consulting Inc.
**Author:** Andrew Narine, CaribbeanGridAI
**Status:** Frozen prior to forecast data acquisition
**Version:** 1.1 — data sources established

---

## 1. The question

Roger Blackman's position, recorded 22 September 2026: a load forecasting model is
of no use without a forward weather forecast to feed it. Historical weather is
freely available and is not the constraint. Forecast weather is.

His requirement before any decision to build: establish whether reliable forecast
data is available for Barbados, and whether it is worth building on.

This assessment answers that question and nothing else. It does **not** build a
Barbados load model. The sequence is deliberate — establish whether the input
exists and carries usable skill before committing to anything that depends on it.

**The question, precisely stated:**

> For temperature, rainfall and solar irradiance at Barbados, how much skill do
> archived operational weather forecasts retain at lead times of one to seven
> days, and does that skill exceed a persistence baseline?

---

## 2. Verification layers

Three layers, named precisely, because the distinction matters:

| Layer | What it is | Role here |
|---|---|---|
| **Forecast** | Archived operational model output, issued at a known initialisation time | The thing under test |
| **Reanalysis verification** | ERA5 — a physics-based reconstruction assimilating observations after the fact | Primary verification dataset |
| **Local observation** | Barbados Meteorological Services SYNOP, Grantley Adams | Secondary verification, limited window |

**ERA5 is not ground truth and is not described as such anywhere in this
assessment.** It is a reanalysis product — itself a model output, blended with
observations through data assimilation. It is used because it provides the
temporal depth the assessment requires.

**On the choice of primary verification layer.** An earlier assumption that
Barbados Meteorological Services data required a formal institutional request was
incorrect and is recorded here as a correction. BMS operates a public WIS 2.0 node
at `barbadosweatherdata.org` exposing an OGC API Features interface. Hourly SYNOP
surface observations are published openly under CC BY 4.0 with attribution, no
registration required.

The constraint is depth, not access. WIS 2.0 is designed for real-time
international exchange and retains a rolling window rather than a climate archive.
Measured on 24 September 2026, the node exposed observations from 17 June 2026 —
approximately 99 days. That is insufficient for a multi-year forecast backtest,
which is why ERA5 is primary.

**What BMS holds internally is unknown.** The rolling window reflects WIS 2.0
retention, not the institution's archive. A longer record may exist and would be
obtainable by direct request. This is recorded as an open question, not a
conclusion.

---

## 3. Data sources — established facts

### 3.1 Barbados Meteorological Services (WIS 2.0 node)

| | |
|---|---|
| Endpoint | `barbadosweatherdata.org/oapi/collections/` |
| Collection | `urn:wmo:md:bb-barbadosmetservices:surface-based-observations.synop` |
| Station | Grantley Adams, WIGOS `0-52-130-78954` |
| Coordinates | 13.073°N, 59.500°W, elevation 62.1 m |
| Exposed window | 17 June 2026 – 24 September 2026 (measured 24 Sep 2026) |
| Records exposed | 59,541 |
| Resolution | Hourly |
| Licence | CC BY 4.0, attribution required |
| Access | Public, no registration |
| Format | GeoJSON; one record per variable per observation |

**Variables published:** air temperature, dewpoint temperature, relative humidity,
cloud cover total, cloud amount, cloud type, height of cloud base, total
precipitation, wind speed, wind direction, horizontal visibility, present weather,
past weather (×2), pressure (station, MSL, 24-hour change), maximum and minimum
temperature over period.

**Variables not published: solar irradiance in any form.** SYNOP does not include
radiation fields. See §4.2.

### 3.2 Open-Meteo

Archived operational forecasts. Previous Runs API for lead-time-stratified
scoring; Single Runs API where exact initialisation-time reconstruction is
required. Free tier permits non-commercial use below 10,000 daily calls; CC BY 4.0
with attribution. Commercial or operational use requires a paid subscription. The
server codebase is AGPLv3 and self-hostable.

Archive depth varies by model and is recorded per model rather than claimed
uniformly. Most Previous Runs models begin January 2024; GFS 2 m temperature
extends to March 2021; ECMWF IFS HRES single runs begin March 2024.

### 3.3 ERA5

Reanalysis, hourly, available from 1940. Accessed via Open-Meteo or Copernicus CDS.

---

## 4. Variables

### 4.1 Under test

| Variable | Open-Meteo parameter | Units | Temporal convention |
|---|---|---|---|
| Air temperature at 2 m | `temperature_2m` | °C | Instantaneous at timestamp |
| Precipitation | `precipitation` | mm | Accumulated over the **preceding** hour |
| Global horizontal irradiance | `shortwave_radiation` | W/m² | Averaged over the **preceding** hour |
| Direct normal irradiance | `direct_normal_irradiance` | W/m² | Averaged over the preceding hour |
| Diffuse irradiance | `diffuse_radiation` | W/m² | Averaged over the preceding hour |
| Cloud cover | `cloud_cover` | % | Total cloud fraction at timestamp |

**Timestamp semantics are established and verified before any scoring.** Two
conventions are in play: temperature and cloud cover are instantaneous at the
stamped hour; precipitation and all irradiance variables are backward-looking over
the preceding hour. Comparing an instantaneous forecast against a
backward-averaged verification — or the reverse — produces a one-hour
misalignment that yields plausible but wrong results.

A convention table is produced and checked for every source before any error is
computed. This is a deliverable in its own right.

### 4.2 The irradiance verification gap

**Declared prominently because it is the most consequential limitation of this
assessment.**

Solar irradiance is the variable of greatest operational significance for a grid
with approximately 100 MW of embedded photovoltaic generation. It is also the only
variable under test that **cannot be verified against local observation**. SYNOP
carries no radiation fields, so GHI, DNI and DHI can be scored only against ERA5 —
a model product on a grid cell that is largely ocean.

Temperature, precipitation and cloud cover can be verified against Grantley Adams
within the overlapping window. Irradiance cannot.

**This is a question for BL&P rather than a problem to be solved unilaterally.**
Utility-scale photovoltaic installations are typically instrumented with
pyranometers. If BL&P holds or can obtain irradiance measurements from any PV site
on the island, that would provide the local verification layer this assessment
otherwise lacks for its most important variable.

### 4.3 Derived fields

Open-Meteo documents that cloud cover is estimated from relative humidity via the
Sundqvist et al. (1989) scheme for models lacking a native cloud field. Where
irradiance components are similarly derived rather than natively modelled, skill
figures describe the derivation as much as the forecast. Native versus derived
status is checked per variable per model and reported.

---

## 5. Location

Barbados, 13.19°N, 59.54°W. Where comparison against Grantley Adams is made, the
station coordinates are used: 13.073°N, 59.500°W.

**Declared limitation.** ERA5 resolves to approximately 31 km. Barbados is roughly
34 km by 23 km, so the island occupies one to two grid cells, a substantial
proportion of which is open ocean. The reanalysis series describes a maritime grid
cell containing Barbados rather than the island itself.

Consequences: sea-moderated temperature will be smoother than a land station
records; precipitation will be spatially averaged and will understate localised
convective rainfall.

**This limitation is measured rather than merely declared.** See §9.

Forecast models vary in resolution — ECMWF IFS HRES at approximately 9 km, global
models at 9–11 km. Where a forecast is finer than the verification dataset,
apparent error partly reflects the coarseness of the verification.

---

## 6. Forecast source and model selection

**`best_match` is not used.** Automatic model selection returns a blended result
with no stable provenance. A figure attributed to "Open-Meteo" is not actionable —
BL&P cannot procure it. Every result is attributed to a named model.

**Primary model: ECMWF IFS HRES**, approximately 9 km, archived by initialisation
time from 14 March 2024. Selected because it is the model a utility would most
plausibly procure, and because individual runs are preserved by exact
initialisation time, permitting operational backtesting without look-ahead bias.

**Secondary models** added only if the primary result justifies further work.

Every scored row preserves: provider · model · initialisation time · valid time ·
lead time · latitude · longitude · variable · units · forecast value ·
verification value.

Results are reported by model and lead time. No blended figure across models or
lead times is produced.

---

## 7. Persistence baseline

A forecast that cannot beat persistence is not useful.

**Definition.** For a valid time *t* and lead time *L*, the persistence forecast is
the verification value at *t − L*: assume conditions at issue time continue
unchanged.

Persistence is scored identically to the forecast, at every lead time, for every
variable.

**Skill score:**

    skill = 1 − (forecast error / persistence error)

Positive skill means the forecast adds information beyond assuming no change. Zero
or negative means it does not, and that variable at that lead time is reported as
not useful regardless of its absolute error.

---

## 8. Metrics

Per variable, per lead time, per model:

- **MAE** — mean absolute error, native units
- **RMSE** — root mean square error
- **Bias** — mean signed error, to distinguish systematic offset from noise
- **Correlation** where meaningful
- **Skill relative to persistence**

MAPE is not reported. Irradiance is zero overnight and precipitation is zero most
hours, which makes percentage error undefined or unstable for two of the six
variables.

Results are tabulated at every lead day from one to seven. **No single blended
skill number is produced.** Degradation with lead time is the finding, not an
inconvenience to be averaged away.

---

## 9. Verification-layer comparison

A secondary experiment, run before the forecast assessment because it establishes
how much confidence the primary verification layer warrants.

**ERA5 versus Grantley Adams observations**, over the overlapping window
(17 June – 24 September 2026), for the three variables present in both:
air temperature, cloud cover, precipitation.

**Purpose.** To quantify rather than merely assert the cost of using a 31 km
maritime grid cell in place of a land station. Reported as MAE, RMSE, bias and
correlation per variable.

**Expected outcome, recorded in advance.** Temperature to agree reasonably, as sea
moderation affects both. Precipitation to diverge substantially, as convective
rainfall is localised and the grid cell averages it away. Cloud cover between the
two.

**Limitation.** Approximately 99 days is adequate to characterise systematic bias.
It is not adequate to draw seasonal conclusions, and none are drawn.

---

## 10. Operational assessment

Skill alone does not answer whether a source is usable in production. Established
and reported for each candidate:

- **Point-in-time correctness** — whether the archive preserves what was issued at
  the time, or has been re-run with the benefit of hindsight. A backtest against
  revised history overstates skill and fails in production.
- **Forecast horizon and update frequency**
- **Latency** — how soon after initialisation output is available
- **Rate limits and licence terms**, specifically whether operational use is
  permitted. Free tiers are typically non-commercial and capped.
- **Notice of model version changes** — a silent substitution breaks a live
  forecast
- **Uptime and support commitment**

A source with adequate skill and inadequate operational terms is reported as such,
not recommended on skill alone.

---

## 11. Exclusion rules

Recorded in advance so that no record is discarded after its effect on the result
is known.

- Observations flagged as missing or null by the source are excluded, and the
  count reported per variable
- A forecast–verification pair is excluded where either side is absent
- Records are not excluded on the basis of being outliers. Extreme values are
  retained; where they materially affect a result, that is reported rather than
  removed
- Where a station reports intermittently, periods of absence are reported as
  coverage rather than silently reducing the sample
- No record is excluded after results are computed. Any exclusion applied
  retrospectively is recorded as a dated amendment with its reason

---

## 12. Pre-registered expectations

Recorded before forecast data acquisition so that results cannot be presented as
having confirmed expectations formed afterwards:

- Temperature is expected to forecast well, degrading modestly with lead time
- Precipitation is expected to forecast poorly at all lead times
- Irradiance is expected to sit between the two, and to degrade faster than
  temperature, because it is cloud-driven
- Cloud cover is expected to be the weakest of the four
- Persistence is expected to be beaten comfortably for temperature at all lead
  times, and to be competitive for precipitation

**If irradiance skill proves inadequate, that is a material finding for a grid
with substantial embedded solar, and it is reported as such. A negative result is
a valid outcome of this assessment and is worth having before a build commitment,
not after.**

---

## 13. Deliverables

1. Data inventory — sources, coordinates, models, archive periods, variables,
   resolution, horizons, initialisation times, licensing
2. Timestamp convention table, verified before scoring
3. Verification-layer comparison — ERA5 against Grantley Adams (§9)
4. Forecast backtest — skill curves at lead days one through seven
5. Persistence benchmark at every lead time
6. Error metrics — MAE, RMSE, bias, correlation, skill
7. Operational assessment per §10
8. Recommendation — at each lead time, which source, model and variable carries
   sufficient skill to justify testing as a load-forecast input

The recommendation is not "provider X is good." It is variable-specific and
lead-time-specific, because the answer will differ between temperature and
irradiance, and at one day versus seven.

---

## 14. What this assessment does not establish

- It does not build or evaluate a Barbados load forecasting model
- It does not use BL&P operational data, which has not been provided
- It does not verify irradiance against local observation, which SYNOP does not
  carry (§4.2)
- It does not establish what Barbados Meteorological Services holds beyond the
  rolling window its WIS 2.0 node exposes
- It does not establish that improved weather input improves load forecast
  accuracy for Barbados. That is a subsequent question, answerable only with
  Barbados load history

---

## Attribution

Barbados Meteorological Services observations: CC BY 4.0.
Open-Meteo forecast and reanalysis data: CC BY 4.0.

---

*Frozen before forecast data acquisition. Changes after this point are recorded as
dated amendments with reasons, not silent edits.*
