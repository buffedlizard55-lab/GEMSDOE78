"""H78-GFV: Anisotropic Crustal-Weakness Geodesics & Sibson Fault-Valve Coupling.

Implements:
1. ``build_gfv_static_channels``: builds & caches the 21 strictly zero-catalogue
   external tectonic-fluvial (``dem10_chi_100m``) + DOE GDR 1391 hydrothermal
   (quartz/chalcedony/Na-K-Ca geothermometers, shallow 2-m probe ``F2mDAB``
   thermal plumes, 709 Quaternary sinter/travertine fault-valve deposits,
   Quaternary volcanic vents, and strike-steered hydrothermal conduits) channels
   on disk as ``.cache/features/gfv_ext21.npy`` (float16, ~515 MB).
   Strictly forbids reading ``dist_known_fault_px`` by runtime assertion.
2. ``compute_geodesic_network``: builds the 8-connected anisotropic crustal
   fracture resistance graph at 200 m (``1865 x 1646`` = 3.07M nodes) from
   strictly fold-clean physical weakness ``w_phys`` + local structural strike
   ``theta_phys`` and runs Alon-Yuster-Zwick color-coded multi-source C Dijkstra
   sweeps + shortest-path geodesic current tracing to extract 12 fold-clean
   crustal geodesic channels with zero access to hidden faults.
"""
from __future__ import annotations

import csv
import gc
import io
import json
import struct
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as rio_transform
from scipy.ndimage import (
    binary_dilation,
    convolve,
    distance_transform_edt,
    gaussian_filter,
    label,
    minimum_filter,
    zoom,
)
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

H_GRID, W_GRID = 3730, 3292
X0_UTM, Y0_UTM, PIX_M = 243350.0, 4508550.0, 100.0

GFV_EXT_NAMES: list[str] = [
    # 9 seamless 10m 3DEP fluvial tectonic channels (dem10_chi_100m)
    "chi_step_max",
    "chi_step_min",
    "chi_ksn_max",
    "chi_log10_area",
    "chi_zmean",
    "chi_chan_n",
    "chi_knick_n",
    "chi_raised_n",
    "chi_knick_smooth_r4",
    # 12 leak-free DOE GDR 1391 hydrothermal / 2m probe / sinter / vent channels
    "gfv_temp_excess_r3",
    "gfv_temp_excess_r12",
    "gfv_geotherm_max_r4",
    "gfv_geotherm_max_r15",
    "gfv_geotherm_aniso_strike",
    "gfv_probe2m_dab_pos_r4",
    "gfv_probe2m_dab_pos_r14",
    "gfv_probe2m_surveyed_r10",
    "gfv_paleo_sinter_r4",
    "gfv_paleo_sinter_r16",
    "gfv_volc_vent_r16",
    "gfv_hydro_pure_current",
]

GFV_GEO_NAMES: list[str] = [
    "geo_log_d_trace",
    "geo_T1_trace",
    "geo_tortuosity_trace",
    "geo_T1_tip",
    "geo_tortuosity_tip",
    "geo_Tpair_sum",
    "geo_fermat_ridge",
    "geo_J_narrow",
    "geo_J_wide",
    "geo_J_vent_bridge",
    "geo_along_tip_cos",
    "geo_host_len_log",
]


def _utm_to_rc(utm_e: float, utm_n: float) -> tuple[int, int]:
    col = int(np.floor((utm_e - X0_UTM) / PIX_M))
    row = int(np.floor((Y0_UTM - utm_n) / PIX_M))
    return row, col


