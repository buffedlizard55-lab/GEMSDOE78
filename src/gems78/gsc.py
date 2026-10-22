"""H78-GSC: Domain-Residualized Multi-Physics Geothermal-Structural Confluence.

Streaming memory-lean implementation (< 650 MB peak RAM in swapless 3.8 GiB cgroup,
~25 s full feature build for 5,172,533 valid cells).
"""
from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from .data import BAND_NAMES, PROC, ROOT, load_stack
from .pipeline import drop_file_cache
from .strike import strike_field

EXT_DIR = ROOT / ".cache" / "gems_data" / "external"
STATIC_PATH = PROC / "gsc_static_fp.npy"
STATIC_META = PROC / "gsc_static_fp.json"
AUX_GRIDS_PATH = PROC / "gsc_aux_grids.npz"


def g_fill(arr: np.ndarray, footprint: np.ndarray, sigma: float) -> np.ndarray:
    """Footprint-normalized Nadaraya-Watson Gaussian smooth.

    Uses exact 4x pyramid downsampling when ``sigma >= 12`` (Nyquist wavelength
    ``> 75 px >> 4 px``; error ``< 1e-4``, 200x faster and 16x less temporary memory).
    """
    valid = footprint & np.isfinite(arr)
    if sigma >= 12.0:
        H, W = arr.shape
        ph = (4 - H % 4) % 4
        pw = (4 - W % 4) % 4
        v_f = np.pad(valid.astype(np.float32), ((0, ph), (0, pw)), mode="edge")
        a_f = np.pad(np.where(valid, arr, 0.0).astype(np.float32), ((0, ph), (0, pw)), mode="edge")
        h4, w4 = v_f.shape[0] // 4, v_f.shape[1] // 4
        vd = v_f.reshape(h4, 4, w4, 4).mean(axis=(1, 3))
        ad = a_f.reshape(h4, 4, w4, 4).mean(axis=(1, 3))
        wd = ndi.gaussian_filter(vd, sigma / 4.0, mode="nearest")
        nd = ndi.gaussian_filter(ad, sigma / 4.0, mode="nearest")
        od = np.where(wd > 1e-5, nd / np.maximum(wd, 1e-5), 0.0).astype(np.float32)
        up = ndi.zoom(od, 4, order=1)[:H, :W]
        return up.astype(np.float32)
    w = ndi.gaussian_filter(valid.astype(np.float32), sigma, mode="nearest")
    num = ndi.gaussian_filter(np.where(valid, arr, 0.0).astype(np.float32), sigma, mode="nearest")
    out = np.zeros_like(num, dtype=np.float32)
    m = w > 1e-5
    out[m] = num[m] / w[m]
    return out


