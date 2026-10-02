#!/usr/bin/env python3
"""Score forecast temperature against ERA5. The first real skill numbers.

JOIN, per A5.14: Open-Meteo temperature_2m is INSTANTANEOUS at the label and
ERA5 temperature is instantaneous at the label, so these pair directly on
valid_time. No interval alignment is needed for this variable; irradiance and
precipitation are different and are scored separately.

BASELINES, per protocol section 7:
  persistence   the reference value 24*lead hours earlier -- what you would
                have said with no forecast at all, at the same lead
  climatology   the mean of the reference for that hour-of-day and
                month-of-year, computed over the window

SKILL, per gate_thresholds.json:
    SS = 1 - MAE_forecast / MAE_baseline

Reported per (model, lead day) with n and both baselines. Nothing is
aggregated across leads or models.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

FC = Path("data/forecasts")
REF = Path("data/reference/era5")
OUT = Path("reports/skill_temperature_common.csv" if "--common" in __import__("sys").argv else "reports/skill_temperature.csv")
# PRIMARY is own-sample, raw MAE, exactly as pre-registered in A5 and
# gate_thresholds.json. COMMON and the debiased columns are SECONDARY and
# were added on 2 October AFTER the primary run, which is declared rather
# than hidden. Set by argv so both are produced from one script.
COMMON = "--common" in __import__("sys").argv
VARIABLE = "temperature_2m"


def load_reference() -> pd.Series:
    frames = []
    for p in sorted(REF.glob("era5_2*.csv")):
        d = pd.read_csv(p)
        frames.append(d[d.variable == VARIABLE])
    r = pd.concat(frames)
    r["valid_time"] = pd.to_datetime(r.valid_time)
    r = r.dropna(subset=["value"]).set_index("valid_time").value.sort_index()
    print(f"reference: {len(r)} hours, {r.index[0]} .. {r.index[-1]}")
    return r


def load_forecasts() -> pd.DataFrame:
    frames = []
    for p in sorted(FC.glob("*/*.csv")):
        d = pd.read_csv(p, usecols=["model", "variable", "lead_day",
                                    "valid_time", "value"])
        d = d[d.variable == VARIABLE]
        if len(d):
            frames.append(d)
    f = pd.concat(frames, ignore_index=True)
    f["valid_time"] = pd.to_datetime(f.valid_time)
    f = f.dropna(subset=["value"])
    print(f"forecasts: {len(f)} rows, "
          f"{f.model.nunique()} models, leads {sorted(f.lead_day.unique())}")
    return f


def main() -> int:
    ref = load_reference()
    fc = load_forecasts()

    # climatology: mean reference by (month, hour of day)
    rdf = ref.rename("ref").to_frame()
    rdf["month"], rdf["hour"] = rdf.index.month, rdf.index.hour
    clim = rdf.groupby(["month", "hour"]).ref.mean()
    print(f"climatology: {len(clim)} month-hour cells")

    # common sample: hours where EVERY model has a forecast at EVERY lead.
    # Without this, models are scored on different hours and the comparison
    # between them is not quite a comparison.
    if COMMON:
        sets = [set(g.valid_time) for _, g in fc.groupby(["model", "lead_day"])]
        common = set.intersection(*sets) & set(ref.index)
        print(f"common sample: {len(common)} hours across all model-lead cells")
        fc = fc[fc.valid_time.isin(common)]

    # common sample: hours where EVERY model has a forecast at EVERY lead.
    # Without this, models are scored on different hours and the comparison
    # between them is not quite a comparison.
    if COMMON:
        sets = [set(g.valid_time) for _, g in fc.groupby(["model", "lead_day"])]
        common = set.intersection(*sets) & set(ref.index)
        print(f"common sample: {len(common)} hours across all model-lead cells")
        fc = fc[fc.valid_time.isin(common)]

    # common sample: hours where EVERY model has a forecast at EVERY lead.
    # Without this, models are scored on different hours and the comparison
    # between them is not quite a comparison.
    if COMMON:
        sets = [set(g.valid_time) for _, g in fc.groupby(["model", "lead_day"])]
        common = set.intersection(*sets) & set(ref.index)
        print(f"common sample: {len(common)} hours across all model-lead cells")
        fc = fc[fc.valid_time.isin(common)]

    rows = []
    for (model, lead), grp in fc.groupby(["model", "lead_day"]):
        j = grp.set_index("valid_time").join(ref.rename("ref"), how="inner")
        j = j.dropna(subset=["ref"])
        if j.empty:
            continue
        # persistence at this lead: the reference 24*lead hours earlier
        pers = ref.reindex(j.index - pd.Timedelta(hours=24 * int(lead)))
        j["pers"] = pers.values
        j["clim"] = [clim.get((t.month, t.hour), np.nan) for t in j.index]
        j = j.dropna(subset=["pers", "clim"])
        if len(j) < 200:
            rows.append(dict(model=model, lead_day=lead, n=len(j),
                             note="insufficient pairs (<200)"))
            continue
        err_f, err_p, err_c = j.value - j.ref, j.pers - j.ref, j.clim - j.ref
        mae_f, mae_p, mae_c = err_f.abs().mean(), err_p.abs().mean(), err_c.abs().mean()
        # bias-corrected: mean absolute deviation about each series' own mean
        # error. A constant offset is the easiest thing a downstream model
        # removes, so scoring it as forecast error overstates the penalty.
        dmae_f = (err_f - err_f.mean()).abs().mean()
        dmae_p = (err_p - err_p.mean()).abs().mean()
        rows.append(dict(
            model=model, lead_day=int(lead), n=len(j),
            mae_forecast=round(mae_f, 4),
            rmse_forecast=round(float(np.sqrt(((j.value - j.ref) ** 2).mean())), 4),
            bias=round(float((j.value - j.ref).mean()), 4),
            mae_persistence=round(mae_p, 4),
            mae_climatology=round(mae_c, 4),
            ss_vs_persistence=round(1 - mae_f / mae_p, 4),
            ss_vs_climatology=round(1 - mae_f / mae_c, 4),
            mae_debiased=round(dmae_f, 4),
            ss_debiased_vs_pers=round(1 - dmae_f / dmae_p, 4),
            first=str(j.index.min())[:10], last=str(j.index.max())[:10],
        ))

    out = pd.DataFrame(rows).sort_values(["model", "lead_day"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    pd.set_option("display.width", 200, "display.max_columns", 20)
    print("\n" + out.to_string(index=False))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
