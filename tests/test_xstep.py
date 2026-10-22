"""Unit tests for H78-STEP cross-strike profile features (synthetic, no large inputs)."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems78 import xstep as X  # noqa: E402


def test_names_count_and_order():
    names = X.step_feature_names()
    assert len(names) == 54
    assert names[0] == "xs_det_elev_step3_z"
    assert names[7] == "xs_det_elev_dev6_absz"
    assert names[8] == "xs_rtp_step3_z"
    assert names[40] == "xs_conc6_throw_z"
    assert names[-1] == "xs_conc10_weakest"


def test_profile_follows_normal_not_tangent():
    # Flat step: value depends only on column (0 left of col 50, 10 right).
    band = np.zeros((101, 101), np.float32)
    band[:, 50:] = 10.0
    ys = np.array([50], np.int32)
    xs = np.array([50], np.int32)
    # phi=0 -> normal along +x (columns): profile must cross the step.
    prof = X.sample_profile(band, ys, xs, np.array([0.0], np.float32))
    assert prof.shape == (1, 7)
    assert prof[0, 0] == 0.0 and prof[0, -1] == 10.0       # -10 px .. +10 px
    cols = X.profile_columns(prof, np.array([1.0], np.float32))
    assert cols[0, 4] == 10.0                               # step10_z = v(+10)-v(-10)
    assert cols[0, 5] == 10.0                               # step10_absz
    # phi=pi/2 -> normal along +y (rows): profile runs parallel to the step edge.
    prof2 = X.sample_profile(band, ys, np.array([30], np.int32),
                             np.array([np.pi / 2], np.float32))
    assert np.all(prof2 == 0.0)


def test_ridge_gives_deviation_not_step():
    xs_grid = np.arange(101, dtype=np.float32)[None, :]
    band = np.repeat((10.0 * np.exp(-((xs_grid - 50) ** 2) / 8.0)).astype(np.float32),
                     101, axis=0)
    prof = X.sample_profile(band, np.array([50], np.int32), np.array([50], np.int32),
                            np.array([0.0], np.float32))
    cols = X.profile_columns(prof, np.array([1.0], np.float32))
    step10 = cols[0, 4]
    dev6 = cols[0, 6]
    assert abs(step10) < 0.5          # symmetric ridge: flanks cancel
    assert dev6 > 5.0                 # centre stands above both flanks


def test_concordance_signs():
    # Perfect throw concordance: deeper(+), lower elev(-), lower grav(-), cond(+).
    cc = X.concordance_columns(np.array([2.0], np.float32), np.array([-2.0], np.float32),
                               np.array([-2.0], np.float32), np.array([2.0], np.float32))
    throw, throw_abs, p_de, p_dg, p_eg, p_dc, weakest = cc[0]
    assert throw == 2.0 and throw_abs == 2.0
    assert p_de == 4.0 and p_dg == 4.0 and p_eg == 4.0 and p_dc == 4.0
    assert weakest == 2.0
    # Opposite throw direction is equally concordant (faults dip both ways).
    cc2 = X.concordance_columns(np.array([-3.0], np.float32), np.array([3.0], np.float32),
                                np.array([3.0], np.float32), np.array([-3.0], np.float32))
    assert cc2[0, 0] == -3.0 and cc2[0, 6] == 3.0
    # One discordant layer (elev rises on the deep side) breaks weakest < 0.
    cc3 = X.concordance_columns(np.array([2.0], np.float32), np.array([2.0], np.float32),
                                np.array([-2.0], np.float32), np.array([2.0], np.float32))
    assert cc3[0, 6] < 0.0
    assert cc3[0, 2] == -4.0          # prod_depth_elev turns negative


def test_local_std_grid_constant_band():
    band = np.full((31, 31), 3.0, np.float32)
    std, gstd = X.local_std_grid(band)
    assert np.isfinite(std).all()
    assert gstd == 0.0
    assert float(std.max()) < 1e-5
