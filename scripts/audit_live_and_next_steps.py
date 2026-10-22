#!/usr/bin/env python3
"""Step 0: Forensic audit of all byte-matched live submissions + Session-1 next steps.

1. Audits outbound reachability of official competition & USGS/DOE URLs inside this sandbox.
2. Matches user-reported live submissions across all 1,089 SHA-256-indexed sibling rasters and
   measures exact off-catalogue pixel counts, d_cat percentiles, 1m LiDAR fraction, quadrant
   balance, and Instrument C_pied DTI right here in GEMSDOE78 (zero unverified claims).
3. Completes Session-1 deferred next steps:
   - Replicates H78-A holdout across Seed 30 and Seed 40 (alongside Seed 20) on unmodified
     vendor/gems57/evaluate_holdout.py (gems57-pooled-hide-v2).
   - Evaluates H78-A under strict 4-quadrant out-of-fold (LOQO) spatial cross-validation to
     test IR-78-INSAMPLE-MEMORIZATION-01 directly.
   - Runs flank sweep B = 2, 3, 4, 5, 6 px across full holdout AND far_gt10px / far_gt20px strata.
"""
from __future__ import annotations

import csv
import gc
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import metric as M  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import features as F  # noqa: E402
from gems78 import pipeline as P  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
EV = ROOT / "evidence"
EV.mkdir(exist_ok=True)


