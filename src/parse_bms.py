"""
parse_bms.py - parse raw BMS SYNOP pages into an analysis-ready table.

Applies the exclusion and alignment rules in protocol/assessment_protocol.md,
Amendment 1:

  A1.1  A temperature record is a surface observation only where the geometry
        carries a third coordinate AND phenomenonTime is a point value equal to
        reportTime. Records failing either test are upper-air sounding levels;
        they are excluded here and retained in data/raw.

  A1.2  Precipitation is a SIX-HOUR accumulation ending at reportTime, with the
        interval in phenomenonTime as start/end. Each observation appears twice;
        records are deduplicated on (reportTime, phenomenonTime) and any
        disagreement between paired values is reported, never silently resolved.

Every record dropped is counted and reported. Nothing is discarded silently.

Run:  python src/parse_bms.py
"""
import json, glob, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bms"
OUT = ROOT / "data" / "processed"


def load(var):
    runs = sorted(RAW.glob("*/"))
    if not runs:
        sys.exit("no raw data - run src/fetch_bms.py first")
    latest = runs[-1]
    feats = []
    for p in sorted((latest / var).glob("page_*.geojson")):
        feats += json.loads(p.read_text())["features"]
    return feats, latest


def surface_point(f):
    """A1.1: three-coordinate geometry and a point phenomenonTime."""
    g = f.get("geometry") or {}
    coords = g.get("coordinates") or []
    p = f["properties"]
    has_elev = len(coords) >= 3
    is_point = "/" not in str(p.get("phenomenonTime", ""))
    matches = p.get("phenomenonTime") == p.get("reportTime")
    return has_elev and is_point and matches


def parse_point(var, label):
    feats, run = load(var)
    total = len(feats)

    kept = [f for f in feats if surface_point(f)]
    excluded = total - len(kept)

    df = pd.DataFrame([{
        "time": f["properties"]["reportTime"],
        label: f["properties"]["value"],
        "units": f["properties"]["units"],
        "elevation_m": f["geometry"]["coordinates"][2],
    } for f in kept])
    df["time"] = pd.to_datetime(df["time"], utc=True)

    before = len(df)
    df = df.drop_duplicates(subset="time", keep="first").sort_values("time")
    dropped_dupes = before - len(df)

    print(f"  {label}")
    print(f"      {total:>6} raw records")
    print(f"      {excluded:>6} excluded as non-surface (A1.1)")
    print(f"      {dropped_dupes:>6} duplicate timestamps removed")
    print(f"      {len(df):>6} surface observations retained")
    print(f"      {df.time.min()} -> {df.time.max()}")
    print(f"      units: {df.units.unique().tolist()}  "
          f"elevation range: {df.elevation_m.min()}-{df.elevation_m.max()} m")
    return df.drop(columns=["units", "elevation_m"]), {
        "variable": label, "raw": total, "excluded_non_surface": excluded,
        "duplicate_timestamps": dropped_dupes, "retained": len(df)}


def parse_precip():
    feats, run = load("precipitation_6h")
    total = len(feats)

    rows = []
    malformed = 0
    for f in feats:
        p = f["properties"]
        pt = str(p.get("phenomenonTime", ""))
        if "/" not in pt:
            malformed += 1
            continue
        start, end = pt.split("/")
        rows.append({"interval_start": start, "interval_end": end,
                     "time": p["reportTime"], "precipitation_mm": p["value"],
                     "units": p["units"], "record_id": p["id"]})

    df = pd.DataFrame(rows)
    for c in ("interval_start", "interval_end", "time"):
        df[c] = pd.to_datetime(df[c], utc=True)

    df["period_hours"] = (
        (df.interval_end - df.interval_start).dt.total_seconds() / 3600)

    # A1.2 - check paired values agree before deduplicating
    key = ["time", "interval_start", "interval_end"]
    spread = df.groupby(key).precipitation_mm.nunique()
    disagree = int((spread > 1).sum())

    df = df.sort_values("record_id").drop_duplicates(subset=key, keep="first")
    df = df.sort_values("time")

    print("  precipitation_6h")
    print(f"      {total:>6} raw records")
    print(f"      {malformed:>6} without an interval (excluded)")
    print(f"      {total - malformed - len(df):>6} duplicates removed")
    print(f"      {len(df):>6} distinct accumulations retained")
    print(f"      {disagree:>6} paired values disagreed"
          f"{'  <-- INVESTIGATE' if disagree else ''}")
    print(f"      {df.time.min()} -> {df.time.max()}")
    print(f"      accumulation periods present: "
          f"{sorted(df.period_hours.unique().tolist())} hours")
    print(f"      units: {df.units.unique().tolist()}")
    return df.drop(columns=["units", "record_id"]), {
        "variable": "precipitation_6h", "raw": total, "malformed": malformed,
        "duplicates_removed": total - malformed - len(df),
        "retained": len(df), "paired_disagreements": disagree}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    print("  PARSE BMS SYNOP - applying Amendment 1 exclusion rules")
    print("=" * 74 + "\n")

    temp, s1 = parse_point("temperature", "temperature_c")
    print()
    cloud, s2 = parse_point("cloud_cover", "cloud_cover_pct")
    print()
    precip, s3 = parse_precip()

    hourly = temp.merge(cloud, on="time", how="outer").sort_values("time")
    hourly.to_parquet(OUT / "bms_hourly.parquet", index=False)
    precip.to_parquet(OUT / "bms_precipitation_6h.parquet", index=False)
    (OUT / "bms_parse_summary.json").write_text(
        json.dumps({"variables": [s1, s2, s3]}, indent=2))

    span = hourly.time.max() - hourly.time.min()
    expected = int(span.total_seconds() / 3600) + 1
    print("\n" + "=" * 74)
    print(f"  hourly table: {len(hourly)} rows, {hourly.time.min()} -> {hourly.time.max()}")
    print(f"  expected hours in span: {expected}  "
          f"({expected - len(hourly)} missing)")
    print(f"  temperature missing: {hourly.temperature_c.isna().sum()}")
    print(f"  cloud cover missing: {hourly.cloud_cover_pct.isna().sum()}")
    print(f"\n  written: data/processed/bms_hourly.parquet")
    print(f"           data/processed/bms_precipitation_6h.parquet")
    print(f"           data/processed/bms_parse_summary.json")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
