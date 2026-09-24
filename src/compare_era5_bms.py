"""
compare_era5_bms.py - quantify ERA5 against station observations.

Protocol section 9. Purpose: measure, rather than assert, the cost of using a
~31 km reanalysis grid cell in place of the Grantley Adams station.

Temperature and cloud cover are compared hour by hour. Precipitation is compared
over each observation's own interval per Amendment 2, six-hour and twelve-hour
accumulations reported separately and pooled.

Run:  python src/compare_era5_bms.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
R = ROOT / "reports"


def stats(obs, ref, label):
    d = pd.DataFrame({"obs": obs, "ref": ref}).dropna()
    e = d.ref - d.obs
    return {"variable": label, "n": len(d),
            "MAE": round(float(e.abs().mean()), 3),
            "RMSE": round(float(np.sqrt((e ** 2).mean())), 3),
            "bias": round(float(e.mean()), 3),
            "correlation": round(float(d.obs.corr(d.ref)), 3),
            "obs_mean": round(float(d.obs.mean()), 3),
            "era5_mean": round(float(d.ref.mean()), 3)}


def main():
    bms = pd.read_parquet(P / "bms_hourly.parquet")
    era = pd.read_parquet(P / "era5_hourly.parquet")
    pcp = pd.read_parquet(P / "bms_precipitation_6h.parquet")

    j = bms.merge(era, on="time", how="inner")
    print("=" * 74)
    print("  ERA5 vs GRANTLEY ADAMS  (protocol section 9)")
    print(f"  {len(j)} matched hours  {j.time.min()} -> {j.time.max()}")
    print("=" * 74 + "\n")

    rows = [stats(j.temperature_c, j.era5_temperature_c, "temperature_c"),
            stats(j.cloud_cover_pct, j.era5_cloud_cover_pct, "cloud_cover_pct")]

    # precipitation over each record's own interval
    era_i = era.set_index("time").sort_index()
    sums = []
    for _, r in pcp.iterrows():
        w = era_i.loc[(era_i.index > r.interval_start) &
                      (era_i.index <= r.interval_end), "era5_precipitation_mm"]
        sums.append(w.sum() if len(w) else np.nan)
    pcp = pcp.assign(era5_mm=sums).dropna(subset=["era5_mm"])

    for period in (6.0, 12.0):
        s = pcp[pcp.period_hours == period]
        if len(s):
            rows.append(stats(s.precipitation_mm, s.era5_mm,
                              f"precipitation_{int(period)}h"))
    rows.append(stats(pcp.precipitation_mm, pcp.era5_mm, "precipitation_pooled"))

    hdr = f"{'variable':24}{'n':>6}{'MAE':>9}{'RMSE':>9}{'bias':>9}{'corr':>8}{'obs':>9}{'era5':>9}"
    print(hdr); print("-" * len(hdr))
    for s in rows:
        print(f"{s['variable']:24}{s['n']:>6}{s['MAE']:>9}{s['RMSE']:>9}"
              f"{s['bias']:>9}{s['correlation']:>8}{s['obs_mean']:>9}{s['era5_mean']:>9}")

    R.mkdir(exist_ok=True)
    (R / "era5_vs_bms.json").write_text(json.dumps({
        "grid_cell": {"era5_lat": 13.110721, "era5_lon": -59.50821,
                      "station_lat": 13.07333, "station_lon": -59.5,
                      "offset_km_approx": 4.3},
        "matched_hours": len(j), "results": rows}, indent=2))
    pd.DataFrame(rows).to_csv(R / "era5_vs_bms.csv", index=False)

    print("\n  bias = ERA5 minus observation. Positive means ERA5 reads high.")
    print(f"  written: reports/era5_vs_bms.csv and .json")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
