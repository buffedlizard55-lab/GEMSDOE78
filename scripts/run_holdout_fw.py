#!/usr/bin/env python3
"""Experiment 1 of lane H78-FW (preregistered in registry/preregistration_h78fw.json).

Evaluates multi-scale antisymmetric footwall/hangingwall flank-warp features
(src/gems78/flank_warp.py) on the buffered whole-component hide-and-recover
holdout (seed 20, 11,321 withheld positive pixels) using the UNMODIFIED shared
evaluator (vendor/gems57/evaluate_holdout.py, version gems57-pooled-hide-v2).

Arms compared on identical folds, training rows, learner hyperparameters, and
greedy >=2.8 px emitter:
  * CAND_FW_PURE   -- 67 H78-FW flank-warp + central-discontinuity + strain features
                      (zero centred H78-A Gaussian derivatives, zero catalogue location)
  * ABL_FW_PLUS_A2 -- 67 H78-FW + 103 H78-A features (170 features)
  * CTRL_A2        -- 103 H78-A features reproduced on the v2-verified feature stack
  * CTRL_A0        -- 19 raw bands (base model class control)
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
from gems78 import flank_warp as FW  # noqa: E402
from gems78 import pipeline as P  # noqa: E402

HGB = dict(
    max_iter=300,
    learning_rate=0.06,
    max_leaf_nodes=63,
    min_samples_leaf=200,
    l2_regularization=1.0,
    max_bins=255,
    early_stopping=False,
    random_state=0,
)
BUDGETS_B3 = [37_654, 44_090, 50_000]
PRIMARY = 44_090


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def assemble(base_mm, fw_mm, rows, base_cols, use_fw: bool):
    parts = []
    if base_cols is not None and len(base_cols) > 0:
        parts.append(np.asarray(base_mm[rows][:, base_cols], np.float32))
    if use_fw:
        parts.append(np.asarray(fw_mm[rows], np.float32))
    if len(parts) == 1:
        return parts[0]
    return np.concatenate(parts, axis=1)


def fit_arm(base_mm, fw_mm, rows_pos, rows_neg, base_cols, use_fw: bool, label: str):
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    X = assemble(base_mm, fw_mm, rows[order], base_cols, use_fw)
    y = np.concatenate([
        np.ones(rows_pos.size, np.int8),
        np.zeros(rows_neg.size, np.int8),
    ])[order]
    clf = HistGradientBoostingClassifier(**HGB)
    t0 = time.time()
    clf.fit(X, y)
    info = dict(
        arm=label,
        n_pos=int(rows_pos.size),
        n_neg=int(rows_neg.size),
        n_features=int(X.shape[1]),
        params=HGB,
        fit_seconds=round(time.time() - t0, 1),
    )
    del X, y
    gc.collect()
    log("fit", info)
    return clf, info


def score_arm(clf, base_mm, fw_mm, base_cols, use_fw: bool, footprint: np.ndarray, chunk: int = 600_000):
    n = fw_mm.shape[0]
    out = np.zeros(n, np.float32)
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        X = assemble(base_mm, fw_mm, np.arange(lo, hi), base_cols, use_fw)
        out[lo:hi] = clf.predict_proba(X)[:, 1].astype(np.float32)
        del X
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out
    return grid


def evaluate_dots(dots, folds, footprint):
    pred = dots.astype(np.float32)
    terms = None
    per_fold = {}
    for f in folds:
        r, t = EH.evaluate(
            pred, f, footprint, block_side=200, origin=(0, 0), global_shape=footprint.shape
        )
        per_fold[f["name"]] = dict(
            dti=r["dti"], n_truth=r["n_truth"], n_emitted=r["n_emitted"]
        )
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
    folds, _ = HO.buffered_component_draw(g, seed=args.seed, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    n_hidden = int(hidden.sum())
    n_scored = int(sum(int(f["truth"].sum()) for f in folds))
    log("visible", int(visible.sum()), "hidden", n_hidden, "scored", n_scored)
    if args.seed == 20:
        assert n_hidden == 11_321 and n_scored == 11_321, "instrument precondition failed"

    tag = f"seed{args.seed}"
    feats_path, fmeta = P.build_feature_matrix(tag, fp, visible)
    phi = np.load(D.PROC / f"phi_{tag}.npy")
    coh = np.load(D.PROC / f"coh_{tag}.npy")
    fw_path, fwmeta = FW.build_fw_matrix(tag, fp, phi, coh)
    del phi, coh
    gc.collect()
    log("features ready base", fmeta["seconds"], "s fw", fwmeta["seconds"], "s")

    base_names = F.feature_names(iso=True, steered=True)
    fw_names = FW.fw_feature_names()
    base_mm = np.load(feats_path, mmap_mode="r")
    fw_mm = np.load(fw_path, mmap_mode="r")
    assert base_mm.shape[1] == 103 and fw_mm.shape[1] == 67 and base_mm.shape[0] == fw_mm.shape[0]

    # ---- leakage canary: single-feature symmetric AUC on withheld truth vs active bg ----
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
    Xb_c = np.asarray(base_mm[rows[order]], np.float32)
    Xfw_c = np.asarray(fw_mm[rows[order]], np.float32)
    yc = y[order]

    canary_base = {}
    for j, nm in enumerate(base_names):
        auc = float(roc_auc_score(yc, Xb_c[:, j]))
        canary_base[nm] = round(max(auc, 1.0 - auc), 4)
    canary_fw = {}
    for j, nm in enumerate(fw_names):
        auc = float(roc_auc_score(yc, Xfw_c[:, j]))
        canary_fw[nm] = round(max(auc, 1.0 - auc), 4)
    del Xb_c, Xfw_c, yc
    gc.collect()

    all_canary = {**canary_base, **canary_fw}
    flagged = {k: v for k, v in all_canary.items() if v > 0.90}
    log("canary max overall", max(all_canary.values()), "FW max", max(canary_fw.values()), "flagged", flagged)
    assert not flagged, f"LEAKAGE CANARY STOP: {flagged}"

    # ---- shared training sample ----
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
        "CAND_FW_PURE": (None, True),
        "ABL_FW_PLUS_A2": (P.arm_columns("A2_h78_steered"), True),
        "CTRL_A2": (P.arm_columns("A2_h78_steered"), False),
        "CTRL_A0": (P.arm_columns("A0_std19"), False),
    }
    terms_all, terms_far = {}, {}
    results = {}
    scores = {}
    allowed = {
        3.0: fp & ~E.flank_mask(visible, 3.0),
        2.0: fp & ~E.flank_mask(visible, 2.0),
    }

    for arm, (cols, use_fw) in arms.items():
        score_path = D.PROC / f"score_{tag}_{arm}.npy"
        if score_path.exists():
            s = np.load(score_path)
            info = dict(
                arm=arm,
                n_pos=int(rows_pos.size),
                n_neg=int(rows_neg.size),
                n_features=(67 if cols is None else int(len(cols)) + (67 if use_fw else 0)),
                params=HGB,
                cached_score=True,
            )
            log("loaded cached score", arm)
        else:
            clf, info = fit_arm(base_mm, fw_mm, rows_pos, rows_neg, cols, use_fw, arm)
            s = score_arm(clf, base_mm, fw_mm, cols, use_fw, fp)
            del clf
            gc.collect()
            np.save(score_path, s)
        results[arm] = dict(fit=info, configs={})
        for bpx, budgets in ((3.0, BUDGETS_B3), (2.0, [PRIMARY])):
            tag_b = f"B{int(bpx)}"
            t0 = time.time()
            rank = E.greedy_dots(s, allowed[bpx], min_dist=2.8, max_dots=max(budgets), pool=1_500_000)
            gsec = round(time.time() - t0, 1)
            for n in budgets:
                dots = E.prefix(rank, n)
                key = f"{arm}|{tag_b}|{n}"
                t, pf = evaluate_dots(dots, folds, fp)
                terms_all[key] = t
                dti = float(EH.from_terms(t.sum(axis=0)))
                results[arm]["configs"][key] = dict(
                    pooled_dti=dti, per_fold=pf, greedy_seconds=gsec,
                    dots_on_visible=int((dots & visible).sum())
                )
                log(f"  {key}: HOLDOUT-DTI {dti:.4f}")
                if bpx == 3.0 and n == PRIMARY:
                    tf, _ = evaluate_dots(dots, far_folds, fp)
                    terms_far[key] = tf
                    log(f"  {key} far>10px: HOLDOUT-DTI {float(EH.from_terms(tf.sum(axis=0))):.4f}")
            del rank
        del s
        gc.collect()

    s_fw = np.load(D.PROC / f"score_{tag}_CAND_FW_PURE.npy")
    s_abl = np.load(D.PROC / f"score_{tag}_ABL_FW_PLUS_A2.npy")
    s_a2 = np.load(D.PROC / f"score_{tag}_CTRL_A2.npy")
    surf_rho_fw_vs_a2 = U.surface_rho(s_fw, s_a2, fp)
    surf_rho_abl_vs_a2 = U.surface_rho(s_abl, s_a2, fp)
    log("surface rho CAND_FW_PURE vs CTRL_A2:", surf_rho_fw_vs_a2)
    log("surface rho ABL_FW_PLUS_A2 vs CTRL_A2:", surf_rho_abl_vs_a2)
    del s_fw, s_abl, s_a2
    gc.collect()

    primary_keys = [f"{a}|B3|{PRIMARY}" for a in arms]
    summary_primary = EH.pooled_summary(
        {k: terms_all[k] for k in primary_keys},
        draws=1000, seed=520810, candidate=f"CAND_FW_PURE|B3|{PRIMARY}"
    )
    summary_abl = EH.pooled_summary(
        {k: terms_all[k] for k in primary_keys},
        draws=1000, seed=520810, candidate=f"ABL_FW_PLUS_A2|B3|{PRIMARY}"
    )
    summary_far = EH.pooled_summary(
        terms_far, draws=1000, seed=520810, candidate=f"CAND_FW_PURE|B3|{PRIMARY}"
    )

    out = dict(
        lane="H78-FW",
        preregistration="registry/preregistration_h78fw.json",
        evaluator_version=EH.VERSION,
        evaluator_sha256=EH.implementation_hashes(),
        input_sha256={k: v["sha256"] for k, v in inputs.items()},
        stack_cache_meta=json.loads((D.PROC / "stack19_cache.json").read_text()),
        seed=args.seed,
        hide_frac=0.20,
        buffer_px=3,
        visible_px=int(visible.sum()),
        withheld_positive_pixels_scored=n_scored,
        far_truth_gt10px_positives=n_far,
        features=dict(
            base={k: v for k, v in fmeta.items() if k != "names"},
            fw={k: v for k, v in fwmeta.items() if k != "names"},
            fw_names=fw_names,
        ),
        canary=dict(
            n_pos=int(pos_flat.size),
            n_neg=int(neg_flat.size),
            threshold=0.90,
            flagged_over_0p90=flagged,
            max_auc_all_170=max(all_canary.values()),
            max_auc_fw_67=max(canary_fw.values()),
            fw_features=canary_fw,
            top10_all=sorted(all_canary.items(), key=lambda kv: -kv[1])[:10],
            top10_fw=sorted(canary_fw.items(), key=lambda kv: -kv[1])[:10],
        ),
        surface_rho_fw_pure_vs_ctrl_a2=surf_rho_fw_vs_a2,
        surface_rho_fw_plus_a2_vs_ctrl_a2=surf_rho_abl_vs_a2,
        results=results,
        pooled_summary_B3_primary=summary_primary,
        pooled_summary_B3_ablation_fw_plus_a2=summary_abl,
        pooled_summary_far_truth_gt10px_B3_primary=summary_far,
        seconds_total=round(time.time() - t_start, 1),
    )
    def _sanitize_for_json(obj):
        if isinstance(obj, float):
            return None if not np.isfinite(obj) else obj
        if isinstance(obj, dict):
            return {k: _sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_sanitize_for_json(v) for v in obj]
        return obj

    out_p = ROOT / "evidence" / f"h78fw_holdout_seed{args.seed}.json"
    out_p.write_text(json.dumps(_sanitize_for_json(out), indent=2, default=float, allow_nan=False) + "\n")
    log("WROTE", out_p, "in", out["seconds_total"], "s")


if __name__ == "__main__":
    main()
