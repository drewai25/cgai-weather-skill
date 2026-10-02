"""Does Level 1 GHI look like sunlight during the flagged months?

sw_dir_sensor_status is 3 throughout the outage and 0 in a working month.
If SWD_global still traces a normal diurnal curve while flagged, the fault
is plausibly confined to the direct sensor and GHI may be recoverable. If it
is flat, stuck or physically impossible, the flag is right about everything.
"""
import numpy as np
import zarr

URL = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
       "/airflow_production/BCO.radiation_c2_08e20c5_0.zarr")
g = zarr.open_consolidated(URL, mode="r")
t = g["time"]
EPOCH = np.datetime64("1970-01-01")
n = t.shape[0]

def at(i):
    return EPOCH + np.int64(t[int(i)]).astype("timedelta64[us]")

def find(target):
    lo, hi = 0, n - 1
    while hi - lo > 5000:
        mid = (lo + hi) // 2
        if at(mid) < target:
            lo = mid
        else:
            hi = mid
    return lo

for day, label in [("2024-12-15", "FLAGGED (status 3)"),
                   ("2025-06-15", "CLEAN   (status 0)")]:
    a = find(np.datetime64(f"{day}T00:00:00"))
    b = find(np.datetime64(f"{day}T23:59:59"))
    b = min(b, a + 90_000)
    tt = EPOCH + t[a:b].astype("timedelta64[us]")
    gl = g["SWD_global"][a:b]
    di = g["SWD_dir"][a:b]
    df = g["SWD_diff"][a:b]
    print(f"\n{day}  {label}   {b-a} samples")
    print(f"  GHI  min {np.nanmin(gl):8.1f}  max {np.nanmax(gl):8.1f}  "
          f"mean {np.nanmean(gl):8.1f}")
    print(f"  DIR  min {np.nanmin(di):8.1f}  max {np.nanmax(di):8.1f}  "
          f"mean {np.nanmean(di):8.1f}")
    print(f"  DIF  min {np.nanmin(df):8.1f}  max {np.nanmax(df):8.1f}  "
          f"mean {np.nanmean(df):8.1f}")
    print("  hourly mean GHI, UTC:")
    hrs = tt.astype("datetime64[h]")
    for h in np.unique(hrs):
        m = hrs == h
        v = np.nanmean(gl[m])
        bar = "#" * int(max(0, v) / 25)
        print(f"    {str(h)[11:]}  {v:7.1f}  {bar}")
