#!/usr/bin/env python3
"""H79-LS holdout: lidar-augmented HGB vs H78-A controls.

Design: same hide-and-recover folds as H78 (seed 20, hide 0.20, buffer 3),
same evaluator gems57-pooled-hide-v2, same training sample (all visible pos +
450k negatives >2px from visible), same HGB params, same greedy ≥√8 px emitter
with flank 3 px. Four arms share folds/emitter/budget; only feature columns differ:

- A0_std19: 19 raw bands
- A1_iso: A0 + 36 iso derivatives
- A2_h78_steered: A1 + 48 steered
- A3_lidar: A2 + 12 lidar_scarp (candidate)

Candidate selected as best A3 B3 config; controls are best A0/A1 at same budget.
Pooled DTI alpha 0.2 beta 0.8 300m triangular, 95% CI paired 20km block bootstrap.
Leakage canary on all 115 features (single-feature AUC >0.90 flags).
"""
from __future__ import annotations

import json, time, sys
from pathlib import Path
import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import grid as G, holdout as HO, evaluate_holdout as EH
from gems78 import pipeline as P, emit as E, features as F, lidar as L

BUDGETS = [25_000, 30_000, 35_000, 37_654, 40_000, 44_090, 50_000, 60_000]
HGB = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
           l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=0)