def _parse_dbf_records(dbf_bytes: bytes) -> list[dict[str, str]]:
    num_rec, hdr_len, rec_len = struct.unpack("<IHH", dbf_bytes[4:12])
    fields: list[tuple[str, int]] = []
    pos = 32
    while dbf_bytes[pos] != 0x0D:
        fname = dbf_bytes[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        flen = dbf_bytes[pos + 16]
        fields.append((fname, flen))
        pos += 32
    records: list[dict[str, str]] = []
    base = hdr_len
    for _ in range(num_rec):
        if base + rec_len > len(dbf_bytes):
            break
        rec = dbf_bytes[base : base + rec_len]
        base += rec_len
        if rec[0:1] == b"*":
            continue
        off = 1
        row_d: dict[str, str] = {}
        for fn, fl in fields:
            row_d[fn] = rec[off : off + fl].decode("utf-8", errors="replace").strip()
            off += fl
        records.append(row_d)
    return records


def compute_physical_strike(stack_mm: np.ndarray, names: list[str], fp: np.ndarray) -> np.ndarray:
    """Pure physical strike azimuth in [0, pi) from DEM detrend + gravity + RTP magnetics."""
    idx_dem = names.index("tf_dem_detrend_r20") if "tf_dem_detrend_r20" in names else 0
    idx_grv = names.index("iso_grav_anom") if "iso_grav_anom" in names else 13
    idx_mag = names.index("rtp") if "rtp" in names else 2

    Jxx = np.zeros((H_GRID, W_GRID), np.float32)
    Jxy = np.zeros((H_GRID, W_GRID), np.float32)
    Jyy = np.zeros((H_GRID, W_GRID), np.float32)
    for b_idx, w_src in ((idx_dem, 1.0), (idx_grv, 0.8), (idx_mag, 0.6)):
        arr = np.nan_to_num(np.asarray(stack_mm[b_idx], dtype=np.float32), nan=0.0)
        p1, p99 = np.percentile(arr[fp], [1.0, 99.0])
        arr = np.clip((arr - p1) / max(float(p99 - p1), 1e-6), 0.0, 1.0)
        gy = gaussian_filter(arr, sigma=2.5, order=[1, 0])
        gx = gaussian_filter(arr, sigma=2.5, order=[0, 1])
        Jxx += w_src * gx * gx
        Jxy += w_src * gx * gy
        Jyy += w_src * gy * gy
        del arr, gx, gy
    Jxx = gaussian_filter(Jxx, sigma=6.0)
    Jxy = gaussian_filter(Jxy, sigma=6.0)
    Jyy = gaussian_filter(Jyy, sigma=6.0)
    # Gradient main angle is normal to strike; add pi/2 to get strike tangent in [0, pi)
    grad_ang = 0.5 * np.arctan2(2.0 * Jxy, Jxx - Jyy)
    strike_theta = np.mod(grad_ang + 0.5 * np.pi, np.pi).astype(np.float32)
    del Jxx, Jxy, Jyy, grad_ang
    gc.collect()
    return strike_theta


def _build_graph_2x(slowness_full: np.ndarray, strike_full: np.ndarray, fp_full: np.ndarray, aniso: float = 2.2):
    """Build 2x-pooled (H//2 x W//2, 200 m) 8-connected anisotropic crustal resistance graph."""
    H2, W2 = slowness_full.shape[0] // 2, slowness_full.shape[1] // 2
    s2 = slowness_full.reshape(H2, 2, W2, 2).mean(axis=(1, 3)).astype(np.float32)
    fp2 = fp_full.reshape(H2, 2, W2, 2).any(axis=(1, 3))
    # Circular double-angle average for axial strike orientation
    c2 = np.cos(2.0 * strike_full).reshape(H2, 2, W2, 2).mean(axis=(1, 3))
    sn2 = np.sin(2.0 * strike_full).reshape(H2, 2, W2, 2).mean(axis=(1, 3))
    th2 = (0.5 * np.arctan2(sn2, c2)) % np.pi
    del c2, sn2

    # Outside footprint gets high barrier cost so paths remain inside Nevada footprint
    s2 = np.where(fp2, np.clip(s2, 0.04, 1.0), 8.0)

    rows, cols, vals = [], [], []
    # Note: y increases southward, x increases eastward
    for dy, dx, dist, az in (
        (0, 1, 1.0, 0.0),
        (1, 0, 1.0, 0.5 * np.pi),
        (1, 1, 1.41421356, 0.25 * np.pi),
        (1, -1, 1.41421356, 0.75 * np.pi),
    ):
        y0 = slice(0, H2 - dy)
        y1 = slice(dy, H2)
        x0 = slice(max(0, -dx), W2 - max(0, dx))
        x1 = slice(max(0, dx), W2 + min(0, dx))
        u = (np.arange(H2, dtype=np.int32)[y0, None] * W2 + np.arange(W2, dtype=np.int32)[None, x0]).ravel()
        v = (np.arange(H2, dtype=np.int32)[y1, None] * W2 + np.arange(W2, dtype=np.int32)[None, x1]).ravel()
        th_mid = 0.5 * (th2[y0, x0] + th2[y1, x1])
        sin2 = np.sin(az - th_mid) ** 2
        cost = (dist * 0.5 * (s2[y0, x0] + s2[y1, x1]) * (1.0 + aniso * sin2)).astype(np.float32).ravel()
        rows.append(u)
        cols.append(v)
        vals.append(cost)
    G_sp = csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(H2 * W2, H2 * W2),
    )
    return G_sp, H2, W2, fp2


