"""Did Level 1 hold data through the winter that Level 2 dropped?

radiation_c2 is 1-second, 324,391,785 points; its time coordinate alone is
2.42 GiB. Read zarr directly and locate each month by linear estimate from
the endpoints (the grid is ~93% dense so the estimate lands within days),
then refine with small reads. Never stride the whole array -- a strided read
pulls every chunk.
"""
import numpy as np
import zarr

URL = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
       "/airflow_production/BCO.radiation_c2_08e20c5_0.zarr")
SCALE = {"microseconds": "us", "milliseconds": "ms",
         "seconds": "s", "nanoseconds": "ns"}

g = zarr.open_consolidated(URL, mode="r")
t = g["time"]
units = t.attrs["units"]
unit = SCALE[units.split()[0]]
epoch = np.datetime64(units.split("since")[-1].strip()[:10])
n = t.shape[0]

def at(i):
    return epoch + np.int64(t[int(i)]).astype(f"timedelta64[{unit}]")

t0, t1 = at(0), at(n - 1)
print(f"L1 c2: {n} records, {t0} .. {t1}")
print("chunks:", t.chunks)

def find(target):
    """Index of the first record at or after `target`, by bisection."""
    lo, hi = 0, n - 1
    while hi - lo > 5000:
        mid = (lo + hi) // 2
        if at(mid) < target:
            lo = mid
        else:
            hi = mid
    return lo

for month in ["2024-04", "2024-12", "2025-02", "2025-06"]:
    lo_t = np.datetime64(f"{month}-01T00:00:00")
    hi_t = (np.datetime64(f"{month}-01") + np.timedelta64(32, "D")
            ).astype("datetime64[M]").astype("datetime64[s]")
    a, b = find(lo_t), find(hi_t)
    if b <= a:
        print(f"  {month}: NO RECORDS in Level 1")
        continue
    b = min(b, a + 3_000_000)
    v = g["SWD_global"][a:b]
    good = int(np.isfinite(v).sum())
    stat = g["sw_dir_sensor_status"][a:b]
    sset = g["sensor_set"][a:b]
    print(f"  {month}: {b-a:>9} L1 records, {good:>9} finite SWD_global "
          f"({100*good/(b-a):5.1f}%)  "
          f"status {np.unique(stat)[:4]}  set {np.unique(sset)[:4]}")
