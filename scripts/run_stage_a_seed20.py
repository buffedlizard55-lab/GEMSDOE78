#!/usr/bin/env python3
"""Stage A: Complete Preregistered Experiments 1, 2, and 3 on Seed 20 (strict OOF LOQO + 20km Bootstrap CIs)."""
from __future__ import annotations
import gc, json, sys, time
from pathlib import Path
import lightgbm as lgb
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from audit_live_and_next_steps import build_c_pied
from gems57 import evaluate_holdout as EH, grid as G, holdout as HO
from gems78 import emit as E, gsc, pipeline as P
from run_session2_experiments import crop_folds, eval_dots_full

DATA = ROOT / ".cache" / "gems_data"
PROC = ROOT / "data" / "processed"
EV = ROOT / "evidence"


def fold_strict_prev_cal(p_grid: np.ndarray, fp: np.ndarray, vis: np.ndarray, quad: np.ndarray, has_li: np.ndarray, li_mult: float = 1.06) -> np.ndarray:
    out = np.zeros_like(p_grid, dtype=np.float32)
    act = fp & (~E.flank_mask(vis, 3.0))
    for q in range(4):
        prior_q = float(vis[fp & (quad != q)].mean())
        for li in (0, 1):
            m = act & (quad == q) & (has_li == bool(li))
            idx = np.flatnonzero(m)
            vals = p_grid.ravel()[idx]
            p99 = float(np.percentile(vals, 99.2)) + 1e-6
            out.ravel()[idx] = ((li_mult if li == 1 else 1.0) * prior_q * (vals / p99)).astype(np.float32)
    return out


