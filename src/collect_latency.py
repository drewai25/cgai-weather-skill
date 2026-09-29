#!/usr/bin/env python3
"""
collect_latency.py — observe when new forecast runs actually become available.

WHY
---
Protocol section 10 requires latency: how soon after initialisation output is
available. Nothing has measured it. The archive work answers whether a
forecast EXISTED; it cannot answer whether it had ARRIVED by the time an
operator needed it.

That distinction is operational. Roger's protocol runs a Tuesday 23:00
cutoff. If a model's 12Z run reaches the provider at 20:00 UTC that is fine;
if it lands at 02:00 the next day, the pipeline silently uses a run six hours
older than assumed and every lead time shifts.

METHOD
------
Poll the live forecast API on a fixed interval and hash the first 24 hours of
each model's temperature series. When the hash changes, a new run has landed.
The poll time brackets its arrival to within one interval.

DELIBERATELY ASSUMES NOTHING ABOUT RUN CYCLES. This records observations
only: poll time, model, hash, whether it changed. Which cycles a model runs,
and the latency from nominal initialisation, are inferred later from the
observed change times. Encoding 00/06/12/18Z here would build an assumption
into the measurement of that very assumption.

Gaps are expected -- a laptop sleeps, a network drops. Every poll is recorded
with its actual time, so gaps are visible rather than interpolated over.

USAGE
-----
    python3 src/collect_latency.py              # one poll, append, exit
    python3 src/collect_latency.py --loop 1800  # poll every 30 min until killed

Run it under nohup so it survives the terminal closing:

    nohup python3 src/collect_latency.py --loop 1800 \\
        >> reports/latency_collector.log 2>&1 &

OUTPUT
------
data/latency/poll_log.csv, append-only, one row per model per poll:

    poll_utc, model, status, first_valid_time, n_values, sha256_24h, changed
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.open-meteo.com/v1/forecast"
LAT, LON = 13.07333, -59.5

MODELS = [
    "ecmwf_ifs025",
    "dwd_icon_global",
    "gem_global",
    "gfs_seamless",
    "meteofrance_arpege_world",
    "jma_gsm",
]

OUT = Path("data/latency")
LOG = OUT / "poll_log.csv"
HEADER = ["poll_utc", "model", "status", "first_valid_time",
          "n_values", "sha256_24h", "changed"]

TIMEOUT = 45


def poll_model(model: str):
    """Return (status, first_time, n_values, digest). Never raises."""
    url = BASE + "?" + urllib.parse.urlencode({
        "latitude": LAT, "longitude": LON,
        "hourly": "temperature_2m", "models": model,
        "forecast_days": 2, "timezone": "UTC",
    })
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            payload = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return f"http_{e.code}", "", 0, ""
    except Exception as e:                                  # noqa: BLE001
        return f"error_{type(e).__name__}", "", 0, ""

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    series = hourly.get("temperature_2m")
    if series is None:
        for k, v in hourly.items():
            if k != "time" and isinstance(v, list):
                series = v
                break
    if not times or series is None:
        return "no_series", "", 0, ""

    first24 = series[:24]
    # None sorts unstably in a hash; render explicitly so a null-to-value
    # change is itself detected as a change.
    body = "|".join("null" if v is None else repr(v) for v in first24)
    digest = hashlib.sha256(body.encode()).hexdigest()[:16]
    return "ok", times[0], len(first24), digest


def last_digests() -> dict[str, str]:
    """Most recent successful digest per model, for change detection."""
    if not LOG.exists():
        return {}
    seen: dict[str, str] = {}
    with LOG.open() as f:
        for row in csv.DictReader(f):
            if row["status"] == "ok" and row["sha256_24h"]:
                seen[row["model"]] = row["sha256_24h"]
    return seen


def one_pass() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fresh = not LOG.exists()
    previous = last_digests()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows, changes = [], 0
    for model in MODELS:
        status, first_time, n, digest = poll_model(model)
        was = previous.get(model)
        changed = ""
        if status == "ok" and digest:
            if was is None:
                changed = "first"
            elif digest != was:
                changed = "yes"
                changes += 1
            else:
                changed = "no"
        rows.append([now, model, status, first_time, n, digest, changed])
        time.sleep(1.0)

    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(HEADER)
        w.writerows(rows)

    ok = sum(1 for r in rows if r[2] == "ok")
    print(f"{now}  polled {len(rows)} models, {ok} ok, {changes} changed")
    for r in rows:
        if r[6] == "yes":
            print(f"    new run detected: {r[1]}")
        elif r[2] != "ok":
            print(f"    {r[1]}: {r[2]}")
    return changes


def main() -> int:
    interval = None
    if "--loop" in sys.argv:
        i = sys.argv.index("--loop")
        interval = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 1800

    if interval is None:
        one_pass()
        return 0

    print(f"Polling every {interval}s. Ctrl-C to stop. Appending to {LOG}")
    try:
        while True:
            try:
                one_pass()
            except Exception as e:                          # noqa: BLE001
                # A collector that dies overnight collects nothing. Record
                # the failure to stdout and keep the schedule.
                print(f"pass failed: {type(e).__name__}: {e}", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
