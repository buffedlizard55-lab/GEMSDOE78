#!/usr/bin/env python3
"""Build cached feature stack (memory-lean, incremental memmap writes).

Output .cache/features/stack.npy float32 (80, 3730, 3292) + names.json.
48 base bands + 28 monogenic phase-congruency (MPC) + 4 Frangi.
No catalogue-derived features (leakage control by construction).
Single-precision FFT (complex64) + per-source processing to fit ~3 GB RAM.
"""
from __future__ import annotations
import gc, json, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import fft as sfft

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".cache" / "gems_data"
OUT = ROOT / ".cache" / "features"; OUT.mkdir(parents=True, exist_ok=True)
H, W = 3730, 3292
SENTINEL = -3.4028234663852886e+38
NB = 80

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

with rasterio.open(DATA / "sample_submission.tif") as s:
    footprint = np.isfinite(s.read(1))
log("footprint", int(footprint.sum()))

mm = np.lib.format.open_memmap(OUT / "stack.npy", mode="w+", dtype=np.float32, shape=(NB, H, W))
names: list[str] = []
def add(name, arr):
    a = np.asarray(arr, np.float32)
    assert a.shape == (H, W), (name, a.shape)
    mm[len(names)] = a; mm.flush()
    names.append(name); log(len(names), name)
    del a; gc.collect()

short = []
with rasterio.open(DATA / "training_features.tif") as s:
    for i, desc in enumerate(s.descriptions, start=1):
        nm = desc.split(" - ")[0].strip(); short.append(nm)
        a = s.read(i).astype(np.float32); a[a <= SENTINEL / 2] = np.nan
        add(f"tf_{nm}", a); del a
idx = {n: i for i, n in enumerate(short)}
for fn, prefix in [("lidar_scarp_features_u8.tif", "lidar"), ("geodawn_rad_u8.tif", "rad"),
                   ("geodawn_extensions_u8.tif", "gdx"), ("topo_10m_derived_100m_u8.tif", "topo10")]:
    with rasterio.open(DATA / "external" / fn) as s:
        for i, desc in enumerate(s.descriptions, start=1):
            add(f"{prefix}_{desc}", s.read(i).astype(np.float32) / 255.0)
n_base = len(names); log("base =", n_base)
assert n_base == 48

# ---- MPC (single precision) ----
fy = sfft.fftfreq(H).astype(np.float32)[:, None]
fx = sfft.rfftfreq(W).astype(np.float32)[None, :]
rho = np.sqrt(fx * fx + fy * fy).astype(np.float32)
rho_safe = rho.copy(); rho_safe[0, 0] = 1.0
rx = (-1j * (fx / rho_safe)).astype(np.complex64)
ry = (-1j * (fy / rho_safe)).astype(np.complex64)
bps = []
for sig in (1.0, 2.0, 4.0):
    bp = (np.exp(-2.0 * (np.pi * sig * rho) ** 2) - np.exp(-2.0 * (np.pi * 2 * sig * rho) ** 2)).astype(np.float32)
    bp[0, 0] = 0.0; bps.append(bp)
del fx, fy, rho_safe; gc.collect()

def mpc_family(src_i: int, label: str):
    x = np.array(mm[src_i], dtype=np.float32)
    med = float(np.nanmedian(x[footprint]))
    x = np.where(np.isfinite(x), x, med)
    p1, p99 = np.nanpercentile(x[footprint], [1, 99])
    x = np.clip((x - med) / max(float(p99 - p1), 1e-12), -3, 3).astype(np.float32)
    F = sfft.rfft2(x, workers=-1); del x; gc.collect()
    sumA = np.zeros((H, W), np.float32); ssum = np.zeros((H, W), np.float32)
    csum = np.zeros((H, W), np.float32); odd_sum = np.zeros((H, W), np.complex64)
    odd_abs = np.zeros((H, W), np.float32)
    amps = []
    # pass 1: amplitudes/phases stored compactly (3 x float32 each)
    phis = []
    for bp in bps:
        G = (F * bp).astype(np.complex64)
        even = sfft.irfft2(G, s=(H, W), workers=-1).astype(np.float32)
        ox = sfft.irfft2((G * rx), s=(H, W), workers=-1).astype(np.float32)
        oy = sfft.irfft2((G * ry), s=(H, W), workers=-1).astype(np.float32)
        del G
        om = np.sqrt(ox * ox + oy * oy)
        A = np.sqrt(even * even + om * om)
        phi = np.arctan2(om, even)
        amps.append(A); phis.append(phi)
        odd_sum += (ox + 1j * oy).astype(np.complex64); odd_abs += om
        del even, ox, oy, om; gc.collect()
    del F; gc.collect()
    for A, phi in zip(amps, phis):
        sumA += A; ssum += A * np.sin(phi); csum += A * np.cos(phi)
    mean_phi = np.arctan2(ssum, csum); del ssum, csum
    pc_num = np.zeros((H, W), np.float32)
    for A, phi in zip(amps, phis):
        pc_num += A * np.cos(phi - mean_phi)
    out = {}
    out["pc"] = (pc_num / (sumA + 1e-12)).astype(np.float32); del pc_num
    out["cos_phase"] = np.cos(mean_phi).astype(np.float32)
    out["sin_phase"] = np.sin(mean_phi).astype(np.float32); del mean_phi
    out["orient_coh"] = (np.abs(odd_sum) / (odd_abs + 1e-12)).astype(np.float32)
    del odd_sum, odd_abs, sumA
    for i, A in enumerate(amps):
        hi = float(np.nanpercentile(A[footprint], 99.5))
        out[f"amp{i+1}"] = np.clip(A / max(hi, 1e-12), 0, 1).astype(np.float32)
    del amps, phis; gc.collect()
    for k in ["pc", "amp1", "amp2", "amp3", "cos_phase", "sin_phase", "orient_coh"]:
        add(f"mpc_{label}_{k}", out.pop(k))

for nm in ["rtp", "iso_grav_anom", "det_elev", "depth_to_base_surf"]:
    mpc_family(idx[nm], nm)

# ---- Frangi tiled ----
from skimage.filters import frangi
def frangi_tiled(src_i, dark):
    x = np.array(mm[src_i], dtype=np.float32)
    med = float(np.nanmedian(x[footprint])); x = np.where(np.isfinite(x), x, med)
    p1, p99 = np.nanpercentile(x[footprint], [1, 99])
    x = np.clip((x - float(p1)) / max(float(p99 - p1), 1e-12), 0, 1).astype(np.float64)
    out = np.zeros((H, W), np.float32); T, OV = 512, 24
    for y0 in range(0, H, T):
        for x0 in range(0, W, T):
            ys, ye = max(0, y0 - OV), min(H, y0 + T + OV)
            xs, xe = max(0, x0 - OV), min(W, x0 + T + OV)
            v = frangi(x[ys:ye, xs:xe], sigmas=(1, 2), black_ridges=dark)
            out[y0:min(H, y0+T), x0:min(W, x0+T)] = v[y0-ys:y0-ys+min(T, H-y0), x0-xs:x0-xs+min(T, W-x0)]
    del x; gc.collect()
    return out
for nm in ["rtp", "det_elev"]:
    for dark, tag in [(False, "bright"), (True, "dark")]:
        add(f"frangi_{nm}_{tag}", frangi_tiled(idx[nm], dark))

assert len(names) == NB, len(names)
(OUT / "names.json").write_text(json.dumps({"names": names, "n_base": n_base}, indent=1))
log("DONE", len(names))
