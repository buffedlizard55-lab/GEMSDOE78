#!/usr/bin/env python3
"""Independent verification of a candidate GeoTIFF against the pinned sample grid
(use this on the file you are about to upload; it does not import the lane code)."""
import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np, rasterio

def main(path):
    path = Path(path)
    root = Path(__file__).resolve().parents[1]
    with rasterio.open(root / "data/bridge/sample_submission.tif") as ref:
        fp = np.isfinite(ref.read(1)); ref_meta = (str(ref.crs), ref.height, ref.width, tuple(ref.transform)[:6])
    with rasterio.open(root / "data/bridge/existing_faults.tif") as c:
        cat = c.read(1) > 0
    with rasterio.open(path) as ds:
        a = ds.read(1); meta = (str(ds.crs), ds.height, ds.width, tuple(ds.transform)[:6]); count = ds.count; dt = ds.dtypes[0]; nod = ds.nodata
    checks = {
        "single_band": count == 1, "float32": dt == "float32",
        "crs_EPSG:32611": meta[0] == "EPSG:32611" == ref_meta[0],
        "shape_3730x3292": (meta[1], meta[2]) == (3730, 3292) == (ref_meta[1], ref_meta[2]),
        "transform_(100,0,243350,0,-100,4508550)": meta[3] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0) == ref_meta[3],
        "no_nodata_tag": nod is None,
        "all_finite": bool(np.isfinite(a).all()),
        "no_nan_inside_footprint": int(np.isnan(a[fp]).sum()) == 0,
        "values_in_[0,1]": bool(a.min() >= 0.0 and a.max() <= 1.0),
        "binary_values_only": set(np.unique(a).tolist()) <= {0.0, 1.0},
        "zero_outside_footprint": bool((a[~fp] == 0).all()),
        "zero_on_catalogue": int((a[cat] > 0).sum()) == 0,
    }
    out = dict(file=path.name, bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               positive_pixels=int((a > 0).sum()), footprint_fraction=float((a[fp] > 0).mean()),
               checks=checks, all_passed=all(checks.values()))
    z = path.with_suffix(".zip")
    if z.exists():
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist(); same = len(names) == 1 and zf.read(names[0]) == path.read_bytes()
        out["zip"] = dict(file=z.name, single_tif_byte_identical=same, sha256=hashlib.sha256(z.read_bytes()).hexdigest())
    print(json.dumps(out, indent=1)); return 0 if out["all_passed"] else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
