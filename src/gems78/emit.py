"""Dot emission for lane H78.

The metric's own first-order condition (vendor/gems57/metric.py) says a binary
dot is worth adding only if its realised kernel credit exceeds ~0.2*DTI and that
a dot redundant with a neighbour earns nothing; the two best owner-reported
files (D2.8 -> H33) are exactly dots at >= sqrt(8) px spacing with the <=2 px
catalogue flank removed. This module makes those two emission decisions
explicit and testable on the holdout:

* ``ridge_nms``   -- optional Canny-style non-maximum suppression across the
                     local ridge normal so dots sit on the centre-line of a
                     thick high-score band rather than zig-zagging across it.
* ``greedy_dots`` -- exact greedy maximum-score packing with a hard minimum
                     separation (default sqrt(8) px, the D2.8 geometry), which
                     returns the acceptance *ranking* so any budget prefix is one
                     slice.
* ``flank_mask``  -- the <= B px catalogue flank exclusion, computed from the
                     VISIBLE catalogue only.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def flank_mask(visible: np.ndarray, b_px: float) -> np.ndarray:
    """True where a cell is within ``b_px`` (Euclidean) of a visible catalogue cell."""
    if b_px <= 0:
        return np.asarray(visible, bool).copy()
    return ndi.distance_transform_edt(~np.asarray(visible, bool)) <= b_px


def ridge_nms(score: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Keep cells that are maxima of ``score`` along the local principal-curvature
    direction (quantised to 0/45/90/135 deg), i.e. the centre-line of a ridge."""
    s = ndi.gaussian_filter(np.asarray(score, np.float32), sigma)
    gxx = ndi.gaussian_filter(s, sigma, order=(0, 2))
    gyy = ndi.gaussian_filter(s, sigma, order=(2, 0))
    gxy = ndi.gaussian_filter(s, sigma, order=(1, 1))
    # direction of most negative curvature (across the ridge)
    theta = 0.5 * np.arctan2(2 * gxy, gxx - gyy)  # principal axis angle
    # choose the eigenvector with the smaller eigenvalue (most negative) -> across-ridge
    half_tr = 0.5 * (gxx + gyy)
    disc = np.sqrt((0.5 * (gxx - gyy)) ** 2 + gxy ** 2)
    lam_major = half_tr + disc  # eigenvalue along theta
    across = np.where(lam_major < half_tr - disc + 1e-12, theta, theta + np.pi / 2)
    del gxx, gyy, gxy, half_tr, disc, lam_major, theta
    q = np.round((np.mod(across, np.pi) / (np.pi / 4))).astype(np.int8) % 4  # 0:x,1:diag,2:y,3:anti
    keep = np.zeros(s.shape, bool)
    pad = np.pad(s, 1, mode="edge")
    H, W = s.shape
    c = pad[1:H + 1, 1:W + 1]
    nbrs = {
        0: (pad[1:H + 1, 0:W], pad[1:H + 1, 2:W + 2]),
        1: (pad[0:H, 2:W + 2], pad[2:H + 2, 0:W]),
        2: (pad[0:H, 1:W + 1], pad[2:H + 2, 1:W + 1]),
        3: (pad[0:H, 0:W], pad[2:H + 2, 2:W + 2]),
    }
    for d, (n1, n2) in nbrs.items():
        keep |= (q == d) & (c >= n1) & (c >= n2)
    return keep


def greedy_dots(score: np.ndarray, allowed: np.ndarray, min_dist: float = 2.8,
                max_dots: int = 80_000, pool: int = 400_000) -> np.ndarray:
    """Greedy max-score packing with a hard minimum separation.

    Returns an int32 grid: 0 = not a dot, k = k-th accepted dot (1-based), so the
    first ``n`` dots of the ranking are ``(rank > 0) & (rank <= n)``.
    """
    score = np.asarray(score, np.float32)
    allowed = np.asarray(allowed, bool)
    H, W = score.shape
    flat = np.where(allowed, score, -np.inf).ravel()
    n_pool = min(pool, int(np.isfinite(flat).sum()))
    cand = np.argpartition(-flat, n_pool - 1)[:n_pool]
    cand = cand[np.argsort(-flat[cand], kind="stable")]
    r = int(np.ceil(min_dist))
    offs = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if (dy or dx) and dy * dy + dx * dx <= min_dist * min_dist + 1e-9]
    Wp = W + 2 * r
    occ = np.zeros((H + 2 * r) * Wp, np.bool_)
    foffs = np.array([dy * Wp + dx for dy, dx in offs], np.int64)
    rank = np.zeros(H * W, np.int32)
    k = 0
    occ_view = occ  # local alias for speed
    for idx in cand:
        y, x = divmod(int(idx), W)
        f = (y + r) * Wp + (x + r)
        if occ_view[f + foffs].any():
            continue
        occ_view[f] = True
        k += 1
        rank[idx] = k
        if k >= max_dots:
            break
    return rank.reshape(H, W)


def prefix(rank: np.ndarray, n: int) -> np.ndarray:
    return (rank > 0) & (rank <= int(n))
