#!/usr/bin/env python3
"""Experiment 2 of lane H78-STEP — COMPLEMENTARITY DIAGNOSTIC ONLY.

Declared in registry/preregistration_h78step.json amendment IR-78STEP-A1
*before* this run, after experiment 1 returned a significant negative for the
preregistered candidate. One extra arm DIAG_A2STEP (103 H78-A features + 54
STEP features) on the identical seed-20 folds/rows/emitter, reusing the cached
feature matrices and the saved CTRL_A2 / CAND_STEP score grids from
experiment 1. This diagnostic CANNOT promote the lane under any outcome (an
append to the H78-A stack is inside the H78-A lane); it exists to tell future
sessions whether STEP signal is redundant with steered derivatives or
complementary but imprecisely localised.

Output: evidence/h78step_append_diag_seed20.json
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import uniqueness as U  # noqa: E402
from gems78 import data as D  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from run_holdout_step import HGB, evaluate_dots, log  # noqa: E402  (scripts dir on path below)

PRIMARY = 44_090
BUDGETS = [37_654, 44_090, 50_000]


def main():
    sys.path.insert(0, str(ROOT / "scripts"))
    t_start = time.time()
    seed = 20
    D.verify_inputs()
    g = G.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    folds, _ = HO.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    assert int(folds[0]["hidden_all"].sum()) == 11_321
    tag = f"seed{seed}"
    # cached matrices from experiment 1 (build_* are no-ops if present)
    feats_path, _ = P.build_feature_matrix(tag, fp, visible)
    from gems78 import step as S
    phi = np.load(D.PROC / f"phi_{tag}.npy")
    step_path, _ = S.build_step_matrix(tag, fp, phi)
    del phi
    base_mm = np.load(feats_path, mmap_mode="r")
    step_mm = np.load(step_path, mmap_mode="r")

    pos, negs = P.training_sample(fp, visible, 450_000, seed=seed)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    X = np.concatenate([np.asarray(base_mm[rows[order]], np.float32),
                        np.asarray(step_mm[rows[order]], np.float32)], axis=1)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    assert X.shape[1] == 157 and np.isfinite(X).all()
    clf = HistGradientBoostingClassifier(**HGB)
    t0 = time.time()
    clf.fit(X, y)
    fit_info = dict(arm="DIAG_A2STEP", n_pos=int(rows_pos.size), n_neg=int(rows_neg.size),
                    n_features=int(X.shape[1]), params=HGB, fit_seconds=round(time.time() - t0, 1))
    del X, y
    gc.collect()
    log("fit", fit_info)

    n = base_mm.shape[0]
    s_diag = np.zeros(fp.shape, np.float32)
    out = np.zeros(n, np.float32)
    for lo in range(0, n, 600_000):
        hi = min(n, lo + 600_000)
        Xc = np.concatenate([np.asarray(base_mm[lo:hi], np.float32),
                             np.asarray(step_mm[lo:hi], np.float32)], axis=1)
        out[lo:hi] = clf.predict_proba(Xc)[:, 1].astype(np.float32)
        del Xc
    del clf
    s_diag[fp] = out
    del out
    np.save(D.PROC / f"score_{tag}_DIAG_A2STEP.npy", s_diag)

    s_ctrl = np.load(D.PROC / f"score_{tag}_CTRL_A2.npy")
    s_cand = np.load(D.PROC / f"score_{tag}_CAND_STEP.npy")
    rho_diag_ctrl = U.surface_rho(s_diag, s_ctrl, fp)
    log("surface rho DIAG vs CTRL", rho_diag_ctrl)

    d_vis = ndi.distance_transform_edt(~np.asarray(visible, bool))
    far_folds = []
    for f in folds:
        ff = dict(f)
        ff["truth"] = np.asarray(f["truth"], bool) & (d_vis > 10.0)
        far_folds.append(ff)
    del d_vis

    allowed = fp & ~E.flank_mask(visible, 3.0)
    terms, terms_far, configs = {}, {}, {}
    dots_primary = {}
    for arm, s in (("CTRL_A2", s_ctrl), ("CAND_STEP", s_cand), ("DIAG_A2STEP", s_diag)):
        rank = E.greedy_dots(s, allowed, min_dist=2.8, max_dots=60_000, pool=1_500_000)
        for nb in BUDGETS:
            dots = E.prefix(rank, nb)
            t, pf = evaluate_dots(dots, folds, fp)
            key = f"{arm}|B3|{nb}"
            configs[key] = dict(pooled_dti=float(EH.from_terms(t.sum(axis=0))), per_fold=pf)
            log(" ", key, "HOLDOUT-DTI", round(configs[key]["pooled_dti"], 4))
            if nb == PRIMARY:
                terms[key] = t
                dots_primary[arm] = dots
                tf, _ = evaluate_dots(dots, far_folds, fp)
                terms_far[key] = tf
        del rank
    fwd_diag_in_ctrl = U.dot_overlap(dots_primary["DIAG_A2STEP"].astype(np.float32),
                                     dots_primary["CTRL_A2"].astype(np.float32), 3.0)
    fwd_cand_in_ctrl = U.dot_overlap(dots_primary["CAND_STEP"].astype(np.float32),
                                     dots_primary["CTRL_A2"].astype(np.float32), 3.0)
    diag_key = f"DIAG_A2STEP|B3|{PRIMARY}"
    summary = EH.pooled_summary(terms, draws=1000, seed=520810, candidate=diag_key)
    far_summary = EH.pooled_summary(terms_far, draws=1000, seed=520810, candidate=diag_key)

    out = dict(
        lane="H78-STEP experiment 2 (complementarity diagnostic, IR-78STEP-A1)",
        evidence_class="HOLDOUT-DTI", diagnostic_only=True, cannot_promote=True,
        evaluator_version=EH.VERSION, evaluator_sha256=EH.implementation_hashes(),
        seed=seed, withheld_positive_pixels_scored=11_321,
        fit=fit_info, configs=configs,
        pooled_summary_B3_primary=summary,
        pooled_summary_far_truth_gt10px_B3_primary=far_summary,
        surface_rho_diag_vs_ctrl=rho_diag_ctrl,
        forward_3px_overlap=dict(diag_dots_within_3px_of_ctrl_dots=fwd_diag_in_ctrl,
                                 cand_dots_within_3px_of_ctrl_dots=fwd_cand_in_ctrl,
                                 note="holdout-fold dot sets at B3/44090; diagnostic of lane duplication, not the production registry audit"),
        seconds_total=round(time.time() - t_start, 1),
    )
    outp = ROOT / "evidence" / "h78step_append_diag_seed20.json"
    outp.write_text(json.dumps(out, indent=2, default=float))
    log("wrote", outp, "in", out["seconds_total"], "s")
    print(json.dumps({k: (round(v["dti"], 4), [round(x, 4) for x in v["ci95"]])
                        for k, v in summary["scores"].items()}, indent=1))
    print(json.dumps({k: (round(v["delta"], 4), [round(x, 4) for x in v["ci95"]])
                        for k, v in summary["paired_differences"].items()}, indent=1))


if __name__ == "__main__":
    main()
