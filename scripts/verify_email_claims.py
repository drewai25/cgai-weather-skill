#!/usr/bin/env python3
"""
verify_email_claims.py — check every factual claim going to Tunde against
the committed artifacts, not against the terminal history.

Each claim is recomputed from the files. Day counts are INCLUSIVE of both
endpoints throughout; a date difference is one less, and mixing the two is
the error this script exists to prevent.
"""
from __future__ import annotations
import csv, re, subprocess, sys
from datetime import date
from pathlib import Path

FROZEN_START, FROZEN_END = date(2024, 1, 1), date(2026, 9, 30)
inclusive = lambda a, b: (b - a).days + 1

ok = True
def check(label, got, want=None):
    global ok
    if want is None:
        print(f"  {label}: {got}")
        return
    good = got == want
    ok = ok and good
    print(f"  [{'PASS' if good else 'FAIL'}] {label}: {got}"
          f"{'' if good else f'  (expected {want})'}")

print("PROTOCOL")
text = Path("protocol/assessment_protocol.md").read_text()
heads = re.findall(r"^## Amendment (\d)", text, re.M)
check("amendment headings", heads, ["1", "2", "3", "4"])
check("A4 subsections", len(re.findall(r"^### A4\.\d", text, re.M)), 8)
check("A4.1 definition present", "all 24 hourly values" in text, True)

print("\nFROZEN WINDOW")
check("frozen days, inclusive", inclusive(FROZEN_START, FROZEN_END), 1004)

print("\nMEASURED WINDOWS (v3)")
rows = list(csv.DictReader(
    Path("data/raw/effective_window_by_variable_lead_v3.csv").open()))
check("combinations", len(rows), 42)
starts = [date.fromisoformat(r["effective_start"])
          for r in rows if r["effective_start"]]
check("rows with a start", len(starts), 42)
check("latest start", max(starts).isoformat(), "2024-03-13")
check("earliest start", min(starts).isoformat(), "2024-02-04")
check("shortest window, inclusive", inclusive(max(starts), FROZEN_END))
check("longest window, inclusive", inclusive(min(starts), FROZEN_END))
check("min carriers", min(int(r["n_models"]) for r in rows), 3)
check("all bound by archive",
      {r["binding_constraint"] for r in rows},
      {"forecast archive availability"})

print("\n  grid for the email (dates 2024, carriers in brackets):")
variables = list(dict.fromkeys(r["variable"] for r in rows))
print("  " + "variable".ljust(22)
      + "".join(f"L{l}".ljust(10) for l in range(1, 8)))
for v in variables:
    line = "  " + v[:21].ljust(22)
    for l in range(1, 8):
        r = next(x for x in rows
                 if x["variable"] == v and int(x["lead_day"]) == l)
        line += f"{r['effective_start'][5:]}[{r['n_models']}]".ljust(10)
    print(line)

print("\nMATRIX (v3 annotated)")
m = list(csv.DictReader(
    Path("data/raw/archive_variable_matrix_v3_annotated.csv").open()))
check("total rows", len(m), 294)
check("measured", sum(1 for r in m if r["first_complete_day"]), 201)
check("not exposed", sum(1 for r in m if not r["first_complete_day"]), 93)
check("floor rows", sum(1 for r in m if r["date_is_floor"] == "yes"), 28)

print("\nCOVERAGE CLAIMS")
exposed = {(r["model"], r["variable"], int(r["lead_day"]))
           for r in m if r["first_complete_day"]}
check("meteofrance max lead",
      max((l for (mo, _, l) in exposed if mo == "meteofrance_seamless"),
          default=0), 3)
check("icon max lead",
      max((l for (mo, _, l) in exposed if mo == "icon_seamless"),
          default=0), 6)
check("jma irradiance rows",
      sum(1 for (mo, v, _) in exposed
          if mo == "jma_seamless" and "radia" in v or
             mo == "jma_seamless" and "irradiance" in v), 0)

print("\nCOMMITS")
for h in ["125dfff", "ff706cd", "6f71a32"]:
    r = subprocess.run(["git", "cat-file", "-t", h],
                       capture_output=True, text=True)
    check(f"{h} exists", r.stdout.strip(), "commit")
dirty = subprocess.run(["git", "status", "--porcelain",
                        "protocol", "data/raw", "scripts"],
                       capture_output=True, text=True).stdout.strip()
check("protocol/data/scripts clean", dirty or "clean", "clean")

print("\nSCRIPTS COMPILE")
import py_compile
for f in sorted(Path("scripts").glob("*.py")):
    try:
        py_compile.compile(str(f), doraise=True)
    except Exception as e:
        check(f.name, f"FAILED: {e}", "compiles")
        continue
print(f"  all {len(list(Path('scripts').glob('*.py')))} scripts compile")

print("\n" + ("ALL CHECKS PASSED - safe to send"
              if ok else "SOME CHECKS FAILED - do not send yet"))
sys.exit(0 if ok else 1)
