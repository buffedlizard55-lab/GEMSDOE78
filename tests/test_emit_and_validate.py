"""Unit tests for the emitter and the independent TIF verifier (synthetic data, no large inputs needed)."""
import sys, json, subprocess
from pathlib import Path
import numpy as np, pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "vendor"))
from gems78 import emit as E


def test_greedy_dots_respects_spacing_and_budget():
    rng = np.random.default_rng(0)
    score = rng.random((120, 140)).astype(np.float32)
    allowed = np.ones_like(score, bool)
    rank = E.greedy_dots(score, allowed, 2.8, 300, 5000)
    dots = E.prefix(rank, 300)
    assert dots.sum() == 300
    yy, xx = np.nonzero(dots)
    d2 = (yy[:, None] - yy[None]) ** 2 + (xx[:, None] - xx[None]) ** 2
    np.fill_diagonal(d2, 10**9)
    assert d2.min() >= 2.8 ** 2 - 1e-6  # >= 283 m apart on the 100 m grid


def test_greedy_dots_never_in_disallowed_and_prefix_is_rank_ordered():
    rng = np.random.default_rng(1)
    score = rng.random((80, 80)).astype(np.float32)
    allowed = np.ones_like(score, bool); allowed[:, :40] = False
    rank = E.greedy_dots(score, allowed, 2.8, 200, 3000)
    assert not (E.prefix(rank, 200) & ~allowed).any()
    a, b = E.prefix(rank, 50), E.prefix(rank, 100)
    assert a.sum() == 50 and b.sum() == 100 and (a & ~b).sum() == 0  # budgets are nested
    # the first dot is the global maximum of the allowed surface
    assert score[E.prefix(rank, 1)].item() == pytest.approx(score[allowed].max())


def test_flank_mask_radius():
    vis = np.zeros((41, 41), bool); vis[20, 20] = True
    m2, m3 = E.flank_mask(vis, 2.0), E.flank_mask(vis, 3.0)
    assert m2[20, 22] and not m2[20, 23]
    assert m3[20, 23] and not m3[20, 24]
    assert m3.sum() > m2.sum()


def test_run_card_and_shipped_file_are_consistent():
    card_p = ROOT / "evidence/h78_run_card.json"
    if not card_p.exists():
        pytest.skip("no run card yet")
    card = json.loads(card_p.read_text())  # immutable historical H78-A run card; current clearance is tested separately
    tif = ROOT / "docs/downloads" / card["raster"]["file"]
    assert tif.exists(), "shipped file missing"
    import hashlib
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster"]["sha256"]
    assert card["note_chars"] <= 140 and len(card["submission_note"]) <= 140
    assert card["ok_to_submit"] == (card["verdict"] == "promote")
    if card["ok_to_submit"]:
        assert card["validator"]["passed"] and card["uniqueness"]["passed"] and card["canary"]["clean"]
        assert card["holdout"]["beats_A0_std19_ci"] and card["holdout"]["evidence_class"] == "HOLDOUT-DTI"


def test_independent_verifier_passes_on_shipped_file():
    card_p = ROOT / "evidence/h78_run_card.json"
    if not card_p.exists() or not (ROOT / "data/bridge/sample_submission.tif").exists():
        pytest.skip("inputs not restored")
    card = json.loads(card_p.read_text())
    r = subprocess.run([sys.executable, str(ROOT / "scripts/verify_tif.py"), str(ROOT / "docs/downloads" / card["raster"]["file"])],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["all_passed"] and out["checks"]["values_in_[0,1]"] and out["checks"]["no_nan_inside_footprint"]
