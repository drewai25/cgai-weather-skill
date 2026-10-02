#!/usr/bin/env python3
"""Fetch ERA5 as the observational reference for temperature, cloud, rainfall.

Open-Meteo's archive endpoint serves ERA5 and ERA5-Land. Same provider as the
forecasts, same no-auth access, so the fetch is small: one point, 1,004 days,
hourly.

MODELS ARE NAMED EXPLICITLY. The archive API defaults to best_match, which
blends ERA5 and ERA5-Land. Protocol section 6 bans best_match and requires
provenance on every scored row, so each model is requested by name and the
name travels with the data.

Conventions, from Open-Meteo's documentation (A5.14):
    temperature_2m        instantaneous at the label
    cloud_cover           instantaneous at the label
    precipitation         sum over the preceding hour
    shortwave_radiation   mean over the preceding hour

Output: data/reference/era5/<model>_<year>.csv
    model, variable, valid_time, value
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://archive-api.open-meteo.com/v1/archive"
LAT, LON = 13.07333, -59.5
START, END = date(2024, 1, 1), date(2026, 9, 30)
MODELS = ["era5", "era5_land"]
VARIABLES = ["temperature_2m", "cloud_cover", "precipitation",
             "shortwave_radiation"]
OUT = Path("data/reference/era5")
SLEEP, RETRIES = 1.5, 4


def request(params: dict) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code == 400:
                raise RuntimeError(f"rejected: {body}")
            last = f"HTTP {e.code}: {body}"
        except Exception as e:                              # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        wait = SLEEP * (2 ** attempt)
        print(f"      retry {attempt+1}/{RETRIES} in {wait:.0f}s -- {last}")
        time.sleep(wait)
    raise RuntimeError(last or "unknown")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for model in MODELS:
        for year in range(START.year, END.year + 1):
            lo = max(START, date(year, 1, 1))
            hi = min(END, date(year, 12, 31))
            path = OUT / f"{model}_{year}.csv"
            if path.exists():
                print(f"{model} {year}  already present, skipped")
                continue
            print(f"{model} {year}  {lo} .. {hi} ... ", end="", flush=True)
            try:
                p = request({
                    "latitude": LAT, "longitude": LON,
                    "start_date": lo.isoformat(), "end_date": hi.isoformat(),
                    "hourly": ",".join(VARIABLES), "models": model,
                    "timezone": "UTC", "cell_selection": "land",
                })
            except RuntimeError as e:
                print(f"FAILED -- {e}")
                continue
            time.sleep(SLEEP)
            h = p.get("hourly") or {}
            times = h.get("time") or []
            if not times:
                print("no time axis")
                continue
            rows = []
            for v in VARIABLES:
                series = h.get(v)
                if series is None:
                    print(f"[{v} absent] ", end="")
                    continue
                rows.extend((model, v, t, val) for t, val in zip(times, series))
            tmp = path.with_suffix(".partial")
            with tmp.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["model", "variable", "valid_time", "value"])
                w.writerows(rows)
            tmp.rename(path)
            nn = sum(1 for r in rows if r[3] is not None)
            print(f"{len(rows)} rows, {nn} non-null, {len(times)} hours")
            total += len(rows)

    print(f"\nWrote {total} rows under {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
