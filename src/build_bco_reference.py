#!/usr/bin/env python3
"""Build the hourly BCO irradiance reference from the PT10M store.

The hourly product MPI advertise does not exist -- PT1H and P1D return 404 --
so the hourly reference is constructed here and the construction is part of
the method.

CONVENTIONS, measured not assumed:
  - A BCO stamp is the CENTRE of its interval (from time_bounds). The six
    bins centred :05 .. :55 cover one clock hour.
  - The aggregate is LABELLED AT THE HOUR END, matching Open-Meteo's
    documented preceding-hour mean.
  - raw_count counts one-second samples per bin, ceiling 600, so an hour's
    denominator is 3,600.

AGGREGATION is a weighted mean, not a mean of means:
    hourly = sum(bin_mean * bin_raw_count) / sum(bin_raw_count)
Each bin mean represents raw_count seconds, so this reconstructs the mean of
the underlying observations. A quarter of bins hold fewer than 582 samples;
an unweighted mean would give those equal weight.

The weighted mean is the mean of the OBSERVED seconds, not of the hour. The
completeness column is what bounds that bias; both travel together.

Output: data/reference/bco_hourly.csv
    valid_time, ghi, dni, dhi, raw_count, complete_fraction, n_bins
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

URL = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
       "/airflow_production/BCO.radiation_x255960_0_PT10M.zarr")
OUT = Path("data/reference/bco_hourly.csv")
WINDOW = ("2024-01-01", "2026-09-30")
VARS = {"sw_down_global": "ghi",
        "sw_down_suntracker": "dni",
        "sw_down_diffuse": "dhi"}
SECONDS_PER_HOUR = 3600


def main() -> int:
    ds = xr.open_zarr(URL, consolidated=True).sel(time=slice(*WINDOW))
    t = pd.to_datetime(ds.time.values)
    rc = ds.raw_count.values.astype("float64")
    print(f"ten-minute bins: {len(t)}")

    # centre stamp -> the clock hour it belongs to, labelled at that hour's END
    hour_end = (t - pd.Timedelta(minutes=5)).floor("h") + pd.Timedelta(hours=1)

    frame = {"hour_end": hour_end, "rc": rc}
    for src, name in VARS.items():
        v = ds[src].values.astype("float64")
        # weight is zero wherever the value is absent, so a NaN bin cannot
        # contribute to the numerator or inflate the denominator
        w = np.where(np.isfinite(v), rc, 0.0)
        frame[f"{name}_wsum"] = np.where(np.isfinite(v), v * rc, 0.0)
        frame[f"{name}_w"] = w
    df = pd.DataFrame(frame)

    agg = {"raw_count": ("rc", "sum"), "n_bins": ("rc", "size")}
    for name in VARS.values():
        agg[f"{name}_wsum"] = (f"{name}_wsum", "sum")
        agg[f"{name}_w"] = (f"{name}_w", "sum")
    g = df.groupby("hour_end").agg(**agg)

    out = pd.DataFrame(index=g.index)
    for name in VARS.values():
        out[name] = np.where(g[f"{name}_w"] > 0,
                             g[f"{name}_wsum"] / g[f"{name}_w"].replace(0, np.nan),
                             np.nan)
    out["raw_count"] = g["raw_count"].astype("int64")
    out["complete_fraction"] = (g["raw_count"] / SECONDS_PER_HOUR).round(4)
    out["n_bins"] = g["n_bins"].astype("int64")
    out.index.name = "valid_time"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT)

    print(f"hours written: {len(out)}")
    print(f"  all six bins present: {int((out.n_bins == 6).sum())}")
    for bar, label in [(1.00, "100%"), (0.95, "95%"), (0.90, "90%"),
                       (0.50, "50%"), (0.0001, "any")]:
        n = int((out.complete_fraction >= bar).sum())
        print(f"  complete >= {label:<5} {n:>6}  {100*n/len(out):5.1f}%")
    ok = out[out.complete_fraction >= 0.90]
    print(f"\nat the 90% bar: {len(ok)} hours")
    print(f"  ghi  non-null {int(ok.ghi.notna().sum())}  "
          f"min {ok.ghi.min():.1f}  max {ok.ghi.max():.1f}  "
          f"mean {ok.ghi.mean():.1f}")
    print(f"  dni  non-null {int(ok.dni.notna().sum())}")
    print(f"  dhi  non-null {int(ok.dhi.notna().sum())}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
