"""Lane H78-MGHD: Multi-scale crustal flank-warp, sub-grid 3DEP 1m/10m/Chi
tectonic geomorphology, GeoDAWN radiometric alteration & DOE GDR-1391 geothermal
upflow fusion, spatial-block out-of-fold dual-target (trace + 300 m kernel credit)
learning, and exact Minoux lazy-heap 300 m submodular kernel cover.

Strict leakage safeguards:
  - Uses ONLY ``visible`` catalogue fault pixels for regional strike orientation
    (sigma = 4 km vs 150 m) and for training labels/targets on holdout folds.
  - Explicitly forbids reading ``sgmc_faults_100m.tif``, ``derived_sgmc_faults_100m_u8.tif``,
    ``gdr_qfaults_traces.csv``, or any ``dist_known_fault_px`` column.
  - Replaces raw long-wavelength valley GPS coordinate proxies with 2.5 km high-pass
    translation-equivariant residuals and predicts out-of-fold across spatial blocks.
"""
from __future__ import annotations

import csv
import heapq
import io
import json
from pathlib import Path
import struct
import time
import zipfile

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy import ndimage as ndi
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from .data import BAND_NAMES, PROC, ROOT, _ensure_proc_dir, load_stack, sha256
from .emit import flank_mask
from .strike import strike_field

import sys
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))
from gems57.metric import ALPHA, OFF_DX, OFF_DY, OFF_K, RADIUS_PX  # noqa: E402

FORBIDDEN_EXTERNAL_FILES = frozenset({
    "sgmc_faults_100m.tif",
    "derived_sgmc_faults_100m_u8.tif",
    "gdr_qfaults_traces.csv",
})

REQUIRED_EXTERNAL_IDS = (
    "ext_lidar_scarp_features_u8",
    "ext_geodawn_rad_u8",
    "ext_geodawn_extensions_u8",
    "ext_gdr_wellspring_in_footprint",
    "ext_gdr_volcanic_vents_in_footprint",
    "ext_topo_10m_derived_100m_u8",
    "ext_dem10_chi_100m_i16",
    "ext_2m_temperature_probe_ingenious",
    "ext_paleo_geothermal_regional",
)


def verify_external_inputs() -> dict[str, dict]:
    """Verify 64-hex SHA-256 of every external input used by H78-MGHD."""
    manifest = json.loads((ROOT / "registry" / "data_manifest_gems73.json").read_text())
    by_id = {}
    by_dest = {}
    for entry in manifest["files"]:
        by_id.setdefault(entry["id"], entry)
        by_dest.setdefault(entry["dest"], entry)

    out: dict[str, dict] = {}
    wanted = list(REQUIRED_EXTERNAL_IDS)
    for eid in wanted:
        e = by_id[eid]
        fname = Path(e["dest"]).name
        if fname in FORBIDDEN_EXTERNAL_FILES:
            raise RuntimeError(f"Forbidden leakage source referenced: {fname}")
        p = ROOT / "data" / e["dest"]
        got = sha256(p)
        if got != e["sha256"]:
            raise RuntimeError(f"External SHA-256 mismatch for {eid}: {got} != {e['sha256']}")
        out[eid] = dict(path=str(p.relative_to(ROOT)), sha256=got, bytes=p.stat().st_size)

    # Verify dem10_chi_100m_u8.tif as well
    chi_u8 = by_dest["external/dem10_chi_100m_u8.tif"]
    p_u8 = ROOT / "data" / chi_u8["dest"]
    got_u8 = sha256(p_u8)
    if got_u8 != chi_u8["sha256"]:
        raise RuntimeError(f"External SHA-256 mismatch for chi_u8: {got_u8} != {chi_u8['sha256']}")
    out["ext_dem10_chi_100m_u8"] = dict(path=str(p_u8.relative_to(ROOT)), sha256=got_u8, bytes=p_u8.stat().st_size)
    return out


def _read_csv_safe(path: Path, forbidden_substr: str = "fault") -> list[dict[str, str]]:
    """Read CSV rows after stripping any column whose name contains ``forbidden_substr``."""
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        safe_cols = [c for c in reader.fieldnames if forbidden_substr not in c.lower()]
        return [{c: row[c] for c in safe_cols} for row in reader]


