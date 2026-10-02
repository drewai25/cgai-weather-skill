"""Is the Nov 2024 - Mar 2025 hole an instrument outage or QC removal?

Level 2 (BCO.radiation) drops flagged, voltage-inconsistent and out-of-range
values. If Level 1 (radiation_c2) holds data where Level 2 does not, the QC
removed it. If Level 1 is empty too, the instrument was down. Different
findings, different consequences.
"""
import numpy as np
import pandas as pd
import xarray as xr

BASE = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
        "/airflow_production")

for name, url in [
    ("L2 PT10M", f"{BASE}/BCO.radiation_x255960_0_PT10M.zarr"),
    ("L1 c2    ", f"{BASE}/BCO.radiation_c2_08e20c5_0.zarr"),
]:
    try:
        ds = xr.open_zarr(url, consolidated=True)
    except Exception as e:
        print(f"{name}  unavailable -- {type(e).__name__}: {str(e)[:90]}")
        continue
    t = pd.to_datetime(ds.time.values[[0, -1]])
    print(f"\n{name}  {t[0]} .. {t[1]}   n={ds.sizes['time']}")
    print("  variables:", list(ds.data_vars))
    for month in ["2024-04", "2024-12", "2025-02", "2025-06"]:
        s = ds.sel(time=month)
        if s.sizes["time"] == 0:
            print(f"  {month}: NO RECORDS")
            continue
        v = ("sw_down_global" if "sw_down_global" in s
             else list(s.data_vars)[0])
        arr = s[v].values
        good = int(np.isfinite(arr).sum())
        print(f"  {month}: {s.sizes['time']:>8} records, "
              f"{good:>8} finite {v} ({100*good/arr.size:5.1f}%)")
