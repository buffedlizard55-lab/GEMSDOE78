#!/usr/bin/env python3
"""Experiment 1+2 of lane H78: hide-and-recover holdout with ablation arms and
emission sweep, scored by the UNMODIFIED shared evaluator
(vendor/gems57/evaluate_holdout.py, version gems57-pooled-hide-v2).

Design
------
* Draw: ``holdout.buffered_component_draw`` -- whole 8-connected catalogue
  components withheld (20 % of catalogue cells per label-blind quadrant), 3-px
  feature collar, catalogue pixels (visible + collar) masked pixel-exactly.
* One global hidden draw; one model per arm trained on *all visible* cells
  (deployment-faithful: live we train on the whole catalogue and predict the
  unmapped faults everywhere); every catalogue-derived input (the strike field)
  is computed from the visible cells only.
* Evaluation per quadrant region, pooled DTI (alpha 0.2, beta 0.8, 300 m
  triangular kernel), 95 % CI by paired 20 km spatial-block bootstrap.
* Arms share the emitter, the dot budget and the folds; the only difference is
  the feature family, so the paired difference isolates the hypothesis.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import features as F  # noqa: E402

BUDGETS = [25_000, 30_000, 35_000, 37_654, 40_000, 44_090, 50_000, 60_000]


def evaluate_dots(dots, folds, footprint):
    """Pooled terms (summed over the four quadrant folds) for one binary dot grid."""
    pred = dots.astype(np.float32)
    terms = None
    per_fold = {}
    for f in folds:
        r, t = EH.evaluate(pred, f, footprint, block_side=200, origin=(0, 0), global_shape=footprint.shape)
        per_fold[f["name"]] = dict(dti=r["dti"], tp=r["tp"], fp=r["fp"], fn=r["fn"], n_truth=r["n_truth"],
                                   n_emitted=r["n_emitted"])
        terms = t if terms is None else terms + t
    return terms, per_fold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20)
    ap.add_argument("--n-neg", type=int, default=450_000)
    ap.add_argument("--arms", default="A0_std19,A1_iso,A2_h78_steered")
    ap.add_argument("--budgets", default=",".join(map(str, BUDGETS)))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    budgets = [int(b) for b in args.budgets.split(",")]
    arms = args.arms.split(",")
    t_start = time.time()

    g = G.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    folds, quad = HO.buffered_component_draw(g, seed=args.seed, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    receipts = [f["receipt"] for f in folds]
    log = dict(lane="H78", evaluator_version=EH.VERSION, evaluator_sha256=EH.implementation_hashes(),
               seed=args.seed, hide_frac=0.20, buffer_px=3, fold_receipts=receipts,
               visible_px=int(visible.sum()), hidden_px=int(hidden.sum()),
               withheld_positive_pixels_scored=int(sum(int((f["truth"]).sum()) for f in folds)))
    print(json.dumps({k: v for k, v in log.items() if k != "evaluator_sha256"}, indent=1))

    # ---- features (strike field from VISIBLE only) ----
    tag = f"seed{args.seed}"
    feats_path, fmeta = P.build_feature_matrix(tag, fp, visible)
    log["features"] = {k: v for k, v in fmeta.items() if k != "names"}
    print("features ready", fmeta["seconds"], "s")

    # ---- leakage canary: single-feature AUC on withheld truth vs active background ----
    names = F.feature_names(iso=True, steered=True)
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
    mm = np.load(feats_path, mmap_mode="r")
    order = np.argsort(rows)
    Xc = np.asarray(mm[rows[order]], np.float32)
    yc = y[order]
    canary = {}
    for j, nm in enumerate(names):
        auc = float(roc_auc_score(yc, Xc[:, j]))
        canary[nm] = round(max(auc, 1 - auc), 4)
    flagged = {k: v for k, v in canary.items() if v > 0.90}
    log["canary"] = dict(n_pos=int(pos_flat.size), n_neg=int(neg_flat.size), threshold=0.90,
                         flagged_over_0p90=flagged, max_auc=max(canary.values()),
                         top10=sorted(canary.items(), key=lambda kv: -kv[1])[:10], all=canary)
    print("canary max AUC", max(canary.values()), "flagged:", flagged)
    del Xc, yc, mm

    # ---- training sample (shared by all arms) ----
    pos, negs = P.training_sample(fp, visible, args.n_neg, seed=args.seed)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)

    # ---- registry comparators on the same folds ----
    def read_dots(p):
        with rasterio.open(p) as ds:
            a = ds.read(1)
        return np.isfinite(a) & (a > 0)
    comparators = {
        "registry_D2.8_44090": read_dots(ROOT / "data/registry/d28_44090_nan.tif"),
        "registry_H33_37654": read_dots(ROOT / "data/registry/h33_2_b2_37654_zeros.tif"),
    }
    terms_by_arm = {}
    results = {}
    for name, d in comparators.items():
        t, pf = evaluate_dots(d, folds, fp)
        terms_by_arm[name] = t
        results[name] = dict(per_fold=pf, dots_total=int(d.sum()),
                             note="built with knowledge of the FULL catalogue (incl. withheld cells); "
                                  "H33 additionally removed every dot <=2 px from the full catalogue, "
                                  "so it is structurally capped on withheld segments")
        print(name, EH.from_terms(t.sum(axis=0)))

    # ---- arms ----
    scores = {}
    for arm in arms:
        clf, info = P.fit_arm(feats_path, rows_pos, rows_neg, arm, seed=0)
        print("fit", info)
        s = P.score_grid(clf, feats_path, arm, fp)
        scores[arm] = s
        np.save(ROOT / "data/processed" / f"score_{tag}_{arm}.npy", s)
        results[arm] = dict(fit=info, variants={})
        variants = [("nms0_B2", False, 2.0)]
        if arm == arms[-1]:
            variants = [("nms0_B0", False, 0.0), ("nms0_B2", False, 2.0), ("nms1_B2", True, 2.0), ("nms0_B3", False, 3.0)]
        for vname, use_nms, bpx in variants:
            allowed = fp & ~E.flank_mask(visible, bpx)
            if use_nms:
                allowed &= E.ridge_nms(s, sigma=1.0)
            t0 = time.time()
            rank = E.greedy_dots(s, allowed, min_dist=2.8, max_dots=max(budgets))
            n_avail = int(rank.max())
            vres = dict(greedy_seconds=round(time.time() - t0, 1), dots_available=n_avail, budgets={})
            for n in budgets:
                if n > n_avail:
                    continue
                dots = E.prefix(rank, n)
                t, pf = evaluate_dots(dots, folds, fp)
                key = f"{arm}|{vname}|{n}"
                terms_by_arm[key] = t
                pooled = float(EH.from_terms(t.sum(axis=0)))
                vres["budgets"][str(n)] = dict(pooled_dti=pooled, per_fold=pf,
                                               dots_on_visible_catalogue=int((dots & visible).sum()))
                print(f"  {key}: pooled HOLDOUT-DTI {pooled:.4f}")
            results[arm]["variants"][vname] = vres

    # ---- pooled summary with CIs: candidate = best steered config; controls = best of each other arm ----
    def best_key(prefix):
        ks = [k for k in terms_by_arm if k.startswith(prefix)]
        return max(ks, key=lambda k: EH.from_terms(terms_by_arm[k].sum(axis=0))) if ks else None
    cand = best_key("A2_h78_steered|")
    summary = None
    if cand:
        sel = {cand: terms_by_arm[cand]}
        for a in arms:
            if a != "A2_h78_steered":
                k = best_key(a + "|")
                if k:
                    sel[k] = terms_by_arm[k]
        # matched-budget controls: same emitter/variant/budget as the candidate
        _, vname, n = cand.split("|")
        for a in arms:
            k = f"{a}|{vname}|{n}"
            if k in terms_by_arm and k not in sel:
                sel[k] = terms_by_arm[k]
        for c in comparators:
            sel[c] = terms_by_arm[c]
        summary = EH.pooled_summary(sel, draws=1000, seed=520810, candidate=cand)
    log["results"] = results
    log["pooled_summary"] = summary
    log["seconds_total"] = round(time.time() - t_start, 1)
    out = Path(args.out) if args.out else ROOT / "evidence" / f"h78_holdout_seed{args.seed}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, indent=2, default=float))
    print("wrote", out, "in", log["seconds_total"], "s")


if __name__ == "__main__":
    main()
