#!/usr/bin/env python3
"""Complete Step 0 [3/3] with strict <500 MB RAM budget:
- Seed 20, Seed 30, Seed 40 replication of H78-A (A0_std19, A1_iso, A2_h78_steered)
- Flank sweep B = 2, 3, 4, 5, 6 px across full holdout, far_gt10px, far_gt20px
- Strict 4-quadrant Out-of-Fold (LOQO) evaluation of H78-A (proving IR-78-INSAMPLE-MEMORIZATION-01)
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import pipeline as P  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
EV = ROOT / "evidence"


def eval_dots(dots, folds, fp, mask_truth=None):
    pred = dots.astype(np.float32)
    tot = None
    for fold in folds:
        f2 = dict(fold)
        if mask_truth is not None:
            f2["truth"] = fold["truth"] & mask_truth
            if not f2["truth"].any():
                continue
        _, t = EH.evaluate(pred, f2, fp, block_side=200, origin=(0, 0), global_shape=fp.shape)
        tot = t if tot is None else tot + t
    return float(EH.from_terms(tot.sum(axis=0)))


def main():
    t0 = time.time()
    g = G.load_grid(DATA)
    fp = g.footprint
    seed_results = {}

    for seed in (20, 30, 40):
        ts = time.time()
        folds, quad = HO.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        d_vis = distance_transform_edt(~visible).astype(np.float32)
        tag = f"seed{seed}"
        print(f"[seed {seed}] building/loading features...", flush=True)
        feats_path, _ = P.build_feature_matrix(tag, fp, visible)
        pos, negs = P.training_sample(fp, visible, 300_000 if seed != 20 else 450_000, seed=seed)
        rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)

        entry = {
            "seed": seed,
            "withheld_positive_pixels": int(sum(int(f["truth"].sum()) for f in folds)),
            "global_visible_arms_B3_44090": {},
            "flank_sweep_A2_44090": {},
            "strict_loqo_arms": {},
        }
        for arm in ("A0_std19", "A1_iso", "A2_h78_steered"):
            sc_path = ROOT / "data/processed" / f"score_{tag}_{arm}.npy"
            if sc_path.exists():
                s = np.load(sc_path)
            else:
                clf, _ = P.fit_arm(feats_path, rows_pos, rows_neg, arm, seed=0)
                s = P.score_grid(clf, feats_path, arm, fp, chunk=250_000)
                np.save(sc_path, s)
                del clf
                gc.collect()
            allowed_b3 = fp & ~E.flank_mask(visible, 3.0)
            rk_b3 = E.greedy_dots(s, allowed_b3, min_dist=2.8, max_dots=44_090)
            dots_b3 = E.prefix(rk_b3, 44_090)
            dti_all = eval_dots(dots_b3, folds, fp)
            dti_far10 = eval_dots(dots_b3, folds, fp, mask_truth=(d_vis > 10.0))
            dti_far20 = eval_dots(dots_b3, folds, fp, mask_truth=(d_vis > 20.0))
            entry["global_visible_arms_B3_44090"][arm] = {
                "pooled_dti": round(dti_all, 5),
                "far_gt10px_dti": round(dti_far10, 5),
                "far_gt20px_dti": round(dti_far20, 5),
            }
            print(f"  [seed {seed}] {arm}: pooled={dti_all:.4f} far10={dti_far10:.4f} far20={dti_far20:.4f}", flush=True)

            if arm == "A2_h78_steered" and seed == 20:
                for bpx in (2.0, 3.0, 4.0, 5.0, 6.0):
                    rk = E.greedy_dots(s, fp & ~E.flank_mask(visible, bpx), min_dist=2.8, max_dots=45_000)
                    d44 = E.prefix(rk, 44_090)
                    entry["flank_sweep_A2_44090"][f"B{int(bpx)}"] = {
                        "all_dti": round(eval_dots(d44, folds, fp), 5),
                        "far_gt10px_dti": round(eval_dots(d44, folds, fp, mask_truth=(d_vis > 10.0)), 5),
                        "far_gt20px_dti": round(eval_dots(d44, folds, fp, mask_truth=(d_vis > 20.0)), 5),
                    }
                print("  [seed 20] flank sweep:", entry["flank_sweep_A2_44090"], flush=True)
            del s
            gc.collect()

        # On seed 20, evaluate H78-A strictly OUT-OF-FOLD (LOQO) with small 200k chunks!
        if seed == 20:
            for arm in ("A0_std19", "A2_h78_steered"):
                loqo_p = ROOT / "data/processed" / f"loqo_seed20_{arm}.npy"
                if loqo_p.exists():
                    oof_grid = np.load(loqo_p)
                else:
                    mm = np.load(feats_path, mmap_mode="r")
                    fp_quad = quad[fp]
                    vis_fp = visible[fp]
                    flank2_fp = E.flank_mask(visible, 2.0)[fp]
                    cols = P.arm_columns(arm)
                    oof_fp = np.zeros(mm.shape[0], np.float32)
                    rng = np.random.default_rng(20)
                    for q in range(4):
                        tr_pos = np.flatnonzero(vis_fp & (fp_quad != q))
                        tr_neg_pool = np.flatnonzero((~flank2_fp) & (fp_quad != q))
                        tr_neg = rng.choice(tr_neg_pool, size=min(4 * tr_pos.size, tr_neg_pool.size), replace=False)
                        rows = np.concatenate([tr_pos, tr_neg])
                        order = np.argsort(rows)
                        Xtr = np.empty((rows.size, cols.size), np.float32)
                        for lo in range(0, rows.size, 50_000):
                            hi = min(rows.size, lo + 50_000)
                            Xtr[lo:hi] = mm[rows[order[lo:hi]]][:, cols]
                        ytr = np.concatenate([np.ones(tr_pos.size, np.int8), np.zeros(tr_neg.size, np.int8)])[order]
                        clf = HistGradientBoostingClassifier(
                            max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
                            min_samples_leaf=200, l2_regularization=1.0, random_state=q,
                        )
                        clf.fit(Xtr, ytr)
                        del Xtr, ytr
                        gc.collect()
                        te_rows = np.flatnonzero(fp_quad == q)
                        for lo in range(0, te_rows.size, 200_000):
                            hi = min(te_rows.size, lo + 200_000)
                            Xb = np.asarray(mm[te_rows[lo:hi]][:, cols], np.float32)
                            oof_fp[te_rows[lo:hi]] = clf.predict_proba(Xb)[:, 1].astype(np.float32)
                            del Xb
                        del clf
                        gc.collect()
                    del mm
                    oof_grid = np.zeros(fp.shape, np.float32)
                    oof_grid[fp] = oof_fp
                    np.save(loqo_p, oof_grid)
                    del oof_fp
                    gc.collect()
                for bpx, nb in [(2.5, 37_654), (3.0, 44_090)]:
                    rk = E.greedy_dots(oof_grid, fp & ~E.flank_mask(visible, bpx), min_dist=2.8, max_dots=nb)
                    dd = E.prefix(rk, nb)
                    d_all = eval_dots(dd, folds, fp)
                    d_f10 = eval_dots(dd, folds, fp, mask_truth=(d_vis > 10.0))
                    d_f20 = eval_dots(dd, folds, fp, mask_truth=(d_vis > 20.0))
                    q_counts = {HO.FOLD_NAMES[q]: int((dd & (quad == q)).sum()) for q in range(4)}
                    entry["strict_loqo_arms"][f"{arm}|B{bpx}|{nb}"] = {
                        "loqo_dti": round(d_all, 5),
                        "far_gt10px_dti": round(d_f10, 5),
                        "far_gt20px_dti": round(d_f20, 5),
                        "quadrant_dots": q_counts,
                    }
                print(f"  [seed 20 LOQO] {arm}:", entry["strict_loqo_arms"], flush=True)
                del oof_grid
                gc.collect()

        # Free non-seed20 2GB feature memmaps immediately to keep disk super clean!
        if seed != 20:
            (ROOT / "data/processed" / f"feats_{tag}.npy").unlink(missing_ok=True)
            for arm in ("A0_std19", "A1_iso"):
                (ROOT / "data/processed" / f"score_{tag}_{arm}.npy").unlink(missing_ok=True)

        seed_results[f"seed{seed}"] = entry
        print(f"Seed {seed} finished in {time.time() - ts:.1f}s", flush=True)

    across = {}
    for arm in ("A0_std19", "A1_iso", "A2_h78_steered"):
        vals = [seed_results[f"seed{s}"]["global_visible_arms_B3_44090"][arm]["pooled_dti"] for s in (20, 30, 40)]
        f10 = [seed_results[f"seed{s}"]["global_visible_arms_B3_44090"][arm]["far_gt10px_dti"] for s in (20, 30, 40)]
        f20 = [seed_results[f"seed{s}"]["global_visible_arms_B3_44090"][arm]["far_gt20px_dti"] for s in (20, 30, 40)]
        across[arm] = {
            "mean_dti_3seeds": round(float(np.mean(vals)), 5),
            "std_dti_3seeds": round(float(np.std(vals, ddof=1)), 5),
            "min_max": [min(vals), max(vals)],
            "mean_far_gt10px_dti_3seeds": round(float(np.mean(f10)), 5),
            "mean_far_gt20px_dti_3seeds": round(float(np.mean(f20)), 5),
        }
    out = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "across_seeds_20_30_40": across,
        "by_seed": seed_results,
    }
    (EV / "h78_session1_next_steps.json").write_text(json.dumps(out, indent=2))
    print(f"ALL DONE in {time.time() - t0:.1f}s:\n" + json.dumps(across, indent=2), flush=True)


if __name__ == "__main__":
    main()
