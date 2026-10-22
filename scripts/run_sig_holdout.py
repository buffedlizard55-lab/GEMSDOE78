#!/usr/bin/env python3
"""Experiment E1 of lane H78-SIGX (preregistration: registry/preregistration_h78sig.json).

Hide-and-recover holdout scored by the UNMODIFIED shared evaluator
(vendor/gems57/evaluate_holdout.py, gems57-pooled-hide-v2), seed 20.

Arms (one shared training sample, one shared emitter; only columns differ):
  CTRL_A2  raw19 + iso + steered (103)   -- reproduced control (repo holdout best)
  SIG100   derivatives only (84)         -- ablation: removal of raw habitat bands
  SIGX     derivatives + 18 external     -- the candidate

Endpoints: overall pooled HOLDOUT-DTI for flank B in {3,5} x budget
{37654, 44090}; far strata (>10 px, >20 px from the visible catalogue,
definition identical to scripts/diagnose_distance.py) for the @44090 configs;
registry D2.8 / H33 dots-as-is and a uniform-random control as comparators.
Every number written to the output JSON is HOLDOUT-DTI.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import sigx as SX  # noqa: E402

BUDGETS = [37_654, 44_090]
FLANKS = [3.0, 5.0]


def evaluate_dots(dots, folds, footprint, truth_mask=None):
    pred = dots.astype(np.float32)
    terms, per_fold = None, {}
    for f in folds:
        f2 = f if truth_mask is None else {**f, "truth": f["truth"] & truth_mask}
        if truth_mask is not None and not f2["truth"].any():
            continue
        r, t = EH.evaluate(pred, f2, footprint, block_side=200, origin=(0, 0),
                           global_shape=footprint.shape)
        per_fold[f["name"]] = dict(dti=r["dti"], tp=r["tp"], fp=r["fp"], fn=r["fn"],
                                   n_truth=r["n_truth"], n_emitted=r["n_emitted"])
        terms = t if terms is None else terms + t
    return terms, per_fold


def read_dots(p):
    with rasterio.open(p) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20)
    ap.add_argument("--n-neg", type=int, default=450_000)
    args = ap.parse_args()
    t_start = time.time()

    g = G.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    folds, _ = HO.buffered_component_draw(g, seed=args.seed, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    log = dict(lane="H78-SIGX", experiment="E1", evidence_class="HOLDOUT-DTI",
               evaluator_version=EH.VERSION, evaluator_sha256=EH.implementation_hashes(),
               seed=args.seed, hide_frac=0.20, buffer_px=3,
               fold_receipts=[f["receipt"] for f in folds],
               visible_px=int(visible.sum()), hidden_px=int(hidden.sum()),
               withheld_positive_pixels_scored=int(sum(int(f["truth"].sum()) for f in folds)))
    print(json.dumps({k: v for k, v in log.items() if k != "evaluator_sha256"}, indent=1), flush=True)

    tag = f"seed{args.seed}"
    feats_sigx, smeta = SX.build_sigx_matrix(tag, fp, visible)
    feats_base = ROOT / "data" / "processed" / f"feats_{tag}.npy"
    log["features"] = {k: v for k, v in smeta.items() if k != "names"}
    print(f"[features] sigx matrix ready in {smeta['seconds']} s", flush=True)

    # ---- leakage canary on candidate features (gate G2) ----
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
    mm = np.load(feats_sigx, mmap_mode="r")
    order = np.argsort(rows)
    Xc = np.asarray(mm[rows[order]], np.float32)
    yc = y[order]
    names = SX.sigx_names()
    canary = {}
    for j, nm in enumerate(names):
        auc = float(roc_auc_score(yc, Xc[:, j]))
        canary[nm] = round(max(auc, 1 - auc), 4)
    flagged = {k: v for k, v in canary.items() if v > 0.90}
    ext_canary = {k: canary[k] for k in SX.ext_names()}
    log["canary"] = dict(n_pos=int(pos_flat.size), n_neg=int(neg_flat.size), threshold=0.90,
                         flagged_over_0p90=flagged, max_auc=max(canary.values()),
                         ext_max_auc=max(ext_canary.values()), ext_all=ext_canary,
                         top10=sorted(canary.items(), key=lambda kv: -kv[1])[:10], all=canary)
    print(f"[canary] max AUC {max(canary.values())} (ext max {max(ext_canary.values())}) flagged: {flagged}", flush=True)
    del Xc, yc, mm
    if flagged:
        log["verdict"] = "STOP: leakage canary"
        out = ROOT / "evidence" / f"h78sig_holdout_seed{args.seed}.json"
        out.write_text(json.dumps(log, indent=2))
        print("STOP", out, flush=True)
        return

    # ---- shared training sample ----
    pos, negs = P.training_sample(fp, visible, args.n_neg, seed=args.seed)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)

    arms = {
        "CTRL_A2": (feats_base, np.arange(103)),
        "SIG100": (feats_sigx, np.arange(84)),
        "SIGX": (feats_sigx, np.arange(102)),
    }
    scores, results, terms_by_key, dots_by_key = {}, {}, {}, {}
    dvis = ndi.distance_transform_edt(~visible)
    for arm, (path, cols) in arms.items():
        clf, info = SX.fit_cols(path, rows_pos, rows_neg, cols, arm)
        s = SX.score_cols(clf, path, cols, fp)
        scores[arm] = s
        np.save(ROOT / "data" / "processed" / f"score_sig_seed{args.seed}_{arm}.npy", s)
        results[arm] = dict(fit=info, configs={})
        print(f"[fit] {arm} {info}", flush=True)
        for bpx in FLANKS:
            rank = E.greedy_dots(s, fp & ~E.flank_mask(visible, bpx), min_dist=2.8,
                                 max_dots=max(BUDGETS))
            for n in BUDGETS:
                key = f"{arm}|B{int(bpx)}|{n}"
                dots = E.prefix(rank, n)
                dots_by_key[key] = dots
                t, pf = evaluate_dots(dots, folds, fp)
                terms_by_key[key] = t
                pooled = float(EH.from_terms(t.sum(axis=0)))
                results[arm]["configs"][key] = dict(
                    pooled_dti=pooled, per_fold=pf,
                    dots_on_visible_catalogue=int((dots & visible).sum()),
                    dot_dist_to_visible_median_px=float(np.median(dvis[dots])))
                print(f"  {key}: pooled HOLDOUT-DTI {pooled:.4f}", flush=True)
        del clf, s

    # ---- surface decorrelation vs CTRL surface (pre-placement diagnostic) ----
    rho = {}
    base_surf = scores["CTRL_A2"][fp]
    for arm in ("SIG100", "SIGX"):
        rho[arm] = float(spearmanr(scores[arm][fp], base_surf).statistic)
    log["surface_spearman_vs_CTRL_A2_full_footprint"] = rho
    print(f"[surface] Spearman vs CTRL_A2: {rho}", flush=True)

    # ---- comparators ----
    comparators = {
        "registry_D2.8_44090": read_dots(ROOT / "data/registry/d28_44090_nan.tif"),
        "registry_H33_37654": read_dots(ROOT / "data/registry/h33_2_b2_37654_zeros.tif"),
    }
    rng_r = np.random.default_rng(123)
    rand_surf = rng_r.random(fp.shape, dtype=np.float32)
    rand_rank = E.greedy_dots(rand_surf, fp & ~E.flank_mask(visible, 3.0), min_dist=2.8,
                              max_dots=max(BUDGETS))
    comparators["random_B3_44090"] = E.prefix(rand_rank, 44_090)
    del rand_surf
    comp_results = {}
    for name, d in comparators.items():
        dots_by_key[name] = d
        t, pf = evaluate_dots(d, folds, fp)
        terms_by_key[name] = t
        comp_results[name] = dict(pooled_dti=float(EH.from_terms(t.sum(axis=0))),
                                  per_fold=pf, dots_total=int(d.sum()))
        print(f"  {name}: pooled HOLDOUT-DTI {comp_results[name]['pooled_dti']:.4f}", flush=True)

    # ---- far strata for @44090 configs ----
    strata = {}
    keys_44 = [k for k in terms_by_key if k.endswith("|44090")] + \
              ["registry_D2.8_44090", "random_B3_44090"]
    for sname, smask in (("far_gt10px", dvis > 10), ("far_gt20px", dvis > 20)):
        sterms, sper = {}, {}
        for k in keys_44:
            t, pf = evaluate_dots(dots_by_key[k], folds, fp, truth_mask=smask)
            sterms[k] = t
            sper[k] = dict(pooled_dti=float(EH.from_terms(t.sum(axis=0))), per_fold=pf)
        strata[sname] = dict(dti={k: v["pooled_dti"] for k, v in sper.items()},
                             n_truth=int((hidden & smask & fp).sum()),
                             per_config=sper,
                             terms={k: v.tolist() for k, v in sterms.items()})
        print(f"[{sname}] " + json.dumps({k: round(v, 4) for k, v in strata[sname]["dti"].items()}), flush=True)

    # ---- pooled CIs: overall, candidate = SIGX config selected by far>10 rule ----
    far = strata["far_gt10px"]["dti"]
    cand44 = max((f"SIGX|B{b}|44090" for b in (3, 5)), key=lambda k: far[k])
    sel = {cand44: terms_by_key[cand44],
           f"SIGX|B{3 if cand44.startswith('SIGX|B5') else 5}|44090":
               terms_by_key[f"SIGX|B{3 if cand44.startswith('SIGX|B5') else 5}|44090"],
           "SIG100|B3|44090": terms_by_key["SIG100|B3|44090"],
           "CTRL_A2|B3|44090": terms_by_key["CTRL_A2|B3|44090"],
           "CTRL_A2|B5|44090": terms_by_key["CTRL_A2|B5|44090"],
           "registry_D2.8_44090": terms_by_key["registry_D2.8_44090"],
           "random_B3_44090": terms_by_key["random_B3_44090"]}
    summary_overall = EH.pooled_summary(sel, draws=1000, seed=520810, candidate=cand44)
    sterms44 = {k: np.asarray(strata["far_gt10px"]["terms"][k]) for k in sel}
    summary_far10 = EH.pooled_summary(sterms44, draws=1000, seed=520810, candidate=cand44)
    sterms44_20 = {k: np.asarray(strata["far_gt20px"]["terms"][k]) for k in sel}
    summary_far20 = EH.pooled_summary(sterms44_20, draws=1000, seed=520810, candidate=cand44)
    for s in (strata["far_gt10px"], strata["far_gt20px"]):
        s.pop("terms", None)

    log["results"] = results
    log["comparators"] = comp_results
    log["strata"] = strata
    log["selected_candidate_config_by_far10_rule"] = cand44
    log["pooled_summary_overall"] = summary_overall
    log["pooled_summary_far_gt10px"] = summary_far10
    log["pooled_summary_far_gt20px"] = summary_far20
    log["seconds_total"] = round(time.time() - t_start, 1)
    out = ROOT / "evidence" / f"h78sig_holdout_seed{args.seed}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, indent=2))
    print(f"DONE {out} in {log['seconds_total']} s", flush=True)


if __name__ == "__main__":
    main()
