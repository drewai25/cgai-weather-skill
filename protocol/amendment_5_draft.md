## Amendment 5 — scoring definitions (DRAFT, not yet in force)

**Status:** proposed 29 September 2026. Nothing in this amendment is binding
until signed off. No scoring code is written before it is.

**Why this exists.** Amendment 4 came out of one undefined word. "Available"
was never given a meaning, so in practice it meant "at least one hour", and
that silently produced wrong window start dates for two days. Six words in
the scoring layer are in the same position right now. They are defined here
before any code can quietly pick a meaning for them.

---

### A5.1 Forecast completeness across the window

A4.1 defined completeness at the archive boundary only. It says nothing about
gaps in the middle of the window.

    day_complete(model, variable, lead, day)
        := all 24 hourly forecast values for that day are present and non-null

    coverage(model, variable, lead)
        := complete days / total days in that cell's effective window

A cell is **reportable** iff coverage >= 0.90. This reuses the 90% figure
Amendment 3 fixed for observations, so one number governs both sides of the
join rather than two that can drift apart.

A cell below 0.90 is reported as **insufficient coverage, with its actual
percentage**. It is never scored on the days that remain and presented beside
cells that met the bar.

Coverage is printed next to every score in every table. A skill number
without its coverage is not a result.

---

### A5.2 Daylight hours for irradiance scoring

Scoring irradiance across all 24 hours inflates apparent skill: half the
values are zero at night and every model gets them right.

    daylight_hour(h) := solar elevation at the midpoint of hour h exceeds 5 degrees

Solar position is computed for 13.07333 N, 59.5 W using the NOAA solar
position equations, implemented in this repository and unit-tested against
three published reference values before first use.

5 degrees rather than 0 because at very low sun the relative errors explode
and clear-sky models are least reliable, so the lowest hours would dominate a
percentage metric while carrying almost no energy.

**Both versions are reported** — daylight-restricted and all-hours. The
restriction is a defensible choice, not a fact, and Roger should be able to
see what it did.

**Open item before sign-off.** Open-Meteo's hourly irradiance is documented as
a preceding-hour mean, not an instantaneous value. If so, the hour labelled
14:00 covers 13:00-14:00 and its midpoint is 13:30. This must be read off the
API documentation per variable and recorded in A5.5, not assumed. Getting it
wrong shifts every irradiance value by half an hour against the reference.

---

### A5.3 Clear-sky model

Required by A3.4, which sets smart persistence on the clear-sky index as the
irradiance baseline. A3.4 does not say which clear-sky model.

    clear-sky index  k(h) := GHI(h) / GHI_clearsky(h)

**Model: Haurwitz.**

    GHI_clearsky = 1098 * cos(z) * exp(-0.059 / cos(z))     W/m2

where z is the solar zenith angle at the hour's midpoint per A5.2.

Chosen because it needs only solar geometry — no turbidity climatology, no
external data file, no dependency this repository cannot reproduce from
stdlib. Its job here is to be a consistent normaliser for a baseline, not an
accurate irradiance estimate, and for that a fully auditable formula beats a
better one with an unverifiable input.

Rules:
- k is computed only for daylight hours per A5.2. Undefined elsewhere.
- k is **not clipped at 1.0**. Cloud enhancement genuinely produces k > 1 and
  clipping it would hide a real physical effect.
- **Constant verified 2 October 2026.** pvlib's reference implementation
  (pvlib.clearsky.haurwitz) reads
  `clearsky_GHI = 1098.0 * cos_zenith * np.exp(-0.059/cos_zenith)`,
  identical to the formula above in both coefficient and exponent. Primary
  sources cited there: B. Haurwitz, "Insolation in Relation to Cloudiness and
  Cloud Density", Journal of Meteorology 2, 154-166, 1945; B. Haurwitz,
  "Insolation in Relation to Cloud Type", Journal of Meteorology 3, 123-124,
  1946; M. Reno, C. Hansen and J. Stein, "Global Horizontal Irradiance Clear
  Sky Models: Implementation and Analysis", Sandia SAND2012-2389, 2012.
  pvlib is NOT a dependency of this project; the formula is implemented here
  in stdlib and the citation is the provenance.

**Sensitivity check, if time allows:** recompute the baseline with Ineichen-
Perez at a fixed Linke turbidity and report whether the model ranking changes.
If it does, the choice of clear-sky model is a finding in its own right.

---

### A5.4 Missing-hour join rule

- Forecast and reference are joined **inner, on valid_time**.
- A pair is scored iff **both sides are present and non-null**.
- **No imputation and no interpolation, on either side, ever.** Filling a gap
  and then scoring it measures the filler.
- For any daily aggregate (daily rainfall total, daily maximum temperature),
  the whole day is dropped if **any** contributing hour is missing on either
  side. A partial sum biases a total downward and a partial maximum biases it
  the same way; both would look like forecast error.
- Every metric is reported with **n pairs scored and n pairs dropped**.
- A metric computed on fewer than 200 hourly pairs, or fewer than 30 daily
  values, is reported as insufficient rather than scored.

---

### A5.5 Timezone and hour-labelling convention