def evaluate_dots(dots, folds, fp):
    pred = dots.astype(np.float32)
    terms = None
    per_fold = {}
    for f in folds:
        r, t = EH.evaluate(pred, f, fp, block_side=200, origin=(0,0), global_shape=fp.shape)
        per_fold[f["name"]] = dict(dti=r["dti"], n_truth=r["n_truth"], n_emitted=r["n_emitted"])
        terms = t if terms is None else terms + t
    return terms, per_fold

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20)
    ap.add_argument("--n-neg", type=int, default=450_000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    t_start = time.time()
    g = G.load_grid(ROOT / "data/bridge")
    fp = g.footprint
    folds, quad = HO.buffered_component_draw(g, seed=args.seed, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    receipts = [f["receipt"] for f in folds]
    log = dict(lane="H79-LS lidar-augmented", evaluator_version=EH.VERSION,
               evaluator_sha256=EH.implementation_hashes(),
               seed=args.seed, hide_frac=0.20, buffer_px=3,
               fold_receipts=receipts,
               visible_px=int(visible.sum()), hidden_px=int(hidden.sum()),
               withheld_positive_pixels_scored=int(sum(int((f["truth"]).sum()) for f in folds)))
    print(json.dumps({k:v for k,v in log.items() if k!="evaluator_sha256"}, indent=2))

    # ---- build base feature matrix (visible-only strike field) ----
    tag = f"seed{args.seed}"
    feats_path, fmeta = P.build_feature_matrix(tag, fp, visible)
    log["features_base"] = {k:v for k,v in fmeta.items() if k!="names"}
    print("base features ready", fmeta["seconds"], "s")

    # ---- lidar features for footprint ----
    lidar_stack, lidar_src = L.load_lidar_stack()
    lidar_fp = L.extract_lidar_for_footprint(lidar_stack, fp)  # (n_footprint,12) float32
    # cache it
    PROC = ROOT / "data/processed"
    PROC.mkdir(parents=True, exist_ok=True)
    lidar_path = PROC / f"lidar_{tag}.npy"
    np.save(lidar_path, lidar_fp)
    print("lidar features", lidar_fp.shape, "lidar src", lidar_src)

    # ---- leakage canary on all 115 features ----
    base_names = F.feature_names(iso=True, steered=True)  # 103
    lidar_names = L.lidar_feature_names()  # 12
    all_names = base_names + lidar_names
    assert len(all_names)==115
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
    Xc_base = np.asarray(mm[rows[order]], np.float32)
    Xc_lidar = lidar_fp[rows[order]]
    Xc = np.concatenate([Xc_base, Xc_lidar], axis=1)
    yc = y[order]
    canary = {}
    for j, nm in enumerate(all_names):
        auc = float(roc_auc_score(yc, Xc[:, j]))
        canary[nm] = round(max(auc, 1-auc),4)
    flagged = {k:v for k,v in canary.items() if v>0.90}
    log["canary"] = dict(n_pos=int(pos_flat.size), n_neg=int(neg_flat.size), threshold=0.90,
                         flagged_over_0p90=flagged, max_auc=max(canary.values()),
                         top10=sorted(canary.items(), key=lambda kv: -kv[1])[:10], all=canary)
    print("canary max AUC", max(canary.values()), "flagged:", flagged)
    del Xc, Xc_base, Xc_lidar, mm

    # ---- training sample shared ----
    pos, negs = P.training_sample(fp, visible, args.n_neg, seed=args.seed)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    n_base_mm = np.load(feats_path, mmap_mode="r")
    n_lidar = lidar_fp

    # helper to assemble training matrix for an arm
    def arm_columns(arm):
        # match pipeline.arm_columns but with lidar extension
        if arm == "A0_std19":
            return np.array([i for i,n in enumerate(all_names) if n in F.feature_names(iso=False, steered=False)], dtype=np.int64)
        elif arm == "A1_iso":
            return np.array([i for i,n in enumerate(all_names) if n in F.feature_names(iso=True, steered=False)], dtype=np.int64)
        elif arm == "A2_h78_steered":
            return np.array([i for i,n in enumerate(all_names) if n in F.feature_names(iso=True, steered=True)], dtype=np.int64)
        elif arm == "A3_lidar":
            # all 115
            return np.arange(115, dtype=np.int64)
        else:
            raise ValueError(arm)

    # For training we need to load both matrices and concatenate; but arm_columns indexes into concatenated
    # So we create a combined memmap on the fly? Instead we will handle fit_arm_lidar directly
    arms = ["A0_std19","A1_iso","A2_h78_steered","A3_lidar"]
    from sklearn.ensemble import HistGradientBoostingClassifier

    def fit_arm(arm):
        cols = arm_columns(arm)
        # Determine which columns come from base vs lidar
        # base columns are 0..102, lidar 103..114
        base_cols = [c for c in cols if c < 103]
        lidar_cols = [c-103 for c in cols if c >=103]
        rows = np.concatenate([rows_pos, rows_neg])
        order = np.argsort(rows)
        # assemble X
        if base_cols and lidar_cols:
            Xb = np.asarray(n_base_mm[rows[order]][:, base_cols], np.float32)
            Xl = n_lidar[rows[order]][:, lidar_cols]
            X = np.concatenate([Xb, Xl], axis=1)
        elif base_cols:
            X = np.asarray(n_base_mm[rows[order]][:, base_cols], np.float32)
        else:
            X = n_lidar[rows[order]][:, lidar_cols]
        y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
        clf = HistGradientBoostingClassifier(**HGB)
        t0=time.time()
        clf.fit(X,y)
        info = dict(arm=arm, n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), n_features=int(cols.size),
                    params=HGB, fit_seconds=round(time.time()-t0,1))
        return clf, info, cols

    def score_grid_lidar(clf, cols, chunk=600_000):
        n = n_base_mm.shape[0]
        out_fp = np.zeros(n, np.float32)
        base_cols = [c for c in cols if c < 103]
        lidar_cols = [c-103 for c in cols if c >=103]
        for lo in range(0,n,chunk):
            hi=min(n, lo+chunk)
            if base_cols and lidar_cols:
                Xb = np.asarray(n_base_mm[lo:hi][:, base_cols], np.float32)
                Xl = n_lidar[lo:hi][:, lidar_cols]
                X = np.concatenate([Xb, Xl], axis=1)
            elif base_cols:
                X = np.asarray(n_base_mm[lo:hi][:, base_cols], np.float32)
            else:
                X = n_lidar[lo:hi][:, lidar_cols]
            out_fp[lo:hi] = clf.predict_proba(X)[:,1].astype(np.float32)
        grid = np.zeros(fp.shape, np.float32)
        grid[fp] = out_fp
        return grid

    # ---- registry comparators ----
    def read_dots(p):
        with rasterio.open(p) as ds:
            a=ds.read(1)
        return np.isfinite(a) & (a>0)
    comparators = {
        "registry_D2.8_44090": read_dots(ROOT/"data/registry/d28_44090_nan.tif"),
        "registry_H33_37654": read_dots(ROOT/"data/registry/h33_2_b2_37654_zeros.tif"),
    }
    terms_by_arm={}
    results={}
    for name,d in comparators.items():
        t,pf = evaluate_dots(d, folds, fp)
        terms_by_arm[name]=t
        results[name]=dict(per_fold=pf, dots_total=int(d.sum()))
        print(name, EH.from_terms(t.sum(axis=0)))

    scores={}
    for arm in arms:
        clf, info, cols = fit_arm(arm)
        print("fit", info)
        s = score_grid_lidar(clf, cols)
        scores[arm]=s
        np.save(ROOT / f"data/processed/score_{tag}_{arm}.npy", s)
        results[arm]=dict(fit=info, variants={})
        variants = [("nms0_B2", False, 2.0)]
        if arm in ("A2_h78_steered","A3_lidar"):
            variants = [("nms0_B0", False, 0.0), ("nms0_B2", False, 2.0), ("nms1_B2", True, 2.0), ("nms0_B3", False, 3.0)]
        for vname,use_nms,bpx in variants:
            allowed = fp & ~E.flank_mask(visible, bpx)
            if use_nms:
                allowed &= E.ridge_nms(s, sigma=1.0)
            t0=time.time()
            rank = E.greedy_dots(s, allowed, min_dist=2.8, max_dots=max(BUDGETS))
            n_avail=int(rank.max())
            vres=dict(greedy_seconds=round(time.time()-t0,1), dots_available=n_avail, budgets={})
            for n in BUDGETS:
                if n>n_avail: continue
                dots=E.prefix(rank,n)
                t,pf=evaluate_dots(dots, folds, fp)
                key=f"{arm}|{vname}|{n}"
                terms_by_arm[key]=t
                pooled=float(EH.from_terms(t.sum(axis=0)))
                vres["budgets"][str(n)]=dict(pooled_dti=pooled, per_fold=pf, dots_on_visible_catalogue=int((dots & visible).sum()))
                print(f"  {key}: pooled HOLDOUT-DTI {pooled:.4f}")
            results[arm]["variants"][vname]=vres

    # ---- pooled summary ----
    def best_key(prefix):
        ks=[k for k in terms_by_arm if k.startswith(prefix)]
        return max(ks, key=lambda k: EH.from_terms(terms_by_arm[k].sum(axis=0))) if ks else None
    cand = best_key("A3_lidar|")
    summary=None
    if cand:
        sel={cand: terms_by_arm[cand]}
        for a in arms:
            if a!="A3_lidar":
                k=best_key(a+"|")
                if k: sel[k]=terms_by_arm[k]
        _, vname,n = cand.split("|")
        for a in arms:
            k=f"{a}|{vname}|{n}"
            if k in terms_by_arm and k not in sel:
                sel[k]=terms_by_arm[k]
        for c in comparators:
            sel[c]=terms_by_arm[c]
        summary=EH.pooled_summary(sel, draws=1000, seed=520810, candidate=cand)
    log["results"]=results
    log["pooled_summary"]=summary
    log["seconds_total"]=round(time.time()-t_start,1)
    out = Path(args.out) if args.out else ROOT / f"evidence/h79_lidar_holdout_seed{args.seed}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, indent=2, default=float))
    print("wrote", out, "in", log["seconds_total"], "s")

if __name__=="__main__":
    main()
