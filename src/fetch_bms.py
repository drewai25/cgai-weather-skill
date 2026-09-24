"""
fetch_bms.py - retrieve BMS SYNOP observations, Grantley Adams.

Source: Barbados Meteorological Services WIS 2.0 node, OGC API Features.
Station WIGOS 0-52-130-78954, 13.073N 59.500W, 62.1 m. Licence CC BY 4.0.

Timestamp semantics, established by inspection 24 Sep 2026:
  air_temperature    - point observation, phenomenonTime == reportTime
  cloud_cover_total  - point observation, phenomenonTime == reportTime
  total_precipitation_or_total_water_equivalent
                     - SIX-HOUR ACCUMULATION ending at reportTime; the interval
                       is carried in phenomenonTime. Units kg m-2 == mm.
                       Must never be joined to a single hour of reanalysis.

Raw pages are written untouched; parsing is a separate stage.
"""
import json, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
import requests

BASE = "https://barbadosweatherdata.org/oapi/collections"
COLL = "urn:wmo:md:bb-barbadosmetservices:surface-based-observations.synop"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bms"
PAGE, PAUSE, TIMEOUT, RETRIES = 500, 0.3, 30, 3

VARIABLES = [
    ("air_temperature", "temperature", "point", None),
    ("cloud_cover_total", "cloud_cover", "point", None),
    ("total_precipitation_or_total_water_equivalent",
     "precipitation_6h", "accumulation", 6),
]


def get(params):
    url = f"{BASE}/{COLL}/items?{urlencode(params)}"
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == RETRIES:
                raise RuntimeError(f"failed: {url}") from e
            print(f"      attempt {attempt} failed; retrying")
            time.sleep(2 ** attempt)


def fetch(bms_name, short, run_dir):
    print(f"\n  {bms_name}")
    expected = int(get({"name": bms_name, "limit": 1})["numberMatched"])
    if not expected:
        print("      no records - check the name")
        return {"variable": bms_name, "expected": 0, "retrieved": 0, "pages": 0}
    print(f"      {expected} records")

    d = run_dir / short
    d.mkdir(parents=True, exist_ok=True)
    got, page, seen = 0, 0, set()

    while got < expected:
        p = get({"name": bms_name, "limit": PAGE, "offset": got,
                 "sortby": "reportTime"})
        feats = p.get("features", [])
        if not feats:
            print(f"      empty page at offset {got}; stopping")
            break
        page += 1
        (d / f"page_{page:04d}.geojson").write_text(json.dumps(p))
        ids = {f.get("id") for f in feats}
        if ids & seen:
            print(f"      WARNING {len(ids & seen)} duplicate ids at {got}")
        seen |= ids
        got += len(feats)
        print(f"      page {page:>3}  {got:>6}/{expected}", end="\r")
        time.sleep(PAUSE)

    state = "complete" if got >= expected else "INCOMPLETE"
    print(f"      page {page:>3}  {got:>6}/{expected}   {state}")
    return {"variable": bms_name, "short_name": short, "expected": expected,
            "retrieved": got, "unique_ids": len(seen), "pages": page}


def main():
    t0 = datetime.now(timezone.utc)
    run_dir = RAW / t0.strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 74)
    print("  BMS SYNOP RETRIEVAL - Grantley Adams (0-52-130-78954)")
    print(f"  {t0.isoformat()}")
    print("=" * 74)

    old = get({"limit": 1, "sortby": "reportTime"})
    new = get({"limit": 1, "sortby": "-reportTime"})
    window = {"oldest": old["features"][0]["properties"]["reportTime"],
              "newest": new["features"][0]["properties"]["reportTime"],
              "collection_records": int(old["numberMatched"])}
    print(f"\n  Window: {window['oldest']} -> {window['newest']}")
    print(f"  Collection holds {window['collection_records']} records")

    results = [fetch(n, s, run_dir) for n, s, _, _ in VARIABLES]

    (run_dir / "manifest.json").write_text(json.dumps({
        "source": {"name": "Barbados Meteorological Services",
                   "station": "Grantley Adams", "wigos_id": "0-52-130-78954",
                   "latitude": 13.07333, "longitude": -59.5,
                   "elevation_m": 62.1, "licence": "CC BY 4.0"},
        "retrieval": {"started_utc": t0.isoformat(),
                      "completed_utc": datetime.now(timezone.utc).isoformat(),
                      "page_size": PAGE, "exposed_window_at_fetch": window},
        "variables": results,
        "timestamp_semantics": {
            n: {"kind": k, "period_hours": h} for n, _, k, h in VARIABLES},
    }, indent=2))

    print("\n" + "=" * 74)
    for r in results:
        ok = "ok" if r["retrieved"] == r["expected"] else "INCOMPLETE"
        print(f"  {r['variable'][:50]:52} {r['retrieved']:>6}  {ok}")
    print(f"\n  Manifest: {(run_dir / 'manifest.json').relative_to(ROOT)}")
    print("=" * 74)
    return 0 if all(r["retrieved"] == r["expected"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