def _parse_2m_probes_utm(zip_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract (utm_x, utm_y, temp_anomaly_weight) from INGENIOUS 2m temperature probe DBF."""
    with zipfile.ZipFile(zip_path) as z:
        dbf = z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    num_rec = struct.unpack("<I", dbf[4:8])[0]
    hdr_len, rec_len = struct.unpack("<HH", dbf[8:12])
    fields = []
    pos = 32
    offset = 1
    while pos < hdr_len - 1 and dbf[pos] != 0x0D:
        fname = dbf[pos:pos + 11].split(b"\x00", 1)[0].decode("ascii", "replace")
        flen = dbf[pos + 16]
        if "fault" not in fname.lower():
            fields.append((fname, offset, flen))
        offset += flen
        pos += 32
    fmap = {n: (off, ln) for n, off, ln in fields}
    xs, ys, ws = [], [], []
    base = hdr_len
    for i in range(num_rec):
        rec = dbf[base + i * rec_len: base + (i + 1) * rec_len]
        if not rec or rec[0:1] == b"*":
            continue
        try:
            ux = float(rec[fmap["UTM_E"][0]: fmap["UTM_E"][0] + fmap["UTM_E"][1]].decode("ascii", "replace").strip())
            uy = float(rec[fmap["UTM_N"][0]: fmap["UTM_N"][0] + fmap["UTM_N"][1]].decode("ascii", "replace").strip())
        except (KeyError, ValueError):
            continue
        t2m = 0.0
        dab = 0.0
        for key, target in (("T2m", "t2m"), ("F2mDAB", "dab")):
            if key in fmap:
                raw = rec[fmap[key][0]: fmap[key][0] + fmap[key][1]].decode("ascii", "replace").strip()
                try:
                    val = float(raw)
                    if np.isfinite(val) and -50.0 < val < 150.0:
                        if target == "t2m":
                            t2m = val
                        else:
                            dab = val
                except ValueError:
                    pass
        w = 1.0 + max(0.0, dab) * 0.5 + max(0.0, t2m - 20.0) * 0.25
        xs.append(ux)
        ys.append(uy)
        ws.append(w)
    return np.asarray(xs, np.float64), np.asarray(ys, np.float64), np.asarray(ws, np.float32)


def build_geothermal_fields(shape: tuple[int, int], transform) -> dict[str, np.ndarray]:
    """Rasterize multi-scale hydrothermal vent, hot-spring, sinter, and 2m-probe density fields."""
    H, W = shape
    thermal_imp = np.zeros((H, W), np.float32)
    sinter_imp = np.zeros((H, W), np.float32)
    probe_imp = np.zeros((H, W), np.float32)

    # 1. GDR-1391 Wells & Springs (dist_known_fault_px stripped by _read_csv_safe)
    ws_rows = _read_csv_safe(ROOT / "data/external/gdr_wellspring_in_footprint.csv", forbidden_substr="fault")
    for row in ws_rows:
        try:
            r = int(round(float(row["row"])))
            c = int(round(float(row["col"])))
        except (KeyError, ValueError):
            continue
        if not (0 <= r < H and 0 <= c < W):
            continue
        temps = []
        for tk in ("temp_c", "geothermquartz_c", "geothermchalc_c"):
            try:
                v = float(row.get(tk, "") or "nan")
                if np.isfinite(v) and 0.0 < v < 400.0:
                    temps.append(v)
            except ValueError:
                pass
        tmax = max(temps) if temps else 20.0
        if tmax >= 30.0 or "warm" in (row.get("thermalclass") or "").lower() or "hot" in (row.get("thermalclass") or "").lower():
            w = float(np.log1p(max(tmax - 20.0, 1.0)))
            thermal_imp[r, c] += w

    # 2. GDR-1391 Paleo-geothermal sinter / travertine / tufa vents (NAD83 lon/lat -> EPSG:32611)
    with zipfile.ZipFile(ROOT / "data/external/paleo_geothermal_regional.zip") as z:
        txt = z.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(txt))
    lons, lats, weights = [], [], []
    for row in reader:
        try:
            lon = float(row["Long_deg_NAD83"])
            lat = float(row["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        dtype = (row.get("Deposit_type") or "").lower()
        w = 2.0 if ("sinter" in dtype or "travertine" in dtype) else 1.2
        lons.append(lon)
        lats.append(lat)
        weights.append(w)
    if lons:
        ux, uy = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
        cols = np.rint((np.asarray(ux) - transform.c) / transform.a).astype(int)
        rows_i = np.rint((np.asarray(uy) - transform.f) / transform.e).astype(int)
        for r, c, w in zip(rows_i, cols, weights):
            if 0 <= r < H and 0 <= c < W:
                sinter_imp[r, c] += float(w)

    # 3. GDR-1391 Quaternary volcanic vents (dist_known_fault_px stripped by _read_csv_safe)
    vv_rows = _read_csv_safe(ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv", forbidden_substr="fault")
    for row in vv_rows:
        try:
            r = int(round(float(row["row"])))
            c = int(round(float(row["col"])))
        except (KeyError, ValueError):
            continue
        if 0 <= r < H and 0 <= c < W:
            sinter_imp[r, c] += 1.0

    # 4. GDR-1391 2-meter shallow temperature probes
    px, py, pw = _parse_2m_probes_utm(ROOT / "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip")
    if px.size:
        cols = np.rint((px - transform.c) / transform.a).astype(int)
        rows_i = np.rint((py - transform.f) / transform.e).astype(int)
        ok = (rows_i >= 0) & (rows_i < H) & (cols >= 0) & (cols < W)
        np.add.at(probe_imp, (rows_i[ok], cols[ok]), pw[ok])

    joint_vent = thermal_imp + 1.5 * sinter_imp
    return {
        "gdr_vent_s6": np.log1p(ndi.gaussian_filter(joint_vent, sigma=6.0) * 100.0).astype(np.float32),
        "gdr_vent_s18": np.log1p(ndi.gaussian_filter(joint_vent, sigma=18.0) * 400.0).astype(np.float32),
        "gdr_vent_s40": np.log1p(ndi.gaussian_filter(joint_vent, sigma=40.0) * 1000.0).astype(np.float32),
        "gdr_probe2m_s12": np.log1p(ndi.gaussian_filter(probe_imp, sigma=12.0) * 100.0).astype(np.float32),
    }


def mghd_feature_names() -> list[str]:
    names = [
        # Core physical regime + translation-equivariant 2.5 km high-pass anomalies (16)
        "det_elev_slope", "depth_to_base_surf", "cond_surf", "tc_totalcount",
        "tmi_hg", "tmi_vg", "iso_grav_anom_slope", "iso_grav_anom_hg", "iso_grav_anom_vg",
        "geod_shearrate", "geod_dilaterate", "geod_2ndinv",
        "det_elev_hp25", "rtp_hp25", "iso_grav_hp25", "depth_base_hp25",
    ]
    # Narrow steered + isotropic lineaments (6 bands x 2 scales x 4 = 48)
    for b in ("det_elev", "rtp", "iso_grav_anom", "depth_to_base_surf", "cond_surf", "tc_totalcount"):
        for s in (1.5, 3.0):
            names += [f"{b}_s{s}_l1", f"{b}_s{s}_Hnn", f"{b}_s{s}_abs_gn", f"{b}_s{s}_aniso_gn"]
    # Broad crustal flank-warp + subsurface cross-layer corroboration (10)
    for b in ("det_elev", "depth_to_base_surf", "iso_grav_anom", "rtp"):
        for s in (6.0, 12.0):
            names += [f"{b}_warp_abs_gn_s{int(s)}", f"{b}_warp_Hnn_s{int(s)}"]
    names += ["warp_s6_elev_vs_basement_concord", "warp_s6_basement_x_grav_step"]
    # USGS 3DEP 1 m LiDAR scarp anatomy & verified strike alignment (16)
    names += [
        "lidar_valid",
        "lidar_ex_max", "lidar_ex_mean", "lidar_step_max",
        "lidar_lapneg_max", "lidar_lappos_max", "lidar_cross_max",
        "lidar_relief", "lidar_coh100",
        "lidar_face_max", "lidar_face_asym",
        "lidar_step_prominence", "lidar_ex_prominence",
        "lidar_strike_align",
        "lidar_step_env_s2", "lidar_step_env_s5",
    ]
    # USGS 3DEP 10 m seamless DEM + river Chi knickpoints + Lahontan shoreline discriminator (15)
    names += [
        "dem10_slope_p90", "dem10_slope_max", "dem10_steep_frac", "dem10_slope_std",
        "dem10_relief_local", "dem10_curv_prof_absmax", "dem10_aspect_coherence", "dem10_hs_lineament",
        "dem10_curv_prominence", "dem10_slope_env_s2", "dem10_along_vs_across_elev",
        "chi_step_s2p5", "chi_step_s6", "chi_ksn_s2p5", "chi_knick_s3",
    ]
    # USGS GeoDAWN radiometric alteration + upward-continued magnetics + GDR-1391 thermal conduits (10)
    names += [
        "rad_K_hp15", "rad_K_minus_ThK", "rad_ThK", "rad_UK", "rad_UTh", "rad_TMI_up150_grad3",
        "gdr_vent_s6", "gdr_vent_s18", "gdr_vent_s40", "gdr_probe2m_s12",
    ]
    return names


def build_mghd_matrix(tag: str, footprint: np.ndarray, visible: np.ndarray,
                      force: bool = False) -> tuple[Path, dict]:
    """Stream all 123 pure-physics features directly into a float32 memmap (<750 MB RAM)."""
    _ensure_proc_dir()
    ext_hashes = verify_external_inputs()
    names = mghd_feature_names()
    out = PROC / f"mghd_feats_{tag}.npy"
    meta_p = PROC / f"mghd_feats_{tag}.json"
    if out.exists() and meta_p.exists() and not force:
        saved = json.loads(meta_p.read_text())
        if saved.get("names") == names and saved.get("external_sha256") == {k: v["sha256"] for k, v in ext_hashes.items()}:
            return out, saved

    t0 = time.time()
    stack = load_stack()
    ys, xs = np.nonzero(footprint)
    n = int(ys.size)
    phi, coh, _ = strike_field(visible)
    cph = np.cos(phi[ys, xs]).astype(np.float32)
    sph = np.sin(phi[ys, xs]).astype(np.float32)

    tmp = out.with_suffix(".npy.partial")
    mm = np.lib.format.open_memmap(tmp, mode="w+", dtype=np.float32, shape=(n, len(names)))
    col = 0

    def put(values_1d: np.ndarray, expected_name: str):
        nonlocal col
        assert names[col] == expected_name, f"Column mismatch: {names[col]} != {expected_name}"
        mm[:, col] = np.asarray(values_1d, dtype=np.float32)
        col += 1

    # 1. Core regime + 2.5 km high-pass anomalies (16 cols)
    for bname in ("det_elev_slope", "depth_to_base_surf", "cond_surf", "tc_totalcount",
                  "tmi_hg", "tmi_vg", "iso_grav_anom_slope", "iso_grav_anom_hg", "iso_grav_anom_vg",
                  "geod_shearrate", "geod_dilaterate", "geod_2ndinv"):
        put(stack[BAND_NAMES.index(bname)][ys, xs], bname)

    for bname, outname in (("det_elev", "det_elev_hp25"),
                           ("rtp", "rtp_hp25"),
                           ("iso_grav_anom", "iso_grav_hp25"),
                           ("depth_to_base_surf", "depth_base_hp25")):
        a = np.ascontiguousarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        hp = a - ndi.gaussian_filter(a, sigma=25.0)
        put(hp[ys, xs], outname)
        del a, hp

    # 2. Narrow steered & isotropic lineaments (48 cols)
    for bname in ("det_elev", "rtp", "iso_grav_anom", "depth_to_base_surf", "cond_surf", "tc_totalcount"):
        a = np.ascontiguousarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        for s in (1.5, 3.0):
            gx = ndi.gaussian_filter(a, s, order=(0, 1))
            gy = ndi.gaussian_filter(a, s, order=(1, 0))
            gxx = ndi.gaussian_filter(a, s, order=(0, 2))
            gyy = ndi.gaussian_filter(a, s, order=(2, 0))
            gxy = ndi.gaussian_filter(a, s, order=(1, 1))
            s1, s2 = np.float32(s), np.float32(s * s)
            Gx, Gy = gx[ys, xs] * s1, gy[ys, xs] * s1
            Gxx, Gyy, Gxy = gxx[ys, xs] * s2, gyy[ys, xs] * s2, gxy[ys, xs] * s2
            del gx, gy, gxx, gyy, gxy
            half_tr = 0.5 * (Gxx + Gyy)
            disc = np.sqrt((0.5 * (Gxx - Gyy)) ** 2 + Gxy ** 2)
            hnn = cph * cph * Gxx + 2.0 * sph * cph * Gxy + sph * sph * Gyy
            gn = np.abs(cph * Gx + sph * Gy)
            gt = np.abs(-sph * Gx + cph * Gy)
            put(half_tr + disc, f"{bname}_s{s}_l1")
            put(hnn, f"{bname}_s{s}_Hnn")
            put(gn, f"{bname}_s{s}_abs_gn")
            put(gn / (gt + np.float32(1e-3) + np.float32(0.1) * np.median(gn)), f"{bname}_s{s}_aniso_gn")
            del Gx, Gy, Gxx, Gyy, Gxy, half_tr, disc, hnn, gn, gt
        del a
    mm.flush()

    # 3. Broad crustal flank-warp + signed cross-layer corroboration (18 cols)
    saved_gn6: dict[str, np.ndarray] = {}
    for bname in ("det_elev", "depth_to_base_surf", "iso_grav_anom", "rtp"):
        a = np.ascontiguousarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
        for s in (6.0, 12.0):
            gx = ndi.gaussian_filter(a, s, order=(0, 1))
            gy = ndi.gaussian_filter(a, s, order=(1, 0))
            gxx = ndi.gaussian_filter(a, s, order=(0, 2))
            gyy = ndi.gaussian_filter(a, s, order=(2, 0))
            gxy = ndi.gaussian_filter(a, s, order=(1, 1))
            s1, s2 = np.float32(s), np.float32(s * s)
            Gx, Gy = gx[ys, xs] * s1, gy[ys, xs] * s1
            Gxx, Gyy, Gxy = gxx[ys, xs] * s2, gyy[ys, xs] * s2, gxy[ys, xs] * s2
            del gx, gy, gxx, gyy, gxy
            gn_signed = cph * Gx + sph * Gy
            hnn = cph * cph * Gxx + 2.0 * sph * cph * Gxy + sph * sph * Gyy
            if s == 6.0 and bname in ("det_elev", "depth_to_base_surf", "iso_grav_anom"):
                saved_gn6[bname] = gn_signed
            put(np.abs(gn_signed), f"{bname}_warp_abs_gn_s{int(s)}")
            put(hnn, f"{bname}_warp_Hnn_s{int(s)}")
            del Gx, Gy, Gxx, Gyy, Gxy, hnn
        del a
    # Hanging-wall subsidence increases depth_to_base_surf across strike while lowering det_elev & iso_grav_anom
    put(-np.sign(saved_gn6["depth_to_base_surf"]) * saved_gn6["det_elev"], "warp_s6_elev_vs_basement_concord")
    put(np.abs(saved_gn6["depth_to_base_surf"]) * np.abs(saved_gn6["iso_grav_anom"]), "warp_s6_basement_x_grav_step")
    saved_gn6.clear()
    mm.flush()

    # 4. Sub-grid USGS 3DEP 1 m LiDAR scarp features (16 cols; NaN where valid == 0)
    with rasterio.open(ROOT / "data/external/lidar_scarp_features_u8.tif") as ds:
        lid = ds.read().astype(np.float32)
    val_mask = lid[11] > 0
    put(val_mask[ys, xs].astype(np.float32), "lidar_valid")
    miss = ~val_mask[ys, xs]

    def masked_1d(arr2d: np.ndarray) -> np.ndarray:
        v = arr2d[ys, xs].astype(np.float32, copy=True)
        v[miss] = np.nan
        return v

    for idx_b, lname in ((0, "lidar_ex_max"), (1, "lidar_ex_mean"), (2, "lidar_step_max"),
                         (3, "lidar_lapneg_max"), (4, "lidar_lappos_max"), (7, "lidar_cross_max"),
                         (8, "lidar_relief"), (9, "lidar_coh100")):
        put(masked_1d(lid[idx_b]), lname)

    face_max = np.maximum(lid[5], lid[6])
    face_asym = np.abs(lid[5] - lid[6])
    put(masked_1d(face_max), "lidar_face_max")
    put(masked_1d(face_asym), "lidar_face_asym")
    put(masked_1d(lid[2] / (lid[8] + np.float32(8.0))), "lidar_step_prominence")
    put(masked_1d(lid[0] / (lid[8] + np.float32(8.0))), "lidar_ex_prominence")

    # Verified tangent-to-normal alignment: strike band (pi * u8 / 256) is tangent = phi + pi/2
    theta_lid = lid[10][ys, xs] * np.float32(np.pi / 256.0)
    align_lid = (lid[9][ys, xs] / np.float32(255.0)) * (-np.cos(np.float32(2.0) * (theta_lid - phi[ys, xs].astype(np.float32))))
    align_lid[miss] = np.nan
    put(align_lid, "lidar_strike_align")

    # Smooth normalized step corridor (ratio of smoothed numerator to smoothed validity weight)
    w_val = ndi.gaussian_filter(val_mask.astype(np.float32), sigma=2.0) + np.float32(1e-4)
    step_s2 = ndi.gaussian_filter(lid[2] * val_mask, sigma=2.0) / w_val
    step_s2[~val_mask & (w_val < 0.05)] = np.nan
    w_val5 = ndi.gaussian_filter(val_mask.astype(np.float32), sigma=5.0) + np.float32(1e-4)
    step_s5 = ndi.gaussian_filter(lid[2] * val_mask, sigma=5.0) / w_val5
    step_s5[w_val5 < 0.05] = np.nan
    put(step_s2[ys, xs], "lidar_step_env_s2")
    put(step_s5[ys, xs], "lidar_step_env_s5")
    del lid, val_mask, face_max, face_asym, theta_lid, align_lid, step_s2, step_s5, w_val, w_val5
    mm.flush()

    # 5. Seamless USGS 3DEP 10 m DEM + river Chi knickpoints (15 cols)
    with rasterio.open(ROOT / "data/external/topo_10m_derived_100m_u8.tif") as ds:
        t10 = ds.read().astype(np.float32)
    for idx_b, tname in ((0, "dem10_slope_p90"), (1, "dem10_slope_max"), (2, "dem10_steep_frac"),
                         (3, "dem10_slope_std"), (4, "dem10_relief_local"), (5, "dem10_curv_prof_absmax"),
                         (6, "dem10_aspect_coherence"), (7, "dem10_hs_lineament")):
        put(t10[idx_b][ys, xs], tname)
    put((t10[5] / (t10[4] + np.float32(8.0)))[ys, xs], "dem10_curv_prominence")
    put(ndi.gaussian_filter(t10[1], sigma=2.0)[ys, xs], "dem10_slope_env_s2")
    gx10 = ndi.gaussian_filter(t10[8], sigma=4.0, order=(0, 1))
    gy10 = ndi.gaussian_filter(t10[8], sigma=4.0, order=(1, 0))
    gn10 = np.abs(cph * gx10[ys, xs] + sph * gy10[ys, xs])
    gt10 = np.abs(-sph * gx10[ys, xs] + cph * gy10[ys, xs])
    put(gt10 / (gn10 + np.float32(1.0)), "dem10_along_vs_across_elev")
    del t10, gx10, gy10, gn10, gt10

    with rasterio.open(ROOT / "data/external/dem10_chi_100m_i16.tif") as ds:
        chi_i = ds.read().astype(np.float32)
        ref_transform = ds.transform
    step_pos = np.where(chi_i[0] > -30000.0, np.maximum(chi_i[0], 0.0), 0.0)
    ksn_pos = np.where(chi_i[2] > -30000.0, np.maximum(chi_i[2], 0.0), 0.0)
    put(ndi.gaussian_filter(step_pos, sigma=2.5)[ys, xs], "chi_step_s2p5")
    put(ndi.gaussian_filter(step_pos, sigma=6.0)[ys, xs], "chi_step_s6")
    put(ndi.gaussian_filter(ksn_pos, sigma=2.5)[ys, xs], "chi_ksn_s2p5")
    del chi_i, step_pos, ksn_pos

    with rasterio.open(ROOT / "data/external/dem10_chi_100m_u8.tif") as ds:
        knick = ds.read(2).astype(np.float32)
    put(ndi.gaussian_filter(knick, sigma=3.0)[ys, xs], "chi_knick_s3")
    del knick
    mm.flush()

    # 6. USGS GeoDAWN radiometric alteration + upward-continued magnetics + GDR-1391 thermal conduits (10 cols)
    with rasterio.open(ROOT / "data/external/geodawn_rad_u8.tif") as ds:
        rad = ds.read().astype(np.float32)
    with rasterio.open(ROOT / "data/external/geodawn_extensions_u8.tif") as ds:
        ext = ds.read().astype(np.float32)
    k_hp = rad[0] - ndi.gaussian_filter(rad[0], sigma=15.0)
    put(k_hp[ys, xs], "rad_K_hp15")
    put((rad[0] - ext[0])[ys, xs], "rad_K_minus_ThK")
    put(ext[0][ys, xs], "rad_ThK")
    put(ext[1][ys, xs], "rad_UK")
    put(ext[2][ys, xs], "rad_UTh")
    gux = ndi.gaussian_filter(ext[3], sigma=3.0, order=(0, 1))
    guy = ndi.gaussian_filter(ext[3], sigma=3.0, order=(1, 0))
    put(np.hypot(gux[ys, xs], guy[ys, xs]), "rad_TMI_up150_grad3")
    del rad, ext, k_hp, gux, guy

    geo_fields = build_geothermal_fields(footprint.shape, ref_transform)
    for gname in ("gdr_vent_s6", "gdr_vent_s18", "gdr_vent_s40", "gdr_probe2m_s12"):
        put(geo_fields[gname][ys, xs], gname)
    del geo_fields

    assert col == len(names), f"Wrote {col} cols, expected {len(names)}"
    mm.flush()
    del mm
    tmp.replace(out)

    meta = dict(
        tag=tag,
        n_footprint=n,
        n_features=len(names),
        names=names,
        visible_catalogue_px=int(np.asarray(visible, bool).sum()),
        coherence_median=float(np.median(coh[footprint])),
        external_sha256={k: v["sha256"] for k, v in ext_hashes.items()},
        seconds=round(time.time() - t0, 1),
    )
    meta_p.write_text(json.dumps(meta, indent=2))
    return out, meta


def fit_predict_spatial_oof(
    feats_path: Path,
    footprint: np.ndarray,
    visible: np.ndarray,
    *,
    n_splits: int = 3,
    block_px: int = 250,
    n_neg_total: int = 240_000,
    seed: int = 20,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Cross-fit dual out-of-fold models across spatial checkerboard blocks:
      1) ``p_trace``: out-of-fold fault-trace probability P(x in G_vis | X)
      2) ``q_kern`` : out-of-fold conditional 300 m kernel credit E[max_{g in G_vis} K(x,g) | X]
    """
    t0 = time.time()
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(footprint)
    n_fp = int(ys.size)

    # Spatial checkerboard blocks (25 km x 25 km tiles) so every validation tile is held out spatially
    fold_id = (((ys // block_px) * 5 + (xs // block_px) * 2) % n_splits).astype(np.int8)

    vis = np.asarray(visible, bool) & footprint
    dist_vis = distance_transform_edt(~vis)
    kern_target_fp = np.maximum(0.0, 1.0 - dist_vis[ys, xs] / float(RADIUS_PX)).astype(np.float32)
    is_pos_fp = vis[ys, xs]
    is_neg_ok_fp = dist_vis[ys, xs] > 2.0
    is_near_halo_fp = (~is_pos_fp) & (dist_vis[ys, xs] <= float(RADIUS_PX))

    pos_rows_all = np.flatnonzero(is_pos_fp)
    neg_pool_all = np.flatnonzero(is_neg_ok_fp)
    neg_sample_all = np.sort(rng.choice(neg_pool_all, size=min(n_neg_total, neg_pool_all.size), replace=False))

    # Include halo rows (0 < K < 1) + sampled background rows (K == 0) with exact inverse-sampling weights
    # so squared-error regression estimates true unbiased conditional expectation E[K(d(x, G_vis)) | X]!
    halo_pool = np.flatnonzero(is_near_halo_fp)
    halo_sample = np.sort(rng.choice(halo_pool, size=min(100_000, halo_pool.size), replace=False))
    halo_weight = float(halo_pool.size) / max(float(halo_sample.size), 1.0)
    bg_pool = np.flatnonzero(dist_vis[ys, xs] > float(RADIUS_PX))
    bg_sample = np.sort(rng.choice(bg_pool, size=min(180_000, bg_pool.size), replace=False))
    bg_weight = float(bg_pool.size) / max(float(bg_sample.size), 1.0)

    mm = np.load(feats_path, mmap_mode="r")
    oof_p = np.zeros(n_fp, dtype=np.float32)
    oof_q = np.zeros(n_fp, dtype=np.float32)

    clf_params = dict(
        max_iter=240,
        learning_rate=0.06,
        max_leaf_nodes=63,
        min_samples_leaf=180,
        l2_regularization=2.0,
        max_bins=255,
        early_stopping=False,
    )
    reg_params = dict(
        loss="squared_error",
        max_iter=240,
        learning_rate=0.06,
        max_leaf_nodes=63,
        min_samples_leaf=180,
        l2_regularization=2.0,
        max_bins=255,
        early_stopping=False,
    )

    for k in range(n_splits):
        val_rows = np.flatnonzero(fold_id == k)

        # Trace classifier training set on the (n_splits - 1) spatial folds
        tr_pos = pos_rows_all[fold_id[pos_rows_all] != k]
        tr_neg = neg_sample_all[fold_id[neg_sample_all] != k]
        tr_cls_rows = np.concatenate([tr_pos, tr_neg])
        order_c = np.argsort(tr_cls_rows)
        tr_cls_rows = tr_cls_rows[order_c]
        y_cls = np.concatenate([np.ones(tr_pos.size, np.int8), np.zeros(tr_neg.size, np.int8)])[order_c]
        neg_upweight = float(neg_pool_all[fold_id[neg_pool_all] != k].size) / max(float(tr_neg.size), 1.0)
        w_cls = np.where(y_cls == 1, 1.0, neg_upweight).astype(np.float32)

        clf = HistGradientBoostingClassifier(**clf_params, random_state=seed * 10 + k)
        clf.fit(np.asarray(mm[tr_cls_rows], np.float32), y_cls, sample_weight=w_cls)

        # Kernel-credit regressor training set on the (n_splits - 1) spatial folds
        tr_rp = pos_rows_all[fold_id[pos_rows_all] != k]
        tr_rh = halo_sample[fold_id[halo_sample] != k]
        tr_rb = bg_sample[fold_id[bg_sample] != k]
        tr_reg_rows = np.concatenate([tr_rp, tr_rh, tr_rb])
        w_reg = np.concatenate([
            np.ones(tr_rp.size, np.float32),
            np.full(tr_rh.size, halo_weight, np.float32),
            np.full(tr_rb.size, bg_weight, np.float32),
        ])
        order_r = np.argsort(tr_reg_rows)
        tr_reg_rows = tr_reg_rows[order_r]
        w_reg = w_reg[order_r]
        y_reg = kern_target_fp[tr_reg_rows]

        reg = HistGradientBoostingRegressor(**reg_params, random_state=seed * 10 + 100 + k)
        reg.fit(np.asarray(mm[tr_reg_rows], np.float32), y_reg, sample_weight=w_reg)

        # Predict strictly out-of-fold on held-out spatial blocks
        for lo in range(0, val_rows.size, 400_000):
            sub = val_rows[lo:lo + 400_000]
            Xv = np.asarray(mm[sub], np.float32)
            oof_p[sub] = clf.predict_proba(Xv)[:, 1].astype(np.float32)
            oof_q[sub] = np.clip(reg.predict(Xv), 0.0, 1.0).astype(np.float32)

    p_grid = np.zeros(footprint.shape, dtype=np.float32)
    q_grid = np.zeros(footprint.shape, dtype=np.float32)
    p_grid[footprint] = oof_p
    q_grid[footprint] = oof_q

    info = dict(
        n_splits=n_splits,
        block_px=block_px,
        n_pos_total=int(pos_rows_all.size),
        n_neg_sampled=int(neg_sample_all.size),
        p_mean=float(oof_p.mean()),
        p_max=float(oof_p.max()),
        q_mean=float(oof_q.mean()),
        q_max=float(oof_q.max()),
        fit_predict_seconds=round(time.time() - t0, 1),
    )
    return p_grid, q_grid, info


def fit_mghd_dual(
    feats_path: Path,
    footprint: np.ndarray,
    visible: np.ndarray,
    *,
    n_neg: int = 450_000,
    seed: int = 20,
    model_seed: int = 0,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Fit unweighted dual MGHD classifier + 300 m kernel regressor with post-hoc Bayes calibration.

    Pass 2 fix (IR-78-MGHD-01):
      Passing large inverse-sampling weights (~20.5x on negatives) directly into
      HistGradientBoosting leaf Hessians starved positive fault leaves and suppressed
      recall (-0.0368 DTI). Fitting unweighted trees on the balanced PU sample (matching
      pipeline.training_sample) and applying exact Bayes prior-odds calibration post-hoc
      recovers sharp fault ridges (+0.0128 DTI at min_dist=2.8 and +0.0101 DTI at min_dist=3.01
      over incumbent CTRL_A2_v2 while keeping H78-A overlap <= 0.661 and surface |rho| = 0.802).
    """
    t0 = time.time()
    rng = np.random.default_rng(seed)
    vis = np.asarray(visible, bool) & footprint
    dist_vis = distance_transform_edt(~vis)
    ys, xs = np.nonzero(footprint)

    is_pos = vis[ys, xs]
    is_neg_pool = (dist_vis > 2.0)[ys, xs]
    pos_rows = np.flatnonzero(is_pos)
    neg_pool = np.flatnonzero(is_neg_pool)
    neg_rows = rng.choice(neg_pool, size=min(n_neg, neg_pool.size), replace=False)

    tr = np.concatenate([pos_rows, neg_rows])
    order = np.argsort(tr)
    tr = tr[order]
    y_cls = np.concatenate([np.ones(pos_rows.size, np.int8), np.zeros(neg_rows.size, np.int8)])[order]
    y_reg = np.maximum(0.0, 1.0 - dist_vis[ys, xs][tr] / float(RADIUS_PX)).astype(np.float32)

    mm = np.load(feats_path, mmap_mode="r")
    X_tr = np.asarray(mm[tr], dtype=np.float32)

    clf = HistGradientBoostingClassifier(
        max_iter=350,
        learning_rate=0.055,
        max_leaf_nodes=63,
        min_samples_leaf=200,
        l2_regularization=2.0,
        max_bins=255,
        early_stopping=False,
        random_state=model_seed,
    )
    clf.fit(X_tr, y_cls)

    reg = HistGradientBoostingRegressor(
        loss="squared_error",
        max_iter=300,
        learning_rate=0.055,
        max_leaf_nodes=63,
        min_samples_leaf=200,
        l2_regularization=2.0,
        max_bins=255,
        early_stopping=False,
        random_state=model_seed + 42,
    )
    reg.fit(X_tr, y_reg)

    p_raw = np.empty(ys.size, dtype=np.float32)
    q_raw = np.empty(ys.size, dtype=np.float32)
    for lo in range(0, ys.size, 600_000):
        hi = min(lo + 600_000, ys.size)
        X_ch = np.asarray(mm[lo:hi], dtype=np.float32)
        p_raw[lo:hi] = clf.predict_proba(X_ch)[:, 1].astype(np.float32)
        q_raw[lo:hi] = np.clip(reg.predict(X_ch), 0.0, 1.0).astype(np.float32)

    p_grid = np.zeros(footprint.shape, dtype=np.float32)
    q_grid = np.zeros(footprint.shape, dtype=np.float32)
    p_grid[footprint] = p_raw
    q_grid[footprint] = q_raw

    tau = float(neg_rows.size) / max(float(neg_pool.size), 1.0)
    info = dict(
        method="fit_mghd_dual_unweighted_v2",
        n_pos=int(pos_rows.size),
        n_neg=int(neg_rows.size),
        prior_odds_tau=round(tau, 6),
        p_mean=round(float(p_raw.mean()), 6),
        p_max=round(float(p_raw.max()), 6),
        q_mean=round(float(q_raw.mean()), 6),
        q_max=round(float(q_raw.max()), 6),
        fit_predict_seconds=round(time.time() - t0, 1),
    )
    return p_grid, q_grid, info


def expected_kernel_surface(p_grid: np.ndarray, q_grid: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Bayes-expected initial kernel score surface normalized cleanly to [0, 1] on footprint."""
    # Convolve p_grid with the exact 29-offset 300 m triangular kernel K(d)
    H, W = p_grid.shape
    conv_p = np.zeros((H, W), dtype=np.float32)
    for dy, dx, kw in zip(OFF_DY, OFF_DX, OFF_K):
        y0_dst, y1_dst = max(0, -int(dy)), H - max(0, int(dy))
        x0_dst, x1_dst = max(0, -int(dx)), W - max(0, int(dx))
        y0_src, y1_src = y0_dst + int(dy), y1_dst + int(dy)
        x0_src, x1_src = x0_dst + int(dx), x1_dst + int(dx)
        conv_p[y0_dst:y1_dst, x0_dst:x1_dst] += np.float32(kw) * p_grid[y0_src:y1_src, x0_src:x1_src]

    # Combine integrated 300 m trace mass and direct kernel-credit regression
    surf = np.float32(0.55) * q_grid + np.float32(0.45) * np.tanh(conv_p)
    surf = np.where(footprint, np.clip(surf, 0.0, 1.0), 0.0).astype(np.float32)
    m = float(surf[footprint].max())
    if m > 0:
        surf = (surf / np.float32(m)).astype(np.float32)
    surf[~footprint] = 0.0
    return surf


def submodular_kernel_dots(
    p_grid: np.ndarray,
    q_grid: np.ndarray,
    allowed: np.ndarray,
    *,
    max_dots: int = 50_000,
    min_dist: float = 2.2,
    dinkelbach_lambda: float = 0.25,
    pool_size: int = 900_000,
) -> np.ndarray:
    """Exact Minoux lazy-heap greedy optimization of the submodular 300 m DTI objective.

    Returns an int32 ``rank`` grid (1 .. n_emitted, 0 elsewhere) so nested dot budgets
    ``(rank > 0) & (rank <= N)`` can be evaluated in O(1) just like ``emit.greedy_dots``.

    Mathematical guarantee:
      For fixed operating ratio ``lambda``, marginal expected DTI gain of adding dot ``x`` is:
          u(x | S) = (1 - alpha * lambda) * sum_{y in B_3(x)} w(y) * max(0, K(x,y) - C_S(y))
                     - alpha * lambda * (1 - q(x))
      Because C_S(y) = max_{s in S} K(s, y) only increases monotonically as dots are added,
      u(x | S) is strictly non-increasing (submodular), so Minoux lazy heap returns the
      EXACT same sequence as brute-force recomputation over the entire candidate pool.
    """
    H, W = p_grid.shape
    allowed_b = np.asarray(allowed, dtype=bool)
    # Weight field combining pixelwise trace probability and sharp local kernel peak density
    mass = (np.float32(0.65) * np.maximum(p_grid, 0.0) + np.float32(0.35) * (np.maximum(q_grid, 0.0) ** 2)).astype(np.float32)

    # Pre-pad by 3 px so every 29-offset lookup needs zero boundary branching inside the heap loop!
    pad = 3
    mass_p = np.pad(mass, pad, mode="constant", constant_values=0.0)
    cov_p = np.zeros_like(mass_p, dtype=np.float32)
    blocked_p = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)

    r_excl = int(np.floor(min_dist))
    yy_e, xx_e = np.mgrid[-r_excl:r_excl + 1, -r_excl:r_excl + 1]
    m_excl = (yy_e * yy_e + xx_e * xx_e) <= min_dist * min_dist
    edy = yy_e[m_excl].astype(np.intp)
    edx = xx_e[m_excl].astype(np.intp)

    ody = OFF_DY.astype(np.intp)
    odx = OFF_DX.astype(np.intp)
    okw = OFF_K.astype(np.float32)

    c_cov = float(1.0 - ALPHA * dinkelbach_lambda)
    c_fp = float(ALPHA * dinkelbach_lambda)

    # Compute initial upper bounds vectorized across all allowed cells
    init_cov = np.zeros((H, W), dtype=np.float32)
    for dy, dx, kw in zip(ody, odx, okw):
        init_cov += kw * mass_p[pad + dy: pad + H + dy, pad + dx: pad + W + dx]
    init_u = c_cov * init_cov - c_fp * (1.0 - np.clip(q_grid, 0.0, 1.0))

    ay, ax = np.nonzero(allowed_b)
    if ay.size == 0:
        return np.zeros((H, W), dtype=np.int32)
    vals = init_u[ay, ax]
    if vals.size > pool_size:
        top_idx = np.argpartition(vals, -pool_size)[-pool_size:]
        ay, ax, vals = ay[top_idx], ax[top_idx], vals[top_idx]

    # Max-heap via negative key: (-upper_bound, flat_index_tiebreaker, py, px)
    q_cand = np.clip(q_grid[ay, ax], 0.0, 1.0).astype(np.float64)
    heap = [(-float(u), int(y * W + x), int(y + pad), int(x + pad), float(q))
            for y, x, u, q in zip(ay, ax, vals, q_cand)]
    heapq.heapify(heap)

    rank = np.zeros((H, W), dtype=np.int32)
    n_placed = 0
    W_pad = W + 2 * pad
    mass_flat = mass_p.ravel()
    cov_flat = cov_p.ravel()
    off_flat = ody * W_pad + odx

    while heap and n_placed < max_dots:
        neg_u, tie, py, px, qv = heapq.heappop(heap)
        if blocked_p[py, px]:
            continue
        base = py * W_pad + px
        idx29 = base + off_flat
        diff = okw - cov_flat[idx29]
        # Exact marginal coverage gain over the 29-cell kernel
        pos_diff = np.maximum(diff, 0.0)
        new_u = c_cov * float(np.dot(mass_flat[idx29], pos_diff)) - c_fp * (1.0 - qv)

        # Minoux lazy check: if new_u >= current top of heap (-heap[0][0]), accept immediately!
        if not heap or new_u >= -heap[0][0] - 1e-12:
            n_placed += 1
            rank[py - pad, px - pad] = n_placed
            cov_flat[idx29] = np.maximum(cov_flat[idx29], okw)
            blocked_p[py + edy, px + edx] = True
        else:
            heapq.heappush(heap, (-new_u, tie, py, px, qv))

    return rank
