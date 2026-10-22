"""Latest generated file must be independently valid and fail closed on duplicate."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
def latest():
    # Builders run during the suite; read the status at test time, not import
    # time, so stale collection state cannot bind the old TIFF to the new card.
    return json.loads((ROOT / "docs/data/status.json").read_text())

CARD = json.loads((ROOT / "evidence" / "crosslayer_run_card.json").read_text())


def test_status_feed_says_do_not_submit():
    STATUS = latest()
    assert STATUS["ok_to_submit"] is False
    assert STATUS["verdict"] == "negative"
    assert STATUS["organizer_confirmed"] is None
    assert STATUS["weekly_slots_used_by_agent"] == 0
    assert STATUS["worst_forward_3px_overlap"] > 0.70
    assert STATUS["duplicate_witnesses"]
    assert STATUS["sha256"] == CARD["raster_sha256"]


def test_homepage_banner_is_no_and_comes_first():
    html = (ROOT / "docs" / "index.html").read_text()
    assert "OK TO SUBMIT: NO" in html
    assert "OK TO SUBMIT: YES" not in html
    assert html.find("OK TO SUBMIT: NO") < html.find("Downloads and automatic checks")
    assert "DO-NOT-SUBMIT" in html
    exec_html = (ROOT / "docs" / "executive-summary.html").read_text()
    assert "OK TO SUBMIT: NO" in exec_html


def test_tif_is_portal_safe_and_not_cleared():
    TIF = ROOT / "docs/downloads" / latest()["generated_tif"]
    assert CARD["ok_to_submit"] is False
    assert CARD["verdict"] == "negative"
    assert CARD["raster_sha256"] == hashlib.sha256(TIF.read_bytes()).hexdigest()
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
    assert CARD["holdout"]["score"] < CARD["holdout"]["control_incumbent"]["score"]
    assert CARD["validator_output"]["all_passed"]
    assert any(r["forward_3px_overlap"] > .70 for r in CARD["registry"]["final_dots"])
