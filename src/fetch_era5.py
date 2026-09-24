"""
fetch_era5.py - ERA5 reanalysis for the BMS observation window.

Source: ERA5 via Open-Meteo archive API. CC BY 4.0, attribution required.

Coordinates are the Grantley Adams station position. ERA5 resolves to ~31 km, so
the returned series describes a grid cell containing Barbados rather than the
station - see protocol section 5. Quantifying that difference is the purpose of
the comparison this data supports.

Variables and conventions (protocol section 4):
  temperature_2m       point, instantaneous at timestamp
  cloud_cover          point, total cloud fraction at timestamp
  precipitation        accumulated over the PRECEDING hour

The window is read from the parsed BMS table so the two sources cover exactly the
same period without a hardcoded date.

Run:  python src/fetch_era5.py
"""
import json
from pathlib import Path
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "era5"

LAT, LON = 13.07333, -59.5          # Grantley Adams
URL = "https://archive-api.open-meteo.com/v1/era5"
VARS = ["temperature_2m", "cloud_cover", "precipitation"]


def main():
    bms = pd.read_parquet(OUT / "bms_hourly.parquet")
    start = bms.time.min().strftime("%Y-%m-%d")
    end = bms.time.max().strftime("%Y-%m-%d")

    print("=" * 74)
    print("  ERA5 RETRIEVAL")
    print(f"  {LAT}N {LON}E   {start} -> {end}")
    print("=" * 74)

    params = {"latitude": LAT, "longitude": LON, "start_date": start,
              "end_date": end, "hourly": ",".join(VARS), "timezone": "UTC"}
    r = requests.get(URL, params=params, timeout=90)
    r.raise_for_status()
    payload = r.json()

    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "era5_hourly.json").write_text(json.dumps(payload))

    h = payload["hourly"]
    df = pd.DataFrame({
        "time": pd.to_datetime(h["time"], utc=True),
        "era5_temperature_c": h["temperature_2m"],
        "era5_cloud_cover_pct": h["cloud_cover"],
        "era5_precipitation_mm": h["precipitation"],
    })
    df.to_parquet(OUT / "era5_hourly.parquet", index=False)

    print(f"\n  units returned: {payload.get('hourly_units')}")
    print(f"  grid cell: {payload.get('latitude')}N {payload.get('longitude')}E"
          f"  elevation {payload.get('elevation')} m")
    print(f"  requested:  {LAT}N {LON}E  station elevation 57.7 m")
    print(f"\n  {len(df)} hourly rows  {df.time.min()} -> {df.time.max()}")
    for c in df.columns[1:]:
        print(f"    {c:26} missing {df[c].isna().sum():>4}")
    print(f"\n  written: data/processed/era5_hourly.parquet")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
