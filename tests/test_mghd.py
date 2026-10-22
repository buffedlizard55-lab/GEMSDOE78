"""Comprehensive regression, mathematical property, and release tests for Session-5 Lane H78-MGHD."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import uniqueness as U
from gems78 import mghd


def _strict_load(rel: str) -> dict:
    def reject_nonfinite(val: str):
        raise AssertionError(f"Non-strict JSON token encountered in {rel}: {val}")

    return json.loads((ROOT / rel).read_text(), parse_constant=reject_nonfinite)


def test_separable_near_matches_scipy_binary_dilation_exact():
    rng = np.random.default_rng(20261022)
    for r in (1.0, 1.5, 2.0, 2.8, 3.0, 3.5):
        rr = int(np.ceil(r))
        yy, xx = np.mgrid[-rr : rr + 1, -rr : rr + 1]
        selem = (yy * yy + xx * xx) <= r * r
        mask = rng.random((43, 51)) > 0.96
        np.testing.assert_array_equal(U._near(mask, r), binary_dilation(mask, structure=selem))


def test_vendor_uniqueness_rows_feed_binding_decision_directly(tmp_path):
    """Regression test for IR-78-VENDOR-UNIQ-01 & IR-78-VENDOR-UNIQ-02."""
    fp = np.ones((12, 14), dtype=bool)
    dense = np.linspace(0.05, 0.95, fp.size, dtype=np.float32).reshape(fp.shape)
    p_dense = tmp_path / "dense_prior.tif"
    with rasterio.open(
        p_dense,
        "w",
        driver="GTiff",
        count=1,
        height=fp.shape[0],
        width=fp.shape[1],
        dtype="float32",
        crs="EPSG:32611",
        transform=rasterio.transform.from_origin(100, 200, 100, 100),
    ) as ds:
        ds.write(dense, 1)

    cand = np.zeros(fp.shape, dtype=np.float32)
    cand[4, 5] = 1.0
    audit = U.compare_array_to_registry(cand, [{"file": str(p_dense)}], fp)
    decision = U.binding_duplicate_decision(audit["rows"])
    assert decision["duplicate"] is True
    assert decision["stop_required"] is True
    assert decision["verdict"] == "negative"
    assert decision["worst_forward_overlap"] == pytest.approx(1.0)

    anti = (1.0 - dense).astype(np.float32)
    surf_audit = U.compare_array_to_registry(anti, [{"file": str(p_dense)}], fp)
    assert surf_audit["rows"][0]["spearman_full_footprint"] == pytest.approx(-1.0)
    assert surf_audit["rows"][0]["duplicate_by_rho"] is True
    assert surf_audit["stop_required"] is True


def test_submodular_minoux_heap_equals_bruteforce_greedy_exact():
    """Verify Minoux lazy heap returns the exact same ranked dots as brute-force greedy cover."""
    rng = np.random.default_rng(78)
    H, W = 28, 32
    p = rng.uniform(0.0, 0.5, size=(H, W)).astype(np.float32)
    q = rng.uniform(0.0, 0.8, size=(H, W)).astype(np.float32)
    allowed = rng.random((H, W)) > 0.15
    lam = 0.25
    min_dist = 2.2
    budget = 18

    rank_fast = mghd.submodular_kernel_dots(
        p, q, allowed, max_dots=budget, min_dist=min_dist, dinkelbach_lambda=lam, pool_size=10_000
    )

    mass = (np.float32(0.65) * p + np.float32(0.35) * (q**2)).astype(np.float32)
    pad = 3
    mass_p = np.pad(mass, pad, mode="constant", constant_values=0.0)
    cov_p = np.zeros_like(mass_p, dtype=np.float32)
    blocked = ~allowed.copy()
    c_cov = 1.0 - mghd.ALPHA * lam
    c_fp = mghd.ALPHA * lam

    r_excl = int(np.floor(min_dist))
    yy_e, xx_e = np.mgrid[-r_excl : r_excl + 1, -r_excl : r_excl + 1]
    m_excl = (yy_e * yy_e + xx_e * xx_e) <= min_dist * min_dist
    edy, edx = yy_e[m_excl], xx_e[m_excl]

    rank_brute = np.zeros((H, W), dtype=np.int32)
    for step in range(1, budget + 1):
        best_key = None
        best_yx = None
        for y in range(H):
            for x in range(W):
                if blocked[y, x]:
                    continue
                gain = 0.0
                for dy, dx, kw in zip(mghd.OFF_DY, mghd.OFF_DX, mghd.OFF_K):
                    diff = kw - cov_p[y + pad + int(dy), x + pad + int(dx)]
                    if diff > 0.0:
                        gain += float(mass_p[y + pad + int(dy), x + pad + int(dx)]) * float(diff)
                u = c_cov * gain - c_fp * (1.0 - float(q[y, x]))
                cand_key = (-u, y * W + x)
                if best_key is None or cand_key < best_key:
                    best_key = cand_key
                    best_yx = (y, x)
        if best_yx is None:
            break
        by, bx = best_yx
        rank_brute[by, bx] = step
        for dy, dx, kw in zip(mghd.OFF_DY, mghd.OFF_DX, mghd.OFF_K):
            cov_p[by + pad + int(dy), bx + pad + int(dx)] = max(
                cov_p[by + pad + int(dy), bx + pad + int(dx)], float(kw)
            )
        for dy, dx in zip(edy, edx):
            ny, nx = by + int(dy), bx + int(dx)
            if 0 <= ny < H and 0 <= nx < W:
                blocked[ny, nx] = True

    np.testing.assert_array_equal(rank_fast, rank_brute)


def test_forbidden_fault_columns_stripped_by_csv_guard(tmp_path):
    csv_p = tmp_path / "vents.csv"
    csv_p.write_text("lat,lon,temp_c,dist_known_fault_m,QFault_ID\n39.5,-118.2,84.0,12.0,F99\n")
    rows = mghd._read_csv_safe(csv_p)
    assert len(rows) == 1
    assert set(rows[0].keys()) == {"lat", "lon", "temp_c"}


def test_h78mghd_evidence_bundle_and_pages_complete():
    rc = _strict_load("evidence/h78mghd_run_card.json")
    rc_root = _strict_load("run_card_h78mghd.json")
    rc_docs = _strict_load("docs/data/h78mghd_run_card.json")
    s20 = _strict_load("evidence/h78mghd_holdout_seed20.json")
    s30 = _strict_load("evidence/h78mghd_holdout_seed30.json")
    uniq = _strict_load("evidence/h78mghd_uniqueness_summary.json")
    tmpl = _strict_load("registry/shared_template_review_2026-10-22.json")

    assert rc == rc_root == rc_docs
    assert rc["experiments_used"] <= 3
    assert rc["leakage_canary_summary"]["all_passed"] is True
    assert rc["leakage_canary_summary"]["max_symmetric_auc"] <= 0.90
    assert rc["organizer_confirmed_score"] is None
    assert rc["weekly_slots_used_by_agent"] == 0
    assert rc["ok_to_download"] is True and rc["ok_to_submit"] is False
    assert rc["verdict"] == "negative"

    assert s20["withheld_positive_pixels"] == 11321
    assert s30["withheld_positive_pixels"] == 11342 and s30["zero_retuning_enforced"] is True
    assert rc["holdout"]["experiment_E2_selected_arm_seed20_44090"]["paired_delta_cand_minus_ctrl"]["ci95"][0] > 0.0
    assert rc["holdout"]["experiment_E3_seed30_zero_retune_44090"]["paired_delta_cand_minus_ctrl"]["ci95"][0] > 0.0
    assert rc["holdout"]["pooled_two_seed_44090"]["paired_delta_cand_minus_ctrl"]["ci95"][0] > 0.0

    assert uniq["accessible_sibling_repo_count"] == 84
    assert uniq["registry_total_rasters_compared"] >= 1103
    assert uniq["preplacement_surface_gate"]["passed"] is True
    assert uniq["final_dots_sparse_dot_submissions_le_65k"]["passed_within_sparse_regime"] is True
    assert uniq["final_dots_binding_literal_audit"]["stop_required"] is True
    assert uniq["merged_local_downloads_audit"]["vs_h78_gsc_forward_3px"] <= 0.70

    assert tmpl["private_fork_created"] is False
    assert tmpl["evaluator_modified"] is False
    assert tmpl["submission_writer_modified"] is False

    tif = ROOT / "docs" / "downloads" / rc["submission_file"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == rc["raster_sha256"]

    docs_dir = ROOT / "docs"
    for page_name in ("h78mghd.html", "h78mghd-executive-summary.html"):
        p = docs_dir / page_name
        assert p.exists()
        txt = p.read_text()
        assert "OK TO DOWNLOAD: YES · OK TO SUBMIT: NO" in txt
        for attr in re.findall(r'(?:href|src)="([^"]+)"', txt):
            if attr.startswith(("http://", "https://", "#", "javascript:", "mailto:")):
                continue
            target = (docs_dir / attr.split("#")[0]).resolve()
            assert target.exists(), f"Broken link in {page_name}: {attr} -> {target}"
