#!/usr/bin/env python3
"""
fetch_forecasts.py — retrieve archived forecasts for the assessment.

Reads the measured per-(model, variable, lead) start dates from
data/raw/archive_variable_matrix_v3.csv. Nothing about the window is assumed
here; every date comes from measurement.

DESIGN
------
Resumable. Output is one CSV per (model, quarter) under data/forecasts/.
A chunk that already exists is skipped, so an interrupted run costs only the
chunk in flight. Re-running after a failure is safe and cheap.

Batched. Open-Meteo accepts many hourly fields in one request, so a quarter
of six variables at seven lead days is one call rather than 42. That keeps
the whole fetch in the low hundreds of requests, well inside the free tier's
10,000/day, which matters because the CC BY 4.0 non-commercial terms cover
this assessment and nothing heavier.

Honest about absence. A (model, variable, lead) that the matrix records as
unexposed is never requested. A field that comes back null is written as
null, not dropped -- the completeness pass needs to see the gaps.

OUTPUT
------
Long format, one row per observation:

    model, variable, lead_day, valid_time, value

Provenance travels on every row, per protocol section 6.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://previous-runs-api.open-meteo.com/v1/forecast"
LAT, LON = 13.07333, -59.5
TZ = "UTC"

RAW = Path("data/raw")
OUT = Path("data/forecasts")
MATRIX = RAW / "archive_variable_matrix_v3.csv"

WINDOW_END = date(2026, 9, 30)          # per Amendment 3; protocol is
                                         # the authoritative record
CELL_SELECTION = "land"                  # default; A3.6 tests alternatives

SLEEP = 1.3
MAX_RETRIES = 4
MAX_FIELDS_PER_CALL = 42


class FetchError(RuntimeError):
    pass


def request(params: dict) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code == 400:
                raise FetchError(f"rejected: {body}")
            last = f"HTTP {e.code}: {body}"
        except Exception as e:                              # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        wait = SLEEP * (2 ** attempt)
        print(f"      retry {attempt + 1}/{MAX_RETRIES} in {wait:.0f}s — {last}")
        time.sleep(wait)
    raise FetchError(last or "unknown")


def load_matrix():
    """(model, variable, lead) -> first complete day, for exposed cells only."""
    starts, models, variables, leads = {}, [], [], set()
    for r in csv.DictReader(MATRIX.open()):
        if r["blended"].strip().lower() == "true":
            continue
        if not r["first_complete_day"]:
            continue
        m, v, l = r["model"], r["variable"], int(r["lead_day"])
        starts[(m, v, l)] = date.fromisoformat(r["first_complete_day"])
        if m not in models:
            models.append(m)
        if v not in variables:
            variables.append(v)
        leads.add(l)
    return starts, models, variables, sorted(leads)


def quarters(start: date, end: date):
    """Yield (qstart, qend) covering [start, end], aligned to calendar quarters."""
    y, q = start.year, (start.month - 1) // 3
    while True:
        qs = date(y, q * 3 + 1, 1)
        qe = (date(y + (q == 3), (q * 3 + 4) if q < 3 else 1, 1)
              - timedelta(days=1))
        lo, hi = max(qs, start), min(qe, end)
        if lo <= hi:
            yield lo, hi
        if qe >= end:
            return
        q += 1
        if q == 4:
            q, y = 0, y + 1


def chunk_path(model: str, lo: date) -> Path:
    return OUT / model / f"{lo.year}Q{(lo.month - 1) // 3 + 1}.csv"


def fetch_chunk(model, fields, lo, hi, starts):
    rows, units = [], {}
    for i in range(0, len(fields), MAX_FIELDS_PER_CALL):
        batch = fields[i:i + MAX_FIELDS_PER_CALL]
        payload = request({
            "latitude": LAT, "longitude": LON,
            "hourly": ",".join(batch), "models": model,
            "start_date": lo.isoformat(), "end_date": hi.isoformat(),
            "timezone": TZ, "cell_selection": CELL_SELECTION,
        })
        time.sleep(SLEEP)
        hourly = payload.get("hourly") or {}
        units.update(payload.get("hourly_units") or {})
        times = hourly.get("time") or []
        if not times:
            raise FetchError(f"no time axis for {model} {lo}..{hi}")
        for field in batch:
            variable, _, leadtxt = field.rpartition("_previous_day")
            lead = int(leadtxt)
            series = hourly.get(field)
            if series is None:
                # Only exposed fields are ever requested, so an absent one is
                # an anomaly -- unless its measured start falls inside this
                # chunk, where the archive legitimately has nothing to return.
                if starts[(model, variable, lead)] <= lo:
                    raise FetchError(
                        f"{field} absent from response for {model} "
                        f"{lo}..{hi}, but measured as available from "
                        f"{starts[(model, variable, lead)]}. Returned keys: "
                        f"{sorted(k for k in hourly if k != 'time')}"
                    )
                print(f"\n      note: {field} absent, starts "
                      f"{starts[(model, variable, lead)]} mid-chunk; "
                      f"recorded as null", end="")
                series = [None] * len(times)
            for t, value in zip(times, series):
                # The Previous Runs API does not expose which run produced a
                # value, so the issue DATE is derived and the initialisation
                # HOUR is unavailable. Protocol section 6 asks for exact
                # initialisation time; that belongs to the Single Runs
                # endpoint, not this one. Recorded, not fabricated.
                issue = (date.fromisoformat(t[:10])
                         - timedelta(days=lead)).isoformat()
                rows.append((model, variable, lead, issue, t, value))
    return rows, units


def main() -> int:
    starts, models, variables, leads = load_matrix()
    if not starts:
        print(f"no exposed cells in {MATRIX}")
        return 1

    end = min(WINDOW_END, date.today() - timedelta(days=1))
    print(f"Point {LAT}, {LON}   cell_selection={CELL_SELECTION}")
    print(f"Window end {end}   models {len(models)}   "
          f"variables {len(variables)}   leads {leads}\n")

    total_rows = 0
    for model in models:
        exposed = {(v, l) for (m, v, l) in starts if m == model}
        if not exposed:
            continue
        model_start = min(starts[(model, v, l)] for v, l in exposed)
        (OUT / model).mkdir(parents=True, exist_ok=True)
        print(f"{model}  from {model_start}  "
              f"{len(exposed)} variable-lead combinations")

        for lo, hi in quarters(model_start, end):
            path = chunk_path(model, lo)
            if path.exists():
                print(f"   {lo}..{hi}  already present, skipped")
                continue

            # Only request fields whose measured start falls before the
            # chunk end; earlier chunks legitimately hold fewer fields.
            fields = [f"{v}_previous_day{l}" for v, l in sorted(exposed)
                      if starts[(model, v, l)] <= hi]
            if not fields:
                print(f"   {lo}..{hi}  nothing available yet, skipped")
                continue

            print(f"   {lo}..{hi}  {len(fields)} fields ... ",
                  end="", flush=True)
            try:
                rows, units = fetch_chunk(model, fields, lo, hi, starts)
            except FetchError as e:
                print(f"FAILED — {e}")
                print("      chunk not written; re-run to retry")
                continue

            tmp = path.with_suffix(".partial")
            with tmp.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["model", "variable", "lead_day",
                            "issue_date", "valid_time", "value"])
                w.writerows(rows)
            tmp.rename(path)                  # atomic: no half-written chunk
            manifest = OUT / model / "_manifest.json"
            if not manifest.exists():
                manifest.write_text(json.dumps({
                    "provider": "Open-Meteo", "api": BASE, "model": model,
                    "latitude": LAT, "longitude": LON, "timezone": TZ,
                    "cell_selection": CELL_SELECTION, "units": units,
                    "retrieved": datetime.now(timezone.utc)
                                 .isoformat(timespec="seconds"),
                    "note": ("issue_date is derived as valid date minus lead "
                             "days; the Previous Runs API does not expose the "
                             "initialisation hour"),
                }, indent=2))
            nn = sum(1 for r in rows if r[5] is not None)
            print(f"{len(rows)} rows, {nn} non-null")
            total_rows += len(rows)

    print(f"\nWrote {total_rows} new rows under {OUT}")
    print("Re-run to retry any chunk that failed; existing chunks are skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
