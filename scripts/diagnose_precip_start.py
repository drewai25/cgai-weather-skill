#!/usr/bin/env python3
"""Where does archived precipitation actually begin, per model and lead?

verify_binding_cells.py found ecmwf_ifs025 precipitation present on the
day BEFORE the claimed lead-shifted start at every lead. This counts
non-null hours per day across a range, so a partial day (a few hours of
accumulation spill-over) is distinguished from a genuinely earlier start.
temperature_2m is run alongside as a control.
"""
import json, time, urllib.parse, urllib.request
from collections import defaultdict

BASE = "https://previous-runs-api.open-meteo.com/v1/forecast"
START, END = "2023-12-01", "2024-02-15"
MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless",
          "gem_seamless", "meteofrance_seamless"]

def hours_per_day(model, var, lead):
    q = urllib.parse.urlencode({
        "latitude": 13.07333, "longitude": -59.5,
        "hourly": f"{var}_previous_day{lead}", "models": model,
        "start_date": START, "end_date": END, "timezone": "UTC"})
    try:
        h = json.load(urllib.request.urlopen(f"{BASE}?{q}", timeout=90))["hourly"]
    except Exception as e:
        return None, str(e)[:80]
    finally:
        time.sleep(1.5)
    series = next((v for k, v in h.items() if k != "time"), [])
    per = defaultdict(int)
    for t, v in zip(h["time"], series):
        if v is not None:
            per[t[:10]] += 1
    return per, None

print(f"{'model':<22}{'var':<16}{'L':<3}{'first any':<12}{'first 24/24':<13}"
      f"hours on first-any days")
for model in MODELS:
    for var in ["precipitation", "temperature_2m"]:
        for lead in [1, 4, 7]:
            per, err = hours_per_day(model, var, lead)
            if err:
                print(f"{model:<22}{var:<16}{lead:<3}ERROR {err}")
                continue
            days = sorted(per)
            if not days:
                print(f"{model:<22}{var:<16}{lead:<3}none in range")
                continue
            full = next((d for d in days if per[d] == 24), "none")
            first5 = ", ".join(f"{d[5:]}:{per[d]}" for d in days[:5])
            print(f"{model:<22}{var:<16}{lead:<3}{days[0]:<12}{full:<13}{first5}")
