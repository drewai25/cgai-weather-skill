"""O3 and O5 -- what raw_count counts, and what a timestamp means.

time_bounds is present and the dataset declares CF-1.12, so the averaging
interval is stated by the data. Read it rather than infer it.
"""
import numpy as np
import xarray as xr

URL = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
       "/airflow_production/BCO.radiation_x255960_0_PT10M.zarr")
ds = xr.open_zarr(URL, consolidated=True)

print("=== O5: what interval does a timestamp cover? ===")
d = ds.sel(time=slice("2024-09-01T00:00", "2024-09-01T01:00"))
for t, b, rc in zip(d.time.values, d.time_bounds.values, d.raw_count.values):
    print(f"  stamp {str(t)[:19]}   bounds {str(b[0])[:19]} .. {str(b[1])[:19]}"
          f"   raw_count {rc:.0f}")

print("\n=== O3: raw_count across the whole record ===")
rc = ds.raw_count.values
print("  n           ", rc.size)
print("  min / max   ", np.nanmin(rc), "/", np.nanmax(rc))
print("  exceeds 600 ", int((rc > 600).sum()))
print("  equals 600  ", int((rc == 600).sum()))
print("  nan         ", int(np.isnan(rc).sum()))
for p in (0, 1, 5, 25, 50, 75, 99, 100):
    print(f"  p{p:<4} {np.nanpercentile(rc, p):.0f}")

print("\n=== coverage inside the frozen window ===")
w = ds.sel(time=slice("2024-01-01", "2026-09-30"))
print("  10-min records present:", w.sizes["time"])
print("  expected if complete:  ", int((np.datetime64('2026-09-26') -
                                       np.datetime64('2024-01-01'))
                                      / np.timedelta64(10, 'm')))
