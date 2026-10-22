"""Unit tests for H78-FW antisymmetric footwall/hangingwall flank-warp features."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems78 import flank_warp as FW  # noqa: E402
from gems78.data import BAND_NAMES  # noqa: E402


def test_monocline_vs_symmetric_ridge_purity_and_dipole():
    """An odd-parity monoclinal warp must have high purity and positive curvature dipole
    at its inflection line, whereas an even-parity symmetric ridge has low purity."""
    H, W = 96, 96
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x0 = 48.0
    # Strike along y-axis -> normal along +x (phi = 0 -> cos(phi)=1, sin(phi)=0)
    ys = np.array([48], dtype=np.int32)
    xs = np.array([48], dtype=np.int32)
    cph = np.ones(1, dtype=np.float32)
    sph = np.zeros(1, dtype=np.float32)

    # 1. Broad antisymmetric monocline (tanh step with width 5 px)
    monocline = np.tanh((xx - x0) / 5.0).astype(np.float32)
    w_mono, _, d_mono = FW.compute_flank_warp_for_band(
        monocline, ys, xs, cph, sph, compute_doublet=True
    )
    # w_mono = [asym_d4, purity_d4, asym_d8, purity_d8, asym_d14, purity_d14, sym_d8]
    purity_mono_d8 = float(w_mono[3][0])
    asym_mono_d8 = float(w_mono[2][0])
    sym_mono_d8 = float(w_mono[6][0])
    dipole_mono_d6 = float(d_mono[1][0])

    assert asym_mono_d8 > 0.25
    assert sym_mono_d8 < 0.01
    assert purity_mono_d8 > 0.95
    assert dipole_mono_d6 > 0.0  # opposite-sign second derivatives on opposing flanks

    # 2. Symmetric ridge (Gaussian ridge centred at x0)
    ridge = np.exp(-0.5 * ((xx - x0) / 5.0) ** 2).astype(np.float32)
    w_ridge, _, d_ridge = FW.compute_flank_warp_for_band(
        ridge, ys, xs, cph, sph, compute_doublet=True
    )
    purity_ridge_d8 = float(w_ridge[3][0])
    asym_ridge_d8 = float(w_ridge[2][0])
    sym_ridge_d8 = float(w_ridge[6][0])

    assert asym_ridge_d8 < 1e-5
    assert sym_ridge_d8 > 0.20
    assert purity_ridge_d8 < 0.01


def test_build_fw_matrix_shape_and_crosslayer_concordance(tmp_path, monkeypatch):
    """Verify build_fw_matrix produces 67 finite columns and positive concordance on
    co-aligned elevation uplift + shallow basement + positive gravity step."""
    monkeypatch.setattr(FW, "PROC", tmp_path)
    H, W = 64, 64
    C = len(BAND_NAMES)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    step = np.tanh((xx - 32.0) / 5.0).astype(np.float32)

    stack = np.zeros((C, H, W), dtype=np.float32)
    # Footwall on +x side: higher det_elev (+step), shallower basement (-step), higher gravity (+step), mag step (+step)
    stack[BAND_NAMES.index("det_elev")] = 100.0 * step
    stack[BAND_NAMES.index("depth_to_base_surf")] = -2.0 * step + 3.0
    stack[BAND_NAMES.index("iso_grav_anom")] = 15.0 * step
    stack[BAND_NAMES.index("rtp")] = 50.0 * step

    fp = np.ones((H, W), dtype=bool)
    phi = np.zeros((H, W), dtype=np.float32)
    coh = np.full((H, W), 0.85, dtype=np.float32)

    out_path, meta = FW.build_fw_matrix("synth", fp, phi, coh, stack=stack, force=True)
    names = FW.fw_feature_names()
    assert len(names) == 67
    assert meta["n_features"] == 67
    mm = np.load(out_path, mmap_mode="r")
    assert mm.shape == (H * W, 67)
    assert np.isfinite(mm).all()

    center_row = 32 * W + 32
    for cname in (
        "fw_concord_elev_base_d8",
        "fw_concord_elev_grav_d8",
        "fw_concord_base_grav_d8",
        "fw_concord_mag_grav_d8",
    ):
        idx = names.index(cname)
        assert float(mm[center_row, idx]) > 0.1, f"{cname} should be positive at fault trace"
