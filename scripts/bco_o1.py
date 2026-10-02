"""O1 -- can we read the BCO reference at all?

Metadata only. Nothing realises a full array: an earlier version called
ds.time.values[0], which pulls the WHOLE time coordinate into memory before
indexing it. At 1-second resolution that is ~350 million timestamps and it
was killed by the OOM reaper. Index first, realise one element.
"""
import datetime
import intake

print("accessed", datetime.datetime.now(datetime.timezone.utc).isoformat())
cat = intake.open_catalog("https://tcodata.mpimet.mpg.de/catalog.yaml")
print("BCO entries:", list(cat.BCO))

print("\nopening radiation at PT1H")
ds = cat.BCO.radiation(time="PT1H").to_dask()

n = ds.sizes.get("time")
print("TIME DIMENSION:", n)
if n and n > 5_000_000:
    print("  -> this is NOT hourly. The time parameter did not take.")
    print("  -> stopping before anything touches it.")
    raise SystemExit(0)

print("first:", ds.time[0].values, " last:", ds.time[-1].values)

print("\nvariables")
for v in list(ds.data_vars) + list(ds.coords):
    a = ds[v].attrs
    print(f"  {v:<22} {a.get('long_name','-'):<38} "
          f"{a.get('standard_name','-'):<30} {a.get('units','-'):<9} "
          f"{a.get('cell_methods','-')}")

print("\nraw_count")
if "raw_count" in ds:
    print("  dtype", ds.raw_count.dtype, " shape", ds.raw_count.shape)
    print("  chunks", ds.raw_count.chunks)
    print("  nbytes if realised", ds.raw_count.nbytes)
    print("  attrs", dict(ds.raw_count.attrs))
else:
    print("  NOT PRESENT")

print("\ndataset attrs")
for k, v in ds.attrs.items():
    print(f"  {k}: {str(v)[:200]}")
