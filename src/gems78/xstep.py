"""H78-STEP: cross-strike step-offset profile + concordance features (2026-10-22).

Preregistration: ``registry/preregistration_h78step.json``. Ranking/rationale:
``research/h78step_hypotheses.md`` hypothesis #1.

For five independent-physics bands (``det_elev`` topography, ``rtp`` magnetics,
``iso_grav_anom`` gravity, ``depth_to_base_surf`` basement depth (the pinned
``log1p`` transform of data.py), ``cond_surf`` conductivity) this module samples
a paired **cross-strike profile**: with strike-normal n = (cos phi, sin phi) in
(x=col, y=row) coordinates and tangent t = (-sin phi, cos phi) -- the same
convention as features.py / collinear.py -- the sigma=1 px smoothed band is
sampled at normal offsets -10,-6,-3,0,3,6,10 px (i.e. up to +/-1 km), each
sample averaged over tangent offsets -3,0,+3 px.

Per band (8 features, all normalised by denom = local sigma=10 px std at the
centre + 0.05 * global std of the smoothed band):
    step{k}_z    = (v(+k) - v(-k)) / denom          k = 3, 6, 10 px
    step{k}_absz = |step{k}_z|
    dev6_z       = (v(0) - (v(+6)+v(-6))/2) / denom (ridge/trough vs pure step)
    dev6_absz    = |dev6_z|

Cross-layer **concordance** (7 features at each of k = 6, 10 px; the magnetic
step is deliberately excluded from the sign logic because a magnetic anomaly's
sign depends on magnetisation, not on throw direction).  With oriented
components o = (depth, -elev, -grav, cond) -- a downthrown side is deeper,
lower, gravity-lower and more conductive:
    throw_z = mean(o), throw_absz = |throw_z|
    prod_depth_elev = -depth*elev, prod_depth_grav = -depth*grav,
    prod_elev_grav = elev*grav, prod_depth_cond = depth*cond
    weakest = min_i(o_i * sign(throw_z))  (>0 only if all four agree)

Total 5*8 + 2*7 = 54 features.  ``phi`` (angle of the strike *normal*) must be
computed from the *visible* catalogue only inside a holdout fold (leakage
rule); no catalogue location/distance/density quantity enters any feature.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from .data import BAND_NAMES, PROC, load_stack

STEP_BANDS = ["det_elev", "rtp", "iso_grav_anom", "depth_to_base_surf", "cond_surf"]
SMOOTH_SIGMA = 1.0
STD_SIGMA = 10.0
OFFSETS = (-10, -6, -3, 0, 3, 6, 10)   # normal offsets, px (100 m/px)
TANGENT = (-3, 0, 3)                    # tangent averaging offsets, px
_OFF_IDX = {k: i for i, k in enumerate(OFFSETS)}


def step_feature_names() -> list[str]:
    names = []
    for b in STEP_BANDS:
        for k in (3, 6, 10):
            names += [f"xs_{b}_step{k}_z", f"xs_{b}_step{k}_absz"]
        names += [f"xs_{b}_dev6_z", f"xs_{b}_dev6_absz"]
    for k in (6, 10):
        names += [f"xs_conc{k}_throw_z", f"xs_conc{k}_throw_absz",
                  f"xs_conc{k}_prod_depth_elev", f"xs_conc{k}_prod_depth_grav",
                  f"xs_conc{k}_prod_elev_grav", f"xs_conc{k}_prod_depth_cond",
                  f"xs_conc{k}_weakest"]
    return names


def sample_profile(band_smooth: np.ndarray, ys: np.ndarray, xs: np.ndarray,
                   phi_vals: np.ndarray) -> np.ndarray:
    """Tangent-averaged cross-strike profile, shape (n, len(OFFSETS)) float32.

    Column j is the mean of the band at centre + OFFSETS[j]*n + t_off*t over
    t_off in TANGENT (bilinear, mode='nearest' at the grid edge).
    """
    nx = np.cos(phi_vals).astype(np.float32)   # normal x (col)
    ny = np.sin(phi_vals).astype(np.float32)   # normal y (row)
    tx, ty = -ny, nx                            # tangent
    offs = np.array([(k, j) for k in OFFSETS for j in TANGENT], np.float32)  # (21, 2)
    cols = (xs.astype(np.float32)[:, None]
            + offs[None, :, 0] * nx[:, None] + offs[None, :, 1] * tx[:, None])
    rows = (ys.astype(np.float32)[:, None]
            + offs[None, :, 0] * ny[:, None] + offs[None, :, 1] * ty[:, None])
    del nx, ny, tx, ty
    samp = ndi.map_coordinates(band_smooth, [rows, cols], order=1,
                               mode="nearest").astype(np.float32)
    del rows, cols
    samp = samp.reshape(-1, len(OFFSETS), len(TANGENT))
    return samp.mean(axis=2).astype(np.float32)


def profile_columns(profile: np.ndarray, denom: np.ndarray) -> np.ndarray:
    """8 per-band STEP columns from an (n, 7) profile and per-pixel denominator."""
    d = np.asarray(denom, np.float32)
    out = []
    for k in (3, 6, 10):
        step = (profile[:, _OFF_IDX[k]] - profile[:, _OFF_IDX[-k]]) / d
        out += [step, np.abs(step)]
    dev = (profile[:, _OFF_IDX[0]]
           - 0.5 * (profile[:, _OFF_IDX[6]] + profile[:, _OFF_IDX[-6]])) / d
    out += [dev, np.abs(dev)]
    return np.stack(out, axis=1).astype(np.float32)


def concordance_columns(depth: np.ndarray, elev: np.ndarray, grav: np.ndarray,
                        cond: np.ndarray) -> np.ndarray:
    """7 concordance columns from signed step_z arrays of one scale."""
    depth, elev, grav, cond = (np.asarray(a, np.float32) for a in (depth, elev, grav, cond))
    oriented = np.stack([depth, -elev, -grav, cond], axis=1)       # (n, 4)
    throw = oriented.mean(axis=1)
    weakest = (oriented * np.sign(throw)[:, None]).min(axis=1)
    cols = [throw, np.abs(throw),
            -depth * elev, -depth * grav, elev * grav, depth * cond,
            weakest]
    return np.stack(cols, axis=1).astype(np.float32)


def local_std_grid(band_smooth: np.ndarray) -> tuple[np.ndarray, float]:
    """(local sigma=STD_SIGMA std grid float32, global std scalar)."""
    mu = ndi.gaussian_filter(band_smooth, STD_SIGMA)
    var = ndi.gaussian_filter(band_smooth * band_smooth, STD_SIGMA) - mu * mu
    del mu
    return np.sqrt(np.maximum(var, 0.0)).astype(np.float32), float(band_smooth.std())


def build_step_matrix(tag: str, footprint: np.ndarray, phi: np.ndarray,
                      block: int = 250_000, force: bool = False) -> tuple[Path, dict]:
    """Float32 memmap ``data/processed/feats_step_<tag>.npy`` (n_footprint, 54),
    rows in the same footprint row-major order as pipeline.build_feature_matrix.
    """
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"feats_step_{tag}.npy"
    meta_p = PROC / f"feats_step_{tag}.json"
    names = step_feature_names()
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
    # signed step_z at k=6,10 for the four sign-meaningful bands (concordance)
    keep = {}
    col = 0
    for bname in STEP_BANDS:
        band = np.ascontiguousarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        smooth = ndi.gaussian_filter(band, SMOOTH_SIGMA)
        del band
        std_grid, gstd = local_std_grid(smooth)
        denom = std_grid[ys, xs] + np.float32(0.05 * gstd) + np.float32(1e-12)
        del std_grid
        s6 = np.empty(n, np.float32)
        s10 = np.empty(n, np.float32)
        for lo in range(0, n, block):
            hi = min(n, lo + block)
            prof = sample_profile(smooth, ys[lo:hi], xs[lo:hi], phi_fp[lo:hi])
            cols = profile_columns(prof, denom[lo:hi])
            mm[lo:hi, col:col + 8] = cols
            s6[lo:hi] = cols[:, 2]    # step6_z column inside the 8
            s10[lo:hi] = cols[:, 4]   # step10_z
            del prof, cols
        del smooth, denom
        keep[bname] = (s6, s10)
        col += 8
        mm.flush()
        print(f"step {bname} done {time.time() - t0:.0f}s", flush=True)
    for si, k in enumerate((6, 10)):
        cc = concordance_columns(keep["depth_to_base_surf"][si], keep["det_elev"][si],
                                 keep["iso_grav_anom"][si], keep["cond_surf"][si])
        mm[:, col:col + 7] = cc
        col += 7
        del cc
    mm.flush()
    del mm, keep, phi_fp, ys, xs
    assert col == len(names) == 54, (col, len(names))
    meta = dict(tag=tag, n_footprint=int(n), n_features=len(names), names=names,
                bands=STEP_BANDS, smooth_sigma_px=SMOOTH_SIGMA, std_sigma_px=STD_SIGMA,
                normal_offsets_px=list(OFFSETS), tangent_offsets_px=list(TANGENT),
                profile="straight centre-pixel strike-normal, bilinear, tangent-averaged",
                seconds=round(time.time() - t0, 1))
    meta_p.write_text(json.dumps(meta, indent=2))
    return out, meta
