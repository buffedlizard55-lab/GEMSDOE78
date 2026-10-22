"""Protocol proof, publication scope and defensive verifier regression tests."""
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pytest
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import saturation_certificate, compare_array_to_registry


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_tif(path, array, transform=None):
    with rasterio.open(path, "w", driver="GTiff", count=1, width=array.shape[1],
                       height=array.shape[0], dtype="float32", crs="EPSG:32611",
                       transform=transform or rasterio.transform.from_origin(100, 200, 10, 10)) as ds:
        ds.write(array.astype("float32"), 1)


def test_full_support_proof_and_wrong_grid_rejected(tmp_path):
    p = tmp_path / "dense.tif"
    fp = np.ones((10, 11), bool)
    cat = np.zeros_like(fp)
    cat[0, 0] = True
    write_tif(p, np.full(fp.shape, .01))
    with rasterio.open(p) as ds:
        grid = (ds.shape, ds.crs, ds.transform)
    cert = saturation_certificate(p, fp, cat, expected_grid=grid)
    assert cert["uncovered_allowed_pixels"] == 0
    assert cert["allowed_pixels"] == 109
    assert cert["universal_overlap_blocker"]
    with pytest.raises(ValueError, match="CRS/transform"):
        saturation_certificate(p, fp, cat, expected_grid=(grid[0], grid[1], grid[2] * rasterio.Affine.translation(1, 0)))


def test_shared_literal_overlap_does_not_exempt_continuous_surface(tmp_path):
    p = tmp_path / "dense.tif"
    fp = np.ones((10, 11), bool)
    write_tif(p, np.linspace(.01, .8, fp.size).reshape(fp.shape))
    candidate = np.zeros(fp.shape, dtype="float32")
    candidate[5, 5] = 1
    result = compare_array_to_registry(candidate, [dict(file=str(p))], fp)
    assert result["worst_dot_overlap"] == 1
    assert result["stop_required"] and not result["unique"]
    assert result["rows"][0]["spearman_full_footprint"] == pytest.approx(
        spearmanr(candidate.ravel(), np.linspace(.01, .8, fp.size)).statistic)


def test_no_lane_or_unverified_certificate_cannot_start_training():
    preflight = module("preflight")
    assert any("method" in r for r in preflight.blocked_reasons(None, None, []))
    assert any("certificate" in r for r in preflight.blocked_reasons("lane", None, []))
    assert preflight.blocked_reasons("lane", {"universal_overlap_blocker": False}, [])


def test_published_certificate_is_pinned_not_an_organizer_score():
    card = json.loads((ROOT / "evidence/protocol_preflight.json").read_text())
    cert = card["correlation_overlap_vs_registry"]
    assert card["verdict"] == "negative" and card["stop_required"]
    assert not card["training_allowed"] and not card["new_tif_generated"]
    assert card["submission_slots_used"] == card["new_experiments"] == 0
    assert card["holdout"] is None and card["raster_sha256"] is None
    assert cert["universal_overlap_blocker"]
    assert cert["covered_allowed_fraction"] == 1 and cert["uncovered_allowed_pixels"] == 0
    witness = next(e for e in card["verified_inputs"] if e["id"] == "saturation_witness")
    assert witness["sha256"] == cert["witness_sha256"]
    assert len(witness["ref"]) == 40 and len(witness["sha256"]) == 64
    assert card["organizer_confirmed_score"] is None
    assert len(card["submission_note"]) <= 140


def test_all_published_tiffs_in_current_audit():
    card = json.loads((ROOT / "evidence/release_audit.json").read_text())
    files = {p.name for p in (ROOT / "docs/downloads").glob("*.tif")}
    assert {r["file"] for r in card["candidates"]} == files
    for row in card["candidates"]:
        assert row["validator"]["all_passed"] and row["integrity_passed"]
        assert row["final_dots_vs_saturation_witness"]["worst_dot_overlap"] == 1
        assert row["surface_before_placement"] is None  # no manufactured pre-placement evidence
        assert not row["ok_to_submit"]
        sidecar = json.loads((ROOT / "docs/downloads" / Path(row["file"]).with_suffix(".json")).read_text())
        assert not sidecar["promoted"] and not sidecar["approved_for_weekly_slot"]


def test_verifier_returns_structured_failure_for_wrong_shape_and_bad_zip(tmp_path):
    verifier = module("verify_tif")
    p = tmp_path / "wrong.tif"
    write_tif(p, np.zeros((3, 4)))
    report = verifier.verify(p)
    assert not report["all_passed"] and not report["checks"]["shape_3730x3292"]
    p.with_suffix(".zip").write_bytes(b"broken archive")
    report = verifier.verify(p)
    assert not report["all_passed"] and "BadZipFile" in report["error"]
    assert not verifier.verify(tmp_path / "missing.tif")["all_passed"]


def test_zip_must_name_the_single_tiff(tmp_path):
    verifier = module("verify_tif")
    card = json.loads((ROOT / "evidence/release_audit.json").read_text())
    source = ROOT / "docs/downloads" / card["candidates"][0]["file"]
    p = tmp_path / source.name
    p.write_bytes(source.read_bytes())
    with zipfile.ZipFile(p.with_suffix(".zip"), "w") as archive:
        archive.writestr("not-a-tiff.txt", p.read_bytes())
    report = verifier.verify(p)
    assert not report["all_passed"] and not report["zip"]["single_tif_byte_identical"]
