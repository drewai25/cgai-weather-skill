"""O6/O7 -- build hourly completeness from the ten-minute bins.

Timestamp convention established from time_bounds: a BCO stamp is the CENTRE
of its interval, so the six bins centred :05 .. :55 cover one clock hour.
The hourly value is LABELLED AT THE HOUR END, matching Open-Meteo's
backward-averaged convention.

Completeness is sum(raw_count) over the six bins, against 3600.
"""
import numpy as np
import pandas as pd
import xarray as xr

URL = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
       "/airflow_production/BCO.radiation_x255960_0_PT10M.zarr")
ds = xr.open_zarr(URL, consolidated=True).sel(time=slice("2024-01-01",
                                                         "2026-09-30"))

t = pd.to_datetime(ds.time.values)
rc = ds.raw_count.values
print("ten-minute bins:", len(t))
print("bins with raw_count 0:", int((rc == 0).sum()),
      f"({100*(rc==0).mean():.1f}%)")

# centre stamp -> the hour it belongs to, labelled at that hour's END
hour_end = (t - pd.Timedelta(minutes=5)).floor("h") + pd.Timedelta(hours=1)
df = pd.DataFrame({"hour_end": hour_end, "rc": rc,
                   "ghi": ds.sw_down_global.values})
g = df.groupby("hour_end").agg(bins=("rc", "size"), raw=("rc", "sum"),
                               ghi_n=("ghi", "count"))
print("\nhours formed:", len(g))
print("hours with all six bins:", int((g.bins == 6).sum()))

for thr, label in [(3600, "100%"), (3420, "95%"), (3240, "90%"),
                   (2700, "75%"), (1800, "50%"), (1, "any data")]:
    n = int((g.raw >= thr).sum())
    print(f"  raw_count >= {thr:<5} ({label:<8}) {n:>6}  {100*n/len(g):5.1f}%")

print("\nmonthly completeness at the 90% bar")
m = g.assign(month=g.index.to_period("M")).groupby("month").apply(
    lambda x: pd.Series({"hours": len(x),
                         "pass90": int((x.raw >= 3240).sum())}),
    include_groups=False)
m["pct"] = (100 * m.pass90 / m.hours).round(1)
print(m.to_string())
