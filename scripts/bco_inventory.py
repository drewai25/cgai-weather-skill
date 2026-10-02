"""O1/O2/O3.5 -- what the BCO radiation store says about itself.

Lazy only. Nothing is computed; the forecast fetch is running concurrently.
"""
import datetime
import intake

URL = "https://tcodata.mpimet.mpg.de/catalog.yaml"

print("accessed", datetime.datetime.now(datetime.timezone.utc).isoformat())
print("intake", intake.__version__)

cat = intake.open_catalog(URL)
print("top level:", list(cat))
print("BCO:", list(cat.BCO))

print("\n=== entry description ===")
try:
    for k, v in cat.BCO.radiation.describe().items():
        print(f"{k}: {str(v)[:400]}")
except Exception as e:
    print("describe failed:", type(e).__name__, e)

print("\n=== opening at PT1H ===")
try:
    ds = cat.BCO.radiation(time="PT1H").to_dask()
except Exception as e:
    print("parameterised open failed:", type(e).__name__, e)
    print("trying without the time parameter")
    ds = cat.BCO.radiation.to_dask()

print("TIME", str(ds.time.values[0]), "to", str(ds.time.values[-1]),
      "| n =", ds.sizes.get("time"))

print("\n=== variables as the store describes them ===")
for v in list(ds.data_vars) + list(ds.coords):
    a = ds[v].attrs
    print(f"{v:<22} {a.get('long_name','-'):<40} "
          f"{a.get('standard_name','-'):<32} {a.get('units','-'):<10} "
          f"{a.get('cell_methods','-')}")

print("\n=== raw_count, lazily ===")
if "raw_count" in ds:
    print(repr(ds.raw_count))
    print("chunks:", ds.raw_count.chunks)
    print("nbytes if realised:", ds.raw_count.nbytes)
else:
    print("raw_count NOT PRESENT in this dataset")

print("\n=== dataset attributes ===")
for k, v in ds.attrs.items():
    print(f"{k}: {str(v)[:300]}")
