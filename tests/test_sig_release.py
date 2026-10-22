"""H78-SIGX release integrity: the one cleared file is hash-bound to its
independent gate report and run card, and is portal-safe."""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/h78sig_run_card.json").read_text())
GATE = json.loads((ROOT / "evidence/h78sig_gate_report.json").read_text())
TIF = ROOT / "docs/downloads" / GATE["file"]


def test_tif_hash_bound_everywhere():
    digest = hashlib.sha256(TIF.read_bytes()).hexdigest()
    assert digest == CARD["raster_sha256"] == GATE["G1_format"]["verify_tif"]["sha256"]
    assert CARD["submission_name"] == TIF.stem
    assert len(CARD["submission_note"]) <= 140


def test_gates_all_pass_and_verdict():
    assert GATE["all_gates_passed"] and GATE["ok_to_submit"]
    assert CARD["verdict"] == "promote-to-selector" and CARD["ok_to_submit"] is True
    assert CARD["organizer_confirmed_score"] is None
    assert CARD["gates"] == {k: True for k in
                             ("G1_format", "G2_canary", "G3_holdout", "G4_uniqueness", "G5_emission")}


def test_holdout_numbers_are_labelled_and_consistent():
    h = CARD["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["withheld_positive_pixels"] == 11321
    # far-field win, overall tie — both statements must stay in the card
    assert h["beats_current_holdout_best_far_gt10px"] is True
    assert h["beats_current_holdout_best_overall"] is False
    assert h["far_gt10px"]["dti"] > h["overall"]["dti"] * 0  # present
    assert h["paired_vs_CTRL_A2_B5_far_gt10px"]["ci95"][0] > 0


def test_tif_is_portal_safe_binary_dots():
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes == ("float32",)
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
    assert np.isfinite(a).all()
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    assert set(np.unique(a).tolist()) <= {0.0, 1.0}
    assert int((a > 0).sum()) == 44_090
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        cat = ds.read(1) > 0
    assert not (a[cat] > 0).any()
    with zipfile.ZipFile(TIF.with_suffix(".zip")) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()


def test_uniqueness_margins_disclosed():
    u = GATE["G4_uniqueness"]
    assert u["worst_abs_surface_spearman"] < 0.90
    assert all(v["passed"] for v in u["dots_vs_registry"].values())
    # literal reading must remain visible, including the space-filling firings
    assert u["worst_literal_forward_overlap_3px"] == 1.0
    kinds = {v["kind"] for v in u["dots_vs_registry"].values()}
    assert kinds == {"discriminating", "space_filling"}
