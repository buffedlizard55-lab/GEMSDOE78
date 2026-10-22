#!/usr/bin/env python3
"""Production build for lane H78-SIGX (E1+E2 selection), with automated gates.

Refits CTRL_A2 and SIGX on the FULL catalogue (strike field from the full
catalogue), rank-fuses the two surfaces (E2 method), then applies gate G4
*before* writing anything: candidate order is [FUSE|B5|44090, SIGX|B5|44090]
(fixed by registry/preregistration_h78sig_e2_amendment.json). The first
candidate whose pre-placement surface |Spearman| < 0.90 against every
registry raster AND whose final forward 3 px dot overlap passes the
documented sparse/top-K rule (< 0.70) is written via the unmodified vendor
submission writer. If neither passes, no TIFF is written (exit 2) and the
negative result is recorded. No human inspection step exists in this path.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import grid as G  # noqa: E402
from gems57 import submission_writer as SW  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import sigx as SX  # noqa: E402
from gems78 import registry_check as RC  # noqa: E402

BUDGET, FLANK = 44_090, 5.0


def main(reuse_surfaces: bool = False):
    t0 = time.time()
    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, np.asarray(g.catalogue, bool)
    if reuse_surfaces:
        # Deterministic refit outputs from the earlier stopped run are reused
        # byte-for-byte; their SHA-256s are recorded in the evidence below.
        import hashlib
        surfaces, surface_sha = {}, {}
        for arm in ("CTRL_A2", "SIGX", "FUSE"):
            p = ROOT / "data/processed" / f"surface_full_{arm}.npy"
            surfaces[arm] = np.load(p)
            surface_sha[arm] = hashlib.sha256(p.read_bytes()).hexdigest()
        prev = json.loads((ROOT / "evidence/h78sig_production.json").read_text())
        fits = prev["fits"]
        fuse = surfaces["FUSE"]
        print(f"[surfaces] reused saved full-catalogue surfaces {surface_sha}", flush=True)
    else:
        surface_sha = None
        tag = "fullsig"
        feats_sigx, smeta = SX.build_sigx_matrix(tag, fp, cat)
        feats_base = ROOT / "data" / "processed" / f"feats_{tag}.npy"
        print(f"[features] full matrices ready ({smeta['seconds']} s)", flush=True)
        pos, negs = P.training_sample(fp, cat, 450_000, seed=20)
        rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
        fits, surfaces = {}, {}
        for arm, path, cols in (("CTRL_A2", feats_base, np.arange(103)),
                                ("SIGX", feats_sigx, np.arange(102))):
            clf, info = SX.fit_cols(path, rows_pos, rows_neg, cols, arm)
            fits[arm] = info
            surfaces[arm] = SX.score_cols(clf, path, cols, fp)
            np.save(ROOT / "data/processed" / f"surface_full_{arm}.npy", surfaces[arm])
            print(f"[fit] {arm} {info['fit_seconds']} s", flush=True)
            del clf
        fuse = np.zeros(fp.shape, np.float32)
        fuse[fp] = ((rankdata(surfaces["CTRL_A2"][fp]) + rankdata(surfaces["SIGX"][fp]))
                    / (2.0 * int(fp.sum()))).astype(np.float32)
        surfaces["FUSE"] = fuse
        np.save(ROOT / "data/processed/surface_full_FUSE.npy", fuse)
    rho_parents = dict(
        FUSE_vs_CTRL=float(spearmanr(fuse[fp], surfaces["CTRL_A2"][fp]).statistic),
        FUSE_vs_SIGX=float(spearmanr(fuse[fp], surfaces["SIGX"][fp]).statistic),
        SIGX_vs_CTRL=float(spearmanr(surfaces["SIGX"][fp], surfaces["CTRL_A2"][fp]).statistic))
    print(f"[surfaces] parent Spearman {rho_parents}", flush=True)

    entries = RC.registry_rasters()
    dcat = ndi.distance_transform_edt(~cat)
    evidence = dict(lane="H78-SIGX", stage="production", built_utc=
                    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                    reused_saved_surfaces=bool(reuse_surfaces), surface_npy_sha256=surface_sha,
                    gate_version="G4 v2 (template halo/Jaccard classes; IR-78-22-03)",
                    fits=fits, parent_surface_spearman=rho_parents,
                    registry_scope=[e["name"] for e in entries],
                    candidates={})
    selected = None
    for cname in ("FUSE", "SIGX"):
        surf_cmp = RC.compare_surface(surfaces[cname], fp, cat, entries)
        worst_rho = max(abs(v["spearman_full_footprint"]) for v in surf_cmp.values())
        rank = E.greedy_dots(surfaces[cname], fp & ~E.flank_mask(cat, FLANK),
                             min_dist=2.8, max_dots=BUDGET)
        dots = E.prefix(rank, BUDGET)
        assert int((dots & cat).sum()) == 0 and float(dcat[dots].min()) > FLANK
        dot_cmp = RC.compare_dots(dots, fp, cat, entries)
        worst_ov = max(v["gate_statistic"] / v["gate_limit"] for v in dot_cmp.values())
        passed = bool(worst_rho < RC.RHO_LIMIT and all(v["passed"] for v in dot_cmp.values()))
        evidence["candidates"][cname] = dict(
            surface_vs_registry=surf_cmp, worst_abs_surface_spearman=worst_rho,
            dots_vs_registry=dot_cmp, worst_gate_statistic_over_limit=worst_ov,
            worst_literal_forward_overlap_3px=max(v["forward_overlap_3px_literal"]
                                                  for v in dot_cmp.values()),
            dots=int(dots.sum()), min_dist_to_catalogue_px=float(dcat[dots].min()),
            median_dist_to_catalogue_px=float(np.median(dcat[dots])),
            uniqueness_gate_passed=passed)
        print(f"[{cname}] worst |rho| {worst_rho:.4f}  worst gate stat/limit {worst_ov:.4f}  "
              f"gate {'PASS' if passed else 'FAIL'}", flush=True)
        if passed and selected is None:
            selected = (cname, dots)
    if selected is None:
        evidence["verdict"] = "negative: no candidate passed uniqueness gate G4; no TIFF written"
        out = ROOT / "evidence" / "h78sig_production.json"
        out.write_text(json.dumps(evidence, indent=2))
        print(f"STOP duplicate: {out}", flush=True)
        return 2

    cname, dots = selected
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"gems78-h78sigx-{cname.lower()}-b5-{BUDGET}dots-{stamp}-zeros"
    note = ("GEMSDOE78 H78-SIGX rank-fusion A2+signature(lidar10m), flank>500m, "
            "44090 spaced dots; HOLDOUT-DTI far0.1053/overall0.1771 s20")
    assert len(note) <= 140, len(note)
    path = ROOT / "docs" / "downloads" / f"{stem}.tif"
    receipt = SW.write_submission(path, dots.astype(np.float32),
                                  ROOT / "data" / "bridge" / "sample_submission.tif",
                                  fp, note=note, name=stem, catalogue=cat,
                                  metadata=dict(lane="H78-SIGX", candidate=cname,
                                                flank_px=FLANK, budget=BUDGET))
    evidence.update(selected_candidate=cname, submission_file=path.name,
                    submission_name=stem, submission_note=note, note_chars=len(note),
                    writer_receipt_file=f"{stem}.json", raster_sha256=receipt["sha256"],
                    seconds_total=round(time.time() - t0, 1), verdict="written; pending independent gate_check")
    np.save(ROOT / "data/processed" / "surface_production_selected.npy", surfaces[cname])
    out = ROOT / "evidence" / "h78sig_production.json"
    out.write_text(json.dumps(evidence, indent=2))
    print(f"WROTE {path} sha256={receipt['sha256']} in {evidence['seconds_total']} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(reuse_surfaces="--reuse-surfaces" in sys.argv))
