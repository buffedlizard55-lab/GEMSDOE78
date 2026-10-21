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

def test_historical_run_card_preserved_and_labeled():
    rc = json.loads((ROOT / "evidence" / "h78mpc_run_card.json").read_text())
    assert rc["verdict"] == "promote"
    assert rc["ok_to_download"] is True and rc["ok_to_submit"] is True
    assert all(rc["preregistered_gate_evaluation"].values())
    assert rc["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert rc["holdout"]["withheld_positive_pixels"] == 11321
    assert len(rc["submission_note"]) <= 140
    assert rc["raster_sha256"] == PROD["sha256"]
    assert rc["validator_output"]["all_checks_passed"] is True
    # both emission readings retained (IR-78-EMIT-01 disclosure)
    cl = rc["holdout"]["pass1_preregistered_emitter_reading_IR-78-EMIT-01"]["scores_clustered"]
    assert cl["E2_MPC"]["dti"] < rc["holdout"]["candidate_E2_MPC_SPACED"]["dti"]
    assert rc["correlation_overlap_vs_registry"]["final_dots_worst_mutual_3px_informative"] <= 0.70

def test_dot_spacing_kernel_packed():
    from scipy.spatial import cKDTree
    with rasterio.open(TIF) as s:
        a = s.read(1)
    ys, xs = np.nonzero(a > 0)
    d, _ = cKDTree(np.c_[ys, xs].astype(float)).query(np.c_[ys, xs].astype(float), k=2)
    assert float((d[:, 1] <= 1.5).mean()) == 0.0  # no contiguous runs (IR-78-EMIT-01)

def test_site_blocks_submission_and_links_audit():
    html = (ROOT / "docs" / "h78mpc.html").read_text()
    assert "OK TO DOWNLOAD: YES · OK TO SUBMIT: NO" in html
    assert "data/release_audit.json" in html
    assert PROD["final_stem"] in html
    release = json.loads((ROOT / "evidence/release_audit.json").read_text())
    assert release["verdict"] == "negative" and release["stop_required"]
    assert not any(c["ok_to_submit"] for c in release["candidates"])
