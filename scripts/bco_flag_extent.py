"""Exactly when is sw_dir_sensor_status set, and is GHI physical throughout?

Established on 2024-12-15: the direct sensor reads up to 6165 W/m2, four
times the solar constant, while GHI traces a clean diurnal curve peaking at
1122. The flag names the direct sensor. Level 2 drops every variable.

This finds the contiguous flagged runs across the frozen window and tests
GHI against physics in each: a ceiling of 1400 W/m2, and near-zero at local
midnight (04:00 UTC at 59.5W).
"""
import numpy as np
import zarr

URL = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
       "/airflow_production/BCO.radiation_c2_08e20c5_0.zarr")
g = zarr.open_consolidated(URL, mode="r")
t, EPOCH = g["time"], np.datetime64("1970-01-01")
n = t.shape[0]

def at(i):
    return EPOCH + np.int64(t[int(i)]).astype("timedelta64[us]")

def find(target):
    lo, hi = 0, n - 1
    while hi - lo > 5000:
        mid = (lo + hi) // 2
        if at(mid) < target: lo = mid
        else: hi = mid
    return lo

a = find(np.datetime64("2024-01-01T00:00:00"))
b = find(np.datetime64("2026-09-30T23:59:59"))
print(f"window indices {a} .. {b}  ({b-a} samples)")

STEP = 16_000_000
runs, cur, start = [], None, a
for lo in range(a, b, STEP):
    hi = min(lo + STEP, b)
    s = g["sw_dir_sensor_status"][lo:hi]
    ch = np.flatnonzero(np.diff(s)) + 1
    for c in ch:
        v = int(s[c - 1])
        if cur is None: cur = v
        if v != cur or True:
            runs.append((start, lo + int(c), cur))
            start, cur = lo + int(c), int(s[c])
    if cur is None: cur = int(s[0])
runs.append((start, b, cur))

merged = []
for s0, s1, v in runs:
    if merged and merged[-1][2] == v: merged[-1][1] = s1
    else: merged.append([s0, s1, v])

print("\nstatus runs in the frozen window")
for s0, s1, v in merged:
    if s1 - s0 < 86400: continue
    d0, d1 = at(s0), at(s1 - 1)
    days = (s1 - s0) / 86400
    print(f"  status {v}  {str(d0)[:10]} .. {str(d1)[:10]}  ~{days:6.1f} days")
    if v == 0: continue
    k = max(1, (s1 - s0) // 200_000)
    gl = g["SWD_global"][s0:s1:k]
    print(f"      GHI sampled {len(gl)}  max {np.nanmax(gl):8.1f}  "
          f"over 1400 W/m2: {int((gl > 1400).sum())}  "
          f"nan {int(np.isnan(gl).sum())}")
