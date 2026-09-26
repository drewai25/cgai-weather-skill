#!/usr/bin/env python3
"""
probe_archive.py — measure forecast-archive availability on the Open-Meteo
Previous Runs API, per model, per variable, per lead day.

Protocol reference: assessment_protocol.md Amendment 3 §A3.10. This is the
blocking prerequisite for the skill curves, benchmark baselines and
operational assessment.

WHAT THIS DOES AND DOES NOT DECIDE
----------------------------------
This script measures ONE input to the verification window: the dates on
which archived forecast data exists. It does not set the verification
window and it does not amend the protocol.

    Verification window =
        Amendment 3 frozen observational window        (already frozen)
      INTERSECT  forecast archive availability         (measured here)
      INTERSECT  observational reference availability  (measured separately)
      INTERSECT  completeness criteria, 90% threshold  (applied separately)

If the archive starts later than the frozen observational window, the
frozen window is NOT redefined. Both are reported, the effective
comparable window is reported as their intersection, and the binding
constraint is named. The freeze is preserved.

GRANULARITY
-----------
Amendment 3 requires skill curves per variable, per lead day, unblended.
So the primary artifact is the per-(model, variable, lead) window. A
single all-models-all-variables-all-leads intersection is reported only
as a secondary, most-restrictive summary: one model missing DNI at lead 7
must not discard every model's GHI at lead 1.

TWO-DATE PROBING
----------------
A model's archive start and a variable's first appearance in that archive
are not the same date. Probing availability at one recent date would
record a variable as available across the whole archive when it may have
been added partway through. Every (model, variable, lead) is therefore
probed at two dates — one near the model's archive start, one recent —
and any combination that is present recently but absent near the start
gets its own binary search.

Outputs
-------
data/raw/archive_start_by_model.csv
data/raw/archive_variable_matrix.csv      the primary artifact
data/raw/effective_window_by_variable_lead.csv
reports/archive_window_finding.md

Runtime: roughly 10-30 minutes, rate-limited by design so the probe is
never throttled into a half-answered table.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE = "https://previous-runs-api.open-meteo.com/v1/forecast"
LAT, LON = 13.07333, -59.5          # Grantley Adams reference point
TZ = "UTC"

# ---------------------------------------------------------------------------
# Inputs carried in from the protocol. These are NOT measured here and NOT
# modified here. They are printed in the report so the intersection is
# auditable against the frozen amendment.
# ---------------------------------------------------------------------------
FROZEN_OBS_START = date(2024, 1, 1)     # Amendment 3 §A3.1
FROZEN_OBS_END = date(2026, 9, 30)      # Amendment 3 §A3.1

# Candidate models. best_match is a blended product, excluded from the skill
# assessment by Amendment 3 §A3.9; probed only so the record shows it was
# considered and excluded rather than overlooked.
MODELS = [
    "best_match",
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
    "gem_seamless",
    "meteofrance_seamless",
    "jma_seamless",
]
BLENDED = {"best_match"}

VARIABLES = [
    "temperature_2m",
    "precipitation",
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
    "cloud_cover",
]

LEADS = [1, 2, 3, 4, 5, 6, 7]

REFERENCE_VARIABLE = "temperature_2m"
REFERENCE_LEAD = 1

SEARCH_FLOOR = date(2021, 1, 1)     # earlier than any plausible archive start
CEILING_BACKOFF = 14                # stay clear of the live edge
NEAR_START_OFFSET = 30              # days after archive start for the early probe

SLEEP_SECONDS = 1.3
MAX_RETRIES = 3

AVAILABLE = "available"
EMPTY = "empty"
NOT_EXPOSED = "not exposed"


class ProbeError(RuntimeError):
    """A request failed after all retries. Distinct from 'no data'."""


# ---------------------------------------------------------------------------
# request layer
# ---------------------------------------------------------------------------

def request(params: dict) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code == 400:
                # A 400 carrying a reason is information: the field is not
                # offered. Distinct from a transport failure.
                return {"api_error": True, "reason": body}
            last = f"HTTP {e.code}: {body}"
        except Exception as e:                      # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(SLEEP_SECONDS * (attempt + 2))
    raise ProbeError(last or "unknown transport failure")


def probe(model: str, variable: str, lead: int, day: date) -> str:
    """AVAILABLE / EMPTY / NOT_EXPOSED. Raises ProbeError on transport failure.

    A raised ProbeError is never converted into an absence. A failed request
    recorded as a missing variable would shrink the window on the basis of a
    timeout, and every downstream skill number would sit on a window narrower
    than the data supports.
    """
    field = f"{variable}_previous_day{lead}"
    payload = request({
        "latitude": LAT,
        "longitude": LON,
        "hourly": field,
        "models": model,
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
        "timezone": TZ,
    })
    time.sleep(SLEEP_SECONDS)

    if payload.get("api_error"):
        return NOT_EXPOSED

    hourly = payload.get("hourly") or {}
    series = hourly.get(field)
    if series is None:
        # Single-model requests may return the bare field name.
        for key, value in hourly.items():
            if key != "time" and isinstance(value, list):
                series = value
                break
    if series is None:
        return NOT_EXPOSED
    return AVAILABLE if any(v is not None for v in series) else EMPTY


# ---------------------------------------------------------------------------
# searches
# ---------------------------------------------------------------------------

def binary_search_start(model: str, variable: str, lead: int,
                        ceiling: date) -> tuple[date | None, str]:
    """Earliest date with non-null data. lo stays known-empty, hi known-full."""
    if probe(model, variable, lead, ceiling) != AVAILABLE:
        return None, "no data at the recent probe date"
    if probe(model, variable, lead, SEARCH_FLOOR) == AVAILABLE:
        return SEARCH_FLOOR, "begins at or before the search floor"

    lo, hi = SEARCH_FLOOR, ceiling
    while (hi - lo).days > 1:
        mid = lo + timedelta(days=(hi - lo).days // 2)
        if probe(model, variable, lead, mid) == AVAILABLE:
            hi = mid
        else:
            lo = mid
    return hi, "binary search, resolved to the day"


def variable_start(model: str, variable: str, model_start: date,
                   near: date, ceiling: date,
                   recent_status: dict[int, str]) -> dict[int, tuple]:
    """Effective start per lead for one (model, variable).

    Leads 1 and 7 bracket the range and are searched individually when the
    near-start probe shows the variable arrived after the model archive did.
    Intermediate leads are then confirmed at the resolved date rather than
    assumed, and any lead that disagrees is searched on its own.
    """
    out: dict[int, tuple] = {}

    for lead in LEADS:
        if recent_status.get(lead) != AVAILABLE:
            out[lead] = (None, recent_status.get(lead, "UNKNOWN"),
                         "absent at the recent probe date")
            continue

        early = probe(model, variable, lead, near)
        if early == AVAILABLE:
            out[lead] = (model_start, AVAILABLE,
                         f"present at {near.isoformat()}, "
                         "tracks the model archive start")
        else:
            start, note = binary_search_start(model, variable, lead, ceiling)
            out[lead] = (start, early,
                         f"added after the model archive start; {note}")
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    root = Path(__file__).resolve().parent.parent
    raw = root / "data" / "raw"
    reports = root / "reports"
    raw.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    ceiling = date.today() - timedelta(days=CEILING_BACKOFF)
    print(f"Point: {LAT}, {LON}   probe ceiling: {ceiling}")
    print(f"Frozen observational window (Amendment 3): "
          f"{FROZEN_OBS_START} to {FROZEN_OBS_END}\n")

    # ---- phase 1: model archive start -------------------------------------
    starts: dict[str, tuple[date | None, str]] = {}
    for model in MODELS:
        print(f"[1/3 start ] {model:<22} ", end="", flush=True)
        try:
            start, note = binary_search_start(
                model, REFERENCE_VARIABLE, REFERENCE_LEAD, ceiling)
        except ProbeError as e:
            starts[model] = (None, f"UNKNOWN ({e})")
            print(f"UNKNOWN ({e})")
            continue
        starts[model] = (start, note)
        print(start.isoformat() if start else f"none - {note}")

    with (raw / "archive_start_by_model.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "archive_start", "note", "blended",
                    "probed_on", "ceiling"])
        for model, (start, note) in starts.items():
            w.writerow([model, start.isoformat() if start else "", note,
                        model in BLENDED, date.today().isoformat(),
                        ceiling.isoformat()])

    # ---- phase 2: availability at the recent date -------------------------
    print()
    recent: dict[str, dict[tuple[str, int], str]] = {}
    for model, (start, _) in starts.items():
        if start is None:
            continue
        print(f"[2/3 recent] {model:<22} at {ceiling} ", end="", flush=True)
        table: dict[tuple[str, int], str] = {}
        for variable in VARIABLES:
            for lead in LEADS:
                try:
                    table[(variable, lead)] = probe(
                        model, variable, lead, ceiling)
                except ProbeError as e:
                    table[(variable, lead)] = f"UNKNOWN ({e})"
        recent[model] = table
        n = sum(1 for v in table.values() if v == AVAILABLE)
        print(f"-> {n}/{len(table)} available")

    # ---- phase 3: variable-specific starts --------------------------------
    print()
    effective: dict[str, dict[tuple[str, int], tuple]] = {}
    for model, table in recent.items():
        model_start = starts[model][0]
        near = min(model_start + timedelta(days=NEAR_START_OFFSET), ceiling)
        print(f"[3/3 early ] {model:<22} at {near} ", end="", flush=True)
        per_model: dict[tuple[str, int], tuple] = {}
        for variable in VARIABLES:
            recent_status = {l: table.get((variable, l)) for l in LEADS}
            if not any(s == AVAILABLE for s in recent_status.values()):
                for lead in LEADS:
                    per_model[(variable, lead)] = (
                        None, recent_status.get(lead, "UNKNOWN"),
                        "absent at the recent probe date")
                continue
            try:
                resolved = variable_start(model, variable, model_start,
                                          near, ceiling, recent_status)
            except ProbeError as e:
                for lead in LEADS:
                    per_model[(variable, lead)] = (
                        None, "UNKNOWN", f"transport failure: {e}")
                continue
            for lead, value in resolved.items():
                per_model[(variable, lead)] = value
        effective[model] = per_model
        late = sum(1 for (s, _, note) in per_model.values()
                   if s is not None and "added after" in note)
        print(f"-> {late} combination(s) start later than the model archive")

    with (raw / "archive_variable_matrix.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "variable", "lead_day", "status_recent",
                    "status_near_start", "effective_start", "method",
                    "blended"])
        for model, per_model in effective.items():
            for variable in VARIABLES:
                for lead in LEADS:
                    start, early_status, note = per_model[(variable, lead)]
                    w.writerow([
                        model, variable, lead,
                        recent[model].get((variable, lead), ""),
                        early_status,
                        start.isoformat() if start else "",
                        note, model in BLENDED,
                    ])

    # ---- per (variable, lead) window across unblended models --------------
    per_vl: dict[tuple[str, int], dict] = {}
    for variable in VARIABLES:
        for lead in LEADS:
            carriers = {}
            for model, per_model in effective.items():
                if model in BLENDED:
                    continue
                start, _, _ = per_model[(variable, lead)]
                if start is not None:
                    carriers[model] = start
            if carriers:
                archive_start = max(carriers.values())
                eff_start = max(archive_start, FROZEN_OBS_START)
                binding = ("frozen observational window"
                           if FROZEN_OBS_START >= archive_start
                           else "forecast archive availability")
            else:
                archive_start = eff_start = None
                binding = "no unblended model carries this combination"
            per_vl[(variable, lead)] = {
                "carriers": carriers,
                "archive_start": archive_start,
                "effective_start": eff_start,
                "binding": binding,
            }

    with (raw / "effective_window_by_variable_lead.csv").open(
            "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variable", "lead_day", "n_models", "models",
                    "common_archive_start", "frozen_obs_start",
                    "effective_start", "effective_end", "binding_constraint"])
        for variable in VARIABLES:
            for lead in LEADS:
                d = per_vl[(variable, lead)]
                w.writerow([
                    variable, lead, len(d["carriers"]),
                    ";".join(sorted(d["carriers"])),
                    d["archive_start"].isoformat() if d["archive_start"] else "",
                    FROZEN_OBS_START.isoformat(),
                    d["effective_start"].isoformat() if d["effective_start"] else "",
                    FROZEN_OBS_END.isoformat(),
                    d["binding"],
                ])

    # ---- report ------------------------------------------------------------
    unblended_starts = [
        d["archive_start"] for d in per_vl.values()
        if d["archive_start"] is not None
    ]
    most_restrictive = max(unblended_starts) if unblended_starts else None
    full_coverage = [
        (v, l) for v in VARIABLES for l in LEADS
        if per_vl[(v, l)]["carriers"]
    ]

    L = [
        "# Forecast archive availability finding",
        "",
        f"Probed {date.today().isoformat()} at {LAT}, {LON} "
        f"(Grantley Adams reference point), Open-Meteo Previous Runs API.",
        "",
        "## What this measures",
        "",
        "Forecast-archive availability only. This is one input to the "
        "verification window, not the verification window itself:",
        "",
        "```",
        "verification window =",
        "      Amendment 3 frozen observational window   (frozen, not touched here)",
        "    ∩ forecast archive availability             (measured here)",
        "    ∩ observational reference availability      (measured separately)",
        "    ∩ completeness criteria, 90% threshold      (applied separately)",
        "```",
        "",
        f"Frozen observational window, Amendment 3 §A3.1: "
        f"**{FROZEN_OBS_START.isoformat()} to {FROZEN_OBS_END.isoformat()}**. "
        "Where the archive starts later, the frozen window is not redefined; "
        "both are reported and the binding constraint is named.",
        "",
        "## Archive start by model",
        "",
        "| Model | Archive start | Blended | Note |",
        "|---|---|---|---|",
    ]
    for model, (start, note) in starts.items():
        L.append(f"| `{model}` | {start.isoformat() if start else '—'} | "
                 f"{'yes' if model in BLENDED else 'no'} | {note} |")

    L += [
        "",
        "Probed on `temperature_2m` at lead day 1. Individual variables may "
        "enter the archive later; that is resolved per variable below.",
        "",
        "## Effective window by variable and lead day",
        "",
        "This is the primary artifact. Amendment 3 requires skill curves per "
        "variable, per lead day, unblended, so each combination carries its "
        "own window. A gap in one combination does not discard the others.",
        "",
        "| Variable | Lead | Models | Common archive start | Effective start | Binding constraint |",
        "|---|---|---|---|---|---|",
    ]
    for variable in VARIABLES:
        for lead in LEADS:
            d = per_vl[(variable, lead)]
            L.append(
                f"| `{variable}` | {lead} | {len(d['carriers'])} | "
                f"{d['archive_start'].isoformat() if d['archive_start'] else '—'} | "
                f"{d['effective_start'].isoformat() if d['effective_start'] else '—'} | "
                f"{d['binding']} |"
            )

    L += [
        "",
        "## Most-restrictive single window",
        "",
        "Reported for completeness only. It is **not** the assessment window: "
        "collapsing to one window would let the weakest variable-lead "
        "combination shrink the usable sample for every other one.",
        "",
    ]
    if most_restrictive:
        L += [
            f"- Latest common archive start across all covered combinations: "
            f"**{most_restrictive.isoformat()}**",
            f"- Intersected with the frozen observational window: "
            f"**{max(most_restrictive, FROZEN_OBS_START).isoformat()} to "
            f"{FROZEN_OBS_END.isoformat()}**",
            f"- Combinations with at least one unblended carrier: "
            f"{len(full_coverage)} of {len(VARIABLES) * len(LEADS)}",
        ]
    else:
        L.append("No unblended model carries any combination. Re-run before "
                 "drawing any conclusion; this is more likely a probe failure "
                 "than a real absence.")

    L += [
        "",
        "## Caveats",
        "",
        "- `best_match` is blended and excluded from the skill assessment per "
        "Amendment 3 §A3.9. Probed for documentation only and excluded from "
        "every window calculation above.",
        "- `UNKNOWN` is a failed request, not an absent variable. Re-run "
        "before treating it as a gap.",
        "- Non-null values on a probe date are an availability signal, not a "
        "completeness claim. Per-variable completeness across the window is "
        "measured separately at the 90% threshold fixed in Amendment 3.",
        "- Availability was probed at two dates per combination, near the "
        "archive start and recently, with a binary search where the two "
        "disagree. Continuous availability between those points is not "
        "established here; the completeness pass measures it.",
        "",
    ]

    out = reports / "archive_window_finding.md"
    out.write_text("\n".join(L))

    print(f"\nWrote:\n  {raw / 'archive_start_by_model.csv'}"
          f"\n  {raw / 'archive_variable_matrix.csv'}"
          f"\n  {raw / 'effective_window_by_variable_lead.csv'}"
          f"\n  {out}")
    if most_restrictive:
        print(f"\nMost-restrictive common archive start: {most_restrictive}")
        print(f"Frozen observational start:              {FROZEN_OBS_START}")
        print(f"Binding on the most-restrictive combination: "
              f"{'archive' if most_restrictive > FROZEN_OBS_START else 'frozen window'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