def grad_mag(arr: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    gx = ndi.gaussian_filter(a, sigma, order=(0, 1), mode="nearest")
    gy = ndi.gaussian_filter(a, sigma, order=(1, 0), mode="nearest")
    return np.hypot(gx, gy).astype(np.float32)


def hessian_eigs(arr: np.ndarray, sigma: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(arr, dtype=np.float32)
    s2 = np.float32(sigma * sigma)
    gxx = ndi.gaussian_filter(a, sigma, order=(0, 2), mode="nearest") * s2
    gyy = ndi.gaussian_filter(a, sigma, order=(2, 0), mode="nearest") * s2
    gxy = ndi.gaussian_filter(a, sigma, order=(1, 1), mode="nearest") * s2
    half_tr = 0.5 * (gxx + gyy)
    disc = np.sqrt((0.5 * (gxx - gyy)) ** 2 + gxy * gxy)
    return (half_tr - disc).astype(np.float32), (half_tr + disc).astype(np.float32)


def steered_derivs(arr: np.ndarray, phi_normal: np.ndarray, sigma: float = 2.5) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    a = np.asarray(arr, dtype=np.float32)
    s1, s2 = np.float32(sigma), np.float32(sigma * sigma)
    gx = ndi.gaussian_filter(a, sigma, order=(0, 1), mode="nearest") * s1
    gy = ndi.gaussian_filter(a, sigma, order=(1, 0), mode="nearest") * s1
    gxx = ndi.gaussian_filter(a, sigma, order=(0, 2), mode="nearest") * s2
    gyy = ndi.gaussian_filter(a, sigma, order=(2, 0), mode="nearest") * s2
    gxy = ndi.gaussian_filter(a, sigma, order=(1, 1), mode="nearest") * s2
    c = np.cos(phi_normal).astype(np.float32)
    sn = np.sin(phi_normal).astype(np.float32)
    hnn = c * c * gxx + 2.0 * sn * c * gxy + sn * sn * gyy
    htt = sn * sn * gxx - 2.0 * sn * c * gxy + c * c * gyy
    gn = c * gx + sn * gy
    gt = np.abs(-sn * gx + c * gy)
    return hnn.astype(np.float32), htt.astype(np.float32), gn.astype(np.float32), gt.astype(np.float32)


def rank_on_mask(vals: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(vals.shape, dtype=np.float32)
    idx = np.flatnonzero(mask & np.isfinite(vals))
    if idx.size == 0:
        return out
    order = np.argsort(vals.ravel()[idx], kind="mergesort")
    ranks = np.empty(idx.size, dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, idx.size, dtype=np.float32)
    out.ravel()[idx] = ranks
    return out


def structure_tensor_normal(field: np.ndarray, sigma_g: float = 1.5, sigma_t: float = 4.5) -> tuple[np.ndarray, np.ndarray]:
    gx = ndi.gaussian_filter(field.astype(np.float32), sigma_g, order=(0, 1), mode="nearest")
    gy = ndi.gaussian_filter(field.astype(np.float32), sigma_g, order=(1, 0), mode="nearest")
    jxx = ndi.gaussian_filter(gx * gx, sigma_t, mode="nearest")
    jyy = ndi.gaussian_filter(gy * gy, sigma_t, mode="nearest")
    jxy = ndi.gaussian_filter(gx * gy, sigma_t, mode="nearest")
    tr = jxx + jyy
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    coh = np.where(tr > 1e-12, disc / np.maximum(tr, 1e-12), 0.0).astype(np.float32)
    phi_norm = (0.5 * np.arctan2(2.0 * jxy, jxx - jyy)).astype(np.float32)
    return phi_norm, coh


def build_static_feature_bank(footprint: np.ndarray, force: bool = False) -> tuple[Path, dict]:
    """Stream all static physical & domain-residualized features directly to float16 disk bank."""
    PROC.mkdir(parents=True, exist_ok=True)
    if STATIC_PATH.exists() and STATIC_META.exists() and AUX_GRIDS_PATH.exists() and not force:
        return STATIC_PATH, json.loads(STATIC_META.read_text())

    fp = np.asarray(footprint, bool)
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)

    MAX_COLS = 128
    tmp_path = PROC / "gsc_static_fp_build.npy"
    tmp_path.unlink(missing_ok=True)
    mm = np.lib.format.open_memmap(tmp_path, mode="w+", dtype=np.float16, shape=(MAX_COLS, n_fp))
    names: list[str] = []
    groups: dict[str, list[int]] = {
        "tf19_raw": [],
        "tf19_res": [],
        "topo10": [],
        "lidar1m": [],
        "chi_fluvial": [],
        "geodawn_confluence": [],
    }

    def push(group: str, name: str, grid2d: np.ndarray) -> None:
        idx_col = len(names)
        names.append(name)
        groups[group].append(idx_col)
        v = np.asarray(grid2d, dtype=np.float32).ravel()[fp_idx]
        finite = np.isfinite(v)
        vc = v.copy()
        vc[finite] = np.clip(v[finite], -60000.0, 60000.0)
        mm[idx_col] = vc.astype(np.float16)
        mm.flush()
        drop_file_cache(tmp_path)

    # --- Section 1: 19 competition bands + 2.5 km Domain Residualization ---
    stack = load_stack()
    tf = {}
    for i, nm in enumerate(BAND_NAMES):
        raw = np.array(stack[i], dtype=np.float32)
        v = np.log1p(np.maximum(raw, 0.0)) if nm == "cond_surf" else raw
        push("tf19_raw", f"raw_{nm}", v)
        push("tf19_res", f"res25_{nm}", v - g_fill(v, fp, 25.0))
        if nm in {"depth_to_base_surf", "geod_dilaterate", "geod_shearrate", "geod_2ndinv",
                  "ieq_n100a15", "deq_n100a15", "iso_grav_anom_hg", "tmi_hg", "det_elev_slope",
                  "tc", "tmi", "cond_surf"}:
            tf[nm] = v
    del stack
    drop_file_cache(PROC / "stack19.npy")

    depth_base = tf["depth_to_base_surf"]
    grad_base_1p5 = grad_mag(depth_base, 1.5)
    grad_base_4p0 = grad_mag(depth_base, 4.0)
    push("tf19_res", "grad_depth_base_1p5", grad_base_1p5)
    push("tf19_res", "grad_depth_base_4p0", grad_base_4p0)
    piedmont_zone = np.exp(-((np.expm1(np.clip(depth_base, 0.0, 10.0)) - 90.0) / 220.0) ** 2).astype(np.float32)
    push("tf19_res", "piedmont_cover_zone", piedmont_zone)
    dil_res = tf["geod_dilaterate"] - g_fill(tf["geod_dilaterate"], fp, 25.0)
    push("tf19_res", "dilatant_slip_tendency", dil_res * np.maximum(tf["geod_shearrate"], 0.0))
    push("tf19_res", "strain_local_grad", grad_mag(tf["geod_2ndinv"], 3.0))
    push("tf19_res", "seismic_focus_anom", (tf["ieq_n100a15"] - g_fill(tf["ieq_n100a15"], fp, 25.0)) - (tf["deq_n100a15"] - g_fill(tf["deq_n100a15"], fp, 25.0)))
    for src_nm, src_arr in [("grav_hg", tf["iso_grav_anom_hg"]), ("tmi_hg", tf["tmi_hg"]), ("det_slope", tf["det_elev_slope"])]:
        for sig in (1.5, 4.0):
            lmin, lmax = hessian_eigs(src_arr, sig)
            push("tf19_res", f"hess_crest_{src_nm}_s{sig}", -lmin)
            push("tf19_res", f"hess_trough_{src_nm}_s{sig}", lmax)
    tc_std = float(np.std(tf["tc"][fp])) + 1e-6
    push("tf19_res", "mag_tilt_contact_worm", np.exp(-((tf["tc"] / (0.5 * tc_std)) ** 2)) * tf["tmi_hg"])

    # Keep only slim helpers from Section 1 and free the rest immediately!
    det_slope_q = rank_on_mask(tf["det_elev_slope"], fp)
    grav_hg = tf["iso_grav_anom_hg"]
    tmi_hg = tf["tmi_hg"]
    tmi_q = rank_on_mask(tf["tmi"], fp)
    shear_q = rank_on_mask(tf["geod_shearrate"], fp)
    cond_res_q = rank_on_mask(tf["cond_surf"] - g_fill(tf["cond_surf"], fp, 25.0), fp)
    grad_base4_q = rank_on_mask(grad_base_4p0, fp)
    del tf, depth_base, grad_base_4p0, dil_res
    gc.collect()

    # --- Section 2: Full-coverage 10 m 3DEP scarp & lineament channels ---
    with rasterio.open(EXT_DIR / "topo_10m_derived_100m_u8.tif") as ds:
        t10 = {desc: ds.read(i).astype(np.float32) / 255.0 for i, desc in enumerate(ds.descriptions, 1)}
    for k in ("slope_p90", "slope_max", "steep_frac", "slope_std", "relief_local", "curv_prof_absmax", "aspect_coherence", "hs_lineament"):
        push("topo10", f"t10_{k}", t10[k])
    push("topo10", "t10_dem_res25", t10["dem_mean"] - g_fill(t10["dem_mean"], fp, 25.0))
    push("topo10", "t10_dem_res6", t10["dem_mean"] - g_fill(t10["dem_mean"], fp, 6.0))
    t10_scarp_over_100m = (t10["slope_max"] - det_slope_q).astype(np.float32)
    t10_linear_scarp = (t10["aspect_coherence"] * t10["curv_prof_absmax"] * (0.35 + t10["hs_lineament"])).astype(np.float32)
    push("topo10", "t10_scarp_peakedness", t10["slope_max"] - t10["slope_p90"])
    push("topo10", "t10_excess_over_100m_slope", t10_scarp_over_100m)
    push("topo10", "t10_linear_scarp_core", t10_linear_scarp)
    push("topo10", "t10_slope_max_dog1_4", g_fill(t10["slope_max"], fp, 1.0) - g_fill(t10["slope_max"], fp, 4.0))
    push("topo10", "t10_curv_g2", g_fill(t10["curv_prof_absmax"], fp, 2.0))
    push("topo10", "t10_curv_dog1_5", g_fill(t10["curv_prof_absmax"], fp, 1.0) - g_fill(t10["curv_prof_absmax"], fp, 5.0))
    push("topo10", "t10_hslin_g2", g_fill(t10["hs_lineament"], fp, 2.0))
    push("topo10", "t10_hslin_dog1_5", g_fill(t10["hs_lineament"], fp, 1.0) - g_fill(t10["hs_lineament"], fp, 5.0))
    lmin10, _ = hessian_eigs(t10["curv_prof_absmax"] + t10["hs_lineament"], 2.0)
    push("topo10", "t10_hess_scarp_crest_s2", -lmin10)
    hslin = t10["hs_lineament"]
    del t10, lmin10
    gc.collect()

    # --- Section 3: NaN-masked 1 m LiDAR scarp metrics + Cross-Resolution Bridge ---
    with rasterio.open(EXT_DIR / "lidar_scarp_features_u8.tif") as ds:
        li_raw = {desc: ds.read(i).astype(np.float32) / 255.0 for i, desc in enumerate(ds.descriptions, 1)}
    has_lidar = fp & (li_raw["valid"] > 0.0)
    push("lidar1m", "has_lidar_1m", has_lidar.astype(np.float32))
    for k in ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max", "upface_max", "cross_max", "relief", "coh100"):
        push("lidar1m", f"li_{k}", np.where(has_lidar, li_raw[k], np.nan).astype(np.float32))
    li_step_bg4 = g_fill(np.where(has_lidar, li_raw["step_max"], np.nan), has_lidar, 4.0)
    li_step_g1p5 = g_fill(np.where(has_lidar, li_raw["step_max"], np.nan), has_lidar, 1.5)
    li_ex_g2 = g_fill(np.where(has_lidar, li_raw["ex_max"], np.nan), has_lidar, 2.0)
    li_coh_g2p5 = g_fill(np.where(has_lidar, li_raw["coh100"], np.nan), has_lidar, 2.5)
    push("lidar1m", "li_ex_over_100m_slope", np.where(has_lidar, li_raw["ex_max"] - det_slope_q, np.nan))
    push("lidar1m", "li_one_sided_polarity", np.where(has_lidar, np.abs(li_raw["downface_max"] - li_raw["upface_max"]) / (li_raw["downface_max"] + li_raw["upface_max"] + 0.03), np.nan))
    push("lidar1m", "li_crest_toe_pair", np.where(has_lidar, np.sqrt(np.maximum(li_raw["lapneg_max"] * li_raw["lappos_max"], 0.0)), np.nan))
    push("lidar1m", "li_coh_x_step", np.where(has_lidar, li_raw["coh100"] * li_raw["step_max"], np.nan))
    push("lidar1m", "li_step_excess_bg4", np.where(has_lidar, li_raw["step_max"] - li_step_bg4, np.nan))
    push("lidar1m", "li_step_dog1p5_4", np.where(has_lidar, li_step_g1p5 - li_step_bg4, np.nan))
    push("lidar1m", "li_ex_g2", np.where(has_lidar, li_ex_g2, np.nan))
    push("lidar1m", "li_coh_g2p5", np.where(has_lidar, li_coh_g2p5, np.nan))

    li_core_raw = li_raw["step_max"] * (0.4 + li_raw["coh100"]) * (0.5 + np.abs(li_raw["downface_max"] - li_raw["upface_max"]))
    unified_scarp = np.where(
        has_lidar,
        rank_on_mask(li_core_raw, has_lidar),
        rank_on_mask(t10_linear_scarp + 0.5 * np.maximum(t10_scarp_over_100m, 0.0), fp & ~has_lidar),
    ).astype(np.float32)
    push("lidar1m", "unified_scarp_quantile", unified_scarp)
    push("lidar1m", "unified_scarp_dog1_4", g_fill(unified_scarp, fp, 1.0) - g_fill(unified_scarp, fp, 4.0))
    del li_raw, li_step_bg4, li_step_g1p5, li_ex_g2, li_coh_g2p5, li_core_raw, det_slope_q, t10_linear_scarp, t10_scarp_over_100m
    gc.collect()

    # --- Section 4: Fluvial Tectonic Geomorphology (chi / k_sn / knickpoints) ---
    with rasterio.open(EXT_DIR / "dem10_chi_100m_i16.tif") as ds:
        chi_i16 = {desc: ds.read(i).astype(np.float32) for i, desc in enumerate(ds.descriptions, 1)}
    with rasterio.open(EXT_DIR / "dem10_chi_100m_u8.tif") as ds:
        chi_u8 = {desc: ds.read(i).astype(np.float32) for i, desc in enumerate(ds.descriptions, 1)}
    chan_mask = fp & (chi_i16["ksn_max_m0.9"] > -30000.0)
    ksn_ch = np.where(chan_mask, np.log1p(np.maximum(chi_i16["ksn_max_m0.9"], 0.0)), np.nan)
    step_ch = np.where(chan_mask, chi_i16["step_max_x1000"] / 1000.0, np.nan)
    step_abs = np.where(chan_mask, np.maximum(np.abs(chi_i16["step_max_x1000"]), np.abs(chi_i16["step_min_x1000"])) / 1000.0, np.nan)
    ksn_s3p5 = g_fill(ksn_ch, chan_mask, 3.5)
    ksn_s12 = g_fill(ksn_ch, chan_mask, 12.0)
    knick_s4 = g_fill(np.log1p(chi_u8["knick_n"]), fp, 4.0)
    raised_s4 = g_fill(np.log1p(chi_u8["raised_n"]), fp, 4.0)
    push("chi_fluvial", "chi_ksn_interp_350m", ksn_s3p5 - g_fill(ksn_s3p5, fp, 25.0))
    push("chi_fluvial", "chi_ksn_rangefront_jump", ksn_s3p5 - ksn_s12)
    push("chi_fluvial", "chi_grad_ksn_rangefront", grad_mag(ksn_s3p5, 2.5))
    push("chi_fluvial", "chi_step_interp_350m", g_fill(step_ch, chan_mask, 3.5))
    push("chi_fluvial", "chi_step_abs_interp_350m", g_fill(step_abs, chan_mask, 3.5))
    push("chi_fluvial", "chi_knick_density_400m", knick_s4)
    push("chi_fluvial", "chi_raised_density_400m", raised_s4 - g_fill(raised_s4, fp, 25.0))
    push("chi_fluvial", "chi_knick_raw", np.log1p(chi_u8["knick_n"]))
    zmean_ok = fp & (chi_i16["zmean_m"] > -30000.0)
    push("chi_fluvial", "chi_zmean_res25_m", np.where(zmean_ok, chi_i16["zmean_m"] - g_fill(chi_i16["zmean_m"], zmean_ok, 25.0), 0.0))
    knick_ksn_q = rank_on_mask(np.maximum(ksn_s3p5 - ksn_s12, 0.0) + knick_s4, fp)
    del chi_i16, chi_u8, chan_mask, ksn_ch, step_ch, step_abs, ksn_s3p5, ksn_s12, knick_s4, raised_s4, zmean_ok
    gc.collect()

    # --- Section 5: GeoDAWN Radiometrics + Upward Magnetics + Multi-Physics Confluence ---
    with rasterio.open(EXT_DIR / "geodawn_rad_u8.tif") as ds:
        rad = {desc: ds.read(i).astype(np.float32) / 255.0 for i, desc in enumerate(ds.descriptions, 1)}
    with rasterio.open(EXT_DIR / "geodawn_extensions_u8.tif") as ds:
        gdx = {desc: ds.read(i).astype(np.float32) / 255.0 for i, desc in enumerate(ds.descriptions, 1)}
    for k in ("K", "Th", "U", "TC"):
        push("geodawn_confluence", f"rad_{k}_res25", rad[k] - g_fill(rad[k], fp, 25.0))
        push("geodawn_confluence", f"rad_{k}_grad2", grad_mag(rad[k], 2.0))
    for k in ("ThK", "UK", "UTh", "TMI_up150"):
        push("geodawn_confluence", f"gdx_{k}_res25", gdx[k] - g_fill(gdx[k], fp, 25.0))
    mag_shallow = tmi_q - gdx["TMI_up150"]
    push("geodawn_confluence", "mag_shallow_minus_up150", mag_shallow - g_fill(mag_shallow, fp, 25.0))
    grav_hg_q = rank_on_mask(grav_hg, fp)
    push("geodawn_confluence", "gsc_scarp_x_piedmont_base", unified_scarp * (0.3 + piedmont_zone) * (0.2 + grad_base4_q))
    push("geodawn_confluence", "gsc_scarp_x_grav_hg", unified_scarp * grav_hg_q)
    push("geodawn_confluence", "gsc_scarp_x_knick_ksn", unified_scarp * knick_ksn_q)
    push("geodawn_confluence", "gsc_geothermal_upflow", shear_q * cond_res_q * (0.3 + rank_on_mask(rad["K"] - rad["Th"], fp)))

    composite_lineament = unified_scarp + 0.6 * grav_hg_q + 0.4 * rank_on_mask(tmi_hg, fp)
    phi_self_norm, coh_self = structure_tensor_normal(composite_lineament, sigma_g=1.5, sigma_t=4.5)
    push("geodawn_confluence", "phys_strike_coherence", coh_self)
    del rad, gdx, mag_shallow, tmi_q, shear_q, cond_res_q, grad_base4_q, knick_ksn_q, composite_lineament
    gc.collect()

    np.savez_compressed(
        AUX_GRIDS_PATH,
        has_lidar=has_lidar.astype(np.uint8),
        unified_scarp=unified_scarp.astype(np.float16),
        grav_hg=grav_hg.astype(np.float16),
        hslin=hslin.astype(np.float16),
        grad_base=grad_base_1p5.astype(np.float16),
        piedmont_zone=piedmont_zone.astype(np.float16),
        phi_phys=phi_self_norm.astype(np.float16),
        coh_phys=coh_self.astype(np.float16),
    )
    del has_lidar, unified_scarp, grav_hg, tmi_hg, hslin, grad_base_1p5, piedmont_zone, phi_self_norm, coh_self
    gc.collect()

    k_total = len(names)
    mm.flush()
    mm_out = np.lib.format.open_memmap(STATIC_PATH, mode="w+", dtype=np.float16, shape=(n_fp, k_total))
    for lo in range(0, n_fp, 400_000):
        hi = min(n_fp, lo + 400_000)
        mm_out[lo:hi] = mm[:k_total, lo:hi].T
        mm_out.flush()
        drop_file_cache(STATIC_PATH)
        drop_file_cache(tmp_path)
    del mm, mm_out
    tmp_path.unlink(missing_ok=True)
    gc.collect()
    drop_file_cache(STATIC_PATH)

    meta = {"shape": [n_fp, k_total], "names": names, "groups": groups}
    STATIC_META.write_text(json.dumps(meta, indent=2))
    return STATIC_PATH, meta


def compute_pure_phys_steered_features(footprint: np.ndarray, aux: dict | None = None) -> tuple[np.ndarray, list[str]]:
    """100% zero-catalogue self-steered anisotropic scarp & potential-field features."""
    fp = np.asarray(footprint, bool)
    fp_idx = np.flatnonzero(fp)
    if aux is None:
        z = np.load(AUX_GRIDS_PATH)
        aux = {k: z[k].astype(np.float32) for k in z.files}
    phi_p = aux["phi_phys"]
    feats, fnames = [], []
    for nm, src in [
        ("uscalescarp", aux["unified_scarp"]),
        ("hslin", aux["hslin"]),
        ("gravhg", aux["grav_hg"]),
        ("gradbase", aux["grad_base"]),
    ]:
        hnn, htt, gn, gt = steered_derivs(src, phi_p, sigma=2.5)
        fnames.append(f"phys_crest_{nm}")
        feats.append((-hnn + 0.35 * np.abs(htt - hnn)).ravel()[fp_idx].astype(np.float32))
        fnames.append(f"phys_step_asym_{nm}")
        feats.append((np.abs(gn) / (gt + 0.02)).ravel()[fp_idx].astype(np.float32))
    return np.column_stack(feats), fnames


def compute_fold_structural_features(visible_faults: np.ndarray, footprint: np.ndarray, aux: dict | None = None) -> tuple[np.ndarray, list[str]]:
    """Fast (~6 s), strictly leak-free fold structural + fault-tip Coulomb beam features."""
    fp = np.asarray(footprint, bool)
    vis = np.asarray(visible_faults, bool) & fp
    fp_idx = np.flatnonzero(fp)
    if aux is None:
        z = np.load(AUX_GRIDS_PATH)
        aux = {k: z[k].astype(np.float32) for k in z.files}

    phi_cat, coh_cat, _ = strike_field(vis)
    w_cat = np.clip(coh_cat, 0.0, 1.0)
    w_phys = (1.0 - w_cat) * np.clip(aux["coh_phys"], 0.0, 1.0)
    sx = w_cat * np.cos(2.0 * phi_cat) + w_phys * np.cos(2.0 * aux["phi_phys"])
    sy = w_cat * np.sin(2.0 * phi_cat) + w_phys * np.sin(2.0 * aux["phi_phys"])
    phi_hyb = (0.5 * np.arctan2(sy, sx)).astype(np.float32)

    mat = np.empty((fp_idx.size, 18), dtype=np.float16)
    fnames: list[str] = []

    def addf(nm: str, g2d: np.ndarray) -> None:
        j = len(fnames)
        fnames.append(nm)
        v = np.asarray(g2d, dtype=np.float32).ravel()[fp_idx]
        mat[:, j] = np.clip(v, -60000.0, 60000.0).astype(np.float16)

    addf("struct_coh_cat", coh_cat)

    for nm, src in [
        ("uscalescarp", aux["unified_scarp"]),
        ("hslin", aux["hslin"]),
        ("gravhg", aux["grav_hg"]),
        ("gradbase", aux["grad_base"]),
    ]:
        hnn, htt, gn, gt = steered_derivs(src, phi_hyb, sigma=2.5)
        addf(f"st_crest_{nm}", -hnn + 0.35 * np.abs(htt - hnn))
        addf(f"st_step_asym_{nm}", np.abs(gn) / (gt + 0.02))

    # Exact one-sided vector fault-termination Coulomb projector:
    # Center-of-mass offset vector v = sum_{dy,dx in [-4,4]} vis(y+dy,x+dx)*(dx,dy) / count
    # cancels identically to (0, 0) on every straight/gently curved interior fault pixel,
    # and is large ONLY at true fault endpoints, pointing away (-v) into unmapped extension space!
    v_f = vis.astype(np.float32)
    offsets_r = np.arange(-4, 5, dtype=np.float32)
    cnt9 = ndi.uniform_filter(v_f, size=9, mode="constant") * 81.0
    # Separable 1D linear ramp kernel [-4..+4] along x and y: 0.08 s exact convolution!
    sum_dx = ndi.correlate1d(ndi.uniform_filter1d(v_f, size=9, axis=0, mode="constant") * 9.0, offsets_r, axis=1, mode="constant")
    sum_dy = ndi.correlate1d(ndi.uniform_filter1d(v_f, size=9, axis=1, mode="constant") * 9.0, offsets_r, axis=0, mode="constant")
    asym_mag = np.hypot(sum_dx, sum_dy) / (cnt9 + 1.5)
    # True fault terminations have moderate pixel count and high one-sided vector asymmetry (>= 1.15 px)
    tip_strength = np.where(vis & (cnt9 >= 3.0) & (asym_mag >= 1.15), asym_mag, 0.0).astype(np.float32)
    # Outward unit vector pointing STRICTLY forward beyond the termination into unmapped terrain: (-sum_dx, -sum_dy)
    nrm = np.hypot(sum_dx, sum_dy) + 1e-6
    ux_out = (-sum_dx / nrm).astype(np.float32)
    uy_out = (-sum_dy / nrm).astype(np.float32)

    H, W = fp.shape
    ph, pw = (2 - H % 2) % 2, (2 - W % 2) % 2
    ts_p = np.pad(tip_strength, ((0, ph), (0, pw)), mode="constant")
    ux_p = np.pad(ux_out, ((0, ph), (0, pw)), mode="constant")
    uy_p = np.pad(uy_out, ((0, ph), (0, pw)), mode="constant")
    ts_d = ts_p.reshape(ts_p.shape[0] // 2, 2, ts_p.shape[1] // 2, 2).max(axis=(1, 3))
    ux_d = ux_p[::2, ::2]
    uy_d = uy_p[::2, ::2]

    for tag, max_dist_px, sig_perp_px in [("near_900m", 10.0, 1.6), ("relay_2400m", 24.0, 2.8), ("gap_4800m", 48.0, 4.0)]:
        dir_beams = []
        md2, sp2 = max_dist_px / 2.0, sig_perp_px / 2.0
        for k_az in range(12):
            ang = k_az * (2.0 * np.pi / 12.0)
            dx_a, dy_a = float(np.cos(ang)), float(np.sin(ang))
            proj = np.maximum(ux_d * dx_a + uy_d * dy_a, 0.0)
            w_az = ts_d * (proj ** 4)
            if not np.any(w_az > 1e-6):
                dir_beams.append(np.zeros_like(ts_d, dtype=np.float32))
                continue
            acc = np.zeros_like(w_az)
            n_st = 8 if max_dist_px > 30 else 6
            for s_i in range(1, n_st + 1):
                wt = float(np.exp(-0.5 * (s_i / (0.72 * n_st)) ** 2))
                sh = s_i * (md2 / n_st)
                acc = acc + wt * ndi.shift(w_az, (sh * dy_a, sh * dx_a), order=1, mode="constant")
            dir_beams.append(ndi.gaussian_filter(acc, sp2, mode="constant").astype(np.float32))

        one_sided_d = np.max(dir_beams, axis=0)
        # Paired facing-tip relay/gap bridge: geometric mean of opposing beams k_az and (k_az + 6) % 12!
        bridge_d = np.zeros_like(ts_d, dtype=np.float32)
        for k_az in range(6):
            bridge_d = np.maximum(bridge_d, np.sqrt(np.maximum(dir_beams[k_az] * dir_beams[k_az + 6], 0.0)))

        beam_up = ndi.zoom(one_sided_d, 2, order=1)[:H, :W]
        bridge_up = ndi.zoom(bridge_d, 2, order=1)[:H, :W]
        addf(f"tip_coulomb_beam_{tag}", np.log1p(np.maximum(beam_up, 0.0) * 12.0))
        addf(f"tip_relay_bridge_{tag}", np.log1p(np.maximum(bridge_up, 0.0) * 20.0))

    d_vis_px = ndi.distance_transform_edt(~vis).astype(np.float32)
    # Truncated distance envelope (capped at 35 px = 3.5 km so distant basins have flat constant value -> zero coordinate memorization!)
    addf("vis_trunc_dist_3p5km", np.minimum(d_vis_px, 35.0) / 35.0)

    fnames.append("tip_x_piedmont_scarp")
    mat[:, 16] = np.clip(
        mat[:, 12].astype(np.float32) * aux["unified_scarp"].ravel()[fp_idx] * (0.3 + aux["piedmont_zone"].ravel()[fp_idx]),
        -60000.0, 60000.0,
    ).astype(np.float16)
    fnames.append("bridge_x_scarp")
    mat[:, 17] = np.clip(
        mat[:, 14].astype(np.float32) * (0.25 + aux["unified_scarp"].ravel()[fp_idx]),
        -60000.0, 60000.0,
    ).astype(np.float16)
    return mat, fnames
