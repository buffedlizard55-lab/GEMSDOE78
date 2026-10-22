"""Regression tests for the H78-FW lane publication gate (2026-10-22 session)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_card():
    return json.loads((ROOT / "evidence/h78fw_run_card.json").read_text())


def test_fw_card_is_negative_and_blocked():
    card = load_card()
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["ok_to_download"] is True
    assert card["submission_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert card["submission_name"].endswith("DO-NOT-SUBMIT")
    assert len(card["submission_name"]) <= 140
    assert 1 <= len(card["submission_note"]) <= 140
    assert "NOT OK TO SUBMIT" in card["submission_note"]


def test_fw_holdout_labels_and_gate():
    card = load_card()
    h = card["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["seed"] == 20
    assert h["withheld_positive_pixels"] == 11321
    assert len(h["ci95"]) == 2 and h["ci95"][0] < h["score"] < h["ci95"][1]
    # Failed the holdout gate: below the stored repo best on the same draw.
    assert h["beats_stored_best_0p1843"] is False
    assert h["score"] < h["stored_incumbent_B3_50000"]["score"]
    # Comparator reproduction on identical folds/terms.
    assert abs(h["comparators_same_folds"]["registry_D2.8_44090"]["dti"] - 0.0919) < 5e-4
    assert abs(h["comparators_same_folds"]["registry_H33_37654"]["dti"] - 0.0037) < 5e-4


def test_fw_canary_clean():
    card = load_card()
    assert card["canary"]["flagged_over_0p90"] == {}
    assert max(card["canary"]["symmetric_auc"].values()) <= 0.90


def test_fw_uniqueness_literal_duplicate_informative_unique():
    card = load_card()
    pre = card["registry"]["preplacement_surface"]
    assert len(pre) >= 4  # D2.8, H33, H19-5, dense witness at minimum
    assert all(r["rho"] is None or abs(r["rho"]) <= 0.90 for r in pre)
    binding = card["registry"]["binding_literal_decision"]
    assert binding["binding_rule"] == "literal-all-rasters"
    assert binding["duplicate"] is True
    assert binding["worst_forward_overlap"] == 1.0
    dot_fields = [r for r in card["registry"]["final_dots"] if r["representation"] == "dot_field"]
    assert dot_fields
    assert max(r["forward_3px_overlap"] for r in dot_fields) <= 0.70


def test_fw_tif_bytes_match_card_and_validate():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_tif import verify
    card = load_card()
    tif = ROOT / "docs/downloads" / (card["submission_name"] + ".tif")
    assert tif.exists()
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert digest == card["raster_sha256"]
    report = verify(tif)
    assert report["all_passed"] is True
    assert report["positive_pixels"] == 44090
    assert report["zip"]["single_tif_byte_identical"] is True


def test_fw_builder_finishes_with_release_audit():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_site_fw.py")],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]
    for page in ("h78fw.html", "h78fw-executive-summary.html"):
        text = (ROOT / "docs" / page).read_text()
        assert "OK TO SUBMIT: NO" in text
        assert "OK TO SUBMIT: YES" not in text
    home = (ROOT / "docs/index.html").read_text()
    assert "H78-FW" in home and "h78fw.html" in home


def test_fw_pages_carry_unambiguous_status():
    page = (ROOT / "docs/h78fw.html").read_text()
    assert "OK TO SUBMIT: NO" in page
    assert "verdict" in page and "negative" in page
    card = load_card()
    assert card["submission_name"] in page
    assert card["raster_sha256"] in page
    home = (ROOT / "docs/index.html").read_text()
    assert "H78-FW" in home
    status = json.loads((ROOT / "docs/data/status.json").read_text())
    lanes = [c["lane"] for c in status["candidates"]]
    assert "H78-FW" in lanes
    fw = next(c for c in status["candidates"] if c["lane"] == "H78-FW")
    assert fw["ok_to_submit"] is False and fw["verdict"] == "negative"
