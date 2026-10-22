#!/usr/bin/env python3
"""Experiment 1 of lane H78-STEP (preregistration registry/preregistration_h78step.json).

Hide-and-recover holdout scored by the UNMODIFIED shared evaluator
(vendor/gems57/evaluate_holdout.py, gems57-pooled-hide-v2). Arms share folds,
training rows, HGB hyperparameters and the greedy >=2.8 px emitter; only the
feature columns differ:

  CTRL_A2   = 103 H78-A features (exact rerun control, current repo best)
  CAND_STEP = 19 raw bands + 54 cross-strike STEP features (candidate, NO
              steered/iso derivative columns: distinct model class)
  ABL_A0    = 19 raw bands (lineage base class)
  ABL_STEPO = 54 STEP features only

Also: 157-feature leakage canary (symmetric AUC, stop > 0.90), far-truth
stratum (withheld truth > 10 px from any visible fault) at B3/44090, and the
score-surface Spearman rho of CAND_STEP vs CTRL_A2 (duplicate-lane diagnostic).
Output: evidence/h78step_holdout_seed<seed>.json (+ score grids in data/processed/).
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import uniqueness as U  # noqa: E402
from gems78 import data as D  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import features as F  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78 import xstep as X  # noqa: E402

HGB = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
           l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=0)
BUDGETS_B3 = [37_654, 44_090, 50_000]
PRIMARY = 44_090


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def assemble(base_mm, step_mm, rows, base_cols, use_step):
    parts = []
    if base_cols is not None:
        parts.append(np.asarray(base_mm[rows][:, base_cols], np.float32))
    if use_step:
        parts.append(np.asarray(step_mm[rows], np.float32))
    return np.concatenate(parts, axis=1)


def fit(base_mm, step_mm, rows_pos, rows_neg, base_cols, use_step, label):
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    Xm = assemble(base_mm, step_mm, rows[order], base_cols, use_step)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    clf = HistGradientBoostingClassifier(**HGB)
    t0 = time.time()
    clf.fit(Xm, y)
    info = dict(arm=label, n_pos=int(rows_pos.size), n_neg=int(rows_neg.size),
                n_features=int(Xm.shape[1]), params=HGB, fit_seconds=round(time.time() - t0, 1))
    del Xm, y
    gc.collect()
    log("fit", info)
    return clf, info


def score(clf, base_mm, step_mm, base_cols, use_step, footprint, chunk=600_000):
    n = base_mm.shape[0]
    out = np.zeros(n, np.float32)
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        Xm = assemble(base_mm, step_mm, np.arange(lo, hi), base_cols, use_step)
        out[lo:hi] = clf.predict_proba(Xm)[:, 1].astype(np.float32)
        del Xm
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out
    return grid


def evaluate_dots(dots, folds, footprint):
    pred = dots.astype(np.float32)
    terms = None
    per_fold = {}
    for f in folds:
        r, t = EH.evaluate(pred, f, footprint, block_side=200, origin=(0, 0),
                           global_shape=footprint.shape)
        per_fold[f["name"]] = dict(dti=r["dti"], n_truth=r["n_truth"], n_emitted=r["n_emitted"])
        terms = t if terms is None else terms + t
    return terms, per_fold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20)
    ap.add_argument("--n-neg", type=int, default=450_000)
    args = ap.parse_args()
    t_start = time.time()

    inputs = D.verify_inputs()
    log("inputs verified", {k: v["ok"] for k, v in inputs.items()})

    g = G.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    folds, quad = HO.buffered_component_draw(g, seed=args.seed, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    n_hidden = int(hidden.sum())
    n_scored = int(sum(int(f["truth"].sum()) for f in folds))
    log("visible", int(visible.sum()), "hidden", n_hidden, "scored", n_scored)
    if args.seed == 20:  # primary draw must reproduce the shipped instrument exactly
        assert n_hidden == 11_321 and n_scored == 11_321, "instrument precondition failed"

    tag = f"seed{args.seed}"
    feats_path, fmeta = P.build_feature_matrix(tag, fp, visible)
    phi = np.load(D.PROC / f"phi_{tag}.npy")
    step_path, stepmeta = X.build_step_matrix(tag, fp, phi)
    del phi
    gc.collect()
    log("features ready base", fmeta["seconds"], "s step", stepmeta["seconds"], "s")

    base_names = F.feature_names(iso=True, steered=True)
    step_names = X.step_feature_names()
    all_names = base_names + step_names
    base_mm = np.load(feats_path, mmap_mode="r")
    step_mm = np.load(step_path, mmap_mode="r")
    assert base_mm.shape[1] == 103 and step_mm.shape[1] == 54 and base_mm.shape[0] == step_mm.shape[0]

    # ---- leakage canary: single-feature symmetric AUC, withheld truth vs active bg ----
    rng = np.random.default_rng(args.seed)
    active = np.zeros(fp.shape, bool)
    truth = np.zeros(fp.shape, bool)
    for f in folds:
        a = fp & f["region"] & ~f["masked_known"]
        active |= a
        truth |= f["truth"] & a
    pos_flat = np.flatnonzero((truth & active).ravel())
    neg_flat = np.flatnonzero((active & ~truth).ravel())
    neg_flat = rng.choice(neg_flat, size=min(300_000, neg_flat.size), replace=False)
    rows = P.flat_to_rows(np.concatenate([pos_flat, neg_flat]), fp)
    y = np.concatenate([np.ones(pos_flat.size), np.zeros(neg_flat.size)])
    order = np.argsort(rows)
    Xc = np.concatenate([np.asarray(base_mm[rows[order]], np.float32),
                         np.asarray(step_mm[rows[order]], np.float32)], axis=1)
    yc = y[order]
    canary = {}
    for j, nm in enumerate(all_names):
        auc = float(roc_auc_score(yc, Xc[:, j]))
        canary[nm] = round(max(auc, 1 - auc), 4)
    del Xc, yc
    gc.collect()
    flagged = {k: v for k, v in canary.items() if v > 0.90}
    canary_step = {k: canary[k] for k in step_names}
    log("canary max", max(canary.values()), "STEP max", max(canary_step.values()), "flagged", flagged)
    assert not flagged, f"LEAKAGE CANARY STOP: {flagged}"

    # ---- shared training rows ----
    pos, negs = P.training_sample(fp, visible, args.n_neg, seed=args.seed)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)

    # ---- far-truth folds (>10 px from any visible fault) ----
    d_vis = ndi.distance_transform_edt(~np.asarray(visible, bool))
    far_folds = []
    for f in folds:
        ff = dict(f)
        ff["truth"] = np.asarray(f["truth"], bool) & (d_vis > 10.0)
        far_folds.append(ff)
    n_far = int(sum(int(ff["truth"].sum()) for ff in far_folds))
    log("far-truth positives", n_far)
    del d_vis

    arms = {
        "CTRL_A2": (P.arm_columns("A2_h78_steered"), False),
        "CAND_STEP": (P.arm_columns("A0_std19"), True),
        "ABL_A0": (P.arm_columns("A0_std19"), False),
        "ABL_STEPO": (None, True),
    }
    terms_all, terms_far = {}, {}
    results = {}
    scores = {}
    allowed = {3.0: fp & ~E.flank_mask(visible, 3.0), 2.0: fp & ~E.flank_mask(visible, 2.0)}
    for arm, (cols, use_step) in arms.items():
        clf, info = fit(base_mm, step_mm, rows_pos, rows_neg, cols, use_step, arm)
        s = score(clf, base_mm, step_mm, cols, use_step, fp)
        del clf
        gc.collect()
        np.save(D.PROC / f"score_{tag}_{arm}.npy", s)
        scores[arm] = s
        results[arm] = dict(fit=info, configs={})
        for bpx, budgets in ((3.0, BUDGETS_B3), (2.0, [PRIMARY])):
            t0 = time.time()
            rank = E.greedy_dots(s, allowed[bpx], min_dist=2.8, max_dots=60_000, pool=1_500_000)
            log(arm, f"B{int(bpx)}", "greedy", round(time.time() - t0, 1), "s avail", int(rank.max()))
            for n in budgets:
                dots = E.prefix(rank, n)
                t, pf = evaluate_dots(dots, folds, fp)
                key = f"{arm}|B{int(bpx)}|{n}"
                pooled = float(EH.from_terms(t.sum(axis=0)))
                results[arm]["configs"][key] = dict(pooled_dti=pooled, per_fold=pf)
                log(" ", key, "HOLDOUT-DTI", round(pooled, 4))
                if bpx == 3.0 and n == PRIMARY:
                    terms_all[key] = t
                    tf, _ = evaluate_dots(dots, far_folds, fp)
                    terms_far[key] = tf
                    results[arm]["far_B3_primary"] = dict(
                        pooled_dti=float(EH.from_terms(tf.sum(axis=0))), n_truth_far=n_far)
                    log(" ", key, "far-truth HOLDOUT-DTI", results[arm]["far_B3_primary"]["pooled_dti"])
            del rank

    rho_cand_ctrl = U.surface_rho(scores["CAND_STEP"], scores["CTRL_A2"], fp)
    log("surface rho CAND vs CTRL", rho_cand_ctrl)
    del scores["ABL_A0"], scores["ABL_STEPO"]
    gc.collect()

    cand_key = f"CAND_STEP|B3|{PRIMARY}"
    summary = EH.pooled_summary(terms_all, draws=1000, seed=520810, candidate=cand_key)
    far_summary = EH.pooled_summary(terms_far, draws=1000, seed=520810, candidate=cand_key)

    out = dict(
        lane="H78-STEP cross-strike step-offset concordance", evidence_class="HOLDOUT-DTI",
        evaluator_version=EH.VERSION, evaluator_sha256=EH.implementation_hashes(),
        seed=args.seed, hide_frac=0.20, buffer_px=3,
        visible_px=int(visible.sum()), hidden_px=n_hidden,
        withheld_positive_pixels_scored=n_scored, far_truth_positives_gt10px=n_far,
        inputs_verified=inputs,
        features_base={k: v for k, v in fmeta.items() if k != "names"},
        features_step={k: v for k, v in stepmeta.items() if k != "names"},
        step_feature_names=step_names,
        canary=dict(n_pos=int(pos_flat.size), n_neg=int(neg_flat.size), threshold=0.90,
                    flagged_over_0p90=flagged, max_auc=max(canary.values()),
                    step_features=canary_step,
                    top10=sorted(canary.items(), key=lambda kv: -kv[1])[:10], all=canary),
        results=results,
        pooled_summary_B3_primary=summary,
        pooled_summary_far_truth_gt10px_B3_primary=far_summary,
        surface_rho_candidate_vs_ctrl=rho_cand_ctrl,
        repo_holdout_best_before=dict(value=0.1826, config="A2_h78_steered|nms0_B3|44090",
                                      value_50000=0.18431154590898757,
                                      source="evidence/h78_pooled_ci_seed20.json / h78cs CTRL rerun",
                                      evidence_class="HOLDOUT-DTI"),
        seconds_total=round(time.time() - t_start, 1),
    )
    outp = ROOT / "evidence" / f"h78step_holdout_seed{args.seed}.json"
    outp.write_text(json.dumps(out, indent=2, default=float))
    log("wrote", outp, "in", out["seconds_total"], "s")
    print(json.dumps({k: (round(v["dti"], 4), [round(x, 4) for x in v["ci95"]])
                        for k, v in summary["scores"].items()}, indent=1))
    print(json.dumps({k: (round(v["delta"], 4), [round(x, 4) for x in v["ci95"]])
                        for k, v in summary["paired_differences"].items()}, indent=1))


if __name__ == "__main__":
    main()
