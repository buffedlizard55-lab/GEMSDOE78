#!/usr/bin/env python3
"""Independent, fail-closed verification against the SHA-pinned sample grid.

This project's binary/all-finite/zero-outside policy is intentionally stricter
than a general [0, 1] raster. PASS is local format compliance, not portal acceptance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path):
    path = Path(path)
    out = dict(file=path.name, checks={}, all_passed=False)
    try:
        manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
        entries = {e["id"]: e for e in manifest["files"]}
        refs = {}
        for name in ("sample_submission", "existing_faults"):
            entry = entries[name]
            ref_path = ROOT / "data" / entry["dest"]
            if sha256(ref_path) != entry["sha256"]:
                raise ValueError(f"{name}: reference SHA256 mismatch")
            refs[name] = ref_path
        with rasterio.open(refs["sample_submission"]) as ref:
            fp = np.isfinite(ref.read(1))
            ref_meta = (ref.crs, ref.shape, ref.transform)
            if ref.count != 1:
                raise ValueError("sample must be single-band")
        with rasterio.open(refs["existing_faults"]) as cat:
            if cat.count != 1 or (cat.crs, cat.shape, cat.transform) != ref_meta:
                raise ValueError("catalogue/reference grid mismatch")
            catalogue = cat.read(1) > 0
        with rasterio.open(path) as ds:
            a = ds.read(1)
            meta = (ds.crs, ds.shape, ds.transform)
            checks = dict(single_band=ds.count == 1, float32=ds.dtypes == ("float32",),
                          crs_EPSG_32611=meta[0] is not None and meta[0].to_epsg() == 32611 == ref_meta[0].to_epsg(),
                          shape_3730x3292=meta[1] == (3730, 3292) == ref_meta[1],
                          transform_matches_sample=meta[2] == ref_meta[2] and tuple(meta[2])[:6] == (100., 0., 243350., 0., -100., 4508550.),
                          no_nodata_tag=ds.nodata is None,
                          reference_hashes_verified=True)
        shape_matches = a.shape == fp.shape
        checks.update({
            "all_finite": bool(np.isfinite(a).all()),
            "no_nan_inside_footprint": shape_matches and not bool(np.isnan(a[fp]).any()),
            "values_in_[0,1]": bool(np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1),
            "binary_values_only": bool(np.all((a == 0) | (a == 1))),
            "zero_outside_footprint": shape_matches and bool((a[~fp] == 0).all()),
            "zero_on_catalogue": shape_matches and bool((a[catalogue] == 0).all()),
        })
        out.update(bytes=path.stat().st_size, sha256=sha256(path),
                   positive_pixels=int((a > 0).sum()),
                   footprint_fraction=float((a[fp] > 0).mean()) if shape_matches else None,
                   checks=checks, all_passed=all(checks.values()))
        zpath = path.with_suffix(".zip")
        if zpath.exists():
            with zipfile.ZipFile(zpath) as archive:
                same = archive.namelist() == [path.name] and archive.read(path.name) == path.read_bytes()
            out["zip"] = dict(file=zpath.name, single_tif_byte_identical=same, sha256=sha256(zpath))
            out["all_passed"] = out["all_passed"] and same
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError, rasterio.errors.RasterioError) as exc:
        out.update(all_passed=False, error=f"{type(exc).__name__}: {exc}")
    return out


def main(path):
    report = verify(path)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