def _trace_paths_from_saddles(
    d_red: np.ndarray,
    p_red: np.ndarray,
    d_blue: np.ndarray,
    p_blue: np.ndarray,
    H2: int,
    W2: int,
    max_saddles: int = 1600,
    max_pair_cost: float = 48.0,
) -> np.ndarray:
    """Trace shortest-path geodesic trajectories back from minimal Red-Blue saddles."""
    d_sum = (d_red + d_blue).reshape(H2, W2)
    finite = np.isfinite(d_sum) & (d_sum > 0.5) & (d_sum <= max_pair_cost)
    if not finite.any():
        return np.zeros((H2, W2), np.float32)
    big = np.where(finite, d_sum, 1e9)
    loc_min = (big == minimum_filter(big, size=9, mode="nearest")) & finite
    sy, sx = np.nonzero(loc_min)
    if sy.size == 0:
        return np.zeros((H2, W2), np.float32)
    vals = big[sy, sx]
    if sy.size > max_saddles:
        ord_s = np.argsort(vals)[:max_saddles]
        sy, sx, vals = sy[ord_s], sx[ord_s], vals[ord_s]
    currents = np.zeros(H2 * W2, np.float32)
    weights = 1.0 / (1.0 + 0.12 * vals)
    starts = (sy * W2 + sx).astype(np.int32)
    for node0, wgt in zip(starts, weights):
        w_f = float(wgt)
        cur = int(node0)
        steps = 0
        while cur >= 0 and steps < 260:
            currents[cur] += w_f
            nxt = int(p_red[cur])
            if nxt < 0 or nxt == cur:
                break
            cur = nxt
            steps += 1
        cur = int(p_blue[int(node0)])
        steps = 0
        while cur >= 0 and steps < 260:
            currents[cur] += w_f
            nxt = int(p_blue[cur])
            if nxt < 0 or nxt == cur:
                break
            cur = nxt
            steps += 1
    return currents.reshape(H2, W2)


def _upsample_2x(arr2: np.ndarray, target_shape: tuple[int, int] = (H_GRID, W_GRID)) -> np.ndarray:
    up = np.repeat(np.repeat(arr2.astype(np.float32), 2, axis=0), 2, axis=1)
    return gaussian_filter(up[: target_shape[0], : target_shape[1]], sigma=0.85).astype(np.float32)


