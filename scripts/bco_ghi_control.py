"""Control: does GHI behave the same in unflagged periods as in flagged ones?

Flagged runs show GHI maxima of 1489 and 1452 W/m2 with no NaN. Those are
above clear-sky and plausible as cloud enhancement -- common in trade-wind
cumulus. Plausible is not established. If unflagged periods show the same
distribution, the pyranometer was behaving identically whether or not the
direct sensor was flagged, and the GHI recovery claim stands.
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

PERIODS = [
    ("2024-03-13", "2024-05-02", "FLAGGED  status 3"),
    ("2024-10-14", "2025-04-06", "FLAGGED  status 3"),
    ("2024-05-03", "2024-10-14", "clean    status 0"),
    ("2025-04-07", "2025-09-30", "clean    status 0"),
    ("2025-10-01", "2026-03-31", "clean    status 0  same season as run 2"),
]

print(f"{'period':<26}{'label':<36}{'n':>9}{'max':>9}{'>1400':>7}"
      f"{'>1100':>8}{'nan':>6}{'neg<-10':>9}")
print("-" * 112)
for d0, d1, label in PERIODS:
    a, b = find(np.datetime64(f"{d0}T00:00:00")), find(np.datetime64(f"{d1}T23:59:59"))
    k = max(1, (b - a) // 200_000)
    v = g["SWD_global"][a:b:k]
    print(f"{d0}..{d1:<14}{label:<36}{len(v):>9}{np.nanmax(v):>9.1f}"
          f"{int((v > 1400).sum()):>7}{int((v > 1100).sum()):>8}"
          f"{int(np.isnan(v).sum()):>6}{int((v < -10).sum()):>9}")
