#!/usr/bin/env python3
"""E1 (+ conditional E2) of lane H78-TOOTH.

Hide-and-recover holdout, evaluator vendor/gems57/evaluate_holdout.py
(gems57-pooled-hide-v2, unmodified). The candidate adds missing-tooth
features to the existing strike-steered columns. The control is that
learner without them, same sample, same emitter. See
registry/preregistration_h78_tooth.json, which was written first.
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
from gems57 import uniqueness as U  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import features as F  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78.tooth import FEATURE_NAMES, missing_tooth_fields, sample_fields  # noqa: E402

BUDGETS = (37_654, 44_090, 50_000)
MATCHED_BUDGET = 44_090
FLANK = 3.0
MIN_DIST = 2.8
POOL = 400_000  # same default run_holdout.py used for the published 0.1826
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
            dti=result["dti"], tp=result["tp"], fp=result["fp"], fn=result["fn"],
            n_truth=result["n_truth"], n_emitted=result["n_emitted"],
        )
        terms = block if terms is None else terms + block
    return terms, per_fold


def fit_and_score(feats_path, extra, rows_pos, rows_neg, footprint, use_extra, seed=0):
    cols = P.arm_columns("A2_h78_steered")
    mm = np.load(feats_path, mmap_mode="r")
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows, kind="stable")
    X = np.asarray(mm[rows[order]][:, cols], np.float32)
    if use_extra:
        X = np.hstack([X, np.asarray(extra[rows[order]], np.float32)])
    y = np.concatenate([
        np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)
    ])[order]
    clf = HistGradientBoostingClassifier(**{**HGB, "random_state": seed})
    t0 = time.time()
    clf.fit(X, y)
    info = dict(n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), n_features=int(X.shape[1]),
                use_extra=use_extra, fit_seconds=round(time.time() - t0, 1), params=HGB)
    del X, y
    n = mm.shape[0]
    out_fp = np.empty(n, np.float32)
    chunk = 500_000
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        block = np.asarray(mm[lo:hi][:, cols], np.float32)
        if use_extra:
            block = np.hstack([block, np.asarray(extra[lo:hi], np.float32)])
        out_fp[lo:hi] = clf.predict_proba(block)[:, 1].astype(np.float32)
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out_fp
    return clf, info, grid


def emit_budgets(score, allowed, folds, footprint, budgets):
    t0 = time.time()
    rank = E.greedy_dots(score, allowed, min_dist=MIN_DIST, max_dots=max(budgets), pool=POOL)
    out = dict(greedy_seconds=round(time.time() - t0, 1), dots_available=int(rank.max()), budgets={})
    terms = {}
    for n in budgets:
        if n > out["dots_available"]:
            continue
        dots = E.prefix(rank, n)
        block, per_fold = evaluate_dots(dots, folds, footprint)
        key = str(n)
        terms[key] = block
        out["budgets"][key] = dict(
            pooled_dti=float(EH.from_terms(block.sum(axis=0))),
            per_fold=per_fold,
            dots=int(dots.sum()),
        )
        print(f"    budget {n}: HOLDOUT-DTI {out['budgets'][key]['pooled_dti']:.4f}", flush=True)
    return out, terms, rank


def symmetric_auc(y, x):
    auc = float(roc_auc_score(y, x))
    return round(max(auc, 1.0 - auc), 4)


def main():
    t_start = time.time()
    import sklearn
    g = G.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    folds, _quad = HO.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    log = dict(
        lane="H78-TOOTH",
        evaluator_version=EH.VERSION,
        evaluator_sha256=EH.implementation_hashes(),
        sklearn_version=sklearn.__version__,
        seed=20, hide_frac=0.20, buffer_px=3,
        fold_receipts=[f["receipt"] for f in folds],
        visible_px=int(visible.sum()),
        hidden_px=int(hidden.sum()),
        withheld_positive_pixels_scored=int(sum(int(f["truth"].sum()) for f in folds)),
        preregistration="registry/preregistration_h78_tooth.json",
    )
    print(json.dumps({k: log[k] for k in ("lane", "evaluator_version", "sklearn_version", "hidden_px",
                                          "withheld_positive_pixels_scored")}, indent=1), flush=True)

    tag = "seed20"
    feats_path, fmeta = P.build_feature_matrix(tag, fp, visible)
    log["base_features"] = {k: v for k, v in fmeta.items() if k != "names"}
    print("base features ready", fmeta.get("seconds"), "s", flush=True)

    t0 = time.time()
    fields = missing_tooth_fields(visible, sigma=40.0)
    ys, xs = P.footprint_index(fp)
    extra = sample_fields(fields, ys, xs)
    tooth_sec = round(time.time() - t0, 1)
    log["tooth"] = dict(
        seconds=tooth_sec, sigma_px=40.0, n_features=len(FEATURE_NAMES), names=list(FEATURE_NAMES),
        footprint_mean={name: float(extra[:, i].mean()) for i, name in enumerate(FEATURE_NAMES)},
        footprint_p95={name: float(np.quantile(extra[:, i], 0.95)) for i, name in enumerate(FEATURE_NAMES)},
        fraction_defined=float((extra[:, 3] > 0).mean()),
    )
    print("tooth features", tooth_sec, "s; defined fraction", log["tooth"]["fraction_defined"], flush=True)

    # ---- leakage canary on every feature the candidate can see ----
    rng = np.random.default_rng(20)
    active = np.zeros(fp.shape, bool)
    truth = np.zeros(fp.shape, bool)
    for f in folds:
        a = fp & f["region"] & ~f["masked_known"]
        active |= a
        truth |= f["truth"] & a
    pos_flat = np.flatnonzero((truth & active).ravel())
    neg_flat = np.flatnonzero((active & ~truth).ravel())
    neg_flat = rng.choice(neg_flat, size=min(300_000, neg_flat.size), replace=False)
    sample_flat = np.concatenate([pos_flat, neg_flat])
    rows = P.flat_to_rows(sample_flat, fp)
    y = np.concatenate([np.ones(pos_flat.size), np.zeros(neg_flat.size)])
    order = np.argsort(rows, kind="stable")
    mm = np.load(feats_path, mmap_mode="r")
    cols = P.arm_columns("A2_h78_steered")
    Xc = np.asarray(mm[rows[order]][:, cols], np.float32)
    Ec = np.asarray(extra[rows[order]], np.float32)
    yc = y[order]
    names = [F.feature_names(iso=True, steered=True)[i] for i in cols]
    canary = {}
    for j, name in enumerate(names):
        canary[name] = symmetric_auc(yc, Xc[:, j])
    for j, name in enumerate(FEATURE_NAMES):
        canary[name] = symmetric_auc(yc, Ec[:, j])
    flagged = {k: v for k, v in canary.items() if v > 0.90}
    # Rotation control for every tooth feature, preregistered as the leakage proof.
    d_vis = fields["distance_to_visible_px"]
    lam = fields["tooth_lambda_px"]
    lam_r = np.roll(lam, shift=(lam.shape[0] // 2, lam.shape[1] // 3), axis=(0, 1))
    sig = np.maximum(0.18 * lam_r, 1.5)
    ok = lam_r >= 8.0
    gap_rolled = np.zeros(lam.shape, np.float32)
    gap_rolled[ok] = np.exp(-0.5 * ((d_vis[ok] - lam_r[ok]) / sig[ok]) ** 2)
    rolled_vals = gap_rolled.ravel()[sample_flat][order]
    rolled_auc = symmetric_auc(yc, rolled_vals)
    tooth_flagged = {k: v for k, v in flagged.items() if k.startswith("tooth_")}
    leakage_stop = bool(tooth_flagged) and rolled_auc >= 0.70
    log["canary"] = dict(
        n_pos=int(pos_flat.size), n_neg=int(neg_flat.size), threshold=0.90,
        flagged_over_0p90=flagged, max_auc=max(canary.values()),
        tooth={k: canary[k] for k in FEATURE_NAMES},
        top10=sorted(canary.items(), key=lambda kv: -kv[1])[:10],
        rotation_control=dict(
            feature="tooth_gap1 recomputed from lambda rolled by (H/2, W/3)",
            auc=rolled_auc,
            interpretation="If tooth AUC > 0.90 and this rolled AUC stays >= 0.70, treat as leakage and stop.",
        ),
        leakage_stop=leakage_stop,
        all=canary,
    )
    print("canary max", log["canary"]["max_auc"], "tooth", log["canary"]["tooth"],
          "rolled", rolled_auc, "stop", leakage_stop, flush=True)
    del Xc, Ec, yc, mm

    if leakage_stop:
        log["verdict_preview"] = "negative-leakage"
        log["seconds_total"] = round(time.time() - t_start, 1)
        out = ROOT / "evidence" / "h78tooth_holdout.json"
        out.write_text(json.dumps(log, indent=2))
        print("LEAKAGE STOP", flush=True)
        return

    pos, negs = P.training_sample(fp, visible, 450_000, seed=20)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    allowed = fp & ~E.flank_mask(visible, FLANK)
    terms_by_key = {}
    scores = {}
    results = {}
    for arm, use_extra in (("A2_control", False), ("T_tooth", True)):
        print("fitting", arm, flush=True)
        _clf, info, score = fit_and_score(feats_path, extra, rows_pos, rows_neg, fp, use_extra)
        scores[arm] = score
        np.save(ROOT / "data" / "processed" / f"score_{tag}_{arm}.npy", score)
        print(" fit", info, flush=True)
        emitted, terms, _rank = emit_budgets(score, allowed, folds, fp, BUDGETS)
        results[arm] = dict(fit=info, emission=emitted)
        for budget, block in terms.items():
            terms_by_key[f"{arm}|nms0_B3|{budget}"] = block

    cand_key = f"T_tooth|nms0_B3|{MATCHED_BUDGET}"
    ctrl_key = f"A2_control|nms0_B3|{MATCHED_BUDGET}"
    summary = EH.pooled_summary(
        {cand_key: terms_by_key[cand_key], ctrl_key: terms_by_key[ctrl_key]},
        draws=1000, seed=520810, candidate=cand_key,
    )
    published = 0.1826
    ctrl_dti = summary["scores"][ctrl_key]["dti"]
    cand_dti = summary["scores"][cand_key]["dti"]
    delta = summary["paired_differences"][ctrl_key]
    supported = bool(delta["ci95"][0] > 0 and cand_dti > ctrl_dti)
    repro_ok = abs(ctrl_dti - published) <= 0.005
    log["E1"] = dict(
        matched_key=cand_key,
        control_key=ctrl_key,
        published_A2_B3_44090=published,
        control_reproduced_within_0p005=repro_ok,
        hypothesis_supported=supported,
        pooled_summary=summary,
    )
    print("E1 candidate", round(cand_dti, 4), "control", round(ctrl_dti, 4),
          "delta CI", delta["ci95"], "supported", supported, "repro_ok", repro_ok, flush=True)

    # Far-truth diagnostic (not a selection rule): withheld pixels > 10 px from visible faults.
    d_vis_full = fields["distance_to_visible_px"]
    far = hidden & (d_vis_full > 10.0)
    log["far_truth_diagnostic"] = dict(
        evidence_class="HOLDOUT-DTI-STRATUM",
        note="Not used to choose a winner. Withheld pixels farther than 10 px from any visible fault.",
        n_far=int(far.sum()),
        n_near=int((hidden & ~far).sum()),
    )

    e2 = dict(ran=False)
    if supported:
        print("E2 flank sweep on frozen T_tooth surface", flush=True)
        e2 = dict(ran=True, kind="flank_sweep_frozen_surface", flanks={})
        h78a = ROOT / "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif"
        import rasterio
        with rasterio.open(h78a) as ds:
            prior = ds.read(1)
        best = None
        for bpx in (3.0, 4.0, 5.0, 6.0, 8.0):
            allow_b = fp & ~E.flank_mask(visible, bpx)
            rank = E.greedy_dots(scores["T_tooth"], allow_b, min_dist=MIN_DIST,
                                 max_dots=MATCHED_BUDGET, pool=POOL)
            dots = E.prefix(rank, MATCHED_BUDGET)
            if int(dots.sum()) < MATCHED_BUDGET:
                e2["flanks"][str(bpx)] = dict(dots=int(dots.sum()), skipped="short")
                continue
            block, per_fold = evaluate_dots(dots, folds, fp)
            dti = float(EH.from_terms(block.sum(axis=0)))
            overlap = U.dot_overlap(dots.astype(np.float32), prior, 3.0)
            row = dict(pooled_dti=dti, per_fold=per_fold, overlap_h78a_3px=overlap, dots=int(dots.sum()))
            e2["flanks"][str(bpx)] = row
            print(f"  B{bpx}: {dti:.4f} overlap_h78a {overlap:.3f}", flush=True)
            if overlap <= 0.70 and (best is None or dti > best[0]):
                best = (dti, bpx, block)
        if best is None:
            e2["selected"] = None
            e2["note"] = "every flank failed the 0.70 overlap screen against H78-A; duplicate risk"
        else:
            sel_key = f"T_tooth|nms0_B{best[1]:g}|{MATCHED_BUDGET}"
            terms_by_key[sel_key] = best[2]
            e2["selected_flank_px"] = best[1]
            e2["selected_key"] = sel_key
            e2["selected_dti"] = best[0]
            e2["paired_vs_control"] = EH.pooled_summary(
                {sel_key: best[2], ctrl_key: terms_by_key[ctrl_key]},
                draws=1000, seed=520810, candidate=sel_key,
            )
    else:
        print("E1 not supported; E2 is the preregistered sigma=20 sensitivity", flush=True)
        t0 = time.time()
        fields20 = missing_tooth_fields(visible, sigma=20.0)
        extra20 = sample_fields(fields20, ys, xs)
        _clf, info, score20 = fit_and_score(feats_path, extra20, rows_pos, rows_neg, fp, True, seed=0)
        emitted, terms, _rank = emit_budgets(score20, allowed, folds, fp, (MATCHED_BUDGET,))
        key = f"T_tooth_sigma20|nms0_B3|{MATCHED_BUDGET}"
        terms_by_key[key] = terms[str(MATCHED_BUDGET)]
        summary20 = EH.pooled_summary(
            {key: terms_by_key[key], ctrl_key: terms_by_key[ctrl_key]},
            draws=1000, seed=520810, candidate=key,
        )
        e2 = dict(
            ran=True, kind="sigma20_sensitivity", fit=info,
            seconds=round(time.time() - t0, 1),
            pooled_summary=summary20,
            hypothesis_supported=bool(summary20["paired_differences"][ctrl_key]["ci95"][0] > 0),
        )
        np.save(ROOT / "data" / "processed" / f"score_{tag}_T_tooth_sigma20.npy", score20)
        print("E2 sigma20", summary20["scores"][key]["dti"], "supported", e2["hypothesis_supported"], flush=True)

    # Far-truth stratum of the matched B3 emission. Diagnostic only; the gate does not use it.
    from gems57 import metric as M
    far_rows = {}
    for arm, score in scores.items():
        allow = fp & ~E.flank_mask(visible, FLANK)
        rank = E.greedy_dots(score, allow, min_dist=MIN_DIST, max_dots=MATCHED_BUDGET, pool=POOL)
        dots = E.prefix(rank, MATCHED_BUDGET)
        far_mask = hidden & (d_vis_full > 10.0) & fp
        near_mask = hidden & (d_vis_full <= 10.0) & fp
        far_rows[arm] = dict(
            far=M.dti_binary(dots, far_mask, valid=fp),
            near=M.dti_binary(dots, near_mask, valid=fp),
        )
        # dti_binary returns numpy scalars; coerce below.
        print(arm, "far DTI", far_rows[arm]["far"]["dti"], "near", far_rows[arm]["near"]["dti"], flush=True)
    log["far_truth_diagnostic"]["by_arm_B3_44090"] = far_rows
    log["results"] = results
    log["E2"] = e2
    log["seconds_total"] = round(time.time() - t_start, 1)
    out = ROOT / "evidence" / "h78tooth_holdout.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, indent=2, default=float))
    print("wrote", out, "seconds", log["seconds_total"], flush=True)


if __name__ == "__main__":
    main()
