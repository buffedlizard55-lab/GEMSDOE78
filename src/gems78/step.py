"""H78-STEP: paired cross-strike flank-step features (session 2026-10-22).

Preregistration: ``registry/preregistration_h78step.json``. Rationale and
ranking: ``research/h78step_hypotheses.md``.

A normal fault is a *step*: basement depth, gravity and elevation change level
across it and stay changed. Pointwise derivatives (lane H78-A) measure
curvature/gradient *at* a pixel at sigma <= 3 px; under sedimentary cover the
scarp disappears and only a broad, weak gradient remains. This module instead
contrasts strike-elongated patch means on the two flanks of a candidate line,
separated by 2*d = 8 px (0.8 km) and 18 px (1.8 km) across strike:

* ``step_<band>_d<D>_signed`` -- mean(+d flank) - mean(-d flank)
* ``step_<band>_d<D>_abs``    -- |signed step|
* ``step_<band>_d<D>_t``      -- |step| / (mean within-patch std + 0.01*|step| + eps),
                                 capped at 50: a noise-normalised step strength
* ``step_<band>_d<D>_cdev``   -- |mean(centre line) - flank midpoint|: near zero
                                 for a pure step, large for a ridge/trough, so the
                                 learner can separate a level change from a lineament
* ``step_<band>_sharp``       -- step_abs(d=4) / (step_abs(d=9) + eps), capped [0,10]:
                                 ~1 for a sharp localised step, <<1 for a broad ramp

6 bands x (2 scales x 4 + 1 sharpness) = 54 features. Bands are pre-smoothed
with an isotropic Gaussian sigma=1.5 px before sampling (noise suppression;
disclosed in the preregistration). Flank patches are sampled along the local
strike tangent at the frozen offsets below.

Orientation convention (unit-tested in tests/test_step.py, identical to
collinear.py / features.py): normal n = (cos phi, sin phi) in (x=col, y=row)
coordinates -- the direction of ``gn = cos(phi)*Gx + sin(phi)*Gy`` -- and
tangent t = (-sin phi, cos phi). A sample at across-offset ``a`` and
along-offset ``k`` sits at (row + a*sin(phi) + k*cos(phi),
col + a*cos(phi) - k*sin(phi)). The caller must compute ``phi`` from the
*visible* catalogue only inside a holdout fold (leakage rule).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from .data import BAND_NAMES, PROC, load_stack

STEP_BANDS = ["det_elev", "rtp", "iso_grav_anom", "depth_to_base_surf", "cond_surf", "tc_totalcount"]
PRESMOOTH_SIGMA = 1.5
SCALES = ((4, (-6, -4, -2, 0, 2, 4, 6)),
          (9, (-12, -9, -6, -3, 0, 3, 6, 9, 12)))
_EPS = 1e-12


def step_feature_names() -> list[str]:
    names = []
    for b in STEP_BANDS:
        for d, _ in SCALES:
            names += [f"step_{b}_d{d}_signed", f"step_{b}_d{d}_abs",
                      f"step_{b}_d{d}_t", f"step_{b}_d{d}_cdev"]
        names.append(f"step_{b}_sharp")
    return names


def _sample(band: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    return ndi.map_coordinates(band, [rows, cols], order=1, mode="nearest").astype(np.float32)


def _flank_means(band: np.ndarray, ys, xs, phi_vals, across: float, along) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Patch means/stds of the two flanks at +/- ``across`` and the centre line.

    Returns (plus_mean, minus_mean, centre_mean, within_std) float32 arrays,
    within_std = 0.5*(std_plus + std_minus) over the along-strike samples.
    """
    c = np.cos(phi_vals).astype(np.float32)   # n_x
    s = np.sin(phi_vals).astype(np.float32)   # n_y
    tx, ty = -s, c                            # tangent (x, y)
    k = np.asarray(along, np.float32)[None, :]
    y0 = ys.astype(np.float32)[:, None]
    x0 = xs.astype(np.float32)[:, None]
    base_r = y0 + k * ty[:, None]
    base_c = x0 + k * tx[:, None]
    centre = _sample(band, base_r, base_c)
    plus = _sample(band, base_r + across * s[:, None], base_c + across * c[:, None])
    minus = _sample(band, base_r - across * s[:, None], base_c - across * c[:, None])
    del c, s, tx, ty, k, y0, x0, base_r, base_c
    within = 0.5 * (plus.std(axis=1) + minus.std(axis=1))
    return (plus.mean(axis=1), minus.mean(axis=1), centre.mean(axis=1),
            within.astype(np.float32))