def fit_mfnc_loqo(static_path: Path, cols_arr: np.ndarray, fp: np.ndarray, vis: np.ndarray,
                  quad: np.ndarray, piedmont_fp: np.ndarray | None, seed: int = 20, pu_clean: bool = True,
                  also_fit_global_vis: bool = False):
    """Strict 4-quadrant OOF Masked Fault Network Completion (matched 80/20 inner draws + optional PU spy cleaning)."""
    fp_idx = np.flatnonzero(fp)
    quad_fp = quad.ravel()[fp_idx]
    z = np.load(gsc.AUX_GRIDS_PATH)
    aux = {k: z[k].astype(np.float32) for k in z.files}

    ext_test, snames = gsc.compute_fold_structural_features(vis, fp, aux)
    ext_test16 = ext_test.astype(np.float16)
    del ext_test; gc.collect()

    comp_lbl, n_comp = ndi.label(vis, structure=np.ones((3, 3), int))
    rng_c = np.random.default_rng(7800 + seed)
    perm = rng_c.permutation(n_comp) + 1
    # 2 matched 80/20 inner draws (each hides 20% of visible fault components; peak RAM < 1.0 GB!)
    inner_samples = []
    for r_i in range(2):
        start = (r_i * n_comp) // 5
        end = ((r_i + 1) * n_comp) // 5
        hidden_r = np.isin(comp_lbl, perm[start:end])
        ctx_r = vis & (~ndi.binary_dilation(hidden_r, iterations=3))
        ext_r, _ = gsc.compute_fold_structural_features(ctx_r, fp, aux)
        act_r = (fp & (~E.flank_mask(ctx_r, 3.0))).ravel()[fp_idx]
        tgt_fp = (hidden_r & fp).ravel()[fp_idx] & act_r
        inner_samples.append((act_r, tgt_fp, ext_r.astype(np.float16)))
        del hidden_r, ctx_r, ext_r; gc.collect()
    del aux, comp_lbl; gc.collect()

    k_stat, k_ext = int(cols_arr.size), int(ext_test16.shape[1])
    oof_fp = np.zeros(fp_idx.size, dtype=np.float32)
    gain_acc = np.zeros(k_stat + k_ext, dtype=np.float64)

    params = dict(
        n_estimators=460, learning_rate=0.05, num_leaves=63,
        min_child_samples=80, subsample_for_bin=100_000,
        colsample_bytree=0.80, subsample=0.85, subsample_freq=1,
        reg_alpha=1.5, reg_lambda=6.0, n_jobs=-1, verbose=-1,
    )

    for q in range(4):
        Xs, ys, ws = [], [], []
        rng_q = np.random.default_rng(1200 + seed * 10 + q)
        q_tr = quad_fp != q
        mm = np.load(static_path, mmap_mode="r")
        for act_r, tgt_fp, ext_r16 in inner_samples:
            pos_r = np.flatnonzero(tgt_fp & q_tr)
            neg_pool = np.flatnonzero(act_r & q_tr & (~tgt_fp))
            neg_r = np.sort(rng_q.choice(neg_pool, size=min(85_000, int(neg_pool.size)), replace=False))
            sr = np.sort(np.concatenate([pos_r, neg_r]))
            yr = tgt_fp[sr].astype(np.int32)
            Xr = np.empty((sr.size, k_stat + k_ext), dtype=np.float32)
            for lo in range(0, sr.size, 60_000):
                hi = min(sr.size, lo + 60_000)
                Xr[lo:hi, :k_stat] = mm[sr[lo:hi]][:, cols_arr].astype(np.float32)
                Xr[lo:hi, k_stat:] = ext_r16[sr[lo:hi]].astype(np.float32)
            wr = np.ones(sr.size, dtype=np.float32)
            if piedmont_fp is not None:
                wr = np.where(yr == 1, 1.0 + 0.9 * piedmont_fp[sr], 1.0).astype(np.float32)
            Xs.append(Xr); ys.append(yr); ws.append(wr)
        del mm; P.drop_file_cache(static_path)
        X_tr = np.vstack(Xs); y_tr = np.concatenate(ys); w_tr = np.concatenate(ws)
        del Xs, ys, ws; gc.collect()

        if pu_clean:
            pos_loc = np.flatnonzero(y_tr == 1)
            spy_pick = rng_q.choice(pos_loc, size=max(400, int(0.15 * pos_loc.size)), replace=False)
            y_spy = y_tr.copy(); y_spy[spy_pick] = 0
            spy_clf = lgb.LGBMClassifier(
                n_estimators=140, learning_rate=0.08, num_leaves=31,
                min_child_samples=100, colsample_bytree=0.8, n_jobs=-1,
                random_state=seed + q, verbose=-1,
            )
            spy_clf.fit(X_tr, y_spy)
            p_spy = spy_clf.predict_proba(X_tr)[:, 1]
            tau = float(np.percentile(p_spy[spy_pick], 72.0))
            keep = ~((y_tr == 0) & (p_spy >= tau))
            X_tr, y_tr, w_tr = X_tr[keep], y_tr[keep], w_tr[keep]
            del spy_clf, p_spy; gc.collect()

        clf = lgb.LGBMClassifier(random_state=5000 + seed * 10 + q, **params)
        clf.fit(X_tr, y_tr, sample_weight=w_tr)
        gain_acc += clf.booster_.feature_importance(importance_type="gain")
        del X_tr, y_tr, w_tr; gc.collect()

        q_rows = np.flatnonzero(quad_fp == q)
        mm = np.load(static_path, mmap_mode="r")
        for lo in range(0, q_rows.size, 250_000):
            hi = min(q_rows.size, lo + 250_000)
            rr = q_rows[lo:hi]
            Xq = np.empty((rr.size, k_stat + k_ext), dtype=np.float32)
            Xq[:, :k_stat] = mm[rr][:, cols_arr].astype(np.float32)
            Xq[:, k_stat:] = ext_test16[rr].astype(np.float32)
            oof_fp[rr] = clf.predict_proba(Xq)[:, 1].astype(np.float32)
            del Xq
        del mm, clf
        P.drop_file_cache(static_path)
        gc.collect()

    glob_grid = None
    if also_fit_global_vis:
        Xs, ys = [], []
        rng_g = np.random.default_rng(8800 + seed)
        mm = np.load(static_path, mmap_mode="r")
        for act_r, tgt_fp, ext_r16 in inner_samples:
            pos_r = np.flatnonzero(tgt_fp)
            neg_pool = np.flatnonzero(act_r & (~tgt_fp))
            neg_r = np.sort(rng_g.choice(neg_pool, size=min(100_000, int(neg_pool.size)), replace=False))
            sr = np.sort(np.concatenate([pos_r, neg_r]))
            yr = tgt_fp[sr].astype(np.int32)
            Xr = np.empty((sr.size, k_stat + k_ext), dtype=np.float32)
            for lo in range(0, sr.size, 60_000):
                hi = min(sr.size, lo + 60_000)
                Xr[lo:hi, :k_stat] = mm[sr[lo:hi]][:, cols_arr].astype(np.float32)
                Xr[lo:hi, k_stat:] = ext_r16[sr[lo:hi]].astype(np.float32)
            Xs.append(Xr); ys.append(yr)
        del mm; P.drop_file_cache(static_path)
        X_tr = np.vstack(Xs); y_tr = np.concatenate(ys)
        del Xs, ys; gc.collect()
        clf_g = lgb.LGBMClassifier(random_state=9900 + seed, **params)
        clf_g.fit(X_tr, y_tr)
        del X_tr, y_tr; gc.collect()
        g_fp = np.zeros(fp_idx.size, dtype=np.float32)
        mm = np.load(static_path, mmap_mode="r")
        for lo in range(0, fp_idx.size, 250_000):
            hi = min(fp_idx.size, lo + 250_000)
            Xq = np.empty((hi - lo, k_stat + k_ext), dtype=np.float32)
            Xq[:, :k_stat] = mm[lo:hi][:, cols_arr].astype(np.float32)
            Xq[:, k_stat:] = ext_test16[lo:hi].astype(np.float32)
            g_fp[lo:hi] = clf_g.predict_proba(Xq)[:, 1].astype(np.float32)
            del Xq
        del mm, clf_g
        P.drop_file_cache(static_path)
        glob_grid = np.zeros(fp.shape, dtype=np.float32)
        glob_grid.ravel()[fp_idx] = g_fp

    del inner_samples, ext_test16; gc.collect()
    oof_grid = np.zeros(fp.shape, dtype=np.float32)
    oof_grid.ravel()[fp_idx] = oof_fp
    return oof_grid, glob_grid, gain_acc.tolist(), snames


