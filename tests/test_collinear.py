"""Unit tests for H78-CS collinear-support features (synthetic, no large inputs)."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems78 import collinear as C  # noqa: E402


def _ridge_grid(h=101, w=101, x0=50, amp=1.0):
    xs = np.arange(w, dtype=np.float32)[None, :]
    return np.repeat(np.exp(-((xs - x0) ** 2) / 8.0).astype(np.float32) * amp, h, axis=0)


def test_names_count_and_order():
    names = C.cs_feature_names()
    assert len(names) == 15
    assert names[:5] == ["cs_det_elev_Hnn_L5_mean", "cs_det_elev_Hnn_L15_mean",
                         "cs_det_elev_gn_L5_mean", "cs_det_elev_gn_L15_mean",
                         "cs_det_elev_Hnn_L15_min"]


def test_path_stats_follows_tangent_not_normal():
    #Vertical ridge (constant along rows/y, varying along cols/x).
    resp = _ridge_grid()
    ys = np.array([50], np.int32)
    xs = np.array([50], np.int32)
    # phi=0: normal along +x, tangent along y -> path stays on the ridge crest.
    m5, m15, mn = C.path_stats(resp, ys, xs, np.array([0.0], np.float32))
    assert m15[0] > 0.99 and mn[0] > 0.99
    # phi=pi/2: normal along +y, tangent along x -> path crosses the ridge, mean collapses.
    m5b, m15b, mnb = C.path_stats(resp, ys, xs, np.array([np.pi / 2], np.float32))
    assert m15b[0] < 0.35 and m15b[0] < m5b[0] < m15[0]


def test_min_half_requires_both_sides():
    resp = np.zeros((101, 101), np.float32)
    resp[50:, 50] = 1.0  # half-line: support only on the +y side of (50, 50) path along y
    ys = np.array([50], np.int32)
    xs = np.array([50], np.int32)
    m5, m15, mn = C.path_stats(resp, ys, xs, np.array([0.0], np.float32))
    assert m15[0] > 0.4          # plain mean still sees the half-line
    assert mn[0] == 0.0          # weaker-side statistic does not


def test_steered_responses_peak_on_ridge_and_step():
    # Ridge: |Hnn| (normal = x) must peak at the crest; step: |gn| peaks at the edge.
    band = _ridge_grid(amp=10.0)
    phi = np.zeros_like(band)  # normal along x everywhere
    hnn, gn = C.steered_abs_responses(band, phi)
    assert np.argmax(hnn[50]) == 50
    step = np.zeros((101, 101), np.float32)
    step[:, 50:] = 10.0
    _, gn2 = C.steered_abs_responses(step, phi)
    assert abs(int(np.argmax(gn2[50])) - 50) <= 1
    assert np.isfinite(hnn).all() and np.isfinite(gn).all()
