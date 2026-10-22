#!/usr/bin/env python3
"""Experiment E2 of lane H78-SIGX: rank fusion of the E1 CTRL_A2 and SIGX surfaces.

Preregistration: registry/preregistration_h78sig_e2_amendment.json.
No new learner; re-emits and re-scores with the UNMODIFIED shared evaluator
(vendor/gems57/evaluate_holdout.py). All numbers are HOLDOUT-DTI.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems78 import emit as E  # noqa: E402

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


def forward_overlap(mine, theirs, radius=3.0):
    if mine.sum() == 0:
        return float("nan")
    d = ndi.distance_transform_edt(~theirs)
    return float((d[mine] <= radius).mean())


def read_dots(p):
    with rasterio.open(p) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def main():
    t_start = time.time()
    g = G.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    folds, _ = HO.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    dvis = ndi.distance_transform_edt(~visible)

    s_ctrl = np.load(ROOT / "data/processed/score_sig_seed20_CTRL_A2.npy")
    s_sigx = np.load(ROOT / "data/processed/score_sig_seed20_SIGX.npy")
    fuse = np.zeros(fp.shape, np.float32)
    r = (rankdata(s_ctrl[fp]) + rankdata(s_sigx[fp])) / (2.0 * int(fp.sum()))
    fuse[fp] = r.astype(np.float32)
    del r
    np.save(ROOT / "data/processed/score_sig_seed20_FUSE.npy", fuse)
    log = dict(lane="H78-SIGX", experiment="E2 rank fusion", evidence_class="HOLDOUT-DTI",
               evaluator_version=EH.VERSION, evaluator_sha256=EH.implementation_hashes(),
               seed=20, withheld_positive_pixels_scored=int(sum(int(f["truth"].sum()) for f in folds)),
               surface_spearman=dict(
                   FUSE_vs_CTRL=float(spearmanr(fuse[fp], s_ctrl[fp]).statistic),
                   FUSE_vs_SIGX=float(spearmanr(fuse[fp], s_sigx[fp]).statistic)))

    surfaces = {"FUSE": fuse, "CTRL_A2": s_ctrl, "SIGX": s_sigx}
    terms_by_key, dots_by_key, results = {}, {}, {}
    for arm, s in surfaces.items():
        for bpx in FLANKS:
            rank = E.greedy_dots(s, fp & ~E.flank_mask(visible, bpx), min_dist=2.8,
                                 max_dots=max(BUDGETS))
            for n in BUDGETS:
                key = f"{arm}|B{int(bpx)}|{n}"
                dots = E.prefix(rank, n)
                dots_by_key[key] = dots
                t, pf = evaluate_dots(dots, folds, fp)
                terms_by_key[key] = t
                results[key] = dict(pooled_dti=float(EH.from_terms(t.sum(axis=0))), per_fold=pf)
                print(f"{key}: pooled HOLDOUT-DTI {results[key]['pooled_dti']:.4f}", flush=True)
    for name, p in (("registry_D2.8_44090", ROOT / "data/registry/d28_44090_nan.tif"),):
        d = read_dots(p)
        dots_by_key[name] = d
        t, pf = evaluate_dots(d, folds, fp)
        terms_by_key[name] = t
        results[name] = dict(pooled_dti=float(EH.from_terms(t.sum(axis=0))), per_fold=pf)
        print(f"{name}: pooled HOLDOUT-DTI {results[name]['pooled_dti']:.4f}", flush=True)

    strata = {}
    keys_44 = [k for k in results if k.endswith("|44090")] + ["registry_D2.8_44090"]
    strata_terms = {}
    for sname, smask in (("far_gt10px", dvis > 10), ("far_gt20px", dvis > 20)):
        sterms, sdti = {}, {}
        for k in keys_44:
            t, _ = evaluate_dots(dots_by_key[k], folds, fp, truth_mask=smask)
            sterms[k] = t
            sdti[k] = float(EH.from_terms(t.sum(axis=0)))
        strata_terms[sname] = sterms
        strata[sname] = sdti
        print(f"[{sname}] " + json.dumps({k: round(v, 4) for k, v in sdti.items()}), flush=True)

    cand = max((f"FUSE|B{b}|44090" for b in (3, 5)), key=lambda k: strata["far_gt10px"][k])
    sel_keys = [cand, "FUSE|B3|44090" if cand != "FUSE|B3|44090" else "FUSE|B5|44090",
                "CTRL_A2|B3|44090", "CTRL_A2|B5|44090", "SIGX|B5|44090", "registry_D2.8_44090"]
    log["selected_candidate_config_by_far10_rule"] = cand
    log["results"] = results
    log["strata"] = strata
    log["pooled_summary_overall"] = EH.pooled_summary(
        {k: terms_by_key[k] for k in sel_keys}, draws=1000, seed=520810, candidate=cand)
    log["pooled_summary_far_gt10px"] = EH.pooled_summary(
        {k: strata_terms["far_gt10px"][k] for k in sel_keys}, draws=1000, seed=520810, candidate=cand)
    log["pooled_summary_far_gt20px"] = EH.pooled_summary(
        {k: strata_terms["far_gt20px"][k] for k in sel_keys}, draws=1000, seed=520810, candidate=cand)

    h78a = read_dots(ROOT / "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif")
    h33 = read_dots(ROOT / "data/registry/h33_2_b2_37654_zeros.tif")
    d28 = dots_by_key["registry_D2.8_44090"]
    log["uniqueness_precheck_forward_overlap_3px"] = {
        k: dict(vs_H78A_production=forward_overlap(dots_by_key[k], h78a),
                vs_H33=forward_overlap(dots_by_key[k], h33),
                vs_D2_8=forward_overlap(dots_by_key[k], d28))
        for k in keys_44}
    print(json.dumps(log["uniqueness_precheck_forward_overlap_3px"], indent=1), flush=True)
    log["seconds_total"] = round(time.time() - t_start, 1)
    out = ROOT / "evidence" / "h78sig_e2_fuse_seed20.json"
    out.write_text(json.dumps(log, indent=2))
    print(f"DONE {out} in {log['seconds_total']} s", flush=True)


if __name__ == "__main__":
    main()
