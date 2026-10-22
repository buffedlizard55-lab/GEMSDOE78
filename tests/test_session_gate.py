"""Latest generated file (Session-5 H78-MGHD + historical cross-layer) must be independently valid and fail closed on literal duplicate."""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def latest():
    return json.loads((ROOT / "docs/data/status.json").read_text())


CARD = json.loads((ROOT / "evidence" / "h78mghd_run_card.json").read_text())
HIST_CROSSLAYER = json.loads((ROOT / "evidence" / "crosslayer_run_card.json").read_text())


def test_status_feed_says_do_not_submit():
    STATUS = latest()
    assert STATUS["ok_to_submit"] is False
    assert STATUS["verdict"] == "negative"
    assert STATUS["organizer_confirmed"] is None
    assert STATUS["weekly_slots_used_by_agent"] == 0
    assert STATUS["worst_forward_3px_overlap"] > 0.70
    assert STATUS["duplicate_witnesses"]
    assert STATUS["sha256"] == CARD["raster_sha256"]
    assert STATUS["generated_tif"] == CARD["submission_file"]


def test_homepage_banner_is_no_and_comes_first():
    html = (ROOT / "docs" / "index.html").read_text()
    assert "OK TO DOWNLOAD: YES · OK TO SUBMIT: NO" in html
    assert "OK TO SUBMIT: YES" not in html
    assert html.find("OK TO DOWNLOAD: YES · OK TO SUBMIT: NO") < html.find("Downloads and automatic checks")
    assert "DO-NOT-SUBMIT" in html
    assert CARD["submission_file"] in html
    exec_html = (ROOT / "docs" / "executive-summary.html").read_text()
    assert "OK TO DOWNLOAD: YES · OK TO SUBMIT: NO" in exec_html
    assert CARD["submission_file"] in exec_html


def test_tif_is_portal_safe_and_not_cleared():
    TIF = ROOT / "docs/downloads" / latest()["generated_tif"]
    assert CARD["ok_to_download"] is True
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
    assert CARD["validator_output"]["all_passed"]
    # H78-MGHD beats incumbent on both seeds AND still stops fail-closed on literal registry overlap > 0.70
    s20 = CARD["holdout"]["experiment_E2_selected_arm_seed20_44090"]
    s30 = CARD["holdout"]["experiment_E3_seed30_zero_retune_44090"]
    assert s20["paired_delta_cand_minus_ctrl"]["ci95"][0] > 0.0
    assert s30["paired_delta_cand_minus_ctrl"]["ci95"][0] > 0.0
    assert CARD["correlation_overlap_vs_registry"]["literal_all_rasters_worst_forward_3px_overlap"] > 0.70
    # Historical cross-layer negative card remains intact
    assert HIST_CROSSLAYER["holdout"]["score"] < HIST_CROSSLAYER["holdout"]["control_incumbent"]["score"]
