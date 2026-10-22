"""Per-pixel feature extraction for lane H78.

Three nested feature families, so the hypothesis can be ablated cleanly:

* ``raw``      -- the 19 official bands (log1p on heavy-tailed ones), the lineage's
                  base model class ("std19").
* ``iso``      -- rotation-invariant multi-scale Hessian eigenvalues and gradient
                  magnitude on six line-expressing bands (control arm A1).
* ``steered``  -- the H78 candidate: the same derivatives projected onto the
                  regional catalogue-strike frame (across-strike 2nd derivative
                  H_nn, along-strike H_tt, across-strike step g_n, |along-strike
                  gradient|). Only this family depends on the catalogue, and only
                  through the strike *angle* (see strike.py).

Filters are recomputed per call from the nodata-filled memmap, one band at a
time, so peak memory stays near 300 MB on the 3 GB sandbox.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .data import BAND_NAMES

STEER_BANDS = ["det_elev", "rtp", "iso_grav_anom", "depth_to_base_surf", "cond_surf", "tc"]
SCALES = (1.5, 3.0)


def feature_names(iso: bool = True, steered: bool = True) -> list[str]:
    names = list(BAND_NAMES)
    for b in STEER_BANDS:
        for s in SCALES:
            if iso:
                names += [f"{b}_s{s}_l1", f"{b}_s{s}_l2", f"{b}_s{s}_gm"]
            if steered:
                names += [f"{b}_s{s}_Hnn", f"{b}_s{s}_Htt", f"{b}_s{s}_gn", f"{b}_s{s}_agt"]
    return names


def extract(stack, idx_sets, phi=None, iso: bool = True, steered: bool = True):
    """Return a list of float32 feature matrices, one per (ys, xs) index set."""
    if steered and phi is None:
        raise ValueError("steered features need the strike field phi")
    cols = [[] for _ in idx_sets]
    for b in range(len(BAND_NAMES)):
        band = stack[b]
        for k, (ys, xs) in enumerate(idx_sets):
            cols[k].append(np.asarray(band[ys, xs], np.float32))
    if not (iso or steered):
        return [np.stack(c, axis=1) for c in cols]
    if steered:
        cph = [np.cos(phi[ys, xs]).astype(np.float32) for ys, xs in idx_sets]
        sph = [np.sin(phi[ys, xs]).astype(np.float32) for ys, xs in idx_sets]
    for bname in STEER_BANDS:
        a = np.ascontiguousarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        for s in SCALES:
            gx = ndi.gaussian_filter(a, s, order=(0, 1))
            gy = ndi.gaussian_filter(a, s, order=(1, 0))
            gxx = ndi.gaussian_filter(a, s, order=(0, 2))
            gyy = ndi.gaussian_filter(a, s, order=(2, 0))
            gxy = ndi.gaussian_filter(a, s, order=(1, 1))
            s1, s2 = np.float32(s), np.float32(s * s)
            for k, (ys, xs) in enumerate(idx_sets):
                Gx, Gy = gx[ys, xs] * s1, gy[ys, xs] * s1
                Gxx, Gyy, Gxy = gxx[ys, xs] * s2, gyy[ys, xs] * s2, gxy[ys, xs] * s2
                if iso:
                    half_tr = 0.5 * (Gxx + Gyy)
                    disc = np.sqrt((0.5 * (Gxx - Gyy)) ** 2 + Gxy ** 2)
                    cols[k] += [half_tr + disc, half_tr - disc, np.hypot(Gx, Gy)]
                if steered:
                    c, sn = cph[k], sph[k]
                    hnn = c * c * Gxx + 2 * sn * c * Gxy + sn * sn * Gyy
                    htt = sn * sn * Gxx - 2 * sn * c * Gxy + c * c * Gyy
                    gn = c * Gx + sn * Gy
                    gt = -sn * Gx + c * Gy
                    cols[k] += [hnn, htt, gn, np.abs(gt)]
            del gx, gy, gxx, gyy, gxy
        del a
    return [np.stack(c, axis=1).astype(np.float32) for c in cols]