def check_urls() -> list[dict]:
    urls = [
        ("github_reference_solution", "https://github.com/drivendataorg/gems-prize-reference-solution"),
        ("drivendata_overview", "https://www.drivendata.org/competitions/306/competition-doe-gems/"),
        ("drivendata_problem_967", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"),
        ("drivendata_about_968", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/"),
        ("drivendata_leaderboard", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"),
        ("nlr_rules_pdf_96647", "https://docs.nlr.gov/docs/fy26osti/96647.pdf"),
        ("usgs_geodawn", "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and"),
        ("gbcge_ingenious", "https://gbcge.org/current-projects/ingenious/"),
        ("openei_gdr_1391", "https://gdr.openei.org/submissions/1391"),
        ("usgs_comcat_api", "https://earthquake.usgs.gov/fdsnws/event/1/version"),
        ("epsg_32611", "https://epsg.io/32611"),
        ("wikipedia_tversky", "https://en.wikipedia.org/wiki/Tversky_index"),
    ]
    rows = []
    for key, u in urls:
        t0 = time.time()
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "gems78-audit/1.0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                status = int(r.status)
                err = None
        except Exception as exc:
            status = None
            err = f"{type(exc).__name__}: {str(exc)[:120]}"
        rows.append({
            "id": key,
            "url": u,
            "http_status": status,
            "reachable_from_sandbox": status == 200,
            "error": err,
            "elapsed_ms": round((time.time() - t0) * 1000, 1),
        })
    return rows


# Prompt-listed user-reported live submissions (with repo hint + token match)
PROMPT_LIVE = [
    ("GEMSDOE32", "e5eb6e7e", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778),
    ("GEMSDOE36", "9b9ea4e6", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750),
    ("GEMSDOE28", "b531dae0", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710),
    ("GEMSDOE28", "8acb75e1", "h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan", 0.2708),
    ("GEMSDOE28", "56a9f473", "h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan", 0.2707),
    ("GEMSDOE28", "31e35eee", "h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan", 0.2649),
    ("GEMSDOE33", "cb490425", "h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632),
    ("GEMSDOE25", "e56ea318", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600),
    ("GEMSDOE29", "59dcaf6d", "wormrank-d28-20261003-59dcaf6dd11d-zeros", 0.2560),
    ("GEMSDOE70", "dual-submod300-oof38k", "gems70-p5-dual-submod300-oof38k-20261020", 0.2478),
    ("GEMSDOE24", "989f5950", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477),
    ("GEMSDOE27", "5512495c", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449),
    ("GEMSDOE49", "gate_ortho_w0.25", "gate_ortho_w0.25-40k-20261006T213721Z-nan", 0.2376),
    ("GEMSDOE63", "c58f60c4", "cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-zeros", 0.2303),
    ("GEMSDOE48", "b79c4c61", "h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8", 0.2296),
    ("19GEMSDOE", "e27054cf", "h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan", 0.1922),
    ("19GEMSDOE", "691e4dfa", "h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan", 0.1894),
    ("20GEMSDOE", "be0e8f6b", "h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan", 0.1890),
    ("16GEMSDOE", "df20f65e", "h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan", 0.1855),
    ("GEMSDOE10", "h28-dotted-ridge", "h28-dotted-ridge-20260928T020256236880Z-6452ae1d00", 0.1839),
    ("GEMSDOE46", "00e049b5", "r11f-scarp-radiometric-fusion-00e049b51218-zeros", 0.1589),
    ("GEMSDOE", "7f00890a", "gems-submission-20260925T001403Z-7f00890a", 0.1563),
    ("8GEMSDOE", "Hedge-v2", "Hedge-v2_submission", 0.1563),
    ("GEMSDOE2", "f68e590f", "gemsdoe2-dual-family-union-20260925T160406Z-f68e590f", 0.1560),
    ("7GEMSDOE", "36c3a3f3", "lidarscarp-ridge-top2pct-36c3a3f341c8", 0.1461),
    ("GEMSDOE67", "ovtr-ml-cover-tau3p0", "ovtr-ml-cover-tau3p0-20261012-nan", 0.1426),
    ("GEMSDOE23", "0d4e02e8", "h30-arrangement-matched-habitat-20261002-0d4e02e8-nan", 0.1352),
    ("12GEMSDOE", "0c9199f1", "r7-nms3-dem10-scarp_0c9199f14e62", 0.1294),
    ("GEMSDOE10", "h25-ctx-ridge", "H25-ctx-ridge-20260927T232947704150Z-6452ae1d00", 0.1280),
    ("GEMSDOE26", "47629f49", "dilcond-oof-v1-20261003-47629f496133-nan", 0.1223),
    ("GEMSDOE37", "0bef9211", "h6-physics-dotted-80k-20261005T055000Z-0bef9211631c", 0.1193),
    ("GEMSDOE66", "37654dots-20261020T190152Z", "gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros", 0.1152),
    ("GEMSDOE51", "9a0b32c8", "h53-twostage-20261008T040951Z-9a0b32c871", 0.1047),
    ("GEMSDOE22", "e2ec4b49", "h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan", 0.1002),
    ("GEMSDOE40", "f28e5cff", "h45-eulerdepthreadcluster-20261006-f28e5cff6826-zeros", 0.0984),
    ("13GEMSDOE", "r13-lattice-s5", "20261001_r13-lattice-s5_v2_nan-outside", 0.0904),
    ("GEMSDOE52", "h97b-candidate", "h97b-candidate", 0.0856),
    ("GEMSDOE50", "h59-sharpened-scarp-scatter", "h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite", 0.0764),
    ("GEMSDOE38", "ecfbf59e", "D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero", 0.0763),
    ("61GEMSDOE", "28d4fac6", "h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea-zeros-zeros", 0.0751),
    ("GEMSDOE44", "b0cfe956", "h46-twostageAB_20261006T160000Z_b0cfe956-zeros", 0.0715),
    ("56GEMSDOE", "h56-final-dotted-ridge", "h56-final-dotted-ridge-d2p8-20261009T190421Z", 0.0658),
    ("GEMSDOE42", "xscale-worm-persistence", "xscale-worm-persistence-20261006T000541Z-nan", 0.0581),
    ("GEMSDOE71", "gems71-hydro-conduit", "gems71-hydro-conduit-38800-20261020T120000Z-zeros", 0.0558),
    ("GEMSDOE29", "c8dcd780", "sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan", 0.0512),
    ("59GEMSDOE", "h59j-coherence-consensus", "h59j-coherence-consensus-dotted-20261011T043000Z", 0.0499),
    ("GEMSDOE72", "6e6525e5", "gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros", 0.0492),
    ("GEMSDOE68", "849a0f04", "gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-zeros", 0.0437),
    ("GEMSDOE65", "5e4660cd", "sar-em-propensity-half-20261011T223500Z-5e4660cd-zeros", 0.0431),
    ("GEMSDOE47", "h60-lidarscarp", "h60-lidarscarp-s2p0-20261007-nanoutside", 0.0430),
    ("GEMSDOE43", "bc2e4e9a", "sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan", 0.0424),
    ("GEMSDOE64", "h64-lidar-scarp-cv", "h64-lidar-scarp-cv-20261011T220000Z", 0.0383),
    ("GEMSDOE67", "h67a-orientip", "h67a-orientip-lane-29447dots-20261012T021226Z-allfinite", 0.0356),
    ("60GEMSDOE", "h73-chi-coherent-corridor", "h73-chi-coherent-corridor-12000-20261011T195818Z-zeros", 0.0351),
    ("55GEMSDOE", "tensor_full-n16000", "tensor_full-n16000-sep3-20261009T211747Z-nan", 0.0290),
    ("57GEMSDOE", "00cf5b20", "h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1-zeros", 0.0254),
    ("58GEMSDOE", "ml-binary-ridge", "ml-binary-ridge-20261012T000000Z", 0.0180),
    ("GEMSDOE53", "49bec522", "h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522-zeros", 0.0159),
    ("GEMSDOE9", "2314b599", "2314b599", 0.0107),
    ("GEMSDOE45", "h51-km-faultzone", "h51-km-faultzone-20261006-zeros", 0.0106),
    ("GEMSDOE69", "f29b6df5", "h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5", 0.0053),
    ("61GEMSDOE", "eb2ae4bb", "h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b-zeros", 0.0009),
    ("62GEMSDOE", "datum-lahontan-strain-gauge", "datum-lahontan-strain-gauge-defensible-440dots-zeros", 0.0000),
]


def build_c_pied(fp, cat):
    with rasterio.open(DATA / "training_features.tif") as ds:
        depth_base = ds.read(15).astype(np.float32)
    with rasterio.open(DATA / "external/lidar_scarp_features_u8.tif") as ds:
        rel_10m_u8 = ds.read(9)
        lidar_valid = ds.read(12) > 0
    with rasterio.open(DATA / "external/topo_10m_derived_100m_u8.tif") as ds:
        slope_p90_u8 = ds.read(1)
    with rasterio.open(DATA / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1) > 0
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    p75_rel = float(np.percentile(rel_10m_u8[cat], 75))
    p80_slp = float(np.percentile(slope_p90_u8[cat], 80))
    # Exclude SGMC inside C_pied training completely — C_pied is NEVER touched in any feature or fit!
    c_pied = (
        fp & sgmc & (~cat) & (d_cat > 2.5)
        & (rel_10m_u8 <= p75_rel)
        & (slope_p90_u8 <= p80_slp)
        & (depth_base >= 250.0)
    )
    return c_pied, d_cat, lidar_valid


def audit_live_submissions(fp, cat, c_pied, d_cat, lidar_valid) -> dict:
    reg = json.loads((DATA / "full_registry_index.json").read_text())
    matched_rows = []
    for repo, tok, sub_name, live_score in PROMPT_LIVE:
        cands = [r for r in reg if tok.lower() in r["name"].lower() or tok.lower() in r["sha256"].lower()]
        cands_repo = [r for r in cands if r["repo"].lower() == repo.lower()]
        pick = cands_repo[0] if cands_repo else (cands[0] if cands else None)
        if pick is None:
            continue
        try:
            with rasterio.open(pick["file"]) as ds:
                if ds.shape != fp.shape or ds.count != 1:
                    continue
                arr = ds.read(1).astype(np.float32)
        except Exception:
            continue
        arr = np.where(np.isfinite(arr) & fp, np.clip(arr, 0.0, 1.0), 0.0)
        support = (arr > 0) & fp & (~cat)
        n_pos = int(support.sum())
        if n_pos == 0:
            continue
        # Soft/binary exact DTI against off-catalogue piedmont/basin benchmark C_pied
        r_cp = M.dti_exact(arr, c_pied, valid=fp, known=cat)
        dc = d_cat[support]
        matched_rows.append({
            "repo": repo,
            "submission_name": sub_name,
            "matched_file": Path(pick["file"]).name,
            "sha256": pick["sha256"],
            "user_reported_live_dti": live_score,
            "c_pied_dti": round(float(r_cp["dti"]), 5),
            "offcat_positive_px": n_pos,
            "mass_sum": round(float(arr[fp & (~cat)].sum()), 1),
            "is_binary": bool(np.all((arr == 0.0) | (arr == 1.0))),
            "median_d_cat_px": round(float(np.median(dc)), 2),
            "frac_le_5px": round(float((dc <= 5.0).mean()), 4),
            "frac_gt_20px": round(float((dc > 20.0).mean()), 4),
            "lidar_1m_frac": round(float(lidar_valid[support].mean()), 4),
        })

    # Deduplicate by sha256 to measure unbiased correlation across unique scored rasters
    uniq = {}
    for r in matched_rows:
        uniq.setdefault(r["sha256"], r)
    urows = list(uniq.values())
    xs = np.array([r["c_pied_dti"] for r in urows])
    ys = np.array([r["user_reported_live_dti"] for r in urows])
    # All unique rasters & off-SGMC-leakage unique rasters (excluding GEMSDOE29/72 that directly emitted SGMC!)
    non_sgmc = [r for r in urows if "sgmc" not in r["submission_name"].lower()]
    xs_ns = np.array([r["c_pied_dti"] for r in non_sgmc])
    ys_ns = np.array([r["user_reported_live_dti"] for r in non_sgmc])

    out = {
        "evidence_class": "DATA-MEASUREMENT (live scores are user-reported portal figures from PROMPT; C_pied uses zero SGMC training and zero fitted LB parameters)",
        "total_prompt_entries_checked": len(PROMPT_LIVE),
        "byte_matched_entries": len(matched_rows),
        "unique_byte_matched_rasters": len(urows),
        "non_sgmc_unique_rasters": len(non_sgmc),
        "spearman_all_unique": {"rho": float(spearmanr(xs, ys).statistic), "p": float(spearmanr(xs, ys).pvalue)},
        "pearson_all_unique": {"r": float(pearsonr(xs, ys).statistic), "p": float(pearsonr(xs, ys).pvalue)},
        "spearman_non_sgmc_unique": {"rho": float(spearmanr(xs_ns, ys_ns).statistic), "p": float(spearmanr(xs_ns, ys_ns).pvalue)},
        "pearson_non_sgmc_unique": {"r": float(pearsonr(xs_ns, ys_ns).statistic), "p": float(pearsonr(xs_ns, ys_ns).pvalue)},
        "rows": matched_rows,
    }
    (EV / "live_submissions_audit.json").write_text(json.dumps(out, indent=2))
    with open(ROOT / "registry" / "family_scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(matched_rows[0].keys()))
        w.writeheader()
        w.writerows(matched_rows)
    return out


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
    return float(EH.from_terms(tot.sum(axis=0))), tot


def run_session1_next_steps(g) -> dict:
    fp = g.footprint
    seed_results = {}
    # 1. Replicate H78-A on Seeds 20, 30, 40 (global-visible protocol AND strict LOQO protocol!) + flank sweep 2..6 px
    for seed in (20, 30, 40):
        folds, quad = HO.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        hidden = folds[0]["hidden_all"]
        d_vis = distance_transform_edt(~visible).astype(np.float32)
        tag = f"seed{seed}"
        feats_path, _ = P.build_feature_matrix(tag, fp, visible)
        pos, negs = P.training_sample(fp, visible, 450_000, seed=seed)
        rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)

        entry = {
            "seed": seed,
            "withheld_positive_pixels": int(sum(int(f["truth"].sum()) for f in folds)),
            "global_visible_arms_B3_44090": {},
            "flank_sweep_A2_44090": {},
            "strict_loqo_arms": {},
        }
        # Global-visible arms (replicating H78-A across seeds 20, 30, 40)
        for arm in ("A0_std19", "A1_iso", "A2_h78_steered"):
            sc_path = ROOT / "data/processed" / f"score_{tag}_{arm}.npy"
            if sc_path.exists():
                s = np.load(sc_path)
            else:
                clf, _ = P.fit_arm(feats_path, rows_pos, rows_neg, arm, seed=0)
                s = P.score_grid(clf, feats_path, arm, fp)
                np.save(sc_path, s)
            allowed_b3 = fp & ~E.flank_mask(visible, 3.0)
            rk_b3 = E.greedy_dots(s, allowed_b3, min_dist=2.8, max_dots=44_090)
            dots_b3 = E.prefix(rk_b3, 44_090)
            dti_all, _ = eval_dots(dots_b3, folds, fp)
            dti_far10, _ = eval_dots(dots_b3, folds, fp, mask_truth=(d_vis > 10.0))
            entry["global_visible_arms_B3_44090"][arm] = {
                "pooled_dti": round(dti_all, 5),
                "far_gt10px_dti": round(dti_far10, 5),
            }
            if arm == "A2_h78_steered" and seed == 20:
                for bpx in (2.0, 3.0, 4.0, 5.0, 6.0):
                    rk = E.greedy_dots(s, fp & ~E.flank_mask(visible, bpx), min_dist=2.8, max_dots=50_000)
                    d44 = E.prefix(rk, 44_090)
                    da, _ = eval_dots(d44, folds, fp)
                    df10, _ = eval_dots(d44, folds, fp, mask_truth=(d_vis > 10.0))
                    df20, _ = eval_dots(d44, folds, fp, mask_truth=(d_vis > 20.0))
                    entry["flank_sweep_A2_44090"][f"B{int(bpx)}"] = {
                        "all_dti": round(da, 5),
                        "far_gt10px_dti": round(df10, 5),
                        "far_gt20px_dti": round(df20, 5),
                    }
            del s
            gc.collect()

        # Also test strict 4-quadrant LOQO on Seed 20 for A0_std19 vs A2_h78_steered!
        if seed == 20:
            mm = np.load(feats_path, mmap_mode="r")
            fp_quad = quad[fp]
            vis_fp = visible[fp]
            flank2_fp = E.flank_mask(visible, 2.0)[fp]
            for arm in ("A0_std19", "A2_h78_steered"):
                cols = P.arm_columns(arm)
                oof_fp = np.zeros(mm.shape[0], np.float32)
                rng = np.random.default_rng(20)
                for q in range(4):
                    tr_pos = np.flatnonzero(vis_fp & (fp_quad != q))
                    tr_neg_pool = np.flatnonzero((~flank2_fp) & (fp_quad != q))
                    tr_neg = rng.choice(tr_neg_pool, size=min(4 * tr_pos.size, tr_neg_pool.size), replace=False)
                    rows = np.concatenate([tr_pos, tr_neg])
                    order = np.argsort(rows)
                    Xtr = np.asarray(mm[rows[order]][:, cols], np.float32)
                    ytr = np.concatenate([np.ones(tr_pos.size, np.int8), np.zeros(tr_neg.size, np.int8)])[order]
                    from sklearn.ensemble import HistGradientBoostingClassifier
                    clf = HistGradientBoostingClassifier(
                        max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
                        min_samples_leaf=200, l2_regularization=1.0, random_state=q,
                    )
                    clf.fit(Xtr, ytr)
                    te_rows = np.flatnonzero(fp_quad == q)
                    oof_fp[te_rows] = clf.predict_proba(np.asarray(mm[te_rows][:, cols], np.float32))[:, 1].astype(np.float32)
                    del Xtr, ytr, clf
                    gc.collect()
                oof_grid = np.zeros(fp.shape, np.float32)
                oof_grid[fp] = oof_fp
                for bpx, nb in [(2.5, 37_654), (3.0, 44_090)]:
                    rk = E.greedy_dots(oof_grid, fp & ~E.flank_mask(visible, bpx), min_dist=2.8, max_dots=nb)
                    dd = E.prefix(rk, nb)
                    d_all, _ = eval_dots(dd, folds, fp)
                    d_f10, _ = eval_dots(dd, folds, fp, mask_truth=(d_vis > 10.0))
                    q_counts = {HO.FOLD_NAMES[q]: int((dd & (quad == q)).sum()) for q in range(4)}
                    entry["strict_loqo_arms"][f"{arm}|B{bpx}|{nb}"] = {
                        "loqo_dti": round(d_all, 5),
                        "far_gt10px_dti": round(d_f10, 5),
                        "quadrant_dots": q_counts,
                    }
            del mm
            gc.collect()

        seed_results[f"seed{seed}"] = entry
        print(f"Seed {seed} complete:", json.dumps(entry["global_visible_arms_B3_44090"]))
        if entry["strict_loqo_arms"]:
            print("  H78-A strict LOQO:", json.dumps(entry["strict_loqo_arms"]))

    # Across-seed summary
    across = {}
    for arm in ("A0_std19", "A1_iso", "A2_h78_steered"):
        vals = [seed_results[f"seed{s}"]["global_visible_arms_B3_44090"][arm]["pooled_dti"] for s in (20, 30, 40)]
        fvals = [seed_results[f"seed{s}"]["global_visible_arms_B3_44090"][arm]["far_gt10px_dti"] for s in (20, 30, 40)]
        across[arm] = {
            "mean_dti_3seeds": round(float(np.mean(vals)), 5),
            "std_dti_3seeds": round(float(np.std(vals, ddof=1)), 5),
            "min_max": [min(vals), max(vals)],
            "mean_far_gt10px_dti_3seeds": round(float(np.mean(fvals)), 5),
        }
    out = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "across_seeds_20_30_40": across,
        "by_seed": seed_results,
    }
    (EV / "h78_session1_next_steps.json").write_text(json.dumps(out, indent=2))
    return out


def main():
    t0 = time.time()
    print("=== [1/3] Checking URL reachability inside sandbox ===")
    urls = check_urls()
    (EV / "url_reachability_audit.json").write_text(json.dumps(urls, indent=2))
    for u in urls:
        print(f"  {u['id']:28s} status={u['http_status']} reachable={u['reachable_from_sandbox']}")

    g = G.load_grid(DATA)
    fp, cat = g.footprint, g.catalogue

    print("=== [2/3] Auditing byte-matched historical live submissions ===")
    c_pied, d_cat, lidar_valid = build_c_pied(fp, cat)
    live = audit_live_submissions(fp, cat, c_pied, d_cat, lidar_valid)
    print("  Unique matched rasters:", live["unique_byte_matched_rasters"],
          "Non-SGMC Spearman rho:", round(live["spearman_non_sgmc_unique"]["rho"], 4),
          "p:", f"{live['spearman_non_sgmc_unique']['p']:.2e}")

    print("=== [3/3] Completing Session-1 deferred next steps (Seeds 20/30/40 + Flank sweep + Strict LOQO diagnostic) ===")
    nxt = run_session1_next_steps(g)
    print("Across 3 seeds (20, 30, 40):", json.dumps(nxt["across_seeds_20_30_40"], indent=2))
    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
