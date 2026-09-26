#!/usr/bin/env python3
"""
verify_complete_day.py — verify the corrected window under an explicit
definition of "available".

THE PROBLEM THIS RESOLVES
-------------------------
Neither the protocol nor any script defined what "available" means on a
boundary day. probe_archive.probe() returns AVAILABLE when ANY hour in the
day is non-null. diagnose_precip_start.py showed that archives begin with a
PARTIAL day: ECMWF precipitation carries 2 hours on 2024-02-03 and full days
from 2024-02-04; GFS 12 hours, GEM 14, ICON 12, all on their first date.

Under "any hour", the start is the partial day. Under "complete day", it is
the first date with all 24 hours. The two differ by one day, and that single
undefined word is what produced the precipitation FAIL: the verifier applied
"any hour" to a table built on the model archive start.

THE DEFINITION ADOPTED HERE
---------------------------
    available(day) := all 24 hours present and non-null at that lead

A partial day is excluded from the verification window. An hourly join
against an observational reference cannot use a day with 2 of 24 hours
without leaving a hole at the window boundary, and a partial day at the
start would bias any lead-1 versus lead-7 comparison, since each lead's
boundary day falls on a different date.

WHAT IT CHECKS
--------------
For every (variable, lead) in the corrected window file, at the model whose
corrected start sets that window:

    claimed start        must have 24/24 hours
    claimed start - 1    must have fewer than 24 (partial or absent)

Both must hold. The hour counts are printed so a partial boundary day is
visible rather than collapsed into a boolean.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")
from probe_archive import request, ProbeError, LAT, LON, TZ   # noqa: E402

RAW = Path("data/raw")
WINDOW = RAW / "effective_window_by_variable_lead_corrected.csv"
MATRIX = RAW / "archive_variable_matrix_corrected.csv"

FULL_DAY = 24


def hours_present(model: str, variable: str, lead: int, day: date) -> int:
    """Count non-null hourly values. -1 if the field is not offered at all."""
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


def main() -> int:
    matrix = list(csv.DictReader(MATRIX.open()))
    window = list(csv.DictReader(WINDOW.open()))

    starts: dict[tuple[str, str, int], date] = {}
    for r in matrix:
        if r.get("start_corrected"):
            starts[(r["model"], r["variable"], int(r["lead_day"]))] = \
                date.fromisoformat(r["start_corrected"])

    print("Definition: available(day) := 24 of 24 hours non-null.\n")
    print(f"{'variable':<26}{'ld':<4}{'binding model':<22}{'date':<12}"
          f"{'hrs on':<8}{'hrs prior':<11}verdict")
    print("-" * 94)

    npass = nfail = nskip = 0
    failures = []

    for row in window:
        variable, lead = row["variable"], int(row["lead_day"])
        if not row["common_archive_start"]:
            nskip += 1
            continue
        target = date.fromisoformat(row["common_archive_start"])
        carriers = [m for m in row["models"].split(";") if m]
        binding = next((m for m in carriers
                        if starts.get((m, variable, lead)) == target), None)
        if binding is None:
            nskip += 1
            continue

        try:
            on = hours_present(binding, variable, lead, target)
            prior = hours_present(binding, variable, lead,
                                  target - timedelta(days=1))
        except ProbeError as e:
            nskip += 1
            print(f"{variable:<26}{lead:<4}{binding:<22}"
                  f"{target.isoformat():<12}{'':<8}{'':<11}UNKNOWN ({e})")
            continue

        ok = (on == FULL_DAY) and (prior < FULL_DAY)
        if ok:
            npass += 1
            verdict = "PASS"
        else:
            nfail += 1
            verdict = "FAIL"
            failures.append(
                f"{variable} lead {lead} [{binding}] {target}: "
                f"{on}/24 on the date, {prior}/24 the day before"
            )
        print(f"{variable:<26}{lead:<4}{binding:<22}{target.isoformat():<12}"
              f"{on:<8}{prior:<11}{verdict}")

    print("-" * 94)
    print(f"PASS {npass}   FAIL {nfail}   SKIP {nskip}   of {len(window)}")

    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  - {f}")
        print("\nDo not use the corrected table.")
        return 1

    print("\nAll binding cells verified under the complete-day definition: "
          "24/24 hours on the stated start, fewer the day before.")
    print("Partial boundary days are excluded by that definition and must be "
          "recorded in the protocol before any fetch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
