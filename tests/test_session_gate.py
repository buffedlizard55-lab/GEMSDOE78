"""Current session (H78-STEP): generated file is format-valid and must not be submittable."""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
STATUS = json.loads((ROOT / "docs" / "data" / "status.json").read_text())
TIF = ROOT / "docs" / "downloads" / STATUS["generated_tif"]
CARD = json.loads((ROOT / "evidence" / "h78step_run_card.json").read_text())


def test_status_feed_says_do_not_submit():
    assert STATUS["ok_to_submit"] is False
    assert STATUS["verdict"] == "negative"
    assert STATUS["organizer_confirmed"] is None
    assert STATUS["weekly_slots_used_by_agent"] == 0
    # the literal duplicate rule fired on final dots vs shipped H78-A lineage
    assert STATUS["forward_3px_overlap_h78a"] > 0.70
    assert STATUS["forward_3px_overlap_max"] > 0.70
    # and the holdout gate failed with a paired CI excluding 0 on the negative side
    assert STATUS["holdout_dti"] < STATUS["control_dti"]
    assert STATUS["paired_delta_ci95"][1] < 0


def test_homepage_banner_is_no_and_comes_first():
    html = (ROOT / "docs" / "index.html").read_text()
    assert "OK TO SUBMIT: NO" in html
    assert "OK TO SUBMIT: YES" not in html
    assert "DO-NOT-SUBMIT" in html
    lane = (ROOT / "docs" / "h78step.html").read_text()
    assert "OK TO SUBMIT: NO" in lane
    assert lane.find("OK TO SUBMIT: NO") < lane.find("Download .tif")
    exec_html = (ROOT / "docs" / "h78step-executive-summary.html").read_text()
    assert "OK TO SUBMIT: NO" in exec_html


def test_tif_is_portal_safe_and_not_cleared():
    assert CARD["ok_to_submit"] is False
    assert CARD["verdict"] == "negative"
    assert CARD["raster_sha256"] == hashlib.sha256(TIF.read_bytes()).hexdigest()
    assert CARD["raster"]["file"] == STATUS["generated_tif"]
    assert CARD["organizer_confirmed_score"] is None
    assert CARD["correlation_overlap_vs_registry"]["complete_registry_verified"] is False
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
    assert len(note) <= 140
    assert note.startswith("NOT OK TO SUBMIT")
