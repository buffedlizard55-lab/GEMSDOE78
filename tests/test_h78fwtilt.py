"""End-to-end regression and contract tests for lane H78-FW (Session 5, 2026-10-22)."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_strict_json(path: Path):
    def _reject(val):
        raise ValueError(f"Non-standard JSON constant {val} in {path}")
    return json.loads(path.read_text(), parse_constant=_reject)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_h78fw_run_card_and_holdout_strict_json():
    rc_path = ROOT / "evidence" / "h78fwtilt_run_card.json"
    hold_path = ROOT / "evidence" / "h78fwtilt_holdout_seed20.json"
    rc = load_strict_json(rc_path)
    hold = load_strict_json(hold_path)

    for mirror in (
        ROOT / "run_card_h78fwtilt.json",
        ROOT / "docs" / "data" / "h78fwtilt_run_card.json",
        ROOT / "docs" / "downloads" / "run_card_h78fwtilt.json",
    ):
        assert mirror.exists(), f"Missing run card mirror: {mirror}"
        assert mirror.read_text() == rc_path.read_text()

    assert rc["verdict"] == "negative"
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is False
    assert rc["weekly_slots_used"] == 0
    assert rc["organizer_confirmed_score"] is None
    assert 0 < len(rc["submission_note"]) == rc["note_chars"] <= 140

    # Verify nearest-exact-mask-v2 stack and CTRL_A2 reproduction
    assert rc["stack_cache_meta"]["fill_algorithm"] == "nearest-exact-mask-v2"
    assert rc["stack_cache_meta"]["stack_sha256"] == "d7f091e732b8103e34e9f9e75fb57d2338edefdc2309a19690d333f8fad98f96"
    assert rc["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert rc["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert rc["holdout"]["withheld_positive_pixels"] == 11321
    assert rc["holdout"]["ctrl_a2"]["dti"] == pytest.approx(0.18258300140522551, abs=1e-6)
    assert rc["holdout"]["candidate"]["dti"] == pytest.approx(0.14808546356533536, abs=1e-6)
    assert rc["holdout"]["far_truth_gt10px"]["cand_dti"] > rc["holdout"]["far_truth_gt10px"]["ctrl_a0_dti"]

    # Leakage canary clean
    assert rc["canary"]["clean"] is True
    assert rc["canary"]["max_single_feature_auc_fw_67"] <= 0.90
    assert rc["canary"]["max_single_feature_auc_all_170"] <= 0.90
    assert len(hold["canary"]["fw_features"]) == 67

    # Uniqueness vs 10 discriminating comparators passes; literal all-rasters fails due to space-filling witnesses
    uq = rc["correlation_overlap_vs_registry"]
    assert uq["surface_max_abs_rho"] <= 0.90
    assert uq["discriminating_dot_fields"]["comparators"] == 10
    assert uq["discriminating_dot_fields"]["max_forward_3px_overlap"] <= 0.70
    assert uq["discriminating_dot_fields"]["passed"] is True
    assert uq["literal_all_rasters"]["comparators"] == 12
    assert uq["literal_all_rasters"]["passed"] is False
    assert uq["passed"] is False


def test_h78fw_tif_zip_and_verifier():
    rc = load_strict_json(ROOT / "evidence" / "h78fwtilt_run_card.json")
    tif = ROOT / "docs" / "downloads" / rc["raster"]["file"]
    zip_path = ROOT / "docs" / "downloads" / rc["raster"]["zip"]
    sidecar_path = tif.with_suffix(".json")

    assert tif.exists() and zip_path.exists() and sidecar_path.exists()
    assert sha256_file(tif) == rc["raster_sha256"] == rc["raster"]["sha256"]
    assert sha256_file(zip_path) == rc["raster"]["zip_sha256"]

    sidecar = load_strict_json(sidecar_path)
    assert sidecar["sha256"] == rc["raster_sha256"]
    assert sidecar["promoted"] is False
    assert sidecar["approved_for_weekly_slot"] is False

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_tif.py"), str(tif)],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(proc.stdout)
    assert report["all_passed"] is True
    assert report["positive_pixels"] == 44090
    assert all(report["checks"].values())


def test_h78fw_pages_and_links():
    class LinkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            for attr in ("href", "src"):
                if attr in d:
                    self.links.append(d[attr])

    for page_name in ("h78fwtilt.html", "h78fwtilt-executive-summary.html", "index.html", "executive-summary.html"):
        page = ROOT / "docs" / page_name
        assert page.exists()
        text = page.read_text()
        assert "OK TO DOWNLOAD: YES" in text
        assert "OK TO SUBMIT: NO" in text
        parser = LinkParser()
        parser.feed(text)
        for link in parser.links:
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (page.parent / link.split("#")[0]).resolve()
            assert target.exists(), f"Broken link {link} in {page_name} -> {target}"


def test_h78fw_hypotheses_report():
    doc = (ROOT / "research" / "h78fwtilt_hypotheses.md").read_text()
    for token in (
        "0.2778",
        "0.4413",
        "0.3195",
        "37,654",
        "44,090",
        "6,436",
        "H78-FW",
        "H78-DRN",
        "H78-TER",
        "H78-MCR",
        "nearest-exact-mask-v2",
        "0.182583",
        "0.148085",
        "0.6542",
    ):
        assert token in doc, f"Missing {token} in research/h78fwtilt_hypotheses.md"
