"""Data access for lane H78 (GEMSDOE78).

All inputs are SHA-256 pinned owner mirrors of DrivenData competition files (see
``registry/data_manifest.json``). The 19-band feature stack is read once, nodata
cells (sentinel -3.4028235e+38, 1,521 of them inside the footprint) are filled
with the nearest valid value so that spatial filters do not ring, and the result
is cached as a float32 memmap ``data/processed/stack19.npy`` (C, H, W).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "training_features.tif"
BRIDGE = ROOT / "data" / "bridge"
PROC = ROOT / "data" / "processed"
STACK = PROC / "stack19.npy"
SENTINEL = -3.0e38

BAND_NAMES = [
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15", "cond_surf",
    "iso_grav_anom_hg", "det_elev_slope",
]
# bands with heavy right tails: log1p(max(x,0)) before use as raw features
LOG_BANDS = {"tmi_hg", "iso_grav_anom_slope", "deq_n100a15", "depth_to_base_surf",
             "det_elev_slope", "ieq_n100a15"}

EXPECTED_SHA = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs() -> dict:
    out = {}
    for name, exp in EXPECTED_SHA.items():
        p = RAW if name == "training_features.tif" else BRIDGE / name
        got = sha256(p)
        out[name] = dict(sha256=got, expected=exp, ok=got == exp, bytes=p.stat().st_size)
        if got != exp:
            raise RuntimeError(f"{name}: sha256 {got} != pinned {exp}")
    return out


def build_stack(force: bool = False) -> Path:
    """Nodata-filled float32 memmap of the 19 bands (C, H, W)."""
    PROC.mkdir(parents=True, exist_ok=True)
    if STACK.exists() and not force:
        return STACK
    with rasterio.open(RAW) as ds:
        C, H, W = ds.count, ds.height, ds.width
        mm = np.lib.format.open_memmap(STACK, mode="w+", dtype=np.float32, shape=(C, H, W))
        fill_idx = None
        receipt = []
        for i in range(C):
            a = ds.read(i + 1)
            bad = ~np.isfinite(a) | (a <= SENTINEL)
            n_bad = int(bad.sum())
            if n_bad:
                if fill_idx is None or n_bad != fill_idx[0]:
                    # nearest valid-cell indices (recomputed only when the mask changes)
                    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
                    fill_idx = (n_bad, idx)
                a = a[fill_idx[1][0], fill_idx[1][1]]
            if BAND_NAMES[i] in LOG_BANDS:
                a = np.log1p(np.maximum(a, 0.0)).astype(np.float32)
            mm[i] = a
            receipt.append(dict(band=i + 1, name=BAND_NAMES[i], nodata_filled=n_bad,
                                log1p="yes" if BAND_NAMES[i] in LOG_BANDS else "no",
                                min=float(a.min()), max=float(a.max())))
            del a
        mm.flush()
        del mm
    (PROC / "stack19_receipt.json").write_text(json.dumps(receipt, indent=2))
    return STACK


def load_stack() -> np.ndarray:
    return np.load(build_stack(), mmap_mode="r")
