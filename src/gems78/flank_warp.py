"""Multi-scale antisymmetric footwall/hangingwall flank-warp features (lane H78-FW).

Physical model
--------------
Normal faults in the Great Basin produce elastic/coseismic footwall uplift and
hangingwall subsidence over 0.8-2.8 km wavelengths (+/-4, 8, 14 px at 100 m
grid resolution). Even where surficial erosion or alluvial-fan deposition has
diffused the narrow (<200 m) surface scarp, the detrended residual field
r(x) = G_1.5(u) - G_16.0(u) retains an odd-parity (antisymmetric) step across
the regional strike normal n = (cos phi, sin phi), an opposite-sign curvature
inflection doublet at +/-600 m, and cross-layer concordance between topographic
footwall uplift, shallow basement depth, and positive isostatic gravity / magnetic
discontinuities.

Catalogue safety
----------------
Only the regional strike angle phi (sigma=40 px = 4 km) and its orientation
coherence coh from the VISIBLE catalogue are used to orient the across-strike
sampling chords. No catalogue distance, location, or density feature is used.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from .data import BAND_NAMES, PROC, load_stack

WARP_BANDS = (
    "det_elev",
    "depth_to_base_surf",
    "rtp",
    "iso_grav_anom",
    "cond_surf",
    "tc_totalcount",
)
DOUBLET_BANDS = (
    "det_elev",
    "depth_to_base_surf",
    "rtp",
    "iso_grav_anom",
)
CONTEXT_BANDS = (
    "tmi_vg",
    "iso_grav_anom_vg",
    "tmi_hg",
    "iso_grav_anom_hg",
    "geod_shearrate",
    "geod_dilaterate",
    "geod_2ndinv",
    "deq_n100a15",
    "ieq_n100a15",
    "det_elev_slope",
)
OFFSETS_PX = (4.0, 8.0, 14.0)
DOUBLET_OFFSET_PX = 6.0
SMOOTH_FINE_PX = 1.5
DETREND_SIGMA_PX = 16.0
EPS = 1e-6


def fw_feature_names() -> list[str]:
    names: list[str] = []
    for b in WARP_BANDS:
        for d in OFFSETS_PX:
            di = int(d)
            names.append(f"fw_{b}_asym_d{di}")
            names.append(f"fw_{b}_purity_d{di}")
        names.append(f"fw_{b}_sym_d8")
    for b in DOUBLET_BANDS:
        di = int(DOUBLET_OFFSET_PX)
        names.append(f"fw_{b}_curv_diff_d{di}")
        names.append(f"fw_{b}_curv_dipole_d{di}")
    names += [
        "fw_concord_elev_base_d8",
        "fw_concord_elev_grav_d8",
        "fw_concord_base_grav_d8",
        "fw_concord_mag_grav_d8",
        "fw_concord_elev_base_d14",
        "fw_concord_base_grav_d14",
    ]
    for b in CONTEXT_BANDS:
        names.append(f"fw_ctx_{b}")
    names.append("fw_strike_coherence")
    return names


def _sample_bilinear(field: np.ndarray, y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Fast bilinear sampling of a 2-D float32 grid at arbitrary (y, x) coordinates."""
    H, W = field.shape
    yc = np.clip(y, 0.0, float(H - 1))
    xc = np.clip(x, 0.0, float(W - 1))
    y0 = np.floor(yc).astype(np.int32)
    x0 = np.floor(xc).astype(np.int32)
    y1 = np.minimum(y0 + 1, H - 1)
    x1 = np.minimum(x0 + 1, W - 1)
    wy = (yc - y0).astype(np.float32)
    wx = (xc - x0).astype(np.float32)
    v00 = field[y0, x0]
    v01 = field[y0, x1]
    v10 = field[y1, x0]
    v11 = field[y1, x1]
    return ((1.0 - wy) * ((1.0 - wx) * v00 + wx * v01)
            + wy * ((1.0 - wx) * v10 + wx * v11)).astype(np.float32)