**Storage and joining: UTC, end to end.** The fetch already requests
timezone=UTC. Every observational reference is converted to UTC before the
join, and each source's native timezone is recorded alongside its data.

**Daily aggregation boundaries: local time, AST = UTC-4, no DST.** The day
that matters to BL&P is the local day. Local-day boundaries are applied by
shifting UTC timestamps, never by re-fetching in a local timezone.

Both are stated because silently mixing them is the standard way this goes
wrong, and a rainfall total assigned to the wrong day is indistinguishable
from a forecast miss.

**Hour labelling** must be recorded per variable per source before scoring,
from documentation, not inference:

| variable | expected convention | verified |
|---|---|---|
| temperature_2m | instantaneous at label | NO |
| precipitation | sum over preceding hour | NO |
| shortwave_radiation | mean over preceding hour | NO |
| cloud_cover | instantaneous at label | NO |

A mismatch here is a systematic one-hour or half-hour offset that would be
scored as forecast error.

---

### A5.6 Rainfall event thresholds

A3.5 requires categorical rainfall metrics "against a stated threshold". The
threshold has never been stated.

**Hourly** (accumulation over one hour):

| threshold | meaning |
|---|---|
| >= 0.1 mm/h | any measurable rain |
| >= 1.0 mm/h | meaningful rain |
| >= 5.0 mm/h | heavy rain — operationally relevant to load and to faults |

**Daily** (accumulation over one AST day per A5.5):

| threshold | meaning |
|---|---|
| >= 1.0 mm | a wet day |
| >= 10.0 mm | a substantially wet day |
| >= 25.0 mm | a heavy-rain day |

**All thresholds are reported. There is no headline threshold.** Skill varies
strongly with threshold, and reporting one number invites picking the
flattering one. Any gate threshold set later must name which of these it
applies to.

Reported at each threshold: hit rate (POD), false alarm ratio (FAR),
frequency bias, **and the base rate**. A rare-event score without its base
rate cannot be read.

**Open item before sign-off.** A tipping-bucket gauge typically resolves in
0.2 mm increments. If the reference gauge does, the 0.1 mm threshold sits
below its resolution and must be raised to 0.2 mm. Check the instrument
specification for whichever gauge becomes the reference.

---

### A5.7 Standard 9 is not measurable as written

Standard 9 requires a comparison the available record cannot support. The BMS
record covers approximately 99 days and contains no radiation measurement at
all.

This is recorded, not worked around. What can be measured in its place is
stated when the reference sources are finalised. The protocol does not carry
a standard that will be quietly skipped.

---

### A5.8 ECMWF product correction

§3.2, §5 and §6 name ECMWF IFS HRES at 9 km. **That product is not available
through Open-Meteo.** Established three ways: rejected with HTTP 400 on both
endpoints; Open-Meteo's own EcmwfDomain.swift defines only ifs04, ifs025,
wam025, aifs025 and ensembles; their documentation lists it on two pages
regardless.

This affects the model selection agreed on 24 September.

**Resolution:** IFS 0.25 (25 km) as primary, with ICON (11 km) and GFS 0.11
degree (~13 km) scored alongside, so that whether resolution is the binding
constraint becomes a measured result rather than a procurement assumption.

§3.2, §5 and §6 are amended accordingly.

---

### A5.9 Irradiance is not sourced from BL&P

Per Tunde Mottley, 28 September 2026. Recorded so the sourcing decision has a
written origin rather than living in a meeting.

---

### A5.10 Partial-day hours: retained at fetch, excluded at scoring

The fetch keeps every hour the archive returns, including the partial
boundary days (ECMWF 2 h, GFS 12 h, GEM 14 h, ICON 12 h). Scoring excludes
them through A5.1, which requires 24 of 24.

The distinction is deliberate: the raw data stays complete and auditable, and
the exclusion happens at one defined point that can be inspected and changed
without re-fetching.

---

### A5.11 Cloud cover cannot be scored absolutely against ERA5

The measured bias between ERA5 cloud cover and the observational reference is
16.5 percentage points. Against a reference carrying a bias that size, an
absolute cloud-cover skill number would mostly measure the reference.

Cloud cover is therefore used for **relative model ranking only**, and no
absolute cloud skill figure is reported. Whether even the ranking survives
that bias is stated with the result.

The 16.5 pp figure must be re-derived from its artifact and cited by file
before sign-off.

---

### Sign-off

| item | signed | date |
|---|---|---|
| A5.1 forecast completeness | | |
| A5.2 daylight hours | | |
| A5.3 clear-sky model | | |
| A5.4 missing-hour join | | |
| A5.5 timezone and labelling | | |
| A5.6 rainfall thresholds | | |
| A5.7 standard 9 | | |
| A5.8 ECMWF product | | |
| A5.9 irradiance sourcing | | |
| A5.10 partial days | | |
| A5.11 cloud cover | | |

Three open items must be closed before sign-off, all marked above:
1. Hour-labelling convention per variable, from documentation (A5.5)
2. Haurwitz constant checked against source (A5.3) -- CLOSED 2 Oct 2026
3. Gauge resolution checked against the 0.1 mm threshold (A5.6)
