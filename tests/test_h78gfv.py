"""End-to-end automated unit & integration tests for Session-7 lane H78-GFV."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems78 import gfv  # noqa: E402


def test_gfv_source_never_touches_dist_known_fault_px():
    src_text = (ROOT / "src" / "gems78" / "gfv.py").read_text()
    # Must never index a DataFrame/row with the leaked column name
    assert 'row["dist_known_fault_px"]' not in src_text
    assert "row['dist_known_fault_px']" not in src_text
    assert 'df["dist_known_fault_px"]' not in src_text
    assert "df['dist_known_fault_px']" not in src_text


def test_synthetic_anisotropic_fermat_geodesic_bridges_relay_gap():
    H, W = 120, 140
    fp = np.ones((H, W), dtype=bool)
    visible = np.zeros((H, W), dtype=bool)
    # Two collinear horizontal fault segments separated by a 24-px blind relay gap
    visible[60, 15:45] = True
    visible[60, 70:105] = True
    weak = np.full((H, W), 0.15, dtype=np.float32)
    weak[59:62, 40:75] = 0.88  # geophysical basement corridor across relay gap
    strike = np.zeros((H, W), dtype=np.float32)  # horizontal strike (theta = 0)
    hydro_nodes = np.array([30 * (W // 2) + 28, 30 * (W // 2) + 42], dtype=np.int32)

    geo = gfv.compute_geodesic_network(
        visible, weak, strike, fp, hydro_nodes, n_color_rounds=6, seed=42
    )
    assert geo.shape == (len(gfv.GFV_GEO_NAMES), H, W)
    assert geo.dtype == np.float16
    assert np.isfinite(geo).all()

    idx_tpair = gfv.GFV_GEO_NAMES.index("geo_Tpair_sum")
    idx_ridge = gfv.GFV_GEO_NAMES.index("geo_fermat_ridge")
    # Center of collinear geophysical relay gap has far lower Fermat travel sum
    # and higher Fermat ridge score than an off-axis background basin cell!
    assert float(geo[idx_tpair, 60, 57]) < float(geo[idx_tpair, 20, 57])
    assert float(geo[idx_ridge, 60, 57]) > float(geo[idx_ridge, 20, 57])


def test_run_card_and_submission_artifacts_are_complete_and_verified():
    def reject_non_strict(val):
        raise AssertionError(f"Non-strict JSON constant: {val}")

    card = json.loads(
        (ROOT / "evidence" / "run_card_h78_gfv.json").read_text(),
        parse_constant=reject_non_strict,
    )
    required_keys = {
        "hypothesis",
        "mechanism",
        "non_fault_mimic",
        "holdout",
        "correlation_overlap_vs_registry",
        "raster_sha256",
        "validator_output",
        "submission_name",
        "submission_note",
        "verdict",
        "ok_to_download",
        "ok_to_submit",
    }
    assert required_keys.issubset(card.keys())
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["weekly_slots_used_by_agent"] == 0
    assert card["organizer_confirmed_score"] is None
    assert 1 <= len(card["submission_note"]) <= 140

    # Leakage canaries across all 272 checks strictly < 0.90
    can = card["holdout"]["leakage_canaries"]
    assert can["passed"] is True
    assert can["flagged_over_0_90"] == 0
    assert can["max_symmetric_auc_seed20"] < 0.90
    assert can["max_symmetric_auc_seed30"] < 0.90

    # Matched holdout beats repository best CTRL_A2 with positive 95% CIs on BOTH seeds
    m_glob = card["holdout"]["matched_same_split_vs_repo_best_CTRL_A2"]
    for s_key, n_exp in (("seed_20", 11321), ("seed_30", 11342)):
        entry = m_glob[s_key]
        assert entry["withheld_positive_pixels"] == n_exp
        assert entry["candidate_B3_44090"]["dti"] > entry["repo_best_CTRL_A2_B3_44090"]["dti"]
        ci = entry["paired_delta_vs_CTRL_A2"]["ci95"]
        assert ci[0] > 0.02 and ci[1] > ci[0]

    # Registry uniqueness audit check
    uq = card["correlation_overlap_vs_registry"]
    assert uq["surface_spearman_pre_placement"]["max_abs_rho"] <= 0.90
    dot_uq = uq["dot_overlap_audit_full_93_repos"]
    assert dot_uq["discriminating_forward_3px_over_0_70"] == 0
    assert dot_uq["max_forward_3px_vs_736_discriminating"] <= 0.70

    # Verify both submissions/ and docs/downloads/ GeoTIFF + single-TIFF ZIP byte-for-byte
    for rel_key_tif, rel_key_zip in (("raster_file", "zip_file"), ("docs_download_tif", "docs_download_zip")):
        tif_p = ROOT / card[rel_key_tif]
        zip_p = ROOT / card[rel_key_zip]
        assert tif_p.is_file() and zip_p.is_file()
        assert hashlib.sha256(tif_p.read_bytes()).hexdigest() == card["raster_sha256"]
        assert hashlib.sha256(zip_p.read_bytes()).hexdigest() == card["zip_sha256"]

        with rasterio.open(tif_p) as ds:
            arr = ds.read(1)
            assert ds.count == 1
            assert ds.dtypes == ("float32",)
            assert (ds.height, ds.width) == (3730, 3292)
            assert str(ds.crs) == "EPSG:32611"
            assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
            assert ds.nodata is None
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
        assert set(np.unique(arr).tolist()) <= {0.0, 1.0}
        assert int((arr > 0).sum()) == 37654

        with zipfile.ZipFile(zip_p) as zf:
            assert zf.namelist() == [tif_p.name]
            assert zf.read(tif_p.name) == tif_p.read_bytes()

    # Run independent CLI verify_tif.py directly
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_tif.py"), str(ROOT / card["raster_file"])],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert json.loads(res.stdout)["all_passed"] is True

    # Top-of-repo and top-of-site status clarity
    readme = (ROOT / "README.md").read_text()
    assert "OK TO DOWNLOAD: YES" in readme and "OK TO SUBMIT: NO" in readme
    assert card["submission_name"] in readme and card["raster_sha256"] in readme
    for html_name in ("index.html", "executive-summary.html", "h78gfv.html"):
        html = (ROOT / "docs" / html_name).read_text()
        assert "OK TO DOWNLOAD: YES · OK TO SUBMIT: NO" in html
        assert card["submission_name"] in html and card["raster_sha256"] in html
