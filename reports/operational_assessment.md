# Operational assessment of candidate forecast sources

Standards 1, 7 and 8 of the nine set out by Mottley Consulting, 22 September
2026. Findings established by inspection of vendor documentation on
26 September 2026. Sources and retrieval date are given for each claim;
anything not published by the vendor is recorded as unverified rather than
inferred.

Standards 2, 4 and 5 were established by measurement and are reported in
`archive_window_finding.md` and Amendment 4. Standards 3 and 6 require the
fetch and are not addressed here.

## Standard 1 — provenance and point-in-time correctness

**Open-Meteo Previous Runs API: satisfied, with one open question.**

The documentation states that `<variable>_previous_day1` is "the value that was
predicted 24 hours before valid time", with `_previous_day0` being the current
run. Values are the forecast as issued, not a re-run benefiting from hindsight.

Stated archive depths: most models from January 2024; GFS 2 m temperature from
March 2021; JMA GSM and MSM from 2018.

These agree with what was measured independently on 26 September before the
documentation was consulted: the archive-wide widening at 2024-01-18, GFS
temperature from 2021-03-23, and JMA earlier than the 2021-01-01 search floor.
Measurement and vendor documentation corroborate each other.

**Open:** the documentation does not state whether archived values are ever
revised or backfilled after issuance. To be put to Open-Meteo directly. Until
answered, point-in-time correctness is established for what the archive
contains, not for whether its contents can change.

Source: https://open-meteo.com/en/docs/previous-runs-api (26 Sep 2026)

## Standard 7 — licence for operational use

| Source | Free tier | Commercial terms |
|---|---|---|
| Open-Meteo | CC BY 4.0, **non-commercial only**; 600/min, 5,000/hr, 10,000/day, 300,000/month | Standard, Professional and Enterprise tiers exist. **Prices not published**; volume and enterprise contracts by email. |
| Weatherbit | 50 requests/day, non-commercial, **no historical access** | All paid tiers carry a commercial licence. Historical: 5 years at Plus, 30 years at Business. Prices not displayed. |
| Solcast | 15 historic site-months and 10 live/forecast requests | Tiered by update frequency (6-hourly, 15-minute, 5-minute). Prices not published. |
| Barbados Met Services | CC BY 4.0, attribution, public, no registration | Not applicable — observations, not a forecast product. |
| Barbados Cloud Observatory | Public catalogue, no key | **Unresolved.** See below. |

**The assessment is not blocked by any of this.** The probe of 26 September
issued one request per day deliberately, to test individual days. A production
fetch requests date ranges and multiple variables per call, putting the whole
assessment on the order of tens of requests, well inside the free tier. The
assessment is non-commercial research and is covered.

The commercial question arises at deployment, not now. It should be separated
from assessment scope so it does not read as a present blocker.

Sources: https://open-meteo.com/en/pricing, https://www.weatherbit.io/pricing,
https://solcast.com/pricing (all 26 Sep 2026)

## Standard 8 — delivery guarantees

| Source | Uptime | Model-version change notice |
|---|---|---|
| Open-Meteo | **No guarantee on free tier.** Paid: 99.9% target on reserved instances; status.open-meteo.com | Not published |
| Weatherbit | 95% free, 99.5% Standard to Business, >99.5% Enterprise | Not published |
| Solcast | SLA available as a paid add-on; no figure published | Not published |

**None of the three publishes a notice policy on model version changes.** That
is the specific risk raised in standard 8 — a silent model substitution breaks
a live forecast — and it is unaddressed by every candidate. It should be raised
directly with whichever source is selected, and recorded as a residual risk if
no commitment is obtainable.

## Barbados Cloud Observatory licence — corroboration of A3.8

Amendment 3 §A3.8 records the licence as unconfirmed, noting CC0 has been
stated but is not declared in the catalogue or dataset attributes.

Independent check on 26 September of all three MPI-operated pages found **no
licence statement of any kind**. The TCO data site carries only
"© Copyright 2023, MPIM / TCO group" — a copyright assertion, not an open
licence. No terms of use, no citation requirement, no data-use agreement.

A3.8 is therefore corroborated rather than merely cautious. Open access to the
catalogue is confirmed; the licence is not. The publication hold in A3.8
stands.

Two points of detail confirmed against MPI's own pages: the radiation
instruments (pyranometer, pyrgeometer, pyrheliometer) date from April 2015, and
the catalogue endpoint remains `https://tcodata.mpimet.mpg.de/catalog.yaml`,
which is what MPI's current documentation points to.

Sources: https://tco-fa2774.gitlab-pages.dkrz.de/intro.html,
https://wiki.mpimet.mpg.de/doku.php?id=observations:bco:start,
https://mpimet.mpg.de/en/research/observations/barbados-cloud-observatory
(all 26 Sep 2026)

## Summary against the nine standards

| # | Standard | Status |
|---|---|---|
| 1 | Provenance, point-in-time | Satisfied; revision policy open |
| 2 | Horizon and resolution | Measured. Meteo-France fails (3 days), ICON fails (6 days) |
| 3 | Lead-time skill measured | Pending the fetch |
| 4 | Variable coverage, GHI/DNI/DHI separate | Measured. JMA fails (no irradiance) |
| 5 | Historical depth, 2-3 years | Measured. 932-970 days, 2.55-2.66 years. Satisfied |
| 6 | Spatial suitability | Pending the fetch |
| 7 | Licence for operational use | Established. Assessment covered; deployment requires paid terms |
| 8 | Delivery guarantees | Established. Version-change notice unpublished by all three |
| 9 | Independent verification | Layers in place: BCO irradiance, BMS SYNOP. Pending the fetch |

Standards 2 and 4 together leave ECMWF IFS, GFS and GEM as the models
satisfying both at all seven lead days — the same three the window measurement
returned as carriers at lead 7, established independently.
