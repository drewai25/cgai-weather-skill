#!/usr/bin/env python3
"""
annotate_v3_matrix.py — mark the rows whose date is a FLOOR, not a measurement.

measure_complete_start.py clamps its scan to 30 days before the frozen window.
Where a model was already complete at that clamp, the recorded date is the
scan floor (2023-12-02), not the archive's real first complete day, which lies
somewhere earlier and does not matter because the frozen window binds there.

That distinction lived only in the terminal output. Written to CSV without it,
archive_variable_matrix_v3.csv asserts a measured date it never measured. This
reads the notes back out of the run log and adds two columns, so the artifact
states exactly what was established and nothing more.

No network. Reads reports/measure_complete_start.log, writes
data/raw/archive_variable_matrix_v3_annotated.csv.
"""
import csv, re, pathlib

LOG = pathlib.Path("reports/measure_complete_start.log")
CSV = pathlib.Path("data/raw/archive_variable_matrix_v3.csv")

notes = {}
for line in LOG.read_text().splitlines():
    p = line.split(None, 5)
    if len(p) < 6 or not p[2].isdigit():
        continue
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p[3]):
        continue
    notes[(p[0], p[1], p[2])] = p[5].strip()

rows = list(csv.DictReader(CSV.open()))
out = CSV.with_name("archive_variable_matrix_v3_annotated.csv")
n_floor = n_noted = 0
with out.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(list(rows[0].keys()) + ["date_is_floor", "note"])
    for r in rows:
        note = notes.get((r["model"], r["variable"], r["lead_day"]), "")
        floor = "yes" if "at or before" in note else "no"
        n_floor += floor == "yes"
        n_noted += bool(note)
        w.writerow(list(r.values()) + [floor, note])

print(f"{len(rows)} rows, {n_noted} matched to a log note, "
      f"{n_floor} marked date_is_floor=yes")
print(f"wrote {out}")
