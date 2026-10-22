#!/usr/bin/env python3
"""Experiment 3: deployment inspection raster for the failed H78-SPY lane.

The holdout gate already failed (evidence/h78spy_holdout.json). This script
still writes a format-valid GeoTIFF so the negative result is downloadable,
and it records uniqueness against the family rasters. ok_to_submit is forced
False. The writer is the unmodified vendor submission_writer.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import grid as G  # noqa: E402
from gems57 import submission_writer as SW  # noqa: E402
from gems57 import uniqueness as U  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import pipeline as P  # noqa: E402

HGB = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
           l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=0)
N_DOTS = 44_090

REGISTRY = {
    "H19-5": ROOT / "data/registry/h19_5_solid_nan.tif",
    "D2.8": ROOT / "data/registry/d28_44090_nan.tif",
    "H33": ROOT / "data/registry/h33_2_b2_37654_zeros.tif",
    "H78-A": ROOT / "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif",
    "H78-A-altB2": ROOT / "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223133Z-ec00c053-altB2-zeros.tif",
    "H78-MPC": ROOT / "docs/downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif",
    "anderson-pinn": ROOT / "data/registry/family/anderson_pinn_zeros.tif",
    "gems70-dual-submod": ROOT / "data/registry/family/gems70_dual_submod.tif",
    "h27-4-solo-d28": ROOT / "data/registry/family/h27_4_solo_d28.tif",
    "h33d-tip-stepover": ROOT / "data/registry/family/h33d_tip_stepover.tif",
}


def read_raster(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.where(np.isfinite(a), a, 0.0).astype(np.float32)


def fit_score(feats_path, rows_pos, rows_neg, footprint):
    cols = P.arm_columns("A2_h78_steered")
    mm = np.load(feats_path, mmap_mode="r")
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows, kind="stable")
    X = np.asarray(mm[rows[order]][:, cols], np.float32)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    clf = HistGradientBoostingClassifier(**HGB)
    t0 = time.time()
    clf.fit(X, y)
    info = dict(n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), fit_seconds=round(time.time() - t0, 1))
    del X, y
    n = mm.shape[0]
    out_fp = np.empty(n, np.float32)
    for lo in range(0, n, 500_000):
        hi = min(n, lo + 500_000)
        out_fp[lo:hi] = clf.predict_proba(np.asarray(mm[lo:hi][:, cols], np.float32))[:, 1].astype(np.float32)
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out_fp
    return info, grid


def main():
    t0 = time.time()
    hold = json.loads((ROOT / "evidence/h78spy_holdout.json").read_text())
    if hold.get("hypothesis_supported"):
        raise SystemExit("refusing to build an inspection-only file: holdout gate unexpectedly passed")
    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    feats_path, fmeta = P.build_feature_matrix("full", fp, cat)
    print("features", {k: fmeta[k] for k in ("n_footprint", "n_features", "seconds")}, flush=True)
    pos, negs = P.training_sample(fp, cat, 450_000, seed=20)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    info1, stage1 = fit_score(feats_path, rows_pos, rows_neg, fp)
    print("stage1", info1, flush=True)
    t = float(np.quantile(stage1.ravel()[pos], 0.15))
    neg_scores = stage1.ravel()[negs]
    qualify = np.flatnonzero(neg_scores >= t)
    cap = int(0.20 * negs.size)
    if qualify.size > cap:
        order = np.argsort(-neg_scores, kind="stable")
        drop = order[:cap]
    else:
        drop = qualify
    keep = np.ones(negs.size, bool)
    keep[drop] = False
    info2, score = fit_score(feats_path, rows_pos, P.flat_to_rows(negs[keep], fp), fp)
    print("stage2", info2, "dropped", int(drop.size), "t", t, flush=True)
    np.save(ROOT / "data/processed/score_full_spy.npy", score)

    surface = {}
    for label, path in REGISTRY.items():
        surface[label] = U.surface_rho(score, read_raster(path), fp)["spearman_full_footprint"]
    surface_max = max(abs(v) for v in surface.values())
    print("surface rho max", round(surface_max, 4), flush=True)

    allowed = fp & ~E.flank_mask(cat, 3.0)
    rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=N_DOTS, pool=400_000)
    dots = E.prefix(rank, N_DOTS)
    n_dots = int(dots.sum())
    if n_dots != N_DOTS:
        raise SystemExit(f"emitter produced {n_dots} dots, expected {N_DOTS}")
    pred = dots.astype(np.float32)
    dot_audit = {}
    for label, path in REGISTRY.items():
        theirs = read_raster(path)
        dot_audit[label] = dict(
            forward_3px=U.dot_overlap(pred, theirs, 3.0),
            reverse_3px=U.dot_overlap(theirs, pred, 3.0),
            spearman=U.surface_rho(pred, theirs, fp)["spearman_full_footprint"],
        )
    worst_overlap = max(v["forward_3px"] for v in dot_audit.values())
    worst_rho = max(abs(v["spearman"]) for v in dot_audit.values())
    unique_ok = surface_max <= 0.90 and worst_rho <= 0.90 and worst_overlap <= 0.70
    print("overlap max", round(worst_overlap, 4), "unique", unique_ok, flush=True)

    # Distance-to-catalogue profile, for the disclosure, not a score.
    from scipy import ndimage as ndi
    dist = ndi.distance_transform_edt(~cat)
    d_dots = dist[dots]
    profile = dict(
        median_px=float(np.median(d_dots)),
        p10_px=float(np.quantile(d_dots, 0.10)),
        p90_px=float(np.quantile(d_dots, 0.90)),
        fraction_within_5px=float((d_dots <= 5).mean()),
        fraction_beyond_30px=float((d_dots > 30).mean()),
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
    name = f"gems78-h78spy-inspection-{n_dots}dots-{stamp}-{digest8}-DO-NOT-SUBMIT"
    note = (
        "NOT OK TO SUBMIT. H78-SPY holdout 0.1808 vs 0.1826 control; inspection only, not a projection"
    )[:140]
    out_dir = ROOT / "docs" / "downloads"
    tif = out_dir / f"{name}.tif"
    receipt = SW.write_submission(
        tif, pred, ROOT / "data/bridge/sample_submission.tif", fp,
        note=note, name=name[:140], catalogue=cat,
        metadata=dict(lane="H78-SPY", ok_to_submit=False, reason="holdout gate failed"),
    )
    # Independent re-read.
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        meta = dict(count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs), shape=[ds.height, ds.width],
                    transform=list(ds.transform)[:6], nodata=ds.nodata)
    validator = dict(
        single_band=meta["count"] == 1,
        dtype_float32=meta["dtype"] == "float32",
        crs_epsg_32611=meta["crs"] == "EPSG:32611",
        shape_3730x3292=meta["shape"] == [3730, 3292],
        transform_match=meta["transform"] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
        nodata_unset=meta["nodata"] is None,
        all_finite=bool(np.isfinite(a).all()),
        no_nan_inside_footprint=int(np.isnan(a[fp]).sum()),
        values_in_0_1=bool(a.min() >= 0 and a.max() <= 1),
        min=float(a.min()), max=float(a.max()),
        zero_outside_footprint=bool((a[~fp] == 0).all()),
        zero_on_catalogue=int((a[cat] > 0).sum()) == 0,
        dots=int((a > 0).sum()),
    )
    validator["passed"] = bool(all([
        validator["single_band"], validator["dtype_float32"], validator["crs_epsg_32611"],
        validator["shape_3730x3292"], validator["transform_match"], validator["nodata_unset"],
        validator["all_finite"], validator["no_nan_inside_footprint"] == 0,
        validator["values_in_0_1"], validator["zero_outside_footprint"],
        validator["zero_on_catalogue"], validator["dots"] == n_dots,
    ]))
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    card = dict(
        lane="H78-SPY",
        hypothesis="Spy-cleaning unlabeled cells that score like faults, then refitting the strike-steered learner, raises hide-and-recover DTI.",
        mechanism="Stage-1 A2 HistGradientBoosting; drop negatives at or above the 15th percentile of positive scores (cap 20%); one refit; dots >= 2.8 px apart, flank <= 3 px, 44090 dots.",
        mimic_nonfault_process="Lithologic contacts and range-front-parallel drainages also score like faults; dropping them from the negatives marks those non-fault lineaments more willingly.",
        holdout=dict(
            evidence_class="HOLDOUT-DTI",
            evaluator_version=hold["evaluator_version"],
            withheld_positive_pixels=hold["withheld_positive_pixels"],
            spy_dti=hold["pooled_summary"]["scores"]["spy|nms0_B3|44090"]["dti"],
            spy_ci95=hold["pooled_summary"]["scores"]["spy|nms0_B3|44090"]["ci95"],
            control_dti=hold["control_B3_44090"],
            paired_delta=hold["pooled_summary"]["paired_differences"]["A2_control|nms0_B3|44090"],
            hypothesis_supported=False,
            beats_published_0_1826=False,
        ),
        organizer_confirmed_score=None,
        leakage_canary=hold["canary"],
        correlation_overlap_vs_registry=dict(
            surface_before_placement=surface,
            surface_max_abs_rho=surface_max,
            final_dots=dot_audit,
            worst_forward_3px=worst_overlap,
            worst_abs_rho=worst_rho,
            rho_limit=0.90,
            overlap_limit=0.70,
            passed=unique_ok,
        ),
        raster_sha256=sha,
        validator_output=validator,
        distance_to_catalogue_px=profile,
        submission_name=name,
        submission_note=note,
        submission_note_chars=len(note),
        file=tif.name,
        zip_file=receipt["zip_file"],
        cleaning_deployment=dict(t=t, n_dropped=int(drop.size), stage1=info1, stage2=info2),
        features={k: v for k, v in fmeta.items() if k != "names"},
        ok_to_download=True,
        ok_to_submit=False,
        weekly_slots_used_by_agent=0,
        experiments_used=3,
        verdict="negative",
        seconds=round(time.time() - t0, 1),
    )
    (ROOT / "evidence/h78spy_run_card.json").write_text(json.dumps(card, indent=2, default=float))
    (ROOT / "run_card_h78spy.json").write_text(json.dumps(card, indent=2, default=float))
    print(json.dumps(dict(file=tif.name, sha256=sha, ok_to_submit=False, verdict="negative",
                          unique=unique_ok, validator=validator["passed"], dots=n_dots), indent=1))


if __name__ == "__main__":
    main()
