#!/usr/bin/env python3
"""
verify_lead_shift.py — test whether a variable's first available valid date
shifts by exactly one day per lead day.

Hypothesis (H): for a variable whose first archived run is date R, the first
valid date carrying previous_dayN data is R + N. If true, per-lead start dates
are one fact, not seven, and the on-time variables in archive_variable_matrix
.csv are reported optimistically at long leads because they were assigned the
model archive start rather than searched.

Two cases, one a positive control:
  ecmwf temperature_2m       on-time variable, starts were ASSIGNED  -> tests H
  ecmwf shortwave_radiation  late variable, starts were SEARCHED     -> control,
                             H already visible in the measured dates

Falsifiable: if implied_first_run is not constant across leads, H is wrong and
the per-lead dates must each be measured.
"""
import sys
from datetime import date, timedelta
sys.path.insert(0, "scripts")
from probe_archive import probe, AVAILABLE, LEADS   # reuse the probed layer

CASES = [
    ("ecmwf_ifs025", "temperature_2m",      date(2024, 2, 1),  12),
    ("ecmwf_ifs025", "shortwave_radiation", date(2024, 3, 3),  12),
]

for model, variable, scan_from, span in CASES:
    print(f"\n{'=' * 64}\n{model}  {variable}\n{'=' * 64}")
    print(f"{'lead':<6}{'first available':<18}{'implied first run':<20}")
    implied = []
    for lead in LEADS:
        found = None
        for i in range(span):
            day = scan_from + timedelta(days=i)
            if probe(model, variable, lead, day) == AVAILABLE:
                found = day
                break
        if found is None:
            print(f"{lead:<6}{'not found in scan':<18}{'—':<20}")
            continue
        run = found - timedelta(days=lead)
        implied.append(run)
        print(f"{lead:<6}{found.isoformat():<18}{run.isoformat():<20}")
    if implied:
        uniq = sorted(set(implied))
        if len(uniq) == 1:
            print(f"\nH HOLDS: single first-run date {uniq[0].isoformat()}, "
                  "constant across all leads found.")
        else:
            print(f"\nH FAILS: implied first-run dates differ -> "
                  f"{[d.isoformat() for d in uniq]}. Each lead must be measured.")
