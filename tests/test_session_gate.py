"""Current session (2026-10-22, H78-STEP): status feed <-> run card <-> homepage banner.

Verdict-agnostic consistency: ok_to_submit must equal the conjunction of the
preregistered gate, the machine-readable status feed must name the same file
and verdict as the run card, and the homepage banner must match. (Replaces
the 2026-10-21 H78-SPY-hardcoded version; that lane's evidence is preserved
in evidence/h78spy_run_card.json and its blocked status on the homepage.)
"""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
STATUS = json.loads((ROOT / "docs" / "data" / "status.json").read_text())
CARD = json.loads((ROOT / "evidence" / "h78step_run_card.json").read_text())
TIF = ROOT / "docs" / "downloads" / STATUS["generated_tif"]


def test_status_feed_matches_run_card():
    gate = CARD["preregistered_gate_evaluation"]
    assert STATUS["generated_tif"] == CARD["raster"]["file"]
    assert STATUS["ok_to_submit"] == CARD["ok_to_submit"] == all(gate.values())
    assert STATUS["verdict"] == CARD["verdict"] == ("promote" if STATUS["ok_to_submit"] else "negative")
    assert STATUS["organizer_confirmed"] is None
    assert STATUS["weekly_slots_used_by_agent"] == 0
    assert STATUS["evidence_class"] == "HOLDOUT-DTI"
    assert STATUS["evaluator"] == "gems57-pooled-hide-v2"
    assert STATUS["withheld_positive_pixels"] == 11321
    assert STATUS["sha256"] == CARD["raster_sha256"]
    assert STATUS["gate"] == gate


def test_homepage_banner_matches_verdict_and_comes_first():
    for name in ("index.html", "executive-summary.html"):
        html = (ROOT / "docs" / name).read_text()
        if CARD["ok_to_submit"]:
            assert "OK TO SUBMIT: YES" in html
            assert html.find("OK TO SUBMIT: YES") < html.find("Download .tif")
        else:
            assert "OK TO SUBMIT: NO" in html
            assert html.find("OK TO SUBMIT: NO") < html.find("Download .tif")
            assert "DO-NOT-SUBMIT" in html
        assert CARD["submission_name"] in html and CARD["raster_sha256"] in html


def test_tif_is_portal_safe_and_gate_consistent():
    assert hashlib.sha256(TIF.read_bytes()).hexdigest() == CARD["raster_sha256"]
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes == ("float32",)
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
    assert np.isfinite(a).all()
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    assert set(np.unique(a).tolist()) <= {0.0, 1.0}
    assert int((a > 0).sum()) == 44090
    zpath = TIF.with_suffix(".zip")
    with zipfile.ZipFile(zpath) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()
    note = CARD["submission_note"]
    assert len(note) <= 140 and CARD["note_chars"] == len(note)
    if not CARD["ok_to_submit"]:
        assert "do-not-submit" in note
        assert "DO-NOT-SUBMIT" in TIF.name