def band_step_features(band_smooth: np.ndarray, ys, xs, phi_vals) -> np.ndarray:
    """9 STEP features (columns of one band) at points (ys, xs)."""
    out = np.empty((ys.size, 9), np.float32)
    abs_by_scale = []
    col = 0
    for d, along in SCALES:
        plus, minus, centre, within = _flank_means(band_smooth, ys, xs, phi_vals,
                                                   float(d), along)
        signed = (plus - minus).astype(np.float32)
        absstep = np.abs(signed)
        tstat = absstep / (within + 0.01 * absstep + _EPS)
        cdev = np.abs(centre - 0.5 * (plus + minus)).astype(np.float32)
        out[:, col] = signed
        out[:, col + 1] = absstep
        out[:, col + 2] = np.minimum(tstat, 50.0).astype(np.float32)
        out[:, col + 3] = cdev
        abs_by_scale.append(absstep)
        col += 4
        del plus, minus, centre, within, signed, tstat, cdev
    sharp = abs_by_scale[0] / (abs_by_scale[1] + _EPS)
    out[:, 8] = np.where(abs_by_scale[1] > 0, np.minimum(sharp, 10.0), 0.0).astype(np.float32)
    return out


def build_step_matrix(tag: str, footprint: np.ndarray, phi: np.ndarray,
                      block: int = 250_000, force: bool = False) -> tuple[Path, dict]:
    """Float32 memmap ``data/processed/feats_step_<tag>.npy`` (n_footprint, 54),
    rows in the same footprint row-major order as pipeline.build_feature_matrix.
    """
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"feats_step_{tag}.npy"
    meta_p = PROC / f"feats_step_{tag}.json"
    names = step_feature_names()
    assert len(names) == 54, len(names)
    if out.exists() and meta_p.exists() and not force:
        return out, json.loads(meta_p.read_text())
    t0 = time.time()
    stack = load_stack()
    ys, xs = np.nonzero(footprint)
    ys = ys.astype(np.int32)
    xs = xs.astype(np.int32)
    n = ys.size
    phi_fp = np.asarray(phi[ys, xs], np.float32)
    mm = np.lib.format.open_memmap(out, mode="w+", dtype=np.float32, shape=(n, len(names)))
    col = 0
    for bname in STEP_BANDS:
        band = np.ascontiguousarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        smooth = ndi.gaussian_filter(band, PRESMOOTH_SIGMA)
        del band
        for lo in range(0, n, block):
            hi = min(n, lo + block)
            mm[lo:hi, col:col + 9] = band_step_features(
                smooth, ys[lo:hi], xs[lo:hi], phi_fp[lo:hi])
        del smooth
        col += 9
        mm.flush()
        print(f"step {bname} done {time.time() - t0:.0f}s", flush=True)
    del mm, phi_fp, ys, xs
    assert col == len(names), (col, len(names))
    meta = dict(tag=tag, n_footprint=int(n), n_features=len(names), names=names,
                bands=STEP_BANDS, presmooth_sigma_px=PRESMOOTH_SIGMA,
                scales=[dict(across_px=d, along_offsets_px=list(a)) for d, a in SCALES],
                segment="straight centre-pixel tangent flanks, bilinear samples",
                seconds=round(time.time() - t0, 1))
    meta_p.write_text(json.dumps(meta, indent=2))
    return out, meta
