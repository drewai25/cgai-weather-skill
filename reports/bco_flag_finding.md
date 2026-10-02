# Level 2 discards 224 days of valid GHI because a different sensor failed

**Found 2 October 2026.** Before any skill number exists.

## What Level 2 shows

`BCO.radiation` PT10M holds complete timestamp coverage across the frozen
window — 143,856 of 143,856 expected ten-minute records — but 24.1% of those
records carry `raw_count = 0` and NaN values. Hourly completeness at the 90%
bar is 16,435 of 23,976 hours (68.5%), and the shortfall is not seasonal: it
is two contiguous runs.

## What the flag says

`sw_dir_sensor_status` in Level 1 (`radiation_c2`) is 3 across exactly two
periods in the window, and 0 elsewhere:

    status 3   2024-03-13 .. 2024-05-02     50.5 days
    status 3   2024-10-14 .. 2025-04-06    173.1 days

Those two runs account for every zero and every degraded month in the Level 2
coverage table. March 2024 at 38% and October 2024 at 39% are the months the
flag begins mid-way; April 2025 at 71.4% is the month it lifts on the 6th.

## Why the flag is correct, and about what

On 2024-12-15, inside the second flagged run:

    SWD_dir     min 0.0   max 6165.2   mean 4546.0 W/m2

The solar constant is about 1361 W/m2 and surface DNI cannot exceed roughly
1100. A daily mean of 4546, including the middle of the night, is not a
measurement. The pyrheliometer was broken, and `sw_dir` names that sensor.

## Why the other sensors were not

On the same flagged day, GHI traces a textbook diurnal curve: zero overnight,
rising from 10:00 UTC, peaking 762 W/m2 hourly mean near solar noon, maximum
1121.6 W/m2 instantaneous.

Across both flagged runs against three unflagged controls, sampled at roughly
200,000 points each:

    period                    label      n        max   >1400  >1100  nan
    2024-03-13..2024-05-02    FLAGGED  208600   1489.8     11   2723    0
    2024-10-14..2025-04-06    FLAGGED  202408   1533.9      1    806    0
    2024-05-03..2024-10-14    clean    201818   1449.1      1   1134    0
    2025-04-07..2025-09-30    clean    201806   1606.2      5   1702    0
    2025-10-01..2026-03-31    clean    200308   1379.9      0    737    0

The highest maximum in the comparison, 1606.2 W/m2, occurs in a CLEAN period.
Values above clear-sky are consistent with cloud enhancement, which is common
in the trade-wind cumulus regime BCO exists to study, and they occur at
similar rates with and without the flag. The third control is deliberately
October to March so a seasonal difference cannot masquerade as an instrument
one.

## Conclusion

Level 2's documented QC drops values carrying a Level 1 anomaly flag. Applied
to `sw_dir_sensor_status`, it removes `sw_down_global` and `sw_down_diffuse`
as well — variables produced by the CMP21 pyranometers, not by the failed
CHP1 pyrheliometer. 224 days of global horizontal irradiance, the variable
this assessment requires, are discarded for a fault in an instrument that
does not measure it.

Those 224 days contain the entire 2024/25 dry season.

## What this does NOT establish

- Calibration. Gross failure is ruled out; a pyranometer reading 5% high
  would be indistinguishable from these results.
- Completeness of the test. Roughly 200,000 sampled points per period, not
  every sample. The diffuse channel was examined on one day only.
- That the data should be used. That is a methodological decision requiring
  sign-off, and it must be recorded before any skill number is computed.

## Reproduction

    scripts/bco_open.py            open the PT10M store directly
    scripts/bco_semantics.py       time_bounds and raw_count semantics
    scripts/bco_hourly_coverage.py hourly completeness, monthly table
    scripts/bco_outage_cause.py    Level 2 NaN confirmation
    scripts/bco_l1_slice.py        Level 1 presence during the outage
    scripts/bco_l1_shape.py        diurnal profiles, flagged vs clean
    scripts/bco_flag_extent.py     exact flag runs
    scripts/bco_ghi_control.py     the control above

Logs for each are in reports/ alongside this file.
