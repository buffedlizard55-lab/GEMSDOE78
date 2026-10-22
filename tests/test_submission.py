"""Fail-closed checks on the published inspection TIF + metric/vendor sanity."""
import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import metric  # noqa

DL = ROOT / "docs" / "downloads"
PROD = json.loads((ROOT / "evidence" / "h78mpc_production.json").read_text())
TIF = DL / f"{PROD['final_stem']}.tif"
ZIP = DL / f"{PROD['final_stem']}.zip"

def test_metric_bruteforce_agrees():
    rng = np.random.default_rng(78)
    g = rng.random((60, 70)) > 0.98
    p = (rng.random((60, 70)) > 0.97).astype(np.float32)
    exact = metric.dti_exact(p, g)["dti"]
    brute = metric.dti_bruteforce(p, g)["dti"]
    assert abs(exact - brute) < 1e-9

def test_marginal_bar():
    # at DTI 0.2778 the textbook bar is 0.2*0.2778 = 0.05556
    assert abs(metric.marginal_inclusion_threshold(0.2778) - 0.05556) < 1e-9

def test_tif_format_portal_safe():
    with rasterio.open(TIF) as s:
        a = s.read(1)
        assert s.count == 1 and s.dtypes == ("float32",)
        assert (s.height, s.width) == (3730, 3292)
        assert str(s.crs) == "EPSG:32611"
        assert tuple(s.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert s.nodata is None
    assert np.isfinite(a).all()                      # the [0,1] portal error cannot fire
    assert a.min() >= 0.0 and a.max() <= 1.0
    assert set(np.unique(a)) <= {0.0, 1.0}
    assert int((a > 0).sum()) == 37654

def test_tif_sha_and_zip():
    h = hashlib.sha256(TIF.read_bytes()).hexdigest()
    assert h == PROD["sha256"]
    with zipfile.ZipFile(ZIP) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()

def test_zero_dots_on_catalogue():
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as s:
        cat = s.read(1) == 1
    with rasterio.open(TIF) as s:
        a = s.read(1)
    assert int(((a > 0) & cat).sum()) == 0

def test_run_card_negative_duplicate_stop_and_labeled():
    rc = json.loads((ROOT / "evidence" / "h78mpc_run_card.json").read_text())
    assert rc["verdict"] == "negative"
    assert rc["ok_to_download"] is True and rc["ok_to_submit"] is False
    assert rc["download_purpose"].startswith("Research / education only")
    assert rc["original_preregistered_gate_passed"] is True
    assert all(rc["preregistered_gate_evaluation"].values())  # historical gate, preserved as originally preregistered
    gates = rc["strict_eligibility_gate_evaluation"]
    assert gates["E2_gt_E1_paired_ci_lower_gt_0"] is True
    assert gates["E2_beats_h33_control_paired_ci_lower_gt_0"] is False
    assert gates["E2_gt_current_repo_best_holdout_point_estimate"] is False
    assert gates["forward_3px_overlap_le_0.70_informative_registry"] is False
    assert gates["forward_3px_overlap_le_0.70_all_registry_rasters"] is False
    assert gates["validator_all_passed"] is True
    assert rc["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert rc["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert rc["holdout"]["seed"] == 20
    assert rc["holdout"]["withheld_positive_pixels"] == 11321
    assert rc["current_repo_best_holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert rc["current_repo_best_holdout"]["seed"] == rc["holdout"]["seed"]
    assert rc["current_repo_best_holdout"]["dti"] > rc["holdout"]["candidate_E2_MPC_SPACED"]["dti"]
    assert len(rc["submission_note"]) <= 140
    assert rc["raster_sha256"] == PROD["sha256"]
    assert rc["validator_output"]["all_checks_passed"] is True
    assert rc["correlation_overlap_vs_registry"]["strict_protocol_gate_passed"] is False
    assert rc["correlation_overlap_vs_registry"]["final_dots_worst_forward_3px_informative"] > 0.70
    assert rc["weekly_slots_used_by_agent"] == 0
    assert json.loads((ROOT / "evidence/h78mpc_duplicate_stop.json").read_text())["status"] == "duplicate-stop"
    # both emission readings retained (IR-78-EMIT-01 disclosure)
    cl = rc["holdout"]["pass1_preregistered_emitter_reading_IR-78-EMIT-01"]["scores_clustered"]
    assert cl["E2_MPC"]["dti"] < rc["holdout"]["candidate_E2_MPC_SPACED"]["dti"]

def test_literal_forward_overlap_is_binding():
    audit = json.loads((ROOT / "evidence/h78mpc_uniqueness.json").read_text())
    strict = audit["strict_protocol"]
    assert strict["max_abs_spearman_pass"] is True
    assert strict["informative_forward_overlap_pass"] is False
    assert strict["literal_all_rasters_forward_overlap_pass"] is False
    assert strict["unique"] is False
    assert audit["worst_forward_informative"] == pytest.approx(0.73)
    assert audit["worst_forward_literal_all_rasters"] == pytest.approx(0.9914)
    prod = json.loads((ROOT / "evidence/h78mpc_production.json").read_text())
    assert prod["unique"] is False and prod["eligible_to_submit"] is False

def test_dot_spacing_kernel_packed():
    from scipy.spatial import cKDTree
    with rasterio.open(TIF) as s:
        a = s.read(1)
    ys, xs = np.nonzero(a > 0)
    d, _ = cKDTree(np.c_[ys, xs].astype(float)).query(np.c_[ys, xs].astype(float), k=2)
    assert float((d[:, 1] <= 1.5).mean()) == 0.0  # no contiguous runs (IR-78-EMIT-01)

def test_prior_root_candidate_fails_closed_until_full_registry_audit():
    review = json.loads((ROOT / "evidence/h78a_current_review.json").read_text())
    release = json.loads((ROOT / "evidence/release_audit.json").read_text())
    assert review["historical_run_card_verdict"] == "promote"
    assert review["current_prompt_status"] == "not-cleared"
    assert review["duplicate_claim"] is False
    home = (ROOT / "docs/index.html").read_text()
    summary = (ROOT / "docs/executive-summary.html").read_text()
    root_candidate = next(c for c in release["candidates"] if c["lane"] == "H78-A")
    # Since the H78-SIGX session (2026-10-22) the banner clears exactly one
    # named file under gates G1-G5; H78-A itself remains not cleared.
    assert "OK TO DOWNLOAD: YES · OK TO SUBMIT: YES — exactly one file:" in home
    assert "h78sigx-fuse-b5-44090dots" in home and "h78sigx-fuse-b5-44090dots" in summary
    oks = [c for c in release["candidates"] if c["ok_to_submit"]]
    assert [c["lane"] for c in oks] == ["H78-SIGX"]
    assert root_candidate["ok_to_submit"] is False
    assert "INCOMPLETE" in root_candidate["reason"]
    assert "not a measured duplicate finding" in root_candidate["reason"]
    assert "H19-5, D2.8, and H33 lineage rasters" in review["prior_uniqueness_scope"]
    assert "INCOMPLETE" in home

def test_site_says_research_only_and_links_release_audit():
    html = (ROOT / "docs" / "h78mpc.html").read_text()
    # The audit page now clears exactly one H78-SIGX file; the MPC row itself
    # remains DUPLICATE / do not submit.
    assert "OK TO DOWNLOAD: YES · OK TO SUBMIT: YES — exactly one file:" in html
    assert "data/release_audit.json" in html
    assert "DUPLICATE" in html and "do not submit" in html
    assert PROD["final_stem"] in html
    release = json.loads((ROOT / "evidence/release_audit.json").read_text())
    assert release["submission_name"] == PROD["name"]
    assert release["submission_note"].startswith("DO NOT SUBMIT")
    assert len(release["submission_note"]) <= 140
    summary = (ROOT / "docs" / "h78mpc-executive-summary.html").read_text()
    assert "h78sigx-fuse-b5-44090dots" in summary and "do not submit" in summary
