#!/usr/bin/env python3
"""Matched Same-Split Head-to-Head Benchmark: H78-GFV vs Repository Best CTRL_A2.

Evaluates H78-GFV directly against exact reproduced repository best
``CTRL_A2|B3|44090`` (0.1826 on seed=20, 0.1834 on seed=30) on identical
``HO.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)`` folds
with zero mmap page-table bloat (< 1.5 GB RSS), 136-feature leakage canaries,
and 1,000-draw paired 20 km spatial-block bootstrap 95% confidence intervals.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, label
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57 import emit as E57  # noqa: E402
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import uniqueness as U  # noqa: E402
from gems78 import data as D  # noqa: E402
from gems78 import emit as E78  # noqa: E402
from gems78 import features as F  # noqa: E402
from gems78 import gfv  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78.strike import strike_field  # noqa: E402
from run_gfv_tournament import (  # noqa: E402
    fit_hetero_classifier,
    fit_kernel_self_credit,
    predict_hetero_proba,
    predict_kernel_self_credit,
)

HGB_CTRL = dict(
    max_iter=300,
    learning_rate=0.06,
    max_leaf_nodes=63,
    min_samples_leaf=200,
    l2_regularization=1.0,
    max_bins=255,
    early_stopping=False,
    random_state=0,
)


def log(*args):
    print(time.strftime("%H:%M:%S"), *args, flush=True)


def eval_dots(dots: np.ndarray, folds: list[dict], fp: np.ndarray):
    pred = dots.astype(np.float32)
    terms = None
    per_fold = {}
    for f in folds:
        r, t = EH.evaluate(pred, f, fp, block_side=200, origin=(0, 0), global_shape=fp.shape)
        per_fold[f["name"]] = {
            "dti": round(r["dti"], 6),
            "tp": round(r["tp"], 3),
            "fp": round(r["fp"], 3),
            "fn": round(r["fn"], 3),
            "n_truth": r["n_truth"],
            "n_emitted": r["n_emitted"],
        }
        terms = t if terms is None else (terms + t)
    return terms, per_fold, float(EH.from_terms(terms.sum(axis=0)))


def write_a2_bin_zero_mmap(bin_path: Path, fp: np.ndarray, visible: np.ndarray, n_blocks: int = 8) -> float:
    t0 = time.time()
    stack = D.load_stack()
    ys, xs = P.footprint_index(fp)
    n = ys.size
    phi, _, _ = strike_field(visible)
    bounds = np.linspace(0, n, n_blocks + 1).astype(int)
    with bin_path.open("wb") as f:
        for b in range(n_blocks):
            lo, hi = bounds[b], bounds[b + 1]
            mats = F.extract(stack, [(ys[lo:hi], xs[lo:hi])], phi=phi, iso=True, steered=True)
            f.write(mats[0].astype(np.float32, copy=False).tobytes())
            del mats
            gc.collect()
    del stack, phi
    gc.collect()
    return round(time.time() - t0, 2)


def gather_a2_plus_ext_geo(
    a2_bin: Path,
    ext_bin: Path,
    fp_rows: np.ndarray,
    ys: np.ndarray | None,
    xs: np.ndarray | None,
    geo12: np.ndarray | None,
) -> np.ndarray:
    order = np.argsort(fp_rows)
    sr = fp_rows[order]
    inv = np.empty_like(order)
    inv[order] = np.arange(order.size)

    n_fp = 5_167_373
    n_g = geo12.shape[0] if geo12 is not None else 0
    X_s = np.empty((order.size, 103 + 21 + n_g), dtype=np.float32)

    step = 520_000
    ptr = 0
    with a2_bin.open("rb") as fa, ext_bin.open("rb") as fe:
        for r0 in range(0, n_fp, step):
            r1 = min(r0 + step, n_fp)
            nc = r1 - r0
            ba = np.fromfile(fa, dtype=np.float32, count=nc * 103).reshape(nc, 103)
            be = np.fromfile(fe, dtype=np.float16, count=nc * 101).reshape(nc, 101)[:, 80:101]
            if ptr < sr.size and sr[ptr] < r1:
                p_end = int(np.searchsorted(sr, r1, side="left"))
                sub = sr[ptr:p_end] - r0
                X_s[ptr:p_end, :103] = ba[sub]
                X_s[ptr:p_end, 103:124] = be[sub].astype(np.float32)
                ptr = p_end
            del ba, be
    X = X_s[inv]
    del X_s
    if geo12 is not None and ys is not None and xs is not None:
        for j in range(n_g):
            X[:, 124 + j] = geo12[j, ys, xs].astype(np.float32)
    return X


def run_seed(seed: int):
    t0 = time.time()
    DATA = ROOT / ".cache" / "gems_data"
    FEAT = ROOT / ".cache" / "features"
    WORK = ROOT / ".cache" / "work"
    REG_FULL = ROOT / ".cache" / "full_registry"
    WORK.mkdir(parents=True, exist_ok=True)

    g = G.load_grid(DATA)
    fp = g.footprint
    fp_idx = np.flatnonzero(fp)
    folds, _ = HO.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    d_vis = distance_transform_edt(~visible).astype(np.float32)
    log(f"=== MATCHED GLOBAL BENCHMARK SEED {seed}: hidden={int(hidden.sum()):,}, visible={int(visible.sum()):,} ===")

    a2_bin = WORK / f"a2_fp103_s{seed}.bin"
    if a2_bin.exists() and a2_bin.stat().st_size == fp_idx.size * 103 * 4:
        log(f"Reusing existing zero-mmap 103-band A2 matrix {a2_bin.name}")
    else:
        sec_a2 = write_a2_bin_zero_mmap(a2_bin, fp, visible, n_blocks=8)
        log(f"Built zero-mmap 103-band A2 base matrix in {sec_a2}s")

    # 1. Exact reproduction of CTRL_A2|B3|44090 on shared training sample
    pos_flat, neg_flat = P.training_sample(fp, visible, 450_000, seed=seed)
    tr_flat = np.concatenate([pos_flat, neg_flat])
    tr_order = np.argsort(tr_flat)
    tr_sorted = tr_flat[tr_order]
    tr_rows = P.flat_to_rows(tr_sorted, fp)
    y_ctrl = np.concatenate([np.ones(pos_flat.size, np.int8), np.zeros(neg_flat.size, np.int8)])[tr_order]

    # Stream ONLY the 103 A2 columns for CTRL_A2
    X_ctrl = np.empty((tr_rows.size, 103), dtype=np.float32)
    ptr = 0
    step = 520_000
    with a2_bin.open("rb") as fa:
        for r0 in range(0, fp_idx.size, step):
            r1 = min(r0 + step, fp_idx.size)
            nc = r1 - r0
            ba = np.fromfile(fa, dtype=np.float32, count=nc * 103).reshape(nc, 103)
            if ptr < tr_rows.size and tr_rows[ptr] < r1:
                pe = int(np.searchsorted(tr_rows, r1, side="left"))
                X_ctrl[ptr:pe] = ba[tr_rows[ptr:pe] - r0]
                ptr = pe
            del ba
    clf_ctrl = HistGradientBoostingClassifier(**HGB_CTRL)
    clf_ctrl.fit(X_ctrl, y_ctrl)
    del X_ctrl, y_ctrl
    gc.collect()

    s_ctrl_fp = np.empty(fp_idx.size, dtype=np.float32)
    with a2_bin.open("rb") as fa:
        for r0 in range(0, fp_idx.size, step):
            r1 = min(r0 + step, fp_idx.size)
            nc = r1 - r0
            ba = np.fromfile(fa, dtype=np.float32, count=nc * 103).reshape(nc, 103)
            s_ctrl_fp[r0:r1] = clf_ctrl.predict_proba(ba)[:, 1].astype(np.float32)
            del ba
    del clf_ctrl
    gc.collect()
    s_ctrl = np.zeros(fp.shape, dtype=np.float32)
    s_ctrl[fp] = s_ctrl_fp
    del s_ctrl_fp

    allow_b3 = fp & (~E78.flank_mask(visible, 3.0))
    rk_ctrl = E78.greedy_dots(s_ctrl, allow_b3, min_dist=2.8, max_dots=50_000, pool=1_500_000)
    log("CTRL_A2 scored & ranked")

    # 2. Compute evaluation Fermat Geodesic network on visible + weak physical surface
    oof_e1_p = np.load(WORK / f"oof_e1_p_s{seed}.npy").astype(np.float32)
    p5, p995 = np.percentile(oof_e1_p[fp], [5.0, 99.5])
    weak_oof = np.clip((oof_e1_p - p5) / max(float(p995 - p5), 1e-6), 0.0, 1.0)
    strike_theta = np.load(FEAT / "gfv_phys_strike.npy").astype(np.float32)
    hydro_nodes2x = np.load(FEAT / "gfv_hydro_nodes2x.npy")
    geo_eval = gfv.compute_geodesic_network(
        visible, weak_oof, strike_theta, fp, hydro_nodes2x, n_color_rounds=8, seed=900 + seed
    )

    # 3. Pre-fit 136-feature single-feature symmetric ROC-AUC canary
    rng_can = np.random.default_rng(seed)
    active = np.zeros(fp.shape, dtype=bool)
    truth = np.zeros(fp.shape, dtype=bool)
    for f in folds:
        a = fp & f["region"] & (~f["masked_known"])
        active |= a
        truth |= f["truth"] & a
    c_pos = np.flatnonzero((truth & active).ravel())
    c_neg = rng_can.choice(np.flatnonzero((active & (~truth)).ravel()), size=250_000, replace=False)
    c_all = np.concatenate([c_pos, c_neg])
    c_ys = (c_all // fp.shape[1]).astype(np.int32)
    c_xs = (c_all % fp.shape[1]).astype(np.int32)
    c_rows = P.flat_to_rows(c_all, fp)
    X_can = gather_a2_plus_ext_geo(a2_bin, FEAT / "fp101_f16.bin", c_rows, c_ys, c_xs, geo_eval)
    y_can = np.r_[np.ones(c_pos.size), np.zeros(c_neg.size)]
    all_136_names = F.feature_names(iso=True, steered=True) + list(gfv.GFV_EXT_NAMES) + list(gfv.GFV_GEO_NAMES)
    canaries = {}
    for j, nm in enumerate(all_136_names):
        v = np.nan_to_num(X_can[:, j], nan=0.0)
        auc = float(roc_auc_score(y_can, v))
        canaries[nm] = round(max(auc, 1.0 - auc), 5)
    del X_can, y_can
    gc.collect()
    max_can = max(canaries.values())
    flagged = {k: v for k, v in canaries.items() if v > 0.90}
    log(f"136-feature canary check: max symmetric AUC = {max_can:.5f} (flagged > 0.90: {len(flagged)})")
    if flagged:
        raise RuntimeError(f"LEAKAGE CANARY BLOCK: {flagged}")

    # 4. Nested K=3 hide-and-recover splits of visible for Dual-Head 136-band H78-GFV fit (1 fit total!)
    comp_vis, n_comp = label(visible, structure=np.ones((3, 3), dtype=np.int32))
    rng_n = np.random.default_rng(5000 + seed)
    comp_fold = np.zeros(n_comp + 1, dtype=np.int32)
    comp_fold[1:] = rng_n.integers(0, 3, size=n_comp)

    X_parts, yp_parts, ym_parts, sw_parts = [], [], [], []
    for k in range(3):
        vis_ctx = visible & (comp_fold[comp_vis] != k)
        vis_tgt = visible & (comp_fold[comp_vis] == k)
        geo_k = gfv.compute_geodesic_network(
            vis_ctx, weak_oof, strike_theta, fp, hydro_nodes2x, n_color_rounds=6, seed=300 + 10 * seed + k
        )
        d_ctx = distance_transform_edt(~vis_ctx).astype(np.float32)
        d_tgt = distance_transform_edt(~vis_tgt).astype(np.float32)
        vp = fp & (d_ctx > 3.0)

        s0 = vp & vis_tgt
        s1 = vp & (~vis_tgt) & (d_tgt <= 3.0)
        s2 = vp & (d_tgt > 3.0) & (d_ctx <= 28.0)
        s3 = vp & (d_tgt > 3.0) & (d_ctx > 28.0)
        y0, x0 = np.nonzero(s0)
        y1, x1 = np.nonzero(s1)
        y2, x2 = np.nonzero(s2)
        y3, x3 = np.nonzero(s3)
        c1 = rng_n.choice(y1.size, size=min(18_000, y1.size), replace=False)
        c2 = rng_n.choice(y2.size, size=min(28_000, y2.size), replace=False)
        c3 = rng_n.choice(y3.size, size=min(28_000, y3.size), replace=False)

        ys_k = np.concatenate([y0, y1[c1], y2[c2], y3[c3]])
        xs_k = np.concatenate([x0, x1[c1], x2[c2], x3[c3]])
        rows_k = P.flat_to_rows(ys_k.astype(np.int64) * fp.shape[1] + xs_k.astype(np.int64), fp)
        X_parts.append(gather_a2_plus_ext_geo(a2_bin, FEAT / "fp101_f16.bin", rows_k, ys_k, xs_k, geo_k))
        yp_parts.append(np.r_[np.ones(y0.size, np.int32), np.zeros(c1.size + c2.size + c3.size, np.int32)])
        ym_parts.append(np.maximum(0.0, 1.0 - d_tgt[ys_k, xs_k] / 3.0).astype(np.float32))
        sw_parts.append(np.r_[
            np.ones(y0.size, np.float64),
            np.full(c1.size, y1.size / max(c1.size, 1), np.float64),
            np.full(c2.size, y2.size / max(c2.size, 1), np.float64),
            np.full(c3.size, y3.size / max(c3.size, 1), np.float64),
        ])
        del geo_k, d_ctx, d_tgt
        gc.collect()
        log(f"Global nested split {k+1}/3 sampled")

    X_tr = np.concatenate(X_parts, axis=0)
    yp_tr = np.concatenate(yp_parts, axis=0)
    ym_tr = np.concatenate(ym_parts, axis=0)
    sw_tr = np.concatenate(sw_parts, axis=0)
    del X_parts, yp_parts, ym_parts, sw_parts
    gc.collect()

    t_fit = time.time()
    models_p = fit_hetero_classifier(X_tr, yp_tr, sw_tr, seed=9100 + seed)
    models_m = fit_kernel_self_credit(X_tr, ym_tr, sw_tr, seed=9200 + seed)
    del X_tr, yp_tr, ym_tr, sw_tr
    gc.collect()

    p_gfv_fp = np.empty(fp_idx.size, dtype=np.float32)
    m_gfv_fp = np.empty(fp_idx.size, dtype=np.float32)
    with a2_bin.open("rb") as fa, (FEAT / "fp101_f16.bin").open("rb") as fe:
        for r0 in range(0, fp_idx.size, step):
            r1 = min(r0 + step, fp_idx.size)
            nc = r1 - r0
            ba = np.fromfile(fa, dtype=np.float32, count=nc * 103).reshape(nc, 103)
            be = np.fromfile(fe, dtype=np.float16, count=nc * 101).reshape(nc, 101)[:, 80:101]
            fc = fp_idx[r0:r1]
            Xb = np.empty((nc, 136), dtype=np.float32)
            Xb[:, :103] = ba
            Xb[:, 103:124] = be.astype(np.float32)
            for j in range(12):
                Xb[:, 124 + j] = geo_eval[j].ravel()[fc]
            del ba, be
            p_gfv_fp[r0:r1] = predict_hetero_proba(models_p, Xb)
            m_gfv_fp[r0:r1] = predict_kernel_self_credit(models_m, Xb)
            del Xb
    del models_p, models_m, geo_eval
    gc.collect()
    log(f"Global Dual-Head 136-band model fitted & scored in {time.time()-t_fit:.1f}s")

    # Clean up 2.13 GB temporary A2 raw matrix immediately to keep plenty of free disk
    a2_bin.unlink(missing_ok=True)

    p_gfv = np.zeros(fp.shape, dtype=np.float32)
    m_gfv = np.zeros(fp.shape, dtype=np.float32)
    p_gfv[fp] = p_gfv_fp
    m_gfv[fp] = m_gfv_fp
    del p_gfv_fp, m_gfv_fp

    from scipy.stats import spearmanr
    np.save(WORK / f"glob_ctrl_s{seed}.npy", s_ctrl.astype(np.float16))
    np.save(WORK / f"glob_p_gfv_s{seed}.npy", p_gfv.astype(np.float16))
    np.save(WORK / f"glob_m_gfv_s{seed}.npy", m_gfv.astype(np.float16))

    sub_sp = np.random.default_rng(7878).choice(fp_idx, size=250_000, replace=False)
    rho_vs_ctrl = float(spearmanr(p_gfv.ravel()[sub_sp], s_ctrl.ravel()[sub_sp]).statistic)
    log(f"Surface Spearman rho (CAND_GFV vs CTRL_A2) = {rho_vs_ctrl:.5f}")

    # Score matched arms on official evaluator
    far_folds = [dict(f, truth=(np.asarray(f["truth"], bool) & (d_vis > 10.0))) for f in folds]
    rk_gfv = E78.greedy_dots(p_gfv, allow_b3, min_dist=2.8, max_dots=50_000, pool=1_500_000)
    k_exp = max(float(p_gfv[allow_b3].sum()), 10_000.0)
    dink_37 = E57.dinkelbach_allocate(
        np.where(allow_b3, p_gfv, 0.0), m_gfv, allow_b3,
        budget=37_654, k_truth=k_exp, min_spacing_px=2.8, dinkelbach_iters=3, candidate_cap=1_800_000,
    ).emitted
    dink_44 = E57.dinkelbach_allocate(
        np.where(allow_b3, p_gfv, 0.0), m_gfv, allow_b3,
        budget=44_090, k_truth=k_exp, min_spacing_px=2.8, dinkelbach_iters=3, candidate_cap=1_800_000,
    ).emitted

    # Also evaluate 94-repo discriminating-halo constrained 37,654 allocation on identical folds!
    inv_doc = json.loads((REG_FULL / "complete_93repo_inventory.json").read_text())
    entries = inv_doc["rasters"]
    n_bytes = int(inv_doc["packbits_row_bytes"])
    fp_to_pos = np.full(fp.size, -1, dtype=np.int32)
    fp_to_pos[fp_idx] = np.arange(fp_idx.size, dtype=np.int32)
    p_eff_c = np.where(allow_b3, np.clip(0.88 * p_gfv + 0.12 * oof_e1_p + 1e-5, 0.0, 1.0), 0.0).astype(np.float32)
    ek_c = E57.expected_credit(p_eff_c)
    c_ys2, c_xs2 = np.nonzero(allow_b3 & (ek_c > 0.0))
    cand_cap = 3_400_000
    if c_ys2.size > cand_cap:
        ti = np.argpartition(-ek_c[c_ys2, c_xs2], cand_cap)[:cand_cap]
        c_ys2, c_xs2 = c_ys2[ti], c_xs2[ti]
    oc = np.argsort(-ek_c[c_ys2, c_xs2], kind="stable")
    cand_fp_pos = fp_to_pos[c_ys2[oc].astype(np.int64) * fp.shape[1] + c_xs2[oc].astype(np.int64)]
    high_rows = []
    with (REG_FULL / "halo_packbits.bin").open("rb") as hf:
        for i, e in enumerate(entries):
            raw = np.fromfile(hf, dtype=np.uint8, count=n_bytes)
            if e["halo_coverage"] < 0.70:
                hb = np.unpackbits(raw)[: fp_idx.size]
                if float(hb[cand_fp_pos[:42_000]].mean()) >= 0.60:
                    high_rows.append(hb[cand_fp_pos].copy())
    dink_constrained_37 = E57.dinkelbach_allocate(
        p_eff_c, m_gfv, allow_b3, budget=37_654, k_truth=k_exp, min_spacing_px=2.8,
        dinkelbach_iters=3, candidate_cap=cand_cap,
        halo_constraints=np.stack(high_rows, axis=0) if high_rows else None,
        halo_max_hits=int(0.640 * 37_654) if high_rows else None,
    ).emitted
    del high_rows
    gc.collect()

    arms_eval = [
        ("CTRL_A2|B3|37654", E78.prefix(rk_ctrl, 37_654)),
        ("CTRL_A2|B3|44090", E78.prefix(rk_ctrl, 44_090)),
        ("CAND_GFV_SingleHead|B3|37654", E78.prefix(rk_gfv, 37_654)),
        ("CAND_GFV_SingleHead|B3|44090", E78.prefix(rk_gfv, 44_090)),
        ("CAND_GFV_DualHead_Dink|B3|37654", dink_37),
        ("CAND_GFV_DualHead_Dink|B3|44090", dink_44),
        ("CAND_GFV_94RepoConstrained|B3|37654", dink_constrained_37),
    ]

    terms_all, terms_far, pf_map = {}, {}, {}
    print(f"\n================ MATCHED GLOBAL-HIDE HEAD-TO-HEAD (SEED {seed}) ================", flush=True)
    for name, dm in arms_eval:
        ta, pfa, da = eval_dots(dm, folds, fp)
        tf, pff, df = eval_dots(dm, far_folds, fp)
        terms_all[name] = ta
        terms_far[name] = tf
        pf_map[name] = {"all": pfa, "far_gt10px": pff}
        print(f"  {name:38s} | ALL={da:.5f} | FAR10={df:.5f} | dots={int(dm.sum()):,}", flush=True)

    primary = "CAND_GFV_DualHead_Dink|B3|44090"
    sum_all = EH.pooled_summary(terms_all, draws=1000, seed=520810, candidate=primary)
    sum_far = EH.pooled_summary(terms_far, draws=1000, seed=520810, candidate=primary)

    # Also compute exact paired bootstrap for 94RepoConstrained vs CTRL_A2|B3|44090!
    sum_con = EH.pooled_summary(terms_all, draws=1000, seed=520810, candidate="CAND_GFV_94RepoConstrained|B3|37654")
    sum_con_far = EH.pooled_summary(terms_far, draws=1000, seed=520810, candidate="CAND_GFV_94RepoConstrained|B3|37654")

    out = {
        "lane": "H78-GFV matched same-split comparison vs repository best CTRL_A2",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "evaluator_sha256": EH.implementation_hashes(),
        "seed": seed,
        "withheld_positive_pixels": int(hidden.sum()),
        "far_withheld_positive_pixels_gt10px": int(sum(int(f["truth"].sum()) for f in far_folds)),
        "visible_positive_pixels": int(visible.sum()),
        "canary_136_features": {
            "count": len(canaries),
            "threshold": 0.90,
            "flagged_over_0_90": flagged,
            "max_symmetric_auc": max_can,
            "top_12": sorted(canaries.items(), key=lambda kv: -kv[1])[:12],
        },
        "surface_rho_cand_vs_ctrl_a2": round(rho_vs_ctrl, 6),
        "per_fold": pf_map,
        "pooled_summary_primary_unconstrained": sum_all,
        "pooled_summary_far_primary_unconstrained": sum_far,
        "pooled_summary_94repo_constrained": sum_con,
        "pooled_summary_far_94repo_constrained": sum_con_far,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    p_out = ROOT / "evidence" / f"h78gfv_matched_global_seed{seed}.json"
    p_out.write_text(json.dumps(out, indent=2))
    log(f"Saved {p_out} in {time.time()-t0:.1f}s!")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()
    run_seed(args.seed)