def compute_flank_warp_for_band(
    arr: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
    cph: np.ndarray,
    sph: np.ndarray,
    compute_doublet: bool = False,
) -> tuple[list[np.ndarray], dict[int, np.ndarray], list[np.ndarray]]:
    """Compute flank-warp features for one band on footprint coordinates (ys, xs).

    Returns:
      - warp_cols: [asym_d4, purity_d4, asym_d8, purity_d8, asym_d14, purity_d14, sym_d8]
      - signed_norm: {8: signed_step_d8_iqr_norm, 14: signed_step_d14_iqr_norm}
      - doublet_cols: [curv_diff_d6, curv_dipole_d6] if compute_doublet else []
    """
    a = np.ascontiguousarray(arr, dtype=np.float32)
    fine = ndi.gaussian_filter(a, SMOOTH_FINE_PX, mode="nearest")
    regional = ndi.gaussian_filter(a, DETREND_SIGMA_PX, mode="nearest")
    res = (fine - regional).astype(np.float32)
    del fine, regional

    r0 = res[ys, xs]
    q25, q75 = np.percentile(r0, [25.0, 75.0])
    scale = float(max(q75 - q25, EPS))

    yf = ys.astype(np.float32)
    xf = xs.astype(np.float32)

    warp_cols: list[np.ndarray] = []
    signed_norm: dict[int, np.ndarray] = {}
    sym_d8: np.ndarray | None = None

    for d in OFFSETS_PX:
        di = int(d)
        dy = np.float32(d) * sph
        dx = np.float32(d) * cph
        rp = _sample_bilinear(res, yf + dy, xf + dx)
        rm = _sample_bilinear(res, yf - dy, xf - dx)
        signed = 0.5 * (rp - rm)
        asym = np.abs(signed).astype(np.float32)
        sym = np.abs(0.5 * (rp + rm) - r0).astype(np.float32)
        purity = (asym / (asym + sym + np.float32(EPS))).astype(np.float32)
        warp_cols.append(asym)
        warp_cols.append(purity)
        if di in (8, 14):
            signed_norm[di] = (signed / np.float32(scale)).astype(np.float32)
        if di == 8:
            sym_d8 = sym
        del rp, rm, signed, asym, sym, purity

    assert sym_d8 is not None
    warp_cols.append(sym_d8)
    del res, r0

    doublet_cols: list[np.ndarray] = []
    if compute_doublet:
        s_curv = np.float32(3.0)
        gxx = ndi.gaussian_filter(a, 3.0, order=(0, 2), mode="nearest") * (s_curv * s_curv)
        gyy = ndi.gaussian_filter(a, 3.0, order=(2, 0), mode="nearest") * (s_curv * s_curv)
        gxy = ndi.gaussian_filter(a, 3.0, order=(1, 1), mode="nearest") * (s_curv * s_curv)
        dy = np.float32(DOUBLET_OFFSET_PX) * sph
        dx = np.float32(DOUBLET_OFFSET_PX) * cph
        gxx_p = _sample_bilinear(gxx, yf + dy, xf + dx)
        gyy_p = _sample_bilinear(gyy, yf + dy, xf + dx)
        gxy_p = _sample_bilinear(gxy, yf + dy, xf + dx)
        gxx_m = _sample_bilinear(gxx, yf - dy, xf - dx)
        gyy_m = _sample_bilinear(gyy, yf - dy, xf - dx)
        gxy_m = _sample_bilinear(gxy, yf - dy, xf - dx)
        del gxx, gyy, gxy
        hnn_p = (cph * cph * gxx_p + 2.0 * sph * cph * gxy_p + sph * sph * gyy_p).astype(np.float32)
        hnn_m = (cph * cph * gxx_m + 2.0 * sph * cph * gxy_m + sph * sph * gyy_m).astype(np.float32)
        del gxx_p, gyy_p, gxy_p, gxx_m, gyy_m, gxy_m
        curv_diff = (0.5 * np.abs(hnn_p - hnn_m)).astype(np.float32)
        prod = hnn_p * hnn_m
        curv_dipole = (-np.sign(prod) * np.sqrt(np.abs(prod))).astype(np.float32)
        doublet_cols = [curv_diff, curv_dipole]
        del hnn_p, hnn_m, prod

    return warp_cols, signed_norm, doublet_cols


