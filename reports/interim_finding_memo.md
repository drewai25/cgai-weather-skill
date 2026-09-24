# Interim Finding — Verification Layer Quality
## Barbados Weather Forecast Skill Assessment

**To:** Tunde Mottley, Mottley Consulting Inc.
**From:** Andrew Narine, CaribbeanGridAI
**Date:** 24 September 2026
**Status:** Interim. The forecast skill assessment is in progress; this reports a
prerequisite finding that affects how its results must be read.

---

## Summary

Before measuring how accurate forecasts are, we need to know how accurate our
measuring stick is. This memo reports that check.

**Temperature verification is sound.** ERA5 reanalysis tracks the Grantley Adams
station closely — 0.58 degC mean absolute error, correlation 0.89, negligible
bias.

**Cloud cover verification is not.** ERA5 reads 16.5 percentage points clearer
than the station on average, with 26 points of mean absolute error and
correlation of only 0.54.

That second result matters more than it might appear. Cloud drives solar
irradiance. Irradiance is the variable BL&P most needs for a grid with
approximately 100 MW of embedded photovoltaic generation. And irradiance is the
one variable we cannot verify against local observation, because the station does
not measure it.

So the forecast skill figures for irradiance will carry an uncertainty we can
describe but not eliminate — unless BL&P can supply local irradiance measurements.

---

## What was done

The BMS WIS 2.0 node at barbadosweatherdata.org publishes hourly surface
observations from Grantley Adams under CC BY 4.0. Contrary to an earlier
assumption, no formal data request is required; the API is public.

Retrieved and compared against ERA5 reanalysis for the same coordinates and
period:

| | |
|---|---|
| Station | Grantley Adams, WIGOS 0-52-130-78954 |
| Window | 17 June to 24 September 2026 |
| Matched hours | 2,386 |
| Coverage | Complete. No missing hours, no gaps in either variable. |

ERA5 resolves to approximately 31 km. The grid cell returned sits at 13.111N
59.508W, about 4 km north of the station, at 52 m elevation against the station's
58 m.

---

## Results

Bias is ERA5 minus observation. Positive means ERA5 reads high.

| Variable | n | MAE | RMSE | Bias | Corr | Obs mean | ERA5 mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Temperature (degC) | 2,386 | 0.58 | 0.80 | +0.08 | 0.89 | 27.8 | 27.9 |
| Cloud cover (%) | 2,386 | 26.20 | 33.15 | -16.54 | 0.54 | 69.9 | 53.4 |
| Precipitation 6h (mm) | 336 | 1.93 | 11.23 | -0.55 | 0.26 | 1.56 | 1.01 |
| Precipitation 12h (mm) | 29 | 1.79 | 3.50 | -0.78 | 0.70 | 2.38 | 1.60 |
| Precipitation pooled | 365 | 1.92 | 10.82 | -0.57 | 0.27 | 1.62 | 1.05 |

### Temperature

Agreement is good and the bias is negligible. Sea moderation affects both the
island and the surrounding grid cell similarly, which is the likely explanation.
Temperature forecast skill measured against ERA5 can be reported with confidence.

### Cloud cover

The systematic under-reading is the significant result. A 16.5-point bias across
2,386 hours is not noise; ERA5 consistently sees less cloud over this grid cell
than the station records over the island.

Convective cloud forms preferentially over land as the surface heats. A cell that
is largely ocean will not reproduce that. The direction of the bias is consistent
with this explanation.

### Precipitation

MAE of 1.9 mm against RMSE of 11.2 indicates that most error comes from a small
number of large events — localised downpours the grid cell averages away.
Correlation is 0.26 for six-hour accumulations.

The twelve-hour accumulations correlate considerably better at 0.70, consistent
with longer windows smoothing the spatial mismatch. The sample is small (29) and
that reading should be treated as indicative.

---

## What this means for the assessment

**Temperature.** Proceed. ERA5 is an adequate verification layer.

**Cloud and irradiance.** Skill figures verified against ERA5 must be qualified.
We can state forecast error against reanalysis; we cannot state forecast error
against what a pyranometer on the island would have recorded.

The gap is not small. If ERA5 under-reads cloud by 16 points, its irradiance is
correspondingly optimistic, and a forecast scored against it inherits that.

**Precipitation.** Reportable, with the caveat that extreme events are the
dominant error source and the grid cell cannot resolve them.

---

## The ask for BL&P

One question, and it is a smaller ask than operational load data:

> Does BL&P hold, or can it obtain, irradiance measurements from any
> photovoltaic installation on the island?

Utility-scale PV sites are normally instrumented with pyranometers. A few months
of hourly GHI from any such site would let us verify forecast irradiance against
local measurement rather than against a reanalysis product we have now shown to
be biased on the driving variable.

Without it, the irradiance conclusion will be honest but qualified. With it, it
would be direct.

---

## Status and next step

The forecast skill assessment proceeds as designed: archived operational
forecasts, lead days one through seven, persistence baseline, no blended figures,
named models rather than automatic selection.

This finding does not delay it. It establishes how its results must be read.

Two protocol amendments were recorded during this work and are in the repository:
upper-air sounding records present in the surface collection and excluded by rule,
and precipitation accumulation intervals that are not uniformly six hours.

---

*Barbados Meteorological Services observations and ERA5 data via Open-Meteo, both
CC BY 4.0.*
