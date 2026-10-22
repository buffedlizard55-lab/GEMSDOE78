"""H78-CS: strike-following collinear-support features (session 3, 2026-10-21).

Preregistration: ``registry/preregistration_h78cs.json``. Rationale and ranking:
``research/h78cs_hypotheses.md``.

For three independent-physics bands (``det_elev`` topography, ``rtp`` magnetics,
``depth_to_base_surf`` basement depth) this module takes the sigma=3 px
strike-steered responses already defined by lane H78-A -- ``|Hnn|`` (across-strike
second derivative, line centre) and ``|gn|`` (across-strike first derivative,
step) -- and integrates each *along* the local catalogue-strike tangent:

* ``cs_<band>_<resp>_L5_mean``   -- mean over a straight 11-sample (1.1 km) segment
* ``cs_<band>_<resp>_L15_mean``  -- mean over a straight 31-sample (3.1 km) segment
* ``cs_<band>_Hnn_L15_min``      -- min(left-half mean, right-half mean) over the
                                    3.1 km segment, centre sample excluded: the
                                    strand must continue on *both* sides.

15 features total. The tangent at each pixel comes from the strike field
``phi`` (angle of the strike *normal*, image x/y convention, see strike.py),
which the caller must have computed from the *visible* catalogue only inside a
holdout fold (leakage rule). Segments are straight (centre-pixel tangent;
curvature over <=3.1 km ignored -- disclosed in the preregistration).

Tangent convention (unit-tested in tests/test_collinear.py): with normal
n = (cos phi, sin phi) in (x=col, y=row) coordinates -- the same convention as
features.py, where gn = cos(phi)*Gx + sin(phi)*Gy -- the tangent is
t = (-sin phi, cos phi). Sample k sits at (row + k*t_y, col + k*t_x).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from .data import BAND_NAMES, PROC, load_stack

CS_BANDS = ["det_elev", "rtp", "depth_to_base_surf"]
CS_SIGMA = 3.0
HALF_LONG = 15   # 31 samples = 3.1 km at 100 m/px
HALF_SHORT = 5   # centre 11 of the same samples = 1.1 km


def cs_feature_names() -> list[str]:
    names = []
    for b in CS_BANDS:
        for resp in ("Hnn", "gn"):
            names += [f"cs_{b}_{resp}_L{HALF_SHORT}_mean", f"cs_{b}_{resp}_L{HALF_LONG}_mean"]
        names.append(f"cs_{b}_Hnn_L{HALF_LONG}_min")
    return names


def steered_abs_responses(band: np.ndarray, phi: np.ndarray, sigma: float = CS_SIGMA):
    """Return (|Hnn|, |gn|) full grids for one band, H78-A definitions verbatim.

    Scale-normalised Gaussian derivatives (gradients x sigma, Hessian x sigma^2),
    projected with c=cos(phi), s=sin(phi) exactly as in features.extract.
    """
    a = np.ascontiguousarray(band, dtype=np.float32)
    gx = ndi.gaussian_filter(a, sigma, order=(0, 1)) * np.float32(sigma)
    gy = ndi.gaussian_filter(a, sigma, order=(1, 0)) * np.float32(sigma)
    gxx = ndi.gaussian_filter(a, sigma, order=(0, 2)) * np.float32(sigma * sigma)
    gyy = ndi.gaussian_filter(a, sigma, order=(2, 0)) * np.float32(sigma * sigma)
    gxy = ndi.gaussian_filter(a, sigma, order=(1, 1)) * np.float32(sigma * sigma)
    del a
    c = np.cos(phi).astype(np.float32)
    s = np.sin(phi).astype(np.float32)
    hnn = c * c * gxx + 2.0 * s * c * gxy + s * s * gyy
    gn = c * gx + s * gy
    del gx, gy, gxx, gyy, gxy, c, s
    return np.abs(hnn).astype(np.float32), np.abs(gn).astype(np.float32)


def path_stats(resp: np.ndarray, ys: np.ndarray, xs: np.ndarray, phi_vals: np.ndarray):
    """Along-strike path statistics of ``resp`` at points (ys, xs).

    Returns (mean_L5, mean_L15, min_half_L15) float32 arrays. Samples the
    31-point straight tangent segment once (bilinear, mode='nearest' at the
    grid edge); the 11-point statistic reuses the centre samples.
    """
    k = np.arange(-HALF_LONG, HALF_LONG + 1, dtype=np.float32)          # (31,)
    tx = -np.sin(phi_vals).astype(np.float32)                            # tangent x (col)
    ty = np.cos(phi_vals).astype(np.float32)                             # tangent y (row)
    cols = xs.astype(np.float32)[:, None] + k[None, :] * tx[:, None]     # (n, 31)
    rows = ys.astype(np.float32)[:, None] + k[None, :] * ty[:, None]
    del tx, ty
    samp = ndi.map_coordinates(resp, [rows, cols], order=1, mode="nearest").astype(np.float32)
    del rows, cols
    lo = HALF_LONG - HALF_SHORT
    hi = HALF_LONG + HALF_SHORT + 1
    mean_short = samp[:, lo:hi].mean(axis=1)
    mean_long = samp.mean(axis=1)
    left = samp[:, :HALF_LONG].mean(axis=1)          # k = -15..-1 (centre excluded)
    right = samp[:, HALF_LONG + 1:].mean(axis=1)     # k = +1..+15
    min_half = np.minimum(left, right)
    del samp, left, right
    return (mean_short.astype(np.float32), mean_long.astype(np.float32),
            min_half.astype(np.float32))


def build_cs_matrix(tag: str, footprint: np.ndarray, phi: np.ndarray,
                    block: int = 300_000, force: bool = False) -> tuple[Path, dict]:
    """Float32 memmap ``data/processed/feats_cs_<tag>.npy`` (n_footprint, 15),
    rows in the same footprint row-major order as pipeline.build_feature_matrix.
    """
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"feats_cs_{tag}.npy"
    meta_p = PROC / f"feats_cs_{tag}.json"
    names = cs_feature_names()
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
    for bname in CS_BANDS:
        band = stack[BAND_NAMES.index(bname)]
        hnn_abs, gn_abs = steered_abs_responses(band, phi)
        del band
        stats = {}  # resp -> (mean5, mean15, min15) full-length arrays, filled per block
        for resp_name, resp in (("Hnn", hnn_abs), ("gn", gn_abs)):
            m5 = np.empty(n, np.float32)
            m15 = np.empty(n, np.float32)
            mn = np.empty(n, np.float32)
            for lo_i in range(0, n, block):
                hi_i = min(n, lo_i + block)
                a, b, c = path_stats(resp, ys[lo_i:hi_i], xs[lo_i:hi_i], phi_fp[lo_i:hi_i])
                m5[lo_i:hi_i], m15[lo_i:hi_i], mn[lo_i:hi_i] = a, b, c
            stats[resp_name] = (m5, m15, mn)
            print(f"cs {bname} {resp_name} done {time.time() - t0:.0f}s", flush=True)
        del hnn_abs, gn_abs
        mm[:, col] = stats["Hnn"][0]
        mm[:, col + 1] = stats["Hnn"][1]
        mm[:, col + 2] = stats["gn"][0]
        mm[:, col + 3] = stats["gn"][1]
        mm[:, col + 4] = stats["Hnn"][2]
        col += 5
        mm.flush()
        del stats
    del mm, phi_fp, ys, xs
    assert col == len(names), (col, len(names))
    meta = dict(tag=tag, n_footprint=int(n), n_features=len(names), names=names,
                bands=CS_BANDS, sigma_px=CS_SIGMA, half_lengths_px=[HALF_SHORT, HALF_LONG],
                segment="straight centre-pixel tangent, bilinear samples every 1 px",
                seconds=round(time.time() - t0, 1))
    meta_p.write_text(json.dumps(meta, indent=2))
    return out, meta
