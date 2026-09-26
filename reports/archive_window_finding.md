# Forecast archive availability finding

Probed 2026-09-26 at 13.07333, -59.5 (Grantley Adams reference point), Open-Meteo Previous Runs API.

## What this measures

Forecast-archive availability only. This is one input to the verification window, not the verification window itself:

```
verification window =
      Amendment 3 frozen observational window   (frozen, not touched here)
    ∩ forecast archive availability             (measured here)
    ∩ observational reference availability      (measured separately)
    ∩ completeness criteria, 90% threshold      (applied separately)
```

Frozen observational window, Amendment 3 §A3.1: **2024-01-01 to 2026-09-30**. Where the archive starts later, the frozen window is not redefined; both are reported and the binding constraint is named.

## Archive start by model

| Model | Archive start | Blended | Note |
|---|---|---|---|
| `best_match` | 2021-03-24 | yes | binary search, resolved to the day |
| `ecmwf_ifs025` | 2024-02-04 | no | binary search, resolved to the day |
| `gfs_seamless` | 2021-03-24 | no | binary search, resolved to the day |
| `icon_seamless` | 2024-01-19 | no | binary search, resolved to the day |
| `gem_seamless` | 2024-01-19 | no | binary search, resolved to the day |
| `meteofrance_seamless` | 2024-01-19 | no | binary search, resolved to the day |
| `jma_seamless` | 2021-01-01 | no | begins at or before the search floor |

Probed on `temperature_2m` at lead day 1. Individual variables may enter the archive later; that is resolved per variable below.

## Effective window by variable and lead day

This is the primary artifact. Amendment 3 requires skill curves per variable, per lead day, unblended, so each combination carries its own window. A gap in one combination does not discard the others.

| Variable | Lead | Models | Common archive start | Effective start | Binding constraint |
|---|---|---|---|---|---|
| `temperature_2m` | 1 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `temperature_2m` | 2 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `temperature_2m` | 3 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `temperature_2m` | 4 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `temperature_2m` | 5 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `temperature_2m` | 6 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `temperature_2m` | 7 | 4 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `precipitation` | 1 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `precipitation` | 2 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `precipitation` | 3 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `precipitation` | 4 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `precipitation` | 5 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `precipitation` | 6 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `precipitation` | 7 | 4 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `shortwave_radiation` | 1 | 5 | 2024-03-06 | 2024-03-06 | forecast archive availability |
| `shortwave_radiation` | 2 | 5 | 2024-03-07 | 2024-03-07 | forecast archive availability |
| `shortwave_radiation` | 3 | 5 | 2024-03-08 | 2024-03-08 | forecast archive availability |
| `shortwave_radiation` | 4 | 4 | 2024-03-09 | 2024-03-09 | forecast archive availability |
| `shortwave_radiation` | 5 | 4 | 2024-03-10 | 2024-03-10 | forecast archive availability |
| `shortwave_radiation` | 6 | 4 | 2024-03-11 | 2024-03-11 | forecast archive availability |
| `shortwave_radiation` | 7 | 3 | 2024-03-12 | 2024-03-12 | forecast archive availability |
| `direct_normal_irradiance` | 1 | 5 | 2024-03-06 | 2024-03-06 | forecast archive availability |
| `direct_normal_irradiance` | 2 | 5 | 2024-03-07 | 2024-03-07 | forecast archive availability |
| `direct_normal_irradiance` | 3 | 5 | 2024-03-08 | 2024-03-08 | forecast archive availability |
| `direct_normal_irradiance` | 4 | 4 | 2024-03-09 | 2024-03-09 | forecast archive availability |
| `direct_normal_irradiance` | 5 | 4 | 2024-03-10 | 2024-03-10 | forecast archive availability |
| `direct_normal_irradiance` | 6 | 4 | 2024-03-11 | 2024-03-11 | forecast archive availability |
| `direct_normal_irradiance` | 7 | 3 | 2024-03-12 | 2024-03-12 | forecast archive availability |
| `diffuse_radiation` | 1 | 5 | 2024-03-06 | 2024-03-06 | forecast archive availability |
| `diffuse_radiation` | 2 | 5 | 2024-03-07 | 2024-03-07 | forecast archive availability |
| `diffuse_radiation` | 3 | 5 | 2024-03-08 | 2024-03-08 | forecast archive availability |
| `diffuse_radiation` | 4 | 4 | 2024-03-09 | 2024-03-09 | forecast archive availability |
| `diffuse_radiation` | 5 | 4 | 2024-03-10 | 2024-03-10 | forecast archive availability |
| `diffuse_radiation` | 6 | 4 | 2024-03-11 | 2024-03-11 | forecast archive availability |
| `diffuse_radiation` | 7 | 3 | 2024-03-12 | 2024-03-12 | forecast archive availability |
| `cloud_cover` | 1 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `cloud_cover` | 2 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `cloud_cover` | 3 | 6 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `cloud_cover` | 4 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `cloud_cover` | 5 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `cloud_cover` | 6 | 5 | 2024-02-04 | 2024-02-04 | forecast archive availability |
| `cloud_cover` | 7 | 4 | 2024-02-04 | 2024-02-04 | forecast archive availability |

## Most-restrictive single window

Reported for completeness only. It is **not** the assessment window: collapsing to one window would let the weakest variable-lead combination shrink the usable sample for every other one.

- Latest common archive start across all covered combinations: **2024-03-12**
- Intersected with the frozen observational window: **2024-03-12 to 2026-09-30**
- Combinations with at least one unblended carrier: 42 of 42

## Caveats

- `best_match` is blended and excluded from the skill assessment per Amendment 3 §A3.9. Probed for documentation only and excluded from every window calculation above.
- `UNKNOWN` is a failed request, not an absent variable. Re-run before treating it as a gap.
- Non-null values on a probe date are an availability signal, not a completeness claim. Per-variable completeness across the window is measured separately at the 90% threshold fixed in Amendment 3.
- Availability was probed at two dates per combination, near the archive start and recently, with a binary search where the two disagree. Continuous availability between those points is not established here; the completeness pass measures it.
