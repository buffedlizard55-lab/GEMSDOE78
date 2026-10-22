"""Across-strike missing-tooth features from the visible catalogue only.

Basin-and-Range normal faults in a mechanical layer are spaced quasi-regularly
(Ackermann, Schlische & Withjack 2001, JSG 23:1803; Soliva & Benedicto 2006,
JGR 10.1029/2004JB003507). A strand missing from the catalogue leaves a gap
about twice as wide as that spacing, so the Euclidean distance to the nearest
*visible* fault at the missing strand is about one spacing (lambda), whereas
the midpoint of a complete pair sits at about lambda/2.

Every output is a function of the boolean visible mask alone. The withheld
holdout components must already have been removed by the caller. Raw distance
and fault density are not returned: the kernels are near zero on a mapped
trace and in an ordinary trough, and peak in a double-width gap.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

FEATURE_NAMES = (
    "tooth_gap1",
    "tooth_gap15",
    "tooth_width_ratio",
    "tooth_lambda_px",
    "tooth_support",
    "tooth_cv",
)

# Separations below 800 m are relay/damage-zone contacts, not array spacing.
# Separations above 10 km are not a local array.
MIN_SPACING_PX = 8.0
MAX_SPACING_PX = 100.0
BIN_PX = 2.0


def _pairwise_separations(visible: np.ndarray):
    """Voronoi-boundary separations between distinct 8-connected components.

    Returns labels, distance-to-visible, and flat arrays (comp_a, comp_b, spacing_px)
    for each unordered adjacent pair of Voronoi cells. spacing = d_a + d_b, which
    equals the Euclidean separation of two parallel strands.
    """
    vis = np.asarray(visible, bool)
    if vis.ndim != 2:
        raise ValueError("visible must be a 2-D mask")
    distance = ndi.distance_transform_edt(~vis)
    labels, nlab = ndi.label(vis, structure=np.ones((3, 3), np.uint8))
    iy, ix = ndi.distance_transform_edt(~vis, return_distances=False, return_indices=True)
    nearest = labels[iy, ix]
    del iy, ix
    h, w = vis.shape
    pad_n = np.pad(nearest, 1, mode="constant", constant_values=0)
    pad_d = np.pad(distance.astype(np.float32, copy=False), 1, mode="constant", constant_values=0)
    center = pad_n[1:-1, 1:-1]
    center_d = pad_d[1:-1, 1:-1]
    comp_a, comp_b, spacing = [], [], []
    # Four shifts cover each unordered 8-neighbor pair once.
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        other = pad_n[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx]
        other_d = pad_d[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx]
        boundary = (center != other) & (center > 0) & (other > 0)
        if not boundary.any():
            continue
        comp_a.append(center[boundary])
        comp_b.append(other[boundary])
        spacing.append(center_d[boundary] + other_d[boundary])
    if not comp_a:
        empty = np.zeros(0, np.int32)
        return labels, nlab, distance.astype(np.float32), empty, empty, empty.astype(np.float32)
    return (
        labels,
        nlab,
        distance.astype(np.float32),
        np.concatenate(comp_a),
        np.concatenate(comp_b),
        np.concatenate(spacing).astype(np.float32),
    )


def _component_percentile(nlab: int, comp_a, comp_b, spacing, percentile: float = 25.0):
    """Per-component spacing percentile, ignoring relay-scale and >10 km contacts."""
    edges = np.arange(MIN_SPACING_PX, MAX_SPACING_PX + BIN_PX, BIN_PX)
    nbins = edges.size - 1
    keep = (spacing >= MIN_SPACING_PX) & (spacing < MAX_SPACING_PX)
    if not keep.any():
        z = np.zeros(nlab + 1, np.float32)
        return z, z, np.zeros(nlab + 1, np.int32)
    bins = np.clip(((spacing[keep] - MIN_SPACING_PX) / BIN_PX).astype(np.int32), 0, nbins - 1)
    hist = np.zeros((nlab + 1, nbins), np.int32)
    np.add.at(hist, (comp_a[keep], bins), 1)
    np.add.at(hist, (comp_b[keep], bins), 1)
    total = hist.sum(axis=1)
    cs = np.cumsum(hist, axis=1)
    # Smallest bin at which the cumulative count reaches the requested percentile.
    target = np.maximum(np.ceil(percentile / 100.0 * total), 1)
    reached = cs >= target[:, None]
    perc_bin = np.argmax(reached, axis=1)
    centers = (edges[:-1] + edges[1:]) * 0.5
    lam = centers[perc_bin].astype(np.float32)
    weight = hist / np.maximum(total, 1)[:, None]
    mean = (weight * centers).sum(axis=1)
    second = (weight * centers ** 2).sum(axis=1)
    var = np.maximum(second - mean ** 2, 0.0)
    cv = np.sqrt(var) / np.maximum(mean, 1e-6)
    ok = total >= 8
    lam = np.where(ok, lam, 0.0).astype(np.float32)
    cv = np.where(ok, cv, 0.0).astype(np.float32)
    return lam, cv.astype(np.float32), total


def missing_tooth_fields(visible: np.ndarray, sigma: float = 40.0, support_min: float = 1e-3) -> dict[str, np.ndarray]:
    """Full-grid float32 features. Undefined cells are 0, never NaN.

    ``sigma`` is the Gaussian diffusion length (pixels) that carries a
    component's spacing from its mapped trace into an adjacent gap.
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    labels, nlab, distance, comp_a, comp_b, spacing = _pairwise_separations(visible)
    lam_c, cv_c, _total = _component_percentile(nlab, comp_a, comp_b, spacing)
    vis = np.asarray(visible, bool)
    painted = np.zeros(vis.shape, np.float32)
    painted_cv = np.zeros(vis.shape, np.float32)
    if vis.any() and lam_c.any():
        painted[vis] = lam_c[labels[vis]]
        painted_cv[vis] = cv_c[labels[vis]]
    mask = (painted > 0).astype(np.float32)
    num = ndi.gaussian_filter(painted, sigma)
    den = ndi.gaussian_filter(mask, sigma)
    cv_num = ndi.gaussian_filter(painted_cv * mask, sigma)
    defined = den >= support_min
    lam = np.zeros(vis.shape, np.float32)
    cv = np.zeros(vis.shape, np.float32)
    lam[defined] = (num[defined] / den[defined]).astype(np.float32)
    cv[defined] = (cv_num[defined] / den[defined]).astype(np.float32)
    ok = defined & (lam >= MIN_SPACING_PX) & (lam <= MAX_SPACING_PX)
    sig1 = np.maximum(0.18 * lam, 1.5)
    sig15 = np.maximum(0.22 * lam, 1.5)
    gap1 = np.zeros(vis.shape, np.float32)
    gap15 = np.zeros(vis.shape, np.float32)
    width = np.zeros(vis.shape, np.float32)
    gap1[ok] = np.exp(-0.5 * ((distance[ok] - lam[ok]) / sig1[ok]) ** 2).astype(np.float32)
    gap15[ok] = np.exp(-0.5 * ((distance[ok] - 1.5 * lam[ok]) / sig15[ok]) ** 2).astype(np.float32)
    width[ok] = np.clip(2.0 * distance[ok] / lam[ok], 0.0, 4.0).astype(np.float32)
    support = np.where(ok, den, 0.0).astype(np.float32)
    lam_out = np.where(ok, lam, 0.0).astype(np.float32)
    cv_out = np.where(ok, cv, 0.0).astype(np.float32)
    return {
        "tooth_gap1": gap1,
        "tooth_gap15": gap15,
        "tooth_width_ratio": width,
        "tooth_lambda_px": lam_out,
        "tooth_support": support,
        "tooth_cv": cv_out,
        "distance_to_visible_px": distance.astype(np.float32),
    }


def sample_fields(fields: dict[str, np.ndarray], ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Stack FEATURE_NAMES at (ys, xs) into a float32 matrix. Drops the diagnostic distance."""
    cols = [np.asarray(fields[name][ys, xs], np.float32) for name in FEATURE_NAMES]
    return np.stack(cols, axis=1)
