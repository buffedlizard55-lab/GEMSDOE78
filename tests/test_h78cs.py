"""H78-CS session-3 consistency tests: run card <-> written TIF <-> site banner.

These assert the *computed* gate logic, so they hold whichever verdict the
evidence produced: ok_to_submit must equal the conjunction of the preregistered
gate, the site banner must match the verdict, and the TIF on disk must be the
one the run card names (sha256, dot count, portal-safe [0,1] format).
"""
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/h78cs_run_card.json").read_text())
TIF = ROOT / "docs/downloads" / CARD["raster"]["file"]


def test_gate_logic_is_the_verdict():
    gate = CARD["preregistered_gate_evaluation"]
    assert set(gate) == {"cand_beats_ctrl_point", "cand_beats_repo_best_0p1826",
                         "paired_delta_ci_lower_gt_0", "canary_clean",
                         "uniqueness_pass", "validator_pass"}
    assert CARD["ok_to_submit"] == all(gate.values())
    assert CARD["verdict"] == ("promote" if CARD["ok_to_submit"] else "negative")
    # seed-20 numbers recomputed from the card must match the holdout evidence file
    hold = json.loads((ROOT / "evidence/h78cs_holdout_seed20.json").read_text())
    ps = hold["pooled_summary_B3_primary"]
    assert CARD["holdout"]["candidate"]["dti"] == ps["scores"]["CAND_CS|B3|44090"]["dti"]
    assert CARD["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert CARD["holdout"]["withheld_positive_pixels"] == 11321
    assert CARD["holdout"]["ctrl"]["dti"] == ps["scores"]["CTRL_A2|B3|44090"]["dti"]
    assert CARD["organizer_confirmed_score"] is None


def test_tif_matches_card_and_is_portal_safe():
    assert TIF.exists()
    assert hashlib.sha256(TIF.read_bytes()).hexdigest() == CARD["raster_sha256"]
    with rasterio.open(TIF) as s:
        a = s.read(1)
        assert s.count == 1 and s.dtypes == ("float32",)
        assert (s.height, s.width) == (3730, 3292)
        assert str(s.crs) == "EPSG:32611"
        assert tuple(s.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert s.nodata is None
    assert np.isfinite(a).all()                       # "[0, 1]" portal error cannot fire
    assert a.min() >= 0.0 and a.max() <= 1.0
    assert set(np.unique(a)) <= {0.0, 1.0}
    assert int((a > 0).sum()) == CARD["raster"]["dots"] == 44090
    with zipfile.ZipFile(TIF.with_suffix(".zip")) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()
    assert CARD["validator_output"]["passed"] is True
    assert all(CARD["validator_output"]["writer_receipt_checks"].values())
    assert len(CARD["submission_note"]) <= 140 and CARD["note_chars"] == len(CARD["submission_note"])


def test_independent_verifier_passes():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/verify_tif.py"), str(TIF)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["all_passed"] and out["sha256"] == CARD["raster_sha256"]


def test_uniqueness_recorded_within_limits_or_gate_fails():
    uq = CARD["correlation_overlap_vs_registry"]
    assert len(uq["final_dots"]) == 6  # 3 family registry + H78-A x2 + H78-MPC
    if uq["passed"]:
        assert uq["surface_max_abs_rho"] <= 0.90 and uq["dots_max_overlap"] <= 0.70
    else:
        assert CARD["ok_to_submit"] is False


def test_site_banner_matches_verdict():
    html = (ROOT / "docs/h78cs.html").read_text()
    assert CARD["submission_name"] in html and CARD["raster_sha256"] in html
    if CARD["verdict"] == "promote":
        assert "OK TO SUBMIT: YES" in html
    else:
        assert "OK TO SUBMIT: NO" in html and "negative" in html
    assert "HOLDOUT-DTI" in html and "ORGANIZER-CONFIRMED" in html
    assert (ROOT / "docs/h78cs-executive-summary.html").exists()
