#!/usr/bin/env python3
"""
check_interpolation.py — are Open-Meteo's hourly values native, or filled in?

WHY
---
Open-Meteo's own model page states three ECMWF products:
    IFS HRES        9 km      hourly to 90 h, 3-hourly to 144 h, then 6-hourly
    IFS 0.25        ~25 km    3-hourly, 6-hourly after 144 h
    AIFS Single     ~28 km    6-hourly

The archive probe measured ecmwf_ifs025 and found 24 non-null hourly values a
day. If that model is natively 3-hourly, those hours are being filled in.

That matters three ways. A4.1 defines availability as 24 of 24 non-null hourly
values, which interpolation satisfies without meaning what it appears to.
Standard 2 requires hourly minimum, met nominally but not actually. And
scoring interpolated hours against the Observatory's one-second aggregates
would partly measure the interpolator rather than the forecast.

THE TEST
--------
Linear interpolation between anchors N hours apart leaves a signature: every
in-between value sits exactly on the straight line joining its anchors.

    expected(t0 + k) = v(t0) + k * (v(t0+N) - v(t0)) / N      for 0 < k < N

Compute the largest deviation from that across the day. Near zero means the
series was constructed by interpolation at that spacing. Genuinely hourly
model output does not lie on straight lines to that precision.

Tested at N = 3 and N = 6. gfs_seamless serves as a control: it should NOT
fit, and if it does the test is measuring something other than interpolation.

Model identifiers are guesses where Open-Meteo's docs give product names
rather than API names, so each is probed and reported as unavailable rather
than assumed absent.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://previous-runs-api.open-meteo.com/v1/forecast"
LAT, LON = 13.07333, -59.5
TZ = "UTC"
DAY = date(2025, 6, 15)          # mid-window, well clear of any ramp-up

CANDIDATES = [
    "ecmwf_ifs025",              # measured by the probe
    "ecmwf_ifs_hres",            # HRES, identifier uncertain
    "ecmwf_ifs04",               # older open-data product
    "gfs_seamless",              # control, expected natively hourly
]
VARIABLES = ["temperature_2m", "shortwave_radiation"]
LEADS = [1, 7]


def fetch(model: str, variable: str, lead: int, day: date):
    field = f"{variable}_previous_day{lead}"
    url = BASE + "?" + urllib.parse.urlencode({
        "latitude": LAT, "longitude": LON, "hourly": field, "models": model,
        "start_date": day.isoformat(), "end_date": day.isoformat(),
        "timezone": TZ,
    })
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            payload = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode(errors='replace')[:120]}"
    except Exception as e:                                   # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"

    hourly = payload.get("hourly") or {}
    series = hourly.get(field)
    if series is None:
        for k, v in hourly.items():
            if k != "time" and isinstance(v, list):
                series = v
                break
    if series is None:
        return None, "field not returned"
    return series, None


def linear_fit_error(series, step: int) -> float | None:
    """Largest deviation from linear interpolation between anchors `step` apart.

    Returns None if the day cannot be tested (nulls in the anchors or gaps).
    """
    worst = 0.0
    tested = 0
    for t0 in range(0, 24 - step, step):
        a, b = series[t0], series[t0 + step]
        if a is None or b is None:
            continue
        for k in range(1, step):
            got = series[t0 + k]
            if got is None:
                continue
            expected = a + k * (b - a) / step
            worst = max(worst, abs(got - expected))
            tested += 1
    return worst if tested else None


def main() -> int:
    print(f"Point {LAT}, {LON}   date {DAY}   (hourly values, UTC)\n")

    for variable in VARIABLES:
        print("=" * 78)
        print(variable)
        print("=" * 78)
        for model in CANDIDATES:
            for lead in LEADS:
                series, err = fetch(model, variable, lead, DAY)
                time.sleep(1.3)
                label = f"{model} L{lead}"
                if series is None:
                    print(f"{label:<28} unavailable — {err}")
                    continue

                n = sum(1 for v in series if v is not None)
                e3 = linear_fit_error(series, 3)
                e6 = linear_fit_error(series, 6)

                def verdict():
                    if e3 is not None and e3 < 1e-6:
                        return "INTERPOLATED from 3-hourly"
                    if e6 is not None and e6 < 1e-6:
                        return "INTERPOLATED from 6-hourly"
                    if e3 is not None and e3 < 0.01:
                        return "near-linear at 3 h — inspect"
                    return "no detectable 3h/6h linear-interpolation signature"

                print(f"{label:<28} {n}/24 non-null   "
                      f"max dev vs 3h-linear {('%.6f' % e3) if e3 is not None else '   n/a'}"
                      f"   vs 6h-linear {('%.6f' % e6) if e6 is not None else '   n/a'}")
                print(f"{'':<28} -> {verdict()}")
                vals = ", ".join("null" if v is None else f"{v:g}"
                                 for v in series[:12])
                print(f"{'':<28}    first 12: {vals}")
        print()

    print("Reading it: a max deviation at or near zero means every in-between")
    print("value lies exactly on the line joining its anchors, which only")
    print("happens when something drew that line. gfs_seamless is the control;")
    print("if it also reads INTERPOLATED, distrust the test, not the archive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