def build_fw_matrix(
    tag: str,
    footprint: np.ndarray,
    phi: np.ndarray,
    coh: np.ndarray,
    stack: np.ndarray | None = None,
    force: bool = False,
) -> tuple[Path, dict]:
    """Build or load the (n_footprint, 67) float32 memmap of H78-FW features."""
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"fw_{tag}.npy"
    meta_p = PROC / f"fw_{tag}.json"
    names = fw_feature_names()
    if out.exists() and meta_p.exists() and not force:
        saved = json.loads(meta_p.read_text())
        if saved.get("n_features") == len(names) and saved.get("names") == names:
            return out, saved

    t0 = time.time()
    if stack is None:
        stack = load_stack()
    ys, xs = np.nonzero(footprint)
    ys = ys.astype(np.int32)
    xs = xs.astype(np.int32)
    n = int(ys.size)

    cph = np.cos(phi[ys, xs]).astype(np.float32)
    sph = np.sin(phi[ys, xs]).astype(np.float32)

    tmp = out.with_suffix(out.suffix + ".partial")
    mm = np.lib.format.open_memmap(tmp, mode="w+", dtype=np.float32, shape=(n, len(names)))

    col_idx = 0
    doublet_store: dict[str, list[np.ndarray]] = {}
    signed_store: dict[str, dict[int, np.ndarray]] = {}

    for bname in WARP_BANDS:
        band_arr = np.asarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        want_doublet = bname in DOUBLET_BANDS
        wcols, snorm, dcols = compute_flank_warp_for_band(
            band_arr, ys, xs, cph, sph, compute_doublet=want_doublet
        )
        for c in wcols:
            mm[:, col_idx] = c
            col_idx += 1
        if bname in ("det_elev", "depth_to_base_surf", "rtp", "iso_grav_anom"):
            signed_store[bname] = snorm
        if want_doublet:
            doublet_store[bname] = dcols
        del band_arr, wcols
        mm.flush()

    for bname in DOUBLET_BANDS:
        for c in doublet_store[bname]:
            mm[:, col_idx] = c
            col_idx += 1
    del doublet_store
    mm.flush()

    # Cross-layer flexural concordance at d=8 and d=14
    s_elev8 = signed_store["det_elev"][8]
    s_base8 = signed_store["depth_to_base_surf"][8]
    s_grav8 = signed_store["iso_grav_anom"][8]
    s_rtp8 = signed_store["rtp"][8]
    s_elev14 = signed_store["det_elev"][14]
    s_base14 = signed_store["depth_to_base_surf"][14]
    s_grav14 = signed_store["iso_grav_anom"][14]

    concord_cols = [
        (-s_elev8 * s_base8).astype(np.float32),
        (s_elev8 * s_grav8).astype(np.float32),
        (-s_base8 * s_grav8).astype(np.float32),
        np.abs(s_rtp8 * s_grav8).astype(np.float32),
        (-s_elev14 * s_base14).astype(np.float32),
        (-s_base14 * s_grav14).astype(np.float32),
    ]
    for c in concord_cols:
        mm[:, col_idx] = c
        col_idx += 1
    del signed_store, concord_cols, s_elev8, s_base8, s_grav8, s_rtp8, s_elev14, s_base14, s_grav14
    mm.flush()

    # Context bands
    for bname in CONTEXT_BANDS:
        band_arr = np.asarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        mm[:, col_idx] = band_arr[ys, xs]
        col_idx += 1
        del band_arr

    # Strike orientation coherence
    mm[:, col_idx] = np.asarray(coh[ys, xs], dtype=np.float32)
    col_idx += 1

    assert col_idx == len(names), f"col_idx {col_idx} != {len(names)}"
    mm.flush()
    del mm
    tmp.replace(out)

    meta = dict(
        tag=tag,
        n_footprint=n,
        n_features=len(names),
        names=names,
        offsets_px=list(OFFSETS_PX),
        doublet_offset_px=DOUBLET_OFFSET_PX,
        detrend_sigma_px=DETREND_SIGMA_PX,
        smooth_fine_px=SMOOTH_FINE_PX,
        seconds=round(time.time() - t0, 1),
    )
    meta_p.write_text(json.dumps(meta, indent=2) + "\n")
    return out, meta
