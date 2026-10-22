"""Synthetic-operator tests for H78-STEP paired flank features."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems78 import step as S  # noqa: E402


def _idx(names, suffix, band="det_elev"):
    return names.index(f"step_{band}_{suffix}") % 9  # within-band column


def test_feature_names_count():
    names = S.step_feature_names()
    assert len(names) == 54 and len(set(names)) == 54
    for b in S.STEP_BANDS:
        assert f"step_{b}_d4_signed" in names and f"step_{b}_sharp" in names


def test_vertical_step_detected_with_sign():
    band = np.zeros((101, 101), np.float32)
    band[:, 50:] = 10.0                      # step up toward +x at col 50
    ys = np.array([50, 50], np.int32)
    xs = np.array([50, 20], np.int32)
    phi = np.zeros(2, np.float32)            # normal = +x, tangent = +y
    f = S.band_step_features(band, ys, xs, phi)
    names = S.step_feature_names()
    i_sign, i_abs, i_cdev = _idx(names, "d4_signed"), _idx(names, "d4_abs"), _idx(names, "d4_cdev")
    assert f[0, i_sign] == 10.0 and f[0, i_abs] == 10.0   # on the step line
    assert f[1, i_abs] == 0.0                             # far from the step
    # pure step: centre sits on the high side, so centre deviation = half the step
    assert abs(f[0, i_cdev] - 5.0) < 1e-5
    assert np.isfinite(f).all()


def test_horizontal_step_and_tangent_convention():
    band = np.zeros((101, 101), np.float32)
    band[50:, :] = 7.0                       # step up toward +y at row 50
    ys = np.array([50], np.int32)
    xs = np.array([50], np.int32)
    phi = np.array([np.pi / 2], np.float32)  # normal = +y
    f = S.band_step_features(band, ys, xs, phi)
    names = S.step_feature_names()
    assert f[0, _idx(names, "d4_signed")] == 7.0
    # wrong orientation (normal along x) must see no step on a horizontal edge
    f2 = S.band_step_features(band, ys, xs, np.zeros(1, np.float32))
    assert f2[0, _idx(names, "d4_abs")] == 0.0


def test_ridge_has_centre_deviation_without_step():
    x = np.arange(101, dtype=np.float32)
    ridge = 10.0 * np.exp(-((x - 50) ** 2) / 8.0)
    band = np.tile(ridge[None, :], (101, 1)).astype(np.float32)
    ys = np.array([50], np.int32)
    xs = np.array([50], np.int32)
    f = S.band_step_features(band, ys, xs, np.zeros(1, np.float32))
    names = S.step_feature_names()
    assert f[0, _idx(names, "d9_abs")] < 0.5              # symmetric flanks: no step
    assert f[0, _idx(names, "d9_cdev")] > 5.0             # but strong centre deviation


def test_flat_and_sharpness_bounds():
    band = np.full((61, 61), 3.25, np.float32)
    ys = np.array([30], np.int32)
    xs = np.array([30], np.int32)
    f = S.band_step_features(band, ys, xs, np.zeros(1, np.float32))
    assert (f == 0).all()
    ramp = np.tile(np.linspace(0, 100, 101, dtype=np.float32)[None, :], (101, 1))
    f2 = S.band_step_features(ramp, np.array([50], np.int32), np.array([50], np.int32),
                              np.zeros(1, np.float32))
    assert 0.0 <= f2[0, 8] <= 10.0 and np.isfinite(f2).all()
    # broad ramp: wide-scale step exceeds narrow-scale step -> sharpness < 1
    assert f2[0, 8] < 1.0