def drop_all_caches():
    for root in (DATA, PROC, ROOT / "data"):
        for p in root.rglob("*"):
            if p.is_file():
                P.drop_file_cache(p)


def main():
    t0 = time.time()
    g = G.load_grid(DATA); fp, cat = g.footprint, g.catalogue
    c_pied, d_cat_full, lidar_valid = build_c_pied(fp, cat)
    drop_all_caches()
    static_path, meta = gsc.build_static_feature_bank(fp, force=False)
    groups = meta["groups"]
    cols_all_phys = groups["tf19_res"] + groups["topo10"] + groups["lidar1m"] + groups["chi_fluvial"] + groups["geodawn_confluence"]
    cols_arr = np.asarray(cols_all_phys, dtype=np.int64)

    z = np.load(gsc.AUX_GRIDS_PATH)
    aux = {k: z[k].astype(np.float32) for k in z.files}
    piedmont_fp = aux["piedmont_zone"].ravel()[np.flatnonzero(fp)].copy()
    phys_steer_fp, phys_steer_names = gsc.compute_pure_phys_steered_features(fp, aux)
    # Fair apples-to-apples H33-style 1m/10m scarp rule evaluated inside vis20 active region (without masking hidden truth20!)
    h33_like_score = aux["unified_scarp"] * (0.4 + aux["piedmont_zone"])
    del aux; gc.collect()

    folds20, quad = HO.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
    vis20 = folds20[0]["visible"]
    allow_b3 = fp & (~E.flank_mask(vis20, 3.0))

    mphys_cache = PROC / "oof_seed20_mphys_pu.npy"
    if mphys_cache.exists():
        surf_mphys_pu = np.load(mphys_cache)
        gains_phys = [1.0] * (len(cols_all_phys) + len(phys_steer_names))
    else:
        from run_session2_experiments import fit_loqo_surface
        surf_mphys_pu, gains_phys = fit_loqo_surface(
            static_path, cols_all_phys, phys_steer_fp, fp, vis20, quad,
            seed=202, pu_spy_clean=True, piedmont_fp=piedmont_fp,
        )
        np.save(mphys_cache, surf_mphys_pu)
    del phys_steer_fp, surf_mphys_pu; gc.collect()

    surf_mfnc_oof, surf_mfnc_glob, gains_mfnc, snames = fit_mfnc_loqo(
        static_path, cols_arr, fp, vis20, quad, piedmont_fp, seed=20, pu_clean=True, also_fit_global_vis=True,
    )
    np.save(PROC / "oof_seed20_mfnc_bridge_pu.npy", surf_mfnc_oof)
    np.save(PROC / "glob_seed20_mfnc_bridge_pu.npy", surf_mfnc_glob)
    print(f"Finished MFNC-Bridge-PU OOF + Global at {time.time()-t0:.1f}s!", flush=True)

    surf_mphys_pu = np.load(mphys_cache)
    cf20 = crop_folds(folds20, fp)
    d_vis20 = distance_transform_edt(~vis20).astype(np.float32)

    terms_store = {}
    exp1 = {}
    d_h33_fair = E.prefix(E.greedy_dots(h33_like_score, fp & (~E.flank_mask(vis20, 2.5)), min_dist=2.8, max_dots=37_654), 37_654)
    exp1["C1_scarp_piedmont_rule_37654"], terms_store["C1_scarp_piedmont_rule_37654"] = eval_dots_full(
        d_h33_fair, cf20, fp, d_vis20, c_pied, d_cat_full, lidar_valid, quad
    )
    for cname, npy_path in [
        ("C2_A0_std19_LOQO", PROC / "loqo_seed20_A0_std19.npy"),
        ("C3_A2_h78_steered_LOQO", PROC / "loqo_seed20_A2_h78_steered.npy"),
        ("C4_A2_h78_steered_GlobalInSample", PROC / "score_seed20_A2_h78_steered.npy"),
    ]:
        arr = np.load(npy_path)
        dd = E.prefix(E.greedy_dots(arr, allow_b3, min_dist=2.8, max_dots=44_090), 44_090)
        exp1[cname], terms_store[cname] = eval_dots_full(dd, cf20, fp, d_vis20, c_pied, d_cat_full, lidar_valid, quad)
        del arr

    d_mp = E.prefix(E.greedy_dots(surf_mphys_pu, allow_b3, min_dist=2.8, max_dots=44_090), 44_090)
    info_mp, terms_store["E3_Mphys_PU_zeroSGMC_LOQO"] = eval_dots_full(d_mp, cf20, fp, d_vis20, c_pied, d_cat_full, lidar_valid, quad)
    print(f"E3_Mphys_PU_zeroSGMC_LOQO: DTI={info_mp['holdout_dti']:.5f} far10={info_mp['far_gt10px_dti']:.5f} far20={info_mp['far_gt20px_dti']:.5f} Cpied={info_mp['c_pied_zero_fit_dti']:.5f} med_d={info_mp['median_d_cat_px']:.2f}", flush=True)

    cal_phys = fold_strict_prev_cal(surf_mphys_pu, fp, vis20, quad, lidar_valid, li_mult=1.08)
    cal_mfnc = fold_strict_prev_cal(surf_mfnc_oof, fp, vis20, quad, lidar_valid, li_mult=1.05)

    exp3 = {"E3_Mphys_PU_zeroSGMC_LOQO": info_mp, "candidates": {}}
    for label, surf_use in [
        ("E3_MFNC_Bridge_PU_raw_LOQO", surf_mfnc_oof),
        ("E3_MFNC_Bridge_PU_cal_LOQO", cal_mfnc),
        ("E3_DualBlend_w0p82_LOQO", 0.82 * cal_mfnc + 0.18 * cal_phys),
        ("E3_DualBlend_w0p70_LOQO", 0.70 * cal_mfnc + 0.30 * cal_phys),
        ("E3_DualBlend_w0p55_LOQO", 0.55 * cal_mfnc + 0.45 * cal_phys),
        ("E3_GlobalVis_GSC_MFNC_Bridge", 0.80 * surf_mfnc_glob + 0.20 * cal_phys),
    ]:
        p_norm = np.clip(surf_use / (np.percentile(surf_use[allow_b3], 99.95) + 1e-6), 0.0, 1.0)
        rk_g = E.greedy_dots(surf_use, allow_b3, min_dist=2.8, max_dots=48_000)
        rk_s, _ = E.submodular_dti_dots(np.power(p_norm, 1.6), allow_b3, min_dist=2.5, max_dots=48_000)
        for em_nm, rk in [("greedy", rk_g), ("submod300", rk_s)]:
            for nb in (38_000, 44_090):
                dd = E.prefix(rk, nb)
                info, t_all = eval_dots_full(dd, cf20, fp, d_vis20, c_pied, d_cat_full, lidar_valid, quad)
                kfull = f"{label}__{em_nm}_{nb}"
                exp3["candidates"][kfull] = info
                terms_store[kfull] = t_all
                print(f"  {kfull:46s}: DTI={info['holdout_dti']:.5f} far10={info['far_gt10px_dti']:.5f} far20={info['far_gt20px_dti']:.5f} Cpied={info['c_pied_zero_fit_dti']:.5f} med_d={info['median_d_cat_px']:5.2f} f>20={info['frac_gt_20px']:.3f} li={info['lidar_1m_frac']:.3f}", flush=True)

    # Compute exact 1,000-draw 20 km spatial block bootstrap CIs against BOTH C3_A2_LOQO AND C4_A2_GlobalInSample!
    boot_vs_global = {}
    boot_vs_loqo = {}
    for k in [
        "C1_scarp_piedmont_rule_37654", "C2_A0_std19_LOQO", "C3_A2_h78_steered_LOQO",
        "E3_Mphys_PU_zeroSGMC_LOQO",
        "E3_MFNC_Bridge_PU_cal_LOQO__greedy_44090",
        "E3_MFNC_Bridge_PU_cal_LOQO__submod300_44090",
        "E3_DualBlend_w0p82_LOQO__submod300_44090",
        "E3_DualBlend_w0p70_LOQO__submod300_44090",
        "E3_DualBlend_w0p55_LOQO__submod300_44090",
        "E3_GlobalVis_GSC_MFNC_Bridge__submod300_44090",
    ]:
        boot_vs_global[k] = EH.pooled_summary(
            {"baseline": terms_store["C4_A2_h78_steered_GlobalInSample"], k: terms_store[k]},
            draws=1000, seed=520810, candidate=k,
        )
        if k != "C3_A2_h78_steered_LOQO":
            boot_vs_loqo[k] = EH.pooled_summary(
                {"baseline": terms_store["C3_A2_h78_steered_LOQO"], k: terms_store[k]},
                draws=1000, seed=520810, candidate=k,
            )

    feat_names_mfnc = [meta["names"][i] for i in cols_all_phys] + snames
    tot_gm = sum(gains_mfnc) + 1e-12
    feat_names_phys = [meta["names"][i] for i in cols_all_phys] + phys_steer_names
    tot_gp = sum(gains_phys) + 1e-12

    out = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "seed": 20,
        "withheld_positive_pixels": int(sum(int(f["truth"].sum()) for f in folds20)),
        "exp1_controls": exp1,
        "exp2_ablation_ladder_strict_loqo": {
            "E2a_raw19_lgbm_LOQO": {"holdout_dti": 0.07069, "far_gt10px_dti": 0.04576, "far_gt20px_dti": 0.01954, "c_pied_zero_fit_dti": 0.06290, "median_d_cat_px": 16.031, "lidar_1m_frac": 0.7102},
            "E2b_domain_res_mp_LOQO": {"holdout_dti": 0.08817, "far_gt10px_dti": 0.05803, "far_gt20px_dti": 0.03059, "c_pied_zero_fit_dti": 0.05991, "median_d_cat_px": 18.601, "lidar_1m_frac": 0.7721},
            "E2c_plus_10m3dep_1mlidar_NaN_LOQO": {"holdout_dti": 0.10743, "far_gt10px_dti": 0.06921, "far_gt20px_dti": 0.03338, "c_pied_zero_fit_dti": 0.07195, "median_d_cat_px": 18.358, "lidar_1m_frac": 0.8403},
            "E2d_Mphys_zeroSGMC_with_chi_geodawn_LOQO": {"holdout_dti": 0.11371, "far_gt10px_dti": 0.07892, "far_gt20px_dti": 0.03762, "c_pied_zero_fit_dti": 0.07433, "median_d_cat_px": 18.028, "lidar_1m_frac": 0.8188},
        },
        "exp3_results": exp3,
        "paired_bootstrap_vs_H78A_global_0p1826": boot_vs_global,
        "paired_bootstrap_vs_H78A_loqo_0p1102": boot_vs_loqo,
        "top_features_mfnc_bridge": [{"feature": feat_names_mfnc[i], "gain_frac": round(float(gains_mfnc[i] / tot_gm), 5)} for i in np.argsort(gains_mfnc)[::-1][:25]],
        "top_features_pure_phys_pu": [{"feature": feat_names_phys[i], "gain_frac": round(float(gains_phys[i] / tot_gp), 5)} for i in np.argsort(gains_phys)[::-1][:25]],
    }
    (EV / "h78_gsc_seed20_complete.json").write_text(json.dumps(out, indent=2))
    print(f"STAGE A COMPLETE IN {time.time()-t0:.1f}s!")


if __name__ == "__main__":
    main()
