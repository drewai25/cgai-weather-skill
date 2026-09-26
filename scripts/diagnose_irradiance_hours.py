#!/usr/bin/env python3
"""
diagnose_irradiance_hours.py — why ECMWF irradiance shows 1-7 hours per day.

verify_complete_day.py found ECMWF shortwave, DNI and diffuse carrying 7 of
24 hours at leads 1-2 and 1 of 24 at leads 3-7 on their stated start dates,
with 0 the day before. A partial boundary day fills in the following day;
one hour at lead 7 does not look like a boundary effect.

Two hypotheses with very different consequences:

  RAMP-UP    sparse for the first days, complete later. The window start
             moves later and nothing else changes.

  STRUCTURAL ECMWF stores irradiance coarser than hourly in this archive,
             degrading with lead time. ECMWF then cannot support hourly
             irradiance verification at all: it leaves the solar comparison,
             the binding model changes for all three irradiance variables,
             and carriers at lead 7 drop from three to two.

The two are told apart by looking at WHICH hours are present, not how many.
Evenly spaced hours mean coarse time resolution. A contiguous block means a
boundary or ramp-up effect. Daylight-only means nulls at night.

GFS and GEM are probed at the same dates as controls: if they return 24/24
where ECMWF returns 7, the cause is ECMWF-specific rather than archive-wide.

Output is a 24-character mask per day, midnight to 23:00 UTC, '#' present
and '.' null, so the pattern is visible directly.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "scripts")
from probe_archive import request, ProbeError, LAT, LON, TZ   # noqa: E402

MODELS = ["ecmwf_ifs025", "gfs_seamless", "gem_seamless"]
VARIABLES = ["shortwave_radiation", "direct_normal_irradiance"]
LEADS = [1, 3, 7]
DATES = [
    date(2024, 3, 6),     # ECMWF irradiance stated start
    date(2024, 3, 13),    # one week in
    date(2024, 6, 15),    # three months in
    date(2025, 3, 15),    # a year in
    date(2026, 6, 15),    # recent
]


def mask(model: str, variable: str, lead: int, day: date) -> tuple[str, int]:
    field = f"{variable}_previous_day{lead}"
    payload = request({
        "latitude": LAT, "longitude": LON, "hourly": field, "models": model,
        "start_date": day.isoformat(), "end_date": day.isoformat(),
        "timezone": TZ,
    })
    if payload.get("api_error"):
        return "not offered", -1
    hourly = payload.get("hourly") or {}
    series = hourly.get(field)
    if series is None:
        for key, value in hourly.items():
            if key != "time" and isinstance(value, list):
                series = value
                break
    if series is None:
        return "no series", -1
    m = "".join("#" if v is not None else "." for v in series)
    return m, sum(1 for v in series if v is not None)


def main() -> int:
    print("Hour mask, 00:00 to 23:00 UTC. '#' present, '.' null.\n")
    print(f"{'model':<16}{'variable':<26}{'ld':<4}{'date':<12}"
          f"{'n':<4}mask")
    print("-" * 96)

    for variable in VARIABLES:
        for model in MODELS:
            for lead in LEADS:
                for day in DATES:
                    try:
                        m, n = mask(model, variable, lead, day)
                    except ProbeError as e:
                        print(f"{model:<16}{variable:<26}{lead:<4}"
                              f"{day.isoformat():<12}{'':<4}UNKNOWN ({e})")
                        continue
                    print(f"{model:<16}{variable:<26}{lead:<4}"
                          f"{day.isoformat():<12}{n:<4}{m}")
            print()

    print("Reading the masks:")
    print("  ########################  complete, hourly")
    print("  #..#..#..#..#..#..#..#..  3-hourly -> coarse resolution")
    print("  #.....#.....#.....#.....  6-hourly -> coarser still with lead")
    print("  .......###########......  daylight only -> nulls at night")
    print("  #######.................  contiguous block -> boundary/ramp-up")
    print()
    print("If ECMWF stays sparse at 2026-06-15 while GFS and GEM are complete,")
    print("the cause is structural and ECMWF leaves the hourly irradiance")
    print("comparison. If ECMWF is complete at later dates, it is a ramp-up")
    print("and only the window start moves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
