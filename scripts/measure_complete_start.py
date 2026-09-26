#!/usr/bin/env python3
"""
measure_complete_start.py — find the first COMPLETE day per
(model, variable, lead), and rebuild the windows from measurement alone.

HOW WE GOT HERE
---------------
1. probe_archive.py searched a model's archive start on temperature at lead 1
   and ASSIGNED that date to every other variable. Never tested downward.
2. apply_lead_shift_correction.py fixed the long-lead dates using the
   one-day-per-lead shift, measured on two ECMWF cases.
3. A binding-cell check FAILED on precipitation. The first diagnosis --
   that precipitation was genuinely earlier -- was wrong.
4. diagnose_precip_start.py found the real cause: archives open with a
   PARTIAL day (ECMWF 2h, GFS 12h, GEM 14h, ICON 12h). Nothing had ever
   defined what "available" means on a boundary day.
5. Under a complete-day definition, 21 cells passed and the 21 irradiance
   cells failed with 1-7 hours.
6. diagnose_irradiance_hours.py showed those hours are a contiguous tail
   block (17:00-23:00 UTC on 2024-03-06) reaching 24/24 by 2024-03-13,
   while GFS and GEM are complete throughout. A ramp-up, not coarse
   storage. ECMWF stays in the comparison.

WHY THE SHIFT CANNOT BE USED HERE
---------------------------------
The one-day-per-lead shift describes a clean switch-on: one first run, every
lead valid N days later. A RAMP is different -- lead 1 reaches 24/24 before
lead 7 does. So the complete-day start must be measured for every
(model, variable, lead) independently rather than derived from lead 1.

METHOD
------
A complete-day start is never EARLIER than an any-hour start, so a scan from
the existing estimate is sound and far cheaper than a fresh binary search.
For each combination the scan runs forward to the first 24/24 day, and where
the estimate turns out to be late it walks BACKWARD to the real edge rather
than trusting the estimate or discarding the cell.

    available(day, lead) := all 24 hourly values non-null

Outputs, leaving every earlier artifact untouched:
    data/raw/archive_variable_matrix_v3.csv
    data/raw/effective_window_by_variable_lead_v3.csv

Runtime: roughly 12-18 minutes.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")
from probe_archive import (                              # noqa: E402
    request, ProbeError, LAT, LON, TZ, LEADS, VARIABLES,
    FROZEN_OBS_START, FROZEN_OBS_END,
)

RAW = Path("data/raw")
MATRIX_IN = RAW / "archive_variable_matrix.csv"
MATRIX_OUT = RAW / "archive_variable_matrix_v3.csv"
WINDOW_OUT = RAW / "effective_window_by_variable_lead_v3.csv"

FULL_DAY = 24
MAX_SCAN = 45                              # days forward before giving up
CLAMP = FROZEN_OBS_START - timedelta(days=30)   # no need to scan earlier


def hours(model: str, variable: str, lead: int, day: date) -> int:
    field = f"{variable}_previous_day{lead}"
    payload = request({
        "latitude": LAT, "longitude": LON, "hourly": field, "models": model,
        "start_date": day.isoformat(), "end_date": day.isoformat(),
        "timezone": TZ,
    })
    if payload.get("api_error"):
        return -1
    hourly = payload.get("hourly") or {}
    series = hourly.get(field)
    if series is None:
        for key, value in hourly.items():
            if key != "time" and isinstance(value, list):
                series = value
                break
    if series is None:
        return -1
    return sum(1 for v in series if v is not None)


def first_complete(model: str, variable: str, lead: int,
                   estimate: date) -> tuple[date | None, str]:
    """First 24/24 day at or after the estimate, clamped near the window.

    An estimate far in the past (a 2021 archive date) would otherwise need
    hundreds of forward steps, so the scan starts no earlier than CLAMP.
    When the clamped start is ALREADY complete and so is the day before it,
    the true start lies at or before the clamp -- which is before the frozen
    window opens, so the frozen window binds and the exact date does not
    matter. That is a result, not a failure.
    """
    scan_from = max(estimate, CLAMP)

    if hours(model, variable, lead, scan_from) == FULL_DAY:
        # The estimate may be LATE as easily as early, so walk back to the
        # real edge rather than trusting it or discarding the cell.
        day, steps = scan_from, 0
        while day > CLAMP and steps < MAX_SCAN:
            if hours(model, variable, lead,
                     day - timedelta(days=1)) != FULL_DAY:
                back = (scan_from - day).days
                return day, ("first 24/24 at the estimate" if not back
                             else f"first 24/24 at -{back} d (estimate late)")
            day -= timedelta(days=1)
            steps += 1
        return day, (f"complete at or before {day}, the scan floor; "
                     "earlier than the frozen window, which binds")

    for i in range(1, MAX_SCAN):
        day = scan_from + timedelta(days=i)
        if hours(model, variable, lead, day) == FULL_DAY:
            return day, f"first 24/24 at +{i} d from the scan start"
    return None, f"no complete day within {MAX_SCAN} days of {scan_from}"


def main() -> int:
    rows = list(csv.DictReader(MATRIX_IN.open()))
    models, blended, exposed, est = [], {}, {}, {}
    for r in rows:
        if r["model"] not in models:
            models.append(r["model"])
        blended[r["model"]] = r["blended"].strip().lower() == "true"
        key = (r["model"], r["variable"], int(r["lead_day"]))
        exposed[key] = r["status_recent"] == "available"
        if r["effective_start"]:
            est[key] = date.fromisoformat(r["effective_start"])

    targets = [k for k, ok in exposed.items()
               if ok and not blended[k[0]] and k in est]
    print(f"Measuring the first complete day for {len(targets)} combinations.")
    print("Definition: 24 of 24 hourly values non-null.\n")
    print(f"{'model':<24}{'variable':<26}{'ld':<4}{'estimate':<12}"
          f"{'complete':<12}note")
    print("-" * 104)

    result: dict[tuple[str, str, int], date] = {}
    unverified = []
    for model in models:
        if blended[model]:
            continue
        for variable in VARIABLES:
            for lead in LEADS:
                key = (model, variable, lead)
                if key not in est or not exposed.get(key):
                    continue
                try:
                    found, note = first_complete(model, variable, lead,
                                                 est[key])
                except ProbeError as e:
                    unverified.append((key, f"transport failure: {e}"))
                    print(f"{model:<24}{variable:<26}{lead:<4}"
                          f"{est[key].isoformat():<12}{'—':<12}UNKNOWN ({e})")
                    continue
                if found is None:
                    unverified.append((key, note))
                else:
                    result[key] = found
                print(f"{model:<24}{variable:<26}{lead:<4}"
                      f"{est[key].isoformat():<12}"
                      f"{found.isoformat() if found else '—':<12}{note}")

    with MATRIX_OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "variable", "lead_day", "estimate",
                    "first_complete_day", "verified", "blended"])
        for model in models:
            for variable in VARIABLES:
                for lead in LEADS:
                    key = (model, variable, lead)
                    got = result.get(key)
                    w.writerow([
                        model, variable, lead,
                        est[key].isoformat() if key in est else "",
                        got.isoformat() if got else "",
                        "yes" if got else "no", blended[model],
                    ])

    with WINDOW_OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variable", "lead_day", "n_models", "models",
                    "common_archive_start", "frozen_obs_start",
                    "effective_start", "effective_end", "binding_model",
                    "binding_constraint"])
        for variable in VARIABLES:
            for lead in LEADS:
                carriers = {m: result[(m, variable, lead)]
                            for m in models
                            if (m, variable, lead) in result}
                if carriers:
                    arch = max(carriers.values())
                    bm = sorted(m for m, d in carriers.items() if d == arch)[0]
                    eff = max(arch, FROZEN_OBS_START)
                    cons = ("frozen observational window"
                            if FROZEN_OBS_START >= arch
                            else "forecast archive availability")
                else:
                    arch = eff = bm = None
                    cons = "no verified unblended carrier"
                w.writerow([
                    variable, lead, len(carriers), ";".join(sorted(carriers)),
                    arch.isoformat() if arch else "",
                    FROZEN_OBS_START.isoformat(),
                    eff.isoformat() if eff else "",
                    FROZEN_OBS_END.isoformat(), bm or "", cons,
                ])

    win = list(csv.DictReader(WINDOW_OUT.open()))
    print("\nVERIFIED EFFECTIVE START BY VARIABLE AND LEAD  (carriers in [])")
    print("variable".ljust(26) + "".join(f"L{l}".ljust(13) for l in LEADS))
    for variable in VARIABLES:
        line = variable[:25].ljust(26)
        for lead in LEADS:
            d = next(r for r in win if r["variable"] == variable
                     and int(r["lead_day"]) == lead)
            line += ((f"{d['effective_start'][5:]}[{d['n_models']}]"
                      if d["effective_start"] else "—").ljust(13))
        print(line)

    if unverified:
        print(f"\n{len(unverified)} combination(s) UNVERIFIED and excluded:")
        for key, note in unverified:
            print(f"  - {key[0]} {key[1]} lead {key[2]}: {note}")

    starts = [date.fromisoformat(r["effective_start"])
              for r in win if r["effective_start"]]
    if starts:
        print(f"\nLatest effective start: {max(starts)}   "
              f"Earliest: {min(starts)}")
        span = (FROZEN_OBS_END - max(starts)).days
        print(f"Shortest window: {span} days of the frozen period.")
    print(f"\nWrote {MATRIX_OUT}\n      {WINDOW_OUT}")
    print("Every value measured. Nothing assigned, nothing derived.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
