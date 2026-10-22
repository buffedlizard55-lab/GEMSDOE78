"""Unit tests for C emission accelerators, 300 m submodular DTI exactness,
IR-78-BAND6-01 band naming, zero-SGMC self-steered physics features,
paired facing-tip structural relay bridges, and H78-GSC GeoTIFF/ZIP validation."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import metric as M
from gems78 import data as D, emit as E, features as F, gsc


def test_band6_fixed_name():
    assert D.BAND_NAMES[5] == "tc", "IR-78-BAND6-01 regression: band 5 (1-based band 6) must be 'tc' (magnetic tilt/curvature)"
    assert len(D.BAND_NAMES) == 19
    assert F.STEER_BANDS[-1] == "tc"


def test_fast_greedy_dots_matches_python_bit_for_bit():
    rng = np.random.default_rng(78)
    score = rng.random((64, 72), dtype=np.float32)
    allowed = rng.random((64, 72)) > 0.25
    rk_c = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=120)
    rk_py = E.greedy_dots_py(score, allowed, min_dist=2.8, max_dots=120)
    np.testing.assert_array_equal(rk_c, rk_py)


def test_submodular_dti_dots_exact_expected_tpw_sum():
    rng = np.random.default_rng(2026)
    prob = (rng.random((48, 56)) ** 3).astype(np.float32)
    allowed = np.ones((48, 56), dtype=bool)
    allowed[:3, :] = False
    rk, gains = E.submodular_dti_dots(prob, allowed, min_dist=2.5, max_dots=35, radius_px=3.0)
    dots = E.prefix(rk, 35)
    assert int(dots.sum()) == 35
    assert np.all(np.diff(gains) <= 1e-9), "Submodular marginal gains must be monotonically non-increasing"
    from scipy.ndimage import distance_transform_edt
    k_map = M.kernel(distance_transform_edt(~dots), radius=3.0)
    expected_tpw = float((prob.astype(np.float64) * k_map).sum())
    assert abs(float(gains.sum()) - expected_tpw) < 1e-5


def test_fold_structural_features_18_columns_and_facing_bridge_geometry():
    H, W = 96, 96
    fp = np.ones((H, W), dtype=bool)
    fp[:2, :] = False
    # Two collinear facing N-S fault tips separated across row 36..58 at col 48!
    vis = np.zeros((H, W), dtype=bool)
    vis[12:36, 48] = True
    vis[58:82, 48] = True
    rng = np.random.default_rng(7801)
    aux = {
        "unified_scarp": np.full((H, W), 0.5, dtype=np.float32),
        "piedmont_zone": np.ones((H, W), dtype=np.float32),
        "hslin": rng.random((H, W), dtype=np.float32),
        "grav_hg": rng.random((H, W), dtype=np.float32),
        "grad_base": rng.random((H, W), dtype=np.float32),
        "phi_phys": np.zeros((H, W), dtype=np.float32),
        "coh_phys": np.full((H, W), 0.8, dtype=np.float32),
    }
    mat, names = gsc.compute_fold_structural_features(vis, fp, aux)
    assert mat.dtype == np.float16
    assert mat.shape == (int(fp.sum()), 18)
    assert len(names) == 18
    assert np.isfinite(mat).all()

    # Check that facing-tip bridge at gap midpoint (47, 48) substantially exceeds off-axis (47, 12)!
    idx_grid = np.full((H, W), -1, dtype=np.int64)
    idx_grid[fp] = np.arange(int(fp.sum()))
    col_b = [i for i, nm in enumerate(names) if "relay_bridge" in nm or "coulomb_beam_relay" in nm][0]
    assert float(mat[idx_grid[47, 48], col_b]) > 5.0 * float(mat[idx_grid[47, 12], col_b])

    pmat, pnames = gsc.compute_pure_phys_steered_features(fp, aux)
    assert pmat.dtype == np.float32
    assert pmat.shape == (int(fp.sum()), 8)
    assert len(pnames) == 8
    assert np.isfinite(pmat).all()


def test_h78_gsc_submission_tif_and_zip_verified():
    tif = ROOT / "docs" / "downloads" / "gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.tif"
    zf = ROOT / "docs" / "downloads" / "gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.zip"
    assert tif.is_file() and zf.is_file()
    out = subprocess.check_output([sys.executable, str(ROOT / "scripts" / "verify_tif.py"), str(tif)], text=True)
    import json
    from gems57 import grid as G, validate as V
    g_chk = G.load_grid(ROOT / ".cache" / "gems_data")
    V.assert_submittable(V.validate(tif, g_chk.footprint, g_chk.catalogue))
    res = json.loads(out)
    assert res["all_passed"] is True
    assert res["positive_pixels"] == 40000
    assert res["checks"]["values_in_[0,1]"] is True
    assert res["checks"]["zero_on_catalogue"] is True
    assert res["zip"]["single_tif_byte_identical"] is True
    h = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert h == res["sha256"]


def test_run_card_and_github_pages_zero_broken_links():
    import json, re
    rc = json.loads((ROOT / "run_card.json").read_text())
    assert rc["lane"] == "H78-GSC"
    assert rc["verdict"] == "promote"
    assert rc["ok_to_download"] is True and rc["ok_to_submit"] is True
    assert len(rc["submission_name"]) <= 140
    assert len(rc["submission_note"]) <= 140
    assert rc["leakage_canary"]["passed"] is True and rc["leakage_canary"]["max_symmetric_auc"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["preplacement_max_abs_spearman_rho"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["worst_mutual_3px_overlap_across_all_1049_rasters"] <= 0.70
    assert rc["holdout"]["seed20_strict_loqo_primary"]["E3_MFNC_Bridge_PU_cal_LOQO__submod300_38000"]["dti"] > 0.18257

    docs_dir = ROOT / "docs"
    for page in ["index.html", "executive-summary.html", "methodology.html", "validation.html", "submission.html", "irregularities.html", "sources.html"]:
        p = docs_dir / page
        assert p.is_file(), f"Missing page {page}"
        txt = p.read_text()
        assert "OK TO DOWNLOAD AND SUBMIT" in txt
        for attr in re.findall(r'(?:href|src)="([^"]+)"', txt):
            if attr.startswith(("http://", "https://", "#", "javascript:", "mailto:")):
                continue
            target = (docs_dir / attr.split("#")[0]).resolve()
            assert target.exists(), f"Broken relative link in {page}: {attr} -> {target}"

