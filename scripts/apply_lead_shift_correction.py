#!/usr/bin/env python3
"""
apply_lead_shift_correction.py — correct the assigned per-lead start dates.

WHY
---
probe_archive.py searched each lead individually for variables that entered
the archive after their model did, so those carry the correct one-day-per-lead
shift. Variables present from the model's archive start were ASSIGNED that
date at all seven leads without being searched, which reads optimistically at
long leads (ECMWF temperature at lead 7 recorded as 2024-02-04 when the true
first valid date is 2024-02-10).

The correction is not an inference. verify_lead_shift.py measured it on
ecmwf temperature (assigned case) and ecmwf shortwave (searched control),
and verify_lead_shift_2.py repeated it on gem and gfs. Both reported a
single first-run date constant across leads.

RULE
----
    first_run(model, variable) = measured_start_at_lowest_lead - that_lead
    corrected_start(lead)      = first_run + lead

PROVENANCE
----------
The raw probe output is never overwritten. Corrected values are written to
new *_corrected.csv files so the measurement and the correction stay
separately auditable.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

RAW = Path("data/raw")
MATRIX = RAW / "archive_variable_matrix.csv"
OUT_MATRIX = RAW / "archive_variable_matrix_corrected.csv"
OUT_WINDOW = RAW / "effective_window_by_variable_lead_corrected.csv"

FROZEN_OBS_START = date(2024, 1, 1)     # Amendment 3 §A3.1
FROZEN_OBS_END = date(2026, 9, 30)      # Amendment 3 §A3.1


def parse(s: str) -> date | None:
    return date.fromisoformat(s) if s else None


def main() -> int:
    rows = list(csv.DictReader(MATRIX.open()))
    if not rows:
        print("empty matrix; nothing to correct")
        return 1

    # ---- derive one first-run date per (model, variable) -------------------
    first_run: dict[tuple[str, str], date] = {}
    for r in rows:
        start = parse(r["effective_start"])
        if start is None:
            continue
        key = (r["model"], r["variable"])
        lead = int(r["lead_day"])
        candidate = start - timedelta(days=lead)
        # Lowest lead present wins; it is the least extrapolated.
        if key not in first_run or lead < first_run[key][1]:
            first_run[key] = (candidate, lead)
    first_run = {k: v[0] for k, v in first_run.items()}

    # ---- rewrite the matrix with corrected starts --------------------------
    variables, leads, models, blended = [], set(), [], {}
    for r in rows:
        if r["variable"] not in variables:
            variables.append(r["variable"])
        if r["model"] not in models:
            models.append(r["model"])
        leads.add(int(r["lead_day"]))
        blended[r["model"]] = r["blended"].strip().lower() == "true"
    leads = sorted(leads)

    corrected: dict[tuple[str, str, int], date | None] = {}
    changed = 0
    with OUT_MATRIX.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "variable", "lead_day", "status_recent",
                    "first_run", "start_as_probed", "start_corrected",
                    "shift_days", "blended"])
        for r in rows:
            key = (r["model"], r["variable"])
            lead = int(r["lead_day"])
            probed = parse(r["effective_start"])
            run = first_run.get(key)
            if probed is None or run is None:
                corrected[(r["model"], r["variable"], lead)] = None
                w.writerow([r["model"], r["variable"], lead,
                            r["status_recent"], "", "", "", "", r["blended"]])
                continue
            fixed = run + timedelta(days=lead)
            corrected[(r["model"], r["variable"], lead)] = fixed
            shift = (fixed - probed).days
            if shift:
                changed += 1
            w.writerow([r["model"], r["variable"], lead, r["status_recent"],
                        run.isoformat(), probed.isoformat(),
                        fixed.isoformat(), shift, r["blended"]])

    # ---- recompute the per (variable, lead) window -------------------------
    with OUT_WINDOW.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variable", "lead_day", "n_models", "models",
                    "common_archive_start", "frozen_obs_start",
                    "effective_start", "effective_end", "binding_constraint"])
        for variable in variables:
            for lead in leads:
                carriers = {
                    m: corrected[(m, variable, lead)]
                    for m in models
                    if not blended[m]
                    and corrected.get((m, variable, lead)) is not None
                }
                if carriers:
                    arch = max(carriers.values())
                    eff = max(arch, FROZEN_OBS_START)
                    binding = ("frozen observational window"
                               if FROZEN_OBS_START >= arch
                               else "forecast archive availability")
                else:
                    arch = eff = None
                    binding = "no unblended model carries this combination"
                w.writerow([
                    variable, lead, len(carriers), ";".join(sorted(carriers)),
                    arch.isoformat() if arch else "",
                    FROZEN_OBS_START.isoformat(),
                    eff.isoformat() if eff else "",
                    FROZEN_OBS_END.isoformat(), binding,
                ])

    # ---- print the corrected grid -----------------------------------------
    win = list(csv.DictReader(OUT_WINDOW.open()))
    print(f"Corrected {changed} of {len(rows)} matrix cells.\n")
    print("CORRECTED EFFECTIVE START BY VARIABLE AND LEAD  (carriers in [])")
    header = "variable".ljust(26) + "".join(f"L{l}".ljust(13) for l in leads)
    print(header)
    for variable in variables:
        line = variable[:25].ljust(26)
        for lead in leads:
            d = next(r for r in win
                     if r["variable"] == variable
                     and int(r["lead_day"]) == lead)
            cell = (f"{d['effective_start'][5:]}[{d['n_models']}]"
                    if d["effective_start"] else "—")
            line += cell.ljust(13)
        print(line)

    starts = [parse(r["effective_start"]) for r in win if r["effective_start"]]
    if starts:
        print(f"\nLatest effective start across combinations: {max(starts)}")
        print(f"Earliest:                                   {min(starts)}")
    print(f"\nWrote {OUT_MATRIX}\n      {OUT_WINDOW}")
    print("Raw probe output left untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
