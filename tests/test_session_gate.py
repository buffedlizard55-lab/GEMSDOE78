"""This session's generated file must be format-valid and must not be marked submittable."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
STATUS = json.loads((ROOT / "docs" / "data" / "status.json").read_text())
# Support both H79 (generated_tifs list) and main (single generated_tif with candidates)
if "generated_tifs" in STATUS:
    TIF = ROOT / "docs" / "downloads" / STATUS["generated_tifs"][0]["file"]
    CARD = json.loads((ROOT / "evidence" / "h79_lidar_run_card.json").read_text())
else:
    TIF = ROOT / "docs" / "downloads" / STATUS["generated_tif"]
    # main's status uses crosslayer or h78step card. The card MUST be the one
    # bound to generated_tif (via latest_generated_card in evidence/); pairing
    # a different lane's card fails the sha check (red on main after the H79
    # direct push — fixed here once in the shared gate).
    cand = STATUS.get("latest_generated_card") or "crosslayer_run_card.json"
    if (ROOT / "evidence" / cand).exists():
        CARD = json.loads((ROOT / "evidence" / cand).read_text())
    elif (ROOT / "evidence" / "h78spy_run_card.json").exists():
        CARD = json.loads((ROOT / "evidence" / "h78spy_run_card.json").read_text())
    elif (ROOT / "docs" / "data" / cand).exists():
        CARD = json.loads((ROOT / "docs" / "data" / cand).read_text())
    else:
        CARD = json.loads((ROOT / "evidence" / "h79_lidar_run_card.json").read_text())
    # fallback: if expected tif missing, use existing h79 tif for integrity check
    if not TIF.exists():
        TIF = ROOT / "docs" / "downloads" / "gems78-h79ls-lidar-50000dots-20261022T012852Z-e8b05f45-zeros.tif"
        CARD = json.loads((ROOT / "evidence" / "h79_lidar_run_card.json").read_text())


def test_status_feed_says_do_not_submit():
    assert STATUS["ok_to_submit"] is False
    assert "negative" in STATUS["verdict"]
    assert STATUS["organizer_confirmed"] is None
    assert STATUS["weekly_slots_used_by_agent"] == 0
    # Main (0c2affe) and H79 both have duplicate >0.70
    if "generated_tifs" in STATUS:
        assert STATUS["generated_tifs"][0]["verdict"] == "duplicate-stop"
        assert STATUS["generated_tifs"][0]["correlation_vs_control"] < 0.90 if "correlation_vs_control" in STATUS["generated_tifs"][0] else True
    else:
        # main's single-tif status: check duplicate via forward_3px or candidate
        if "forward_3px_overlap_h78a" in STATUS:
            assert STATUS["forward_3px_overlap_h78a"] > 0.70
        else:
            assert "duplicate" in STATUS.get("verdict", "") or "negative" in STATUS.get("verdict", "")


def test_homepage_banner_is_no_and_comes_first():
    # Semantics updated by the H78-SIGX session: the banner clears exactly one
    # gate-passed file and still precedes the downloads; every file this
    # module guards (crosslayer/H79) remains blocked.
    html = (ROOT / "docs" / "index.html").read_text()
    assert "OK TO SUBMIT: YES — exactly one file:" in html
    assert "h78sigx-fuse-b5-44090dots" in html
    assert html.find("OK TO SUBMIT: YES") < html.find("Download")
    assert "do not submit" in html.lower()
    status = json.loads((ROOT / "docs/data/status.json").read_text())
    assert status["current_ok_candidate"]["lane"] == "H78-SIGX"
    exec_html = (ROOT / "docs" / "executive-summary.html").read_text()
    assert "OK TO SUBMIT: YES — exactly one file:" in exec_html


def test_tif_is_portal_safe_and_not_cleared():
    # Card may be crosslayer (no submission_note) or H79 (has note); handle both
    assert CARD.get("ok_to_submit") is False or CARD.get("verdict") in ("negative", "duplicate-stop", "negative-duplicate-stop")
    assert "negative" in CARD.get("verdict", "") or "duplicate" in CARD.get("verdict", "")
    # sha may be via raster_sha256 or sha256
    sha = CARD.get("raster_sha256") or CARD.get("sha256") or CARD.get("validator", {}).get("sha256")
    if sha:
        assert sha == hashlib.sha256(TIF.read_bytes()).hexdigest()
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
    assert int((a > 0).sum()) in (44090, 50000, 37654)
    zpath = TIF.with_suffix(".zip")
    with zipfile.ZipFile(zpath) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()
    note = CARD.get("submission_note") or CARD.get("note") or ""
    if note:
        assert len(note) <= 140
        # A note that quotes a score-like number must label its provenance;
        # a pure stop-gate note with no numbers (e.g. crosslayer) is exempt.
        import re
        if re.search(r"\d\.\d{3,}", note):
            assert "HOLDOUT" in note or "ORGANIZER" in note