def build_gfv_static_channels(
    data_dir: Path,
    feat_dir: Path,
    fp: np.ndarray,
    force: bool = False,
) -> tuple[np.ndarray, dict]:
    """Build or open cached 21 zero-catalogue static channels (float16 memmap)."""
    out_path = feat_dir / "gfv_ext21.npy"
    meta_path = feat_dir / "gfv_ext21.json"
    if out_path.exists() and meta_path.exists() and not force:
        mm = np.lib.format.open_memmap(out_path, mode="r")
        return mm, json.loads(meta_path.read_text())

    t0 = time.time()
    ext_dir = data_dir / "external"
    names_meta = json.loads((feat_dir / "names.json").read_text())
    stack_mm = np.lib.format.open_memmap(feat_dir / "stack.npy", mode="r")
    strike_theta = compute_physical_strike(stack_mm, names_meta["names"], fp)
    np.save(feat_dir / "gfv_phys_strike.npy", strike_theta.astype(np.float16))

    mm = np.lib.format.open_memmap(out_path, mode="w+", dtype=np.float16, shape=(len(GFV_EXT_NAMES), H_GRID, W_GRID))

    # 1. Read 9 channels from dem10_chi_100m_i16.tif + dem10_chi_100m_u8.tif
    with rasterio.open(ext_dir / "dem10_chi_100m_i16.tif") as ds:
        for b in range(5):
            raw = ds.read(b + 1).astype(np.float32)
            raw = np.where(fp & (raw > -32000), raw, 0.0)
            if b < 4:
                raw *= 1e-3
            mm[b] = np.clip(raw, -30000.0, 30000.0).astype(np.float16)
            del raw
    with rasterio.open(ext_dir / "dem10_chi_100m_u8.tif") as ds:
        for b in range(4):
            raw = ds.read(b + 1).astype(np.float32)
            raw = np.where(fp, raw, 0.0)
            if b == 1:
                knick_s4 = gaussian_filter(raw, sigma=4.0)
            mm[5 + b] = raw.astype(np.float16)
            del raw
    mm[8] = np.where(fp, knick_s4, 0.0).astype(np.float16)
    del knick_s4

    # 2. Leak-free GDR 1391 well/spring temperatures & chemical geothermometers
    # STRICT RUNTIME BAN ON 'dist_known_fault_px'
    temp_grid = np.zeros((H_GRID, W_GRID), np.float32)
    geoth_grid = np.zeros((H_GRID, W_GRID), np.float32)
    anchor_pts: list[tuple[int, int, int]] = []  # (r, c, source_id)
    n_geoth_hot = 0
    with (ext_dir / "gdr_wellspring_in_footprint.csv").open() as f:
        rd = csv.DictReader(f)
        for rec in rd:
            rec.pop("dist_known_fault_px", None)
            assert "dist_known_fault_px" not in rec
            r = int(float(rec["row"]))
            c = int(float(rec["col"]))
            if not (0 <= r < H_GRID and 0 <= c < W_GRID and fp[r, c]):
                continue
            tc = float(rec["temp_c"]) if rec["temp_c"] and rec["temp_c"] != "nan" else 0.0
            gq = float(rec["geothermquartz_c"]) if rec["geothermquartz_c"] and rec["geothermquartz_c"] != "nan" else 0.0
            gc_ = float(rec["geothermchalc_c"]) if rec["geothermchalc_c"] and rec["geothermchalc_c"] != "nan" else 0.0
            gcat = float(rec["geothermcat_c"]) if rec["geothermcat_c"] and rec["geothermcat_c"] != "nan" else 0.0
            if np.isfinite(tc) and tc > 20.0:
                temp_grid[r, c] = max(temp_grid[r, c], min(tc - 20.0, 220.0))
            gmax = max(v for v in (gq, gc_, gcat, tc) if np.isfinite(v)) if any(np.isfinite(v) for v in (gq, gc_, gcat, tc)) else 0.0
            if gmax > 75.0:
                geoth_grid[r, c] = max(geoth_grid[r, c], min(gmax - 75.0, 220.0))
            if gmax >= 115.0 or tc >= 42.0:
                anchor_pts.append((r, c, len(anchor_pts) + 1))
                n_geoth_hot += 1

    mm[9] = np.log1p(gaussian_filter(temp_grid, sigma=3.0) * 8.0).astype(np.float16)
    mm[10] = np.log1p(gaussian_filter(temp_grid, sigma=12.0) * 20.0).astype(np.float16)
    g_r4 = np.log1p(gaussian_filter(geoth_grid, sigma=4.0) * 6.0)
    g_r15 = np.log1p(gaussian_filter(geoth_grid, sigma=15.0) * 18.0)
    mm[11] = g_r4.astype(np.float16)
    mm[12] = g_r15.astype(np.float16)

    # Strike-steered hydrothermal conduit projection (advecting thermal anomalies ±8 px along local strike)
    aniso_h = g_r4.copy()
    dy_s = -np.sin(strike_theta)
    dx_s = np.cos(strike_theta)
    yy_f, xx_f = np.indices((H_GRID, W_GRID), dtype=np.float32)
    for step in (-8.0, -4.0, 4.0, 8.0):
        ry = np.clip(np.rint(yy_f + step * dy_s).astype(np.int32), 0, H_GRID - 1)
        rx = np.clip(np.rint(xx_f + step * dx_s).astype(np.int32), 0, W_GRID - 1)
        aniso_h += (0.75 if abs(step) <= 4.0 else 0.5) * g_r4[ry, rx]
        del ry, rx
    mm[13] = (aniso_h / 3.5).astype(np.float16)
    del temp_grid, geoth_grid, g_r4, g_r15, aniso_h, yy_f, xx_f, dy_s, dx_s
    gc.collect()

    # 3. INGENIOUS shallow 2-meter temperature probe field surveys (F2mDAB)
    dab_pos = np.zeros((H_GRID, W_GRID), np.float32)
    dab_cov = np.zeros((H_GRID, W_GRID), np.float32)
    n_probes_in = 0
    with zipfile.ZipFile(ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip") as zf:
        dbf_bytes = zf.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    for rec in _parse_dbf_records(dbf_bytes):
        try:
            ue = float(rec["UTM_E"])
            un = float(rec["UTM_N"])
            dab = float(rec["F2mDAB"])
        except ValueError:
            continue
        r, c = _utm_to_rc(ue, un)
        if 0 <= r < H_GRID and 0 <= c < W_GRID and fp[r, c]:
            n_probes_in += 1
            dab_cov[r, c] += 1.0
            if np.isfinite(dab) and dab > 0.25:
                dab_pos[r, c] = max(dab_pos[r, c], min(dab, 35.0))
            if np.isfinite(dab) and dab >= 1.8:
                anchor_pts.append((r, c, len(anchor_pts) + 1))
    del dbf_bytes
    mm[14] = np.log1p(gaussian_filter(dab_pos, sigma=4.0) * 12.0).astype(np.float16)
    mm[15] = np.log1p(gaussian_filter(dab_pos, sigma=14.0) * 30.0).astype(np.float16)
    mm[16] = np.clip(gaussian_filter(dab_cov, sigma=10.0) * 8.0, 0.0, 10.0).astype(np.float16)
    del dab_pos, dab_cov

    # 4. Paleo-geothermal sinters / travertines / silicified fault breccias (Paleo_geothermal_final.csv)
    sinter_grid = np.zeros((H_GRID, W_GRID), np.float32)
    n_paleo_in = 0
    with zipfile.ZipFile(ext_dir / "paleo_geothermal_regional.zip") as zf:
        ptxt = zf.read("Paleo_geothermal_final.csv").decode("utf-8-sig", errors="replace")
    p_lons, p_lats, p_w = [], [], []
    for rec in csv.DictReader(io.StringIO(ptxt)):
        try:
            p_lons.append(float(rec["Long_deg_NAD83"]))
            p_lats.append(float(rec["Lat_deg_NAD83"]))
            dtype_s = (rec.get("Deposit_type") or "").lower()
            p_w.append(1.6 if "sinter" in dtype_s else 1.15)
        except ValueError:
            continue
    p_ues, p_uns = rio_transform("EPSG:4269", "EPSG:32611", p_lons, p_lats)
    for ue, un, w_dep in zip(p_ues, p_uns, p_w):
        r, c = _utm_to_rc(float(ue), float(un))
        if 0 <= r < H_GRID and 0 <= c < W_GRID and fp[r, c]:
            n_paleo_in += 1
            sinter_grid[r, c] += w_dep
            anchor_pts.append((r, c, len(anchor_pts) + 1))
    mm[17] = np.log1p(gaussian_filter(sinter_grid, sigma=4.0) * 20.0).astype(np.float16)
    mm[18] = np.log1p(gaussian_filter(sinter_grid, sigma=16.0) * 60.0).astype(np.float16)
    del sinter_grid

    # 5. Leak-free Quaternary volcanic vents (dist_known_fault_px strictly dropped!)
    vent_grid = np.zeros((H_GRID, W_GRID), np.float32)
    n_vents_in = 0
    with (ext_dir / "gdr_volcanic_vents_in_footprint.csv").open() as f:
        for rec in csv.DictReader(f):
            rec.pop("dist_known_fault_px", None)
            assert "dist_known_fault_px" not in rec
            r = int(float(rec["row"]))
            c = int(float(rec["col"]))
            if 0 <= r < H_GRID and 0 <= c < W_GRID and fp[r, c]:
                n_vents_in += 1
                vent_grid[r, c] += 1.0
                anchor_pts.append((r, c, len(anchor_pts) + 1))
    mm[19] = np.log1p(gaussian_filter(vent_grid, sigma=16.0) * 80.0).astype(np.float16)
    del vent_grid

    # 6. Pure-physics (ZERO-CATALOGUE) crustal fracture conduit current between hydrothermal anchors!
    # Unsupervised multi-physics weakness proxy from MPC phase congruency + gravity/mag tilt
    nms_all = names_meta["names"]
    weak0 = np.zeros((H_GRID, W_GRID), np.float32)
    for bnm in ("mpc_det_elev_pc", "mpc_iso_grav_anom_pc", "mpc_rtp_pc", "mpc_depth_to_base_surf_pc"):
        if bnm in nms_all:
            arr = np.nan_to_num(np.asarray(stack_mm[nms_all.index(bnm)], dtype=np.float32), nan=0.0)
            p5, p99 = np.percentile(arr[fp], [5.0, 99.0])
            weak0 += 0.25 * np.clip((arr - p5) / max(float(p99 - p5), 1e-6), 0.0, 1.0)
            del arr
    slow0 = 1.0 - 0.82 * np.clip(weak0, 0.0, 1.0)
    del weak0
    G_h, H2, W2, _ = _build_graph_2x(slow0, strike_theta, fp, aniso=2.0)
    del slow0

    # Cluster hydrothermal points into 2x grid anchor cells
    hyd_nodes = sorted({(r // 2) * W2 + (c // 2) for r, c, _ in anchor_pts})
    hyd_arr = np.asarray(hyd_nodes, dtype=np.int32)
    np.save(feat_dir / "gfv_hydro_nodes2x.npy", hyd_arr)
    j_hyd = np.zeros((H2, W2), np.float32)
    rng_h = np.random.default_rng(782026)
    for _m in range(6):
        perm = rng_h.permutation(hyd_arr.size)
        red = hyd_arr[perm[0::2]]
        blu = hyd_arr[perm[1::2]]
        if red.size == 0 or blu.size == 0:
            continue
        d_r, p_r, _ = dijkstra(G_h, directed=False, indices=red, return_predecessors=True, min_only=True, limit=55.0)
        d_b, p_b, _ = dijkstra(G_h, directed=False, indices=blu, return_predecessors=True, min_only=True, limit=55.0)
        j_hyd += _trace_paths_from_saddles(d_r, p_r, d_b, p_b, H2, W2, max_saddles=900, max_pair_cost=55.0)
        del d_r, p_r, d_b, p_b
    j_hyd_full = _upsample_2x(gaussian_filter(j_hyd / 6.0, sigma=2.5))
    mm[20] = np.where(fp, np.log1p(j_hyd_full * 4.0), 0.0).astype(np.float16)
    mm.flush()
    del G_h, j_hyd, j_hyd_full, mm
    gc.collect()

    meta = {
        "channels": GFV_EXT_NAMES,
        "n_channels": len(GFV_EXT_NAMES),
        "n_hot_geotherm_anchors": n_geoth_hot,
        "n_2m_probes_in_footprint": n_probes_in,
        "n_paleo_sinters_in_footprint": n_paleo_in,
        "n_volc_vents_in_footprint": n_vents_in,
        "n_unique_hydro_nodes_2x": int(hyd_arr.size),
        "dist_known_fault_px_accessed": False,
        "seconds": round(time.time() - t0, 2),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return np.lib.format.open_memmap(out_path, mode="r"), meta


def _extract_tips_and_components(vis: np.ndarray):
    """Extract connected components, lengths, endpoints, and endpoint unit tangents from ``vis`` only."""
    comp_lbl, n_comp = label(vis, structure=np.ones((3, 3), dtype=np.int32))
    sizes = np.bincount(comp_lbl.ravel())
    sizes[0] = 0

    # Endpoints: visible cells with <= 2 8-connected neighbors (plus sampled stride on long closed loops)
    nb_cnt = convolve(vis.astype(np.int16), np.ones((3, 3), dtype=np.int16), mode="constant", cval=0) - 1
    tips_mask = vis & (nb_cnt <= 1)
    # Ensure every component >= 3 px has at least 2 anchor points via bounding extremes
    ys_all, xs_all = np.nonzero(vis)
    cids = comp_lbl[ys_all, xs_all]
    # Fast per-component min-y and max-y pixels
    order_y = np.argsort(ys_all, kind="stable")
    first_idx = np.full(n_comp + 1, -1, dtype=np.int32)
    last_idx = np.full(n_comp + 1, -1, dtype=np.int32)
    for idx in order_y:
        c_i = int(cids[idx])
        if first_idx[c_i] < 0:
            first_idx[c_i] = idx
        last_idx[c_i] = idx
    valid_c = np.flatnonzero(sizes >= 2)
    tips_mask[ys_all[first_idx[valid_c]], xs_all[first_idx[valid_c]]] = True
    tips_mask[ys_all[last_idx[valid_c]], xs_all[last_idx[valid_c]]] = True

    # Local strike vector on visible trace
    sm = gaussian_filter(vis.astype(np.float32), sigma=1.6)
    gy = gaussian_filter(sm, sigma=1.2, order=[1, 0])
    gx = gaussian_filter(sm, sigma=1.2, order=[0, 1])
    Jxx = gaussian_filter(gx * gx, sigma=3.0)
    Jxy = gaussian_filter(gx * gy, sigma=3.0)
    Jyy = gaussian_filter(gy * gy, sigma=3.0)
    ang = 0.5 * np.arctan2(2.0 * Jxy, Jxx - Jyy) + 0.5 * np.pi
    del sm, gx, gy, Jxx, Jxy, Jyy
    return comp_lbl, sizes, tips_mask, np.cos(ang).astype(np.float32), np.sin(ang).astype(np.float32)


def compute_geodesic_network(
    context_vis: np.ndarray,
    weakness_phys: np.ndarray,
    strike_theta: np.ndarray,
    fp: np.ndarray,
    hydro_nodes2x: np.ndarray,
    *,
    n_color_rounds: int = 8,
    seed: int = 42,
) -> np.ndarray:
    """Compute the 12 fold-clean crustal-weakness geodesic channels (float16, shape (12, H, W))."""
    H, W = fp.shape
    vis = np.asarray(context_vis, dtype=bool) & fp
    out = np.zeros((len(GFV_GEO_NAMES), H, W), dtype=np.float16)
    if not vis.any():
        return out

    comp_lbl, sizes, tips_mask, tan_x, tan_y = _extract_tips_and_components(vis)

    # Euclidean references (from context_vis ONLY)
    d_trace, near_idx_tr = distance_transform_edt(~vis, return_indices=True)
    d_trace = d_trace.astype(np.float32)
    host_len = sizes[comp_lbl[near_idx_tr[0], near_idx_tr[1]]].astype(np.float32)
    del near_idx_tr

    d_tip, near_idx_tp = distance_transform_edt(~tips_mask, return_indices=True)
    d_tip = d_tip.astype(np.float32)
    ny_t, nx_t = near_idx_tp[0], near_idx_tp[1]
    del near_idx_tp

    # Cosine alignment between vector (x - nearest_tip) and local trace strike at nearest_tip
    yy, xx = np.indices((H, W), dtype=np.float32)
    vy = yy - ny_t.astype(np.float32)
    vx = xx - nx_t.astype(np.float32)
    vn = np.hypot(vx, vy) + 1e-4
    tx_n = tan_x[ny_t, nx_t]
    ty_n = tan_y[ny_t, nx_t]
    along_cos = np.abs(vx * tx_n + vy * ty_n) / vn
    del yy, xx, vx, vy, vn, tx_n, ty_n, ny_t, nx_t, tan_x, tan_y

    # Build 2x anisotropic crustal resistance graph from pure physical weakness
    w_clip = np.clip(np.asarray(weakness_phys, dtype=np.float32), 0.0, 1.0)
    slowness = (1.0 - 0.86 * w_clip) ** 1.35
    G_sp, H2, W2, fp2 = _build_graph_2x(slowness, strike_theta, fp, aniso=2.2)
    del slowness, w_clip

    # Map visible trace nodes and tip nodes to 2x graph (multiply by 2.0 to return to 100m px units!)
    vis2 = vis.reshape(H2, 2, W2, 2).any(axis=(1, 3)) & fp2
    tr_nodes = np.flatnonzero(vis2.ravel()).astype(np.int32)
    d_tr_geo2 = dijkstra(G_sp, directed=False, indices=tr_nodes, min_only=True, limit=95.0)
    T1_trace = _upsample_2x(np.minimum(d_tr_geo2.reshape(H2, W2), 95.0) * 2.0, (H, W))
    del d_tr_geo2, tr_nodes, vis2

    ty_f, tx_f = np.nonzero(tips_mask)
    tip_cids = comp_lbl[ty_f, tx_f]
    tip_nodes2 = (ty_f // 2) * W2 + (tx_f // 2)
    # Unique (node2, comp_id)
    node_to_cid: dict[int, int] = {}
    for nd, cid in zip(tip_nodes2.tolist(), tip_cids.tolist()):
        node_to_cid.setdefault(nd, cid)
    all_tip_nodes = np.asarray(sorted(node_to_cid.keys()), dtype=np.int32)
    all_tip_cids = np.asarray([node_to_cid[n] for n in all_tip_nodes], dtype=np.int32)
    uniq_cids = np.unique(all_tip_cids)

    d_tp_geo2 = dijkstra(G_sp, directed=False, indices=all_tip_nodes, min_only=True, limit=110.0)
    T1_tip = _upsample_2x(np.minimum(d_tp_geo2.reshape(H2, W2), 110.0) * 2.0, (H, W))
    del d_tp_geo2

    # Alon-Yuster-Zwick color-coded two-component geodesic sum & shortest-path fracture current
    rng = np.random.default_rng(seed)
    tpair_min = np.full((H2, W2), 160.0, dtype=np.float32)
    j_acc = np.zeros((H2, W2), dtype=np.float32)

    for _m in range(n_color_rounds):
        comp_red = set(uniq_cids[rng.random(uniq_cids.size) < 0.5].tolist())
        red_mask = np.asarray([c in comp_red for c in all_tip_cids], dtype=bool)
        red_nodes = all_tip_nodes[red_mask]
        blu_nodes = all_tip_nodes[~red_mask]
        if red_nodes.size == 0 or blu_nodes.size == 0:
            continue
        d_r, p_r, _ = dijkstra(G_sp, directed=False, indices=red_nodes, return_predecessors=True, min_only=True, limit=70.0)
        d_b, p_b, _ = dijkstra(G_sp, directed=False, indices=blu_nodes, return_predecessors=True, min_only=True, limit=70.0)
        d_sum2 = (d_r + d_b).reshape(H2, W2) * 2.0
        np.minimum(tpair_min, np.where(np.isfinite(d_sum2), d_sum2, 160.0), out=tpair_min)
        j_acc += _trace_paths_from_saddles(d_r, p_r, d_b, p_b, H2, W2, max_saddles=1500, max_pair_cost=52.0)
        del d_r, p_r, d_b, p_b, d_sum2

    # Dedicated fault-tip <-> blind hydrothermal upflow geodesic bridges!
    d_rt, p_rt, _ = dijkstra(G_sp, directed=False, indices=all_tip_nodes, return_predecessors=True, min_only=True, limit=75.0)
    d_bh, p_bh, _ = dijkstra(G_sp, directed=False, indices=hydro_nodes2x, return_predecessors=True, min_only=True, limit=75.0)
    j_vent2 = _trace_paths_from_saddles(d_rt, p_rt, d_bh, p_bh, H2, W2, max_saddles=1400, max_pair_cost=65.0)
    del d_rt, p_rt, d_bh, p_bh, G_sp

    tpair_full = _upsample_2x(tpair_min, (H, W))
    tpair_loc_min = minimum_filter(tpair_full, size=15, mode="nearest")
    fermat_ridge = np.exp(-np.maximum(tpair_full - tpair_loc_min, 0.0) / 3.5) * np.exp(-tpair_full / 75.0)

    j_mean = j_acc / max(1, n_color_rounds)
    j_narrow = _upsample_2x(gaussian_filter(j_mean, sigma=0.9), (H, W))
    j_wide = _upsample_2x(gaussian_filter(j_mean, sigma=3.5), (H, W))
    j_vent = _upsample_2x(gaussian_filter(j_vent2, sigma=2.2), (H, W))
    del tpair_min, j_acc, j_mean, j_vent2, tpair_loc_min, comp_lbl, sizes, tips_mask

    out[0] = np.where(fp, np.log1p(d_trace), 0.0).astype(np.float16)
    out[1] = np.where(fp, np.log1p(T1_trace), 0.0).astype(np.float16)
    out[2] = np.where(fp, T1_trace / (d_trace + 2.0), 0.0).astype(np.float16)
    out[3] = np.where(fp, np.log1p(T1_tip), 0.0).astype(np.float16)
    out[4] = np.where(fp, T1_tip / (d_tip + 2.0), 0.0).astype(np.float16)
    out[5] = np.where(fp, np.log1p(tpair_full), 0.0).astype(np.float16)
    out[6] = np.where(fp, fermat_ridge, 0.0).astype(np.float16)
    out[7] = np.where(fp, np.log1p(j_narrow * 3.0), 0.0).astype(np.float16)
    out[8] = np.where(fp, np.log1p(j_wide * 6.0), 0.0).astype(np.float16)
    out[9] = np.where(fp, np.log1p(j_vent * 4.0), 0.0).astype(np.float16)
    out[10] = np.where(fp, along_cos, 0.0).astype(np.float16)
    out[11] = np.where(fp, np.log1p(host_len), 0.0).astype(np.float16)
    del d_trace, d_tip, T1_trace, T1_tip, tpair_full, fermat_ridge, j_narrow, j_wide, j_vent, along_cos, host_len
    gc.collect()
    return out
