"""H78-STEP lane: run card, TIF and pages must all fail closed (negative)."""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence" / "h78stepflank_run_card.json").read_text())
TIF = ROOT / "docs" / "downloads" / CARD["raster"]["file"]


def test_step_card_is_negative_and_gate_failed():
    assert CARD["ok_to_submit"] is False and CARD["verdict"] == "negative"
    assert CARD["organizer_confirmed_score"] is None
    g = CARD["preregistered_gate_evaluation"]
    assert g["cand_beats_ctrl_point"] is False
    assert g["paired_delta_ci_lower_gt_0"] is False
    assert CARD["holdout"]["candidate"]["dti"] < CARD["holdout"]["control"]["dti"]
    assert CARD["holdout"]["paired_delta_cand_minus_ctrl"]["ci95"][1] < 0
    assert CARD["correlation_overlap_vs_registry"]["dots_max_forward_overlap"] > 0.70
    assert CARD["correlation_overlap_vs_registry"]["complete_registry_verified"] is False
    assert len(CARD["submission_note"]) <= 140
    assert CARD["submission_note"].startswith("NOT OK TO SUBMIT")
    assert "DO-NOT-SUBMIT" in CARD["raster"]["file"]


def test_step_tif_is_portal_safe():
    assert CARD["raster_sha256"] == hashlib.sha256(TIF.read_bytes()).hexdigest()
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes == ("float32",)
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
    assert np.isfinite(a).all()
    assert set(np.unique(a).tolist()) <= {0.0, 1.0}
    assert int((a > 0).sum()) == 44090
    with zipfile.ZipFile(TIF.with_suffix(".zip")) as z:
        assert z.namelist() == [TIF.name] and z.read(TIF.name) == TIF.read_bytes()


def test_step_pages_banner_no():
    for name in ("h78stepflank.html", "h78stepflank-executive-summary.html"):
        text = (ROOT / "docs" / name).read_text()
        assert "OK TO SUBMIT: NO" in text
    release = json.loads((ROOT / "evidence" / "release_audit.json").read_text())
    row = next(c for c in release["candidates"] if c["lane"] == "H78-STEP-FLANK")
    assert row["ok_to_submit"] is False and row["verdict"] == "negative"
    assert row["sha256"] == CARD["raster_sha256"]
