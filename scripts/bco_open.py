"""Open the BCO hourly radiation store directly, bypassing intake.

WHY NOT INTAKE
The catalog templates the store URL as
    BCO.radiation_{{rev}}_{{build}}{% if time != 'raw' %}_{{time}}{% endif %}.zarr
MPI pin intake==2.0.8. Under 2.0.9 that conditional does not render, the URL
collapses to the raw store, and opening it realises a 285,915,926-point time
coordinate -- 2.13 GiB, which killed the process twice.

FURTHER: the PT1H and P1D stores the catalog advertises DO NOT EXIST.
safer and better provenance: it names the exact revision and build.
"""
import xarray as xr

BASE = ("https://swift.dkrz.de/v1/dkrz_948e7d4bbfbb445fbff5315fc433e36a"
        "/airflow_production")
REV, BUILD, AGG = "x255960", 0, "PT10M"
URL = f"{BASE}/BCO.radiation_{REV}_{BUILD}_{AGG}.zarr"

print("store:", URL)
ds = xr.open_zarr(URL, consolidated=True)

print("time dimension:", ds.sizes.get("time"))
print("first:", ds.time[0].values, " last:", ds.time[-1].values)

print("\nvariables")
for v in list(ds.data_vars) + list(ds.coords):
    a = ds[v].attrs
    print(f"  {v:<20} {a.get('long_name','-'):<40} "
          f"{a.get('standard_name','-'):<28} {a.get('units','-'):<9} "
          f"{a.get('cell_methods','-')}")

print("\nraw_count")
if "raw_count" in ds:
    print("  dtype", ds.raw_count.dtype, " shape", ds.raw_count.shape)
    print("  attrs", dict(ds.raw_count.attrs))
else:
    print("  NOT PRESENT")

print("\ntime_bounds present:", "time_bounds" in ds)

print("\ndataset attrs")
for k, v in ds.attrs.items():
    print(f"  {k}: {str(v)[:200]}")
