#!/usr/bin/env python3
"""
measure_first_run.py — measure the true first archived run for every
(model, variable) pair, replacing the assumed values.

WHY THIS EXISTS
---------------
probe_archive.py binary-searched each model's archive start using
temperature_2m at lead 1, then ASSIGNED that date to every other variable
found present at the near-date. That assumption was never tested downward.

verify_binding_cells.py caught it: ECMWF precipitation is available the day
BEFORE its assigned start at all seven leads, so precipitation entered the
archive earlier than ECMWF temperature did. Temperature is correct because
it was the searched variable; cloud cover happens to share the date; nothing
guaranteed precipitation would.

The lead-shift correction is not at fault. The shift was measured on two
ECMWF cases and reconfirmed by the 35 CONFIRMED cells. What was wrong is the
first_run value the shift was applied to.

WHAT THIS DOES
--------------
Binary-searches lead 1 for every (model, variable) pair that the recent
probe found exposed, derives first_run = that date - 1, and rebuilds every
lead as first_run + lead. Nothing is assigned; every pair is measured.

Outputs (raw probe output and the v1 correction both left untouched):
    data/raw/archive_variable_matrix_v2.csv
    data/raw/effective_window_by_variable_lead_v2.csv

Runtime: roughly 8-12 minutes.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")
from probe_archive import (                              # noqa: E402
    binary_search_start, ProbeError, LEADS, VARIABLES,
    BLENDED, CEILING_BACKOFF, FROZEN_OBS_START, FROZEN_OBS_END,
)

RAW = Path("data/raw")
MATRIX_IN = RAW / "archive_variable_matrix.csv"          # raw probe output
MATRIX_OUT = RAW / "archive_variable_matrix_v2.csv"
WINDOW_OUT = RAW / "effective_window_by_variable_lead_v2.csv"

AVAILABLE_STATUS = "available"


def main() -> int:
    rows = list(csv.DictReader(MATRIX_IN.open()))
    if not rows:
        print(f"{MATRIX_IN} is empty")
        return 1

    models, blended, exposed = [], {}, {}
    prior_start = {}
    for r in rows:
        if r["model"] not in models:
            models.append(r["model"])
        blended[r["model"]] = r["blended"].strip().lower() == "true"
        key = (r["model"], r["variable"], int(r["lead_day"]))
        exposed[key] = r["status_recent"] == AVAILABLE_STATUS
        if r["effective_start"]:
            prior_start[key] = date.fromisoformat(r["effective_start"])

    ceiling = date.today() - timedelta(days=CEILING_BACKOFF)
    print(f"Measuring first archived run per (model, variable). "
          f"Ceiling {ceiling}.\n")
    print(f"{'model':<24}{'variable':<26}{'first run':<13}"
          f"{'was assumed':<13}{'delta'}")
    print("-" * 84)

    first_run: dict[tuple[str, str], date] = {}
    for model in models:
        for variable in VARIABLES:
            if not exposed.get((model, variable, 1)):
                continue
            try:
                found, _ = binary_search_start(model, variable, 1, ceiling)
            except ProbeError as e:
                print(f"{model:<24}{variable:<26}UNKNOWN ({e})")
                continue
            if found is None:
                print(f"{model:<24}{variable:<26}{'not found':<13}")
                continue
            run = found - timedelta(days=1)
            first_run[(model, variable)] = run
            was = prior_start.get((model, variable, 1))
            delta = (found - was).days if was else None
            print(f"{model:<24}{variable:<26}{run.isoformat():<13}"
                  f"{was.isoformat() if was else '—':<13}"
                  f"{'' if delta in (0, None) else f'{delta:+d} d'}")

    # ---- rebuild the matrix, every lead derived from a measured first run --
    with MATRIX_OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "variable", "lead_day", "status_recent",
                    "first_run", "start_measured", "method", "blended"])
        for model in models:
            for variable in VARIABLES:
                run = first_run.get((model, variable))
                for lead in LEADS:
                    if not exposed.get((model, variable, lead)) or run is None:
                        w.writerow([model, variable, lead, "not exposed",
                                    "", "", "not exposed at the recent probe",
                                    blended[model]])
                        continue
                    w.writerow([
                        model, variable, lead, AVAILABLE_STATUS,
                        run.isoformat(), (run + timedelta(days=lead)).isoformat(),
                        "first run measured by binary search at lead 1; "
                        "lead applied per verified shift",
                        blended[model],
                    ])

    # ---- recompute the per (variable, lead) window ------------------------
    with WINDOW_OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variable", "lead_day", "n_models", "models",
                    "common_archive_start", "frozen_obs_start",
                    "effective_start", "effective_end", "binding_model",
                    "binding_constraint"])
        for variable in VARIABLES:
            for lead in LEADS:
                carriers = {}
                for model in models:
                    if blended[model]:
                        continue
                    run = first_run.get((model, variable))
                    if run is None or not exposed.get((model, variable, lead)):
                        continue
                    carriers[model] = run + timedelta(days=lead)
                if carriers:
                    arch = max(carriers.values())
                    binding_model = sorted(
                        m for m, d in carriers.items() if d == arch)[0]
                    eff = max(arch, FROZEN_OBS_START)
                    constraint = ("frozen observational window"
                                  if FROZEN_OBS_START >= arch
                                  else "forecast archive availability")
                else:
                    arch = eff = binding_model = None
                    constraint = "no unblended model carries this combination"
                w.writerow([
                    variable, lead, len(carriers), ";".join(sorted(carriers)),
                    arch.isoformat() if arch else "",
                    FROZEN_OBS_START.isoformat(),
                    eff.isoformat() if eff else "",
                    FROZEN_OBS_END.isoformat(),
                    binding_model or "", constraint,
                ])

    # ---- print the grid ----------------------------------------------------
    win = list(csv.DictReader(WINDOW_OUT.open()))
    print("\nMEASURED EFFECTIVE START BY VARIABLE AND LEAD  (carriers in [])")
    print("variable".ljust(26) + "".join(f"L{l}".ljust(13) for l in LEADS))
    for variable in VARIABLES:
        line = variable[:25].ljust(26)
        for lead in LEADS:
            d = next(r for r in win if r["variable"] == variable
                     and int(r["lead_day"]) == lead)
            cell = (f"{d['effective_start'][5:]}[{d['n_models']}]"
                    if d["effective_start"] else "—")
            line += cell.ljust(13)
        print(line)

    print("\nBinding model per variable at lead 1:")
    for variable in VARIABLES:
        d = next(r for r in win if r["variable"] == variable
                 and int(r["lead_day"]) == 1)
        print(f"  {variable:<26}{d['binding_model'] or '—'}")

    starts = [date.fromisoformat(r["effective_start"])
              for r in win if r["effective_start"]]
    if starts:
        print(f"\nLatest effective start: {max(starts)}   "
              f"Earliest: {min(starts)}")
    print(f"\nWrote {MATRIX_OUT}\n      {WINDOW_OUT}")
    print("Raw probe output and the v1 correction left untouched.")
    print("\nRe-run the binding-cell check against the v2 files before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
