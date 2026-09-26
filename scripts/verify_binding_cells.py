#!/usr/bin/env python3
"""Confirm the lead-shifted effective start for every binding cell.

For each variable x lead, the binding model is ecmwf_ifs025. The corrected
table claims start = first_run + lead. Each claim is confirmed with two
probes: data present on the claimed date, absent the day before.
"""
import json, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, timedelta

BASE = "https://previous-runs-api.open-meteo.com/v1/forecast"
MODEL = "ecmwf_ifs025"
FIRST_RUN = {
    "temperature_2m": date(2024, 2, 3),
    "precipitation": date(2024, 2, 3),
    "cloud_cover": date(2024, 2, 3),
    "shortwave_radiation": date(2024, 3, 5),
    "direct_normal_irradiance": date(2024, 3, 5),
    "diffuse_radiation": date(2024, 3, 5),
}

def has(var, lead, d):
    q = urllib.parse.urlencode({
        "latitude": 13.07333, "longitude": -59.5,
        "hourly": f"{var}_previous_day{lead}", "models": MODEL,
        "start_date": d.isoformat(), "end_date": d.isoformat(),
        "timezone": "UTC"})
    for attempt in range(3):
        try:
            h = json.load(urllib.request.urlopen(f"{BASE}?{q}", timeout=60))
            h = h.get("hourly", {})
            s = next((v for k, v in h.items() if k != "time"), [])
            time.sleep(1.3)
            return len(s) == 24 and all(x is not None for x in s)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                return False
        except Exception:
            pass
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"transport failure {var} lead {lead} {d}")

fails = 0
print(f"{'variable':<26}{'L':<3}{'claimed':<12}{'on day':<8}{'day before':<11}result")
for var, run in FIRST_RUN.items():
    for lead in range(1, 8):
        claimed = run + timedelta(days=lead)
        on_day = has(var, lead, claimed)
        before = has(var, lead, claimed - timedelta(days=1))
        ok = on_day and not before
        fails += not ok
        print(f"{var:<26}{lead:<3}{claimed.isoformat():<12}"
              f"{str(on_day):<8}{str(before):<11}{'CONFIRMED' if ok else 'FAIL'}")
print()
print("ALL 42 BINDING CELLS CONFIRMED" if fails == 0
      else f"{fails} CELL(S) FAILED - do not use the corrected table yet")
sys.exit(1 if fails else 0)
