#!/usr/bin/env python3
"""Experiment 2: Liu spy drop-and-refit of the strike-steered learner.

Preregistered in registry/preregistration_h78_spy.json before this fit.
Reuses the cached seed-20 feature matrix and the unmodified evaluator.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import features as F  # noqa: E402
from gems78 import pipeline as P  # noqa: E402

BUDGETS = (37_654, 44_090, 50_000)
MATCHED = 44_090
HGB = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
           l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=0)


def evaluate_dots(dots, folds, footprint):
    pred = dots.astype(np.float32)
    terms = None
    per_fold = {}
    for f in folds:
        result, block = EH.evaluate(
            pred, f, footprint, block_side=200, origin=(0, 0), global_shape=footprint.shape
        )
        per_fold[f["name"]] = dict(
            dti=float(result["dti"]), n_truth=int(result["n_truth"]), n_emitted=int(result["n_emitted"])
        )
        terms = block if terms is None else terms + block
    return terms, per_fold


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
    info = dict(n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), n_features=int(X.shape[1]),
                fit_seconds=round(time.time() - t0, 1))
    del X, y
    n = mm.shape[0]
    out_fp = np.empty(n, np.float32)
    for lo in range(0, n, 500_000):
        hi = min(n, lo + 500_000)
        block = np.asarray(mm[lo:hi][:, cols], np.float32)
        out_fp[lo:hi] = clf.predict_proba(block)[:, 1].astype(np.float32)
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out_fp
    return info, grid


def main():
    t_start = time.time()
    g = G.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    folds, _ = HO.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    feats_path = ROOT / "data" / "processed" / "feats_seed20.npy"
    if not feats_path.exists():
        raise SystemExit("missing cached feats_seed20.npy; run scripts/run_tooth_holdout.py first")
    stage1 = np.load(ROOT / "data" / "processed" / "score_seed20_A2_control.npy")

    # Canary restatement on A2 columns only.
    rng = np.random.default_rng(20)
    active = np.zeros(fp.shape, bool)
    truth = np.zeros(fp.shape, bool)
    for f in folds:
        a = fp & f["region"] & ~f["masked_known"]
        active |= a
        truth |= f["truth"] & a
    pos_flat = np.flatnonzero((truth & active).ravel())
    neg_flat = np.flatnonzero((active & ~truth).ravel())
    neg_flat = rng.choice(neg_flat, size=min(200_000, neg_flat.size), replace=False)
    sample = np.concatenate([pos_flat, neg_flat])
    rows = P.flat_to_rows(sample, fp)
    y = np.concatenate([np.ones(pos_flat.size), np.zeros(neg_flat.size)])
    order = np.argsort(rows, kind="stable")
    cols = P.arm_columns("A2_h78_steered")
    names = F.feature_names(iso=True, steered=True)
    mm = np.load(feats_path, mmap_mode="r")
    Xc = np.asarray(mm[rows[order]][:, cols], np.float32)
    yc = y[order]
    canary = {}
    for j, col in enumerate(cols):
        auc = float(roc_auc_score(yc, Xc[:, j]))
        canary[names[col]] = round(max(auc, 1.0 - auc), 4)
    flagged = {k: v for k, v in canary.items() if v > 0.90}
    print("canary max", max(canary.values()), "flagged", flagged, flush=True)
    if flagged:
        raise SystemExit("leakage canary failed; not fitting")

    pos, negs = P.training_sample(fp, visible, 450_000, seed=20)
    # Stage-1 scores. Positives are visible cells; their scores are exactly the training labels' scores.
    pos_scores = stage1.ravel()[pos]
    t = float(np.quantile(pos_scores, 0.15))
    neg_scores = stage1.ravel()[negs]
    qualify = neg_scores >= t
    n_qualify = int(qualify.sum())
    cap = int(0.20 * negs.size)
    if n_qualify > cap:
        # Drop the highest-scoring `cap` negatives, not every cell above t.
        order_neg = np.argsort(-neg_scores, kind="stable")
        drop_local = order_neg[:cap]
    else:
        drop_local = np.flatnonzero(qualify)
    keep = np.ones(negs.size, bool)
    keep[drop_local] = False
    negs_clean = negs[keep]
    dropped_hidden = int(hidden.ravel()[negs[drop_local]].sum())
    cleaning = dict(
        threshold_rule="15th percentile of stage-1 scores on training positives",
        t=t,
        positive_score_p15=t,
        positive_score_p50=float(np.quantile(pos_scores, 0.50)),
        n_neg=int(negs.size),
        n_qualify=n_qualify,
        n_dropped=int(drop_local.size),
        cap=cap,
        dropped_fraction=round(drop_local.size / negs.size, 4),
        dropped_that_were_withheld_truth=dropped_hidden,
        note="Withheld labels were counted after the drop for this audit only; they were not an input.",
    )
    print("cleaning", json.dumps(cleaning), flush=True)

    rows_pos = P.flat_to_rows(pos, fp)
    rows_neg = P.flat_to_rows(negs_clean, fp)
    info, score = fit_score(feats_path, rows_pos, rows_neg, fp)
    np.save(ROOT / "data" / "processed" / "score_seed20_spy.npy", score)
    print("fit", info, "score p50/p99/max",
          float(np.quantile(score[fp], 0.50)), float(np.quantile(score[fp], 0.99)), float(score.max()),
          flush=True)

    allowed = fp & ~E.flank_mask(visible, 3.0)
    rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=max(BUDGETS), pool=400_000)
    print("dots_available", int(rank.max()), flush=True)
    terms = {}
    per = {}
    for n in BUDGETS:
        if n > int(rank.max()):
            print("short of", n, flush=True)
            continue
        dots = E.prefix(rank, n)
        block, folds_d = evaluate_dots(dots, folds, fp)
        terms[n] = block
        per[n] = dict(pooled_dti=float(EH.from_terms(block.sum(axis=0))), per_fold=folds_d, dots=int(dots.sum()))
        print(f"  spy B3 {n}: HOLDOUT-DTI {per[n]['pooled_dti']:.4f}", flush=True)

    ctrl_key = "A2_control|nms0_B3|44090"
    # Rebuild the control's block terms from the saved control score so the paired CI is on this process.
    ctrl = np.load(ROOT / "data" / "processed" / "score_seed20_A2_control.npy")
    crank = E.greedy_dots(ctrl, allowed, min_dist=2.8, max_dots=MATCHED, pool=400_000)
    cdots = E.prefix(crank, MATCHED)
    cblock, _ = evaluate_dots(cdots, folds, fp)
    ctrl_dti = float(EH.from_terms(cblock.sum(axis=0)))
    print("control recompute", ctrl_dti, flush=True)

    summary = None
    if MATCHED in terms:
        summary = EH.pooled_summary(
            {"spy|nms0_B3|44090": terms[MATCHED], ctrl_key: cblock},
            draws=1000, seed=520810, candidate="spy|nms0_B3|44090",
        )
    log = dict(
        lane="H78-SPY",
        evaluator_version=EH.VERSION,
        evaluator_sha256=EH.implementation_hashes(),
        withheld_positive_pixels=int(hidden.sum()),
        canary=dict(max_auc=max(canary.values()), flagged=flagged, threshold=0.90,
                    top10=sorted(canary.items(), key=lambda kv: -kv[1])[:10]),
        cleaning=cleaning,
        fit=info,
        budgets={str(k): v for k, v in per.items()},
        control_B3_44090=ctrl_dti,
        pooled_summary=summary,
        seconds_total=round(time.time() - t_start, 1),
    )
    if summary:
        delta = summary["paired_differences"][ctrl_key]
        dti = summary["scores"]["spy|nms0_B3|44090"]["dti"]
        log["hypothesis_supported"] = bool(delta["ci95"][0] > 0 and dti > ctrl_dti)
        log["beats_0p1826"] = bool(dti > 0.1826)
        print("spy", round(dti, 4), "control", round(ctrl_dti, 4), "CI", delta["ci95"],
              "supported", log["hypothesis_supported"], flush=True)
    out = ROOT / "evidence" / "h78spy_holdout.json"
    out.write_text(json.dumps(log, indent=2, default=float))
    print("wrote", out, flush=True)


if __name__ == "__main__":
    main()
