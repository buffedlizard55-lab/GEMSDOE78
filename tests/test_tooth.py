"""Synthetic checks for the missing-tooth spacing feature. No competition rasters."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems78.tooth import FEATURE_NAMES, missing_tooth_fields  # noqa: E402


def _paint_row(mask, y, x0, x1):
    mask[y, x0:x1] = True


def test_double_width_gap_peaks_and_ordinary_trough_does_not():
    mask = np.zeros((120, 140), bool)
    # Array spacing 20 px. The strand at y=60 is absent; both neighbours still
    # have a tight neighbour on their far side, so the 25th percentile stays 20.
    for y in (20, 40, 80, 100):
        _paint_row(mask, y, 20, 120)
    fields = missing_tooth_fields(mask, sigma=12.0, support_min=1e-4)
    gap = fields["tooth_gap1"]
    lam = fields["tooth_lambda_px"]
    # Centre of the missing strand.
    assert lam[60, 70] == 0 or abs(lam[60, 70] - 20) < 6, lam[60, 70]
    assert gap[60, 70] > 0.45, (gap[60, 70], lam[60, 70], fields["distance_to_visible_px"][60, 70])
    # Ordinary trough between y=20 and y=40: d=10, lambda~20, kernel must be quiet.
    assert gap[30, 70] < 0.15, (gap[30, 70], lam[30, 70], fields["distance_to_visible_px"][30, 70])
    # On a mapped trace the kernel is ~0 (d=0, peak is at d=lambda).
    assert gap[40, 70] < 0.05


def test_lone_fault_has_no_spacing_and_no_gap_score():
    mask = np.zeros((40, 40), bool)
    _paint_row(mask, 20, 5, 35)
    fields = missing_tooth_fields(mask, sigma=6.0, support_min=1e-4)
    for name in FEATURE_NAMES:
        assert np.isfinite(fields[name]).all()
        assert fields[name].max() == 0.0


def test_feature_names_are_finite_and_bounded():
    rng = np.random.default_rng(0)
    mask = np.zeros((80, 90), bool)
    for y in (15, 32, 50, 68):
        _paint_row(mask, y, 10, 80)
    # Punch out part of one strand so a gap exists.
    mask[32, 40:70] = False
    fields = missing_tooth_fields(mask, sigma=8.0, support_min=1e-4)
    for name in FEATURE_NAMES:
        a = fields[name]
        assert a.shape == mask.shape
        assert a.dtype == np.float32
        assert np.isfinite(a).all()
        assert a.min() >= 0.0
    assert fields["tooth_gap1"].max() <= 1.0 + 1e-6
    assert fields["tooth_width_ratio"].max() <= 4.0 + 1e-6
    # The punched strand should outscore a random empty cell far from the array.
    assert fields["tooth_gap1"][32, 55] > fields["tooth_gap1"][5, 5]
