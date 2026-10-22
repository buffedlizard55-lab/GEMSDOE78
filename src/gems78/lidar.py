"""Lidar scarp morphology features for H79-LS.

Reads the restored 12-band uint8 lidar_scarp_features_u8.tif (USGS 3DEP 1m DEM
derived, 100m resampled). Bands 1-11 are morphometrics, band 12 is valid mask
(255 = coverage, 0 = no lidar). We expose 11 normalized features (band value /
255) plus one binary valid indicator, total 12. For cells outside footprint or
where valid==0, the morphometric values are already 0 in the source; we keep
them as 0 (the learner can treat 0 as missing when valid==0).

No catalogue information is used; leakage canary must stay clean.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

LIDAR_BANDS = [
    "lidar_ex_max", "lidar_ex_mean", "lidar_step_max",
    "lidar_lapneg_max", "lidar_lappos_max",
    "lidar_downface_max", "lidar_upface_max",
    "lidar_cross_max", "lidar_relief",
    "lidar_coh100", "lidar_strike",
]
# valid is separate
LIDAR_VALID = "lidar_valid"

# Descriptions in source file (see data/external/lidar_scarp_features_u8.tif)
SRC_DESCRIPTIONS = (
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
    "downface_max", "upface_max", "cross_max", "relief", "coh100", "strike", "valid"
)

def lidar_feature_names() -> list[str]:
    return LIDAR_BANDS + [LIDAR_VALID]

def load_lidar_stack(cache_root: Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return (lidar_stack, footprint_mask) where lidar_stack is (12, H, W) uint8.

    We read from .cache/gems_data/external/lidar_scarp_features_u8.tif if present,
    else data/external/lidar_scarp_features_u8.tif.
    """
    from .data import PROC  # noqa

    candidates = []
    if cache_root:
        candidates.append(Path(cache_root) / "external/lidar_scarp_features_u8.tif")
    candidates += [
        Path(".cache/gems_data/external/lidar_scarp_features_u8.tif"),
        Path("data/external/lidar_scarp_features_u8.tif"),
        Path("data/bridge/external/lidar_scarp_features_u8.tif"),
    ]
    for p in candidates:
        if p.exists():
            src = p
            break
    else:
        raise FileNotFoundError("lidar_scarp_features_u8.tif not found; run restore_data.py --group external")

    with rasterio.open(src) as ds:
        assert (ds.height, ds.width) == (3730, 3292), f"lidar shape {ds.height}x{ds.width}"
        assert str(ds.crs) == "EPSG:32611"
        stack = ds.read()  # (12, H, W) uint8
    # Also need footprint for later? caller will mask
    return stack, src

def extract_lidar_for_footprint(stack: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Convert 12-band uint8 stack to (n_footprint, 12) float32 in footprint row-major order.

    Stack shape (12, H, W) uint8, footprint bool (H,W). Output columns 0-10 are
    morphometrics /255, column 11 is valid indicator (0 or 1).
    """
    assert stack.shape[0] == 12
    assert stack.shape[1:] == footprint.shape
    ys, xs = np.nonzero(footprint)
    n = ys.size
    out = np.empty((n, 12), dtype=np.float32)
    for i in range(11):
        band = stack[i]  # 0-indexed, i=0 is ex_max
        out[:, i] = (band[ys, xs].astype(np.float32) / 255.0)
    # valid band (index 11)
    valid = stack[11]
    # valid is 0 or 255; map to 0/1
    out[:, 11] = (valid[ys, xs] > 127).astype(np.float32)
    return out
