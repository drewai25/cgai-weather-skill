"""What does a raw_count of zero actually contain, and how much is daylight?

If a missing interval is encoded as 0.0 W/m2 rather than NaN, it is
indistinguishable from a genuine night-time zero, and any hour built from
such bins would look like valid darkness. This must be known before a single
hourly value is constructed.
"""
import numpy as np
import pandas as pd
import xarray as xr

URL = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
       "/airflow_production/BCO.radiation_x255960_0_PT10M.zarr")
ds = xr.open_zarr(URL, consolidated=True).sel(time=slice("2024-01-01",
                                                         "2026-09-30"))
rc = ds.raw_count.values
VARS = ["sw_down_global", "sw_down_diffuse", "sw_down_suntracker"]

print("=== bins where raw_count == 0 ===")
z = rc == 0
print(f"  count {z.sum()}  ({100*z.mean():.1f}%)")
for v in VARS:
    a = ds[v].values[z]
    print(f"  {v:<20} nan {np.isnan(a).sum():>7}   "
          f"exactly 0.0 {int((a == 0).sum()):>7}   "
          f"other {int(np.sum(~np.isnan(a) & (a != 0))):>7}")

print("\n=== bins where raw_count > 0 ===")
p = rc > 0
for v in VARS:
    a = ds[v].values[p]
    print(f"  {v:<20} nan {np.isnan(a).sum():>7}   "
          f"finite {int(np.isfinite(a).sum()):>7}")

print("\n=== partial bins: is the mean still trustworthy? ===")
for lo, hi in [(1, 60), (60, 300), (300, 599), (599, 601)]:
    m = (rc >= lo) & (rc < hi)
    if m.sum() == 0:
        continue
    a = ds.sw_down_global.values[m]
    print(f"  raw_count {lo:>3}-{hi:<3}  bins {m.sum():>7}  "
          f"finite {int(np.isfinite(a).sum()):>7}  "
          f"nan {int(np.isnan(a).sum()):>7}")

print("\n=== rough daylight share of passing hours ===")
print("  (approximate: solar noon at 13.07N 59.5W is near 16:00 UTC;")
print("   this is a sanity check, NOT the A5.2 elevation criterion)")
t = pd.to_datetime(ds.time.values)
hour_end = (t - pd.Timedelta(minutes=5)).floor("h") + pd.Timedelta(hours=1)
g = pd.DataFrame({"h": hour_end, "rc": rc}).groupby("h").rc.sum()
ok = g[g >= 3240]
day = ok[(ok.index.hour >= 10) & (ok.index.hour <= 22)]
print(f"  hours passing 90%:            {len(ok)}")
print(f"  of those, 10:00-22:00 UTC:    {len(day)}  ({100*len(day)/len(ok):.0f}%)")
