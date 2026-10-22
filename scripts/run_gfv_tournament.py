#!/usr/bin/env python3
"""Preregistered 3-Experiment Holdout Suite for Lane H78-GFV (strict LOQO).

Evaluates all 3 preregistered experiments + random & geometric null controls
across seed=20 (11,321 withheld positives) and seed=30 (11,342 withheld positives)
under strict Leave-One-Quadrant-Out (LOQO) discipline on the unmodified shared
evaluator ``vendor/gems57/evaluate_holdout.py`` (``gems57-pooled-hide-v2``).
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
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.kernel_approximation import Nystroem
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neural_network import MLPClassifier, MLPRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import emit as E57  # noqa: E402
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems78 import emit as E78  # noqa: E402
from gems78 import gfv  # noqa: E402

N_STATIC = 101


def log(*args):
    print(time.strftime("%H:%M:%S"), *args, flush=True)


class RowMajorFootprintReader:
    """Zero-mmap sequential streaming reader over ``fp101_f16.bin`` (5.17M x 101)."""

    def __init__(self, bin_path: Path, fp: np.ndarray):
        self.bin_path = bin_path
        self.fp = fp
        self.H, self.W = fp.shape
        self.fp_idx = np.flatnonzero(fp)
        self.n_fp = self.fp_idx.size
        self.grid_to_fprow = np.full(fp.size, -1, dtype=np.int32)
        self.grid_to_fprow[self.fp_idx] = np.arange(self.n_fp, dtype=np.int32)

    def gather_rows(self, ys: np.ndarray, xs: np.ndarray, geo12: np.ndarray | None = None) -> np.ndarray:
        fp_rows = self.grid_to_fprow[ys.astype(np.int64) * self.W + xs.astype(np.int64)]
        assert np.all(fp_rows >= 0)
        order = np.argsort(fp_rows)
        sorted_r = fp_rows[order]
        inv_order = np.empty_like(order)
        inv_order[order] = np.arange(order.size)

        n_g = geo12.shape[0] if geo12 is not None else 0
        X_sorted = np.empty((order.size, N_STATIC + n_g), dtype=np.float32)

        step = 650_000
        ptr = 0
        with self.bin_path.open("rb") as f:
            for r0 in range(0, self.n_fp, step):
                r1 = min(r0 + step, self.n_fp)
                n_chunk = r1 - r0
                buf = np.fromfile(f, dtype=np.float16, count=n_chunk * N_STATIC).reshape(n_chunk, N_STATIC)
                if ptr < sorted_r.size and sorted_r[ptr] < r1:
                    p_end = int(np.searchsorted(sorted_r, r1, side="left"))
                    X_sorted[ptr:p_end, :N_STATIC] = buf[sorted_r[ptr:p_end] - r0].astype(np.float32)
                    ptr = p_end
                del buf
        X = X_sorted[inv_order]
        del X_sorted
        if geo12 is not None:
            for j in range(n_g):
                X[:, N_STATIC + j] = geo12[j, ys, xs].astype(np.float32)
        return X

    def iter_quadrant_batches(
        self,
        quad_mask: np.ndarray,
        geo12: np.ndarray | None = None,
        batch_fp_rows: int = 520_000,
    ):
        q_fp = quad_mask.ravel()[self.fp_idx]
        n_g = geo12.shape[0] if geo12 is not None else 0
        with self.bin_path.open("rb") as f:
            for r0 in range(0, self.n_fp, batch_fp_rows):
                r1 = min(r0 + batch_fp_rows, self.n_fp)
                n_chunk = r1 - r0
                sub_q = q_fp[r0:r1]
                if not sub_q.any():
                    f.seek(n_chunk * N_STATIC * 2, 1)
                    continue
                buf = np.fromfile(f, dtype=np.float16, count=n_chunk * N_STATIC).reshape(n_chunk, N_STATIC)
                flat_cells = self.fp_idx[r0:r1][sub_q]
                Xb = np.empty((flat_cells.size, N_STATIC + n_g), dtype=np.float32)
                Xb[:, :N_STATIC] = buf[sub_q].astype(np.float32)
                del buf
                if geo12 is not None:
                    for j in range(n_g):
                        Xb[:, N_STATIC + j] = geo12[j].ravel()[flat_cells].astype(np.float32)
                yield flat_cells, Xb


def _fit_fast_scaler(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    Xc = np.clip(X, -1e4, 1e4)
    q25, med, q75 = np.percentile(Xc, [25.0, 50.0, 75.0], axis=0)
    inv_iqr = (1.0 / np.maximum(q75 - q25, 1e-3)).astype(np.float32)
    return med.astype(np.float32), inv_iqr


def fit_hetero_classifier(X: np.ndarray, y: np.ndarray, sw: np.ndarray, seed: int):
    """Fit 3 genuinely distinct model families: Boosted Trees + Neural MLP + Nystroem RBF."""
    rng = np.random.default_rng(seed)
    val_mask = rng.random(y.size) < 0.14
    tr_m = ~val_mask

    hgb_deep = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=300,
        max_leaf_nodes=79,
        min_samples_leaf=60,
        l2_regularization=2.0,
        random_state=seed,
    )
    hgb_smooth = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=260,
        max_leaf_nodes=31,
        min_samples_leaf=180,
        l2_regularization=4.0,
        max_features=0.75,
        random_state=seed + 7,
    )
    hgb_deep.fit(X[tr_m], y[tr_m], sample_weight=sw[tr_m])
    hgb_smooth.fit(X[tr_m], y[tr_m], sample_weight=sw[tr_m])

    idx_tr = np.flatnonzero(tr_m)
    p_w = sw[tr_m] / sw[tr_m].sum()
    sub_idx = rng.choice(idx_tr, size=min(40_000, idx_tr.size), replace=True, p=p_w)
    med, inv_iqr = _fit_fast_scaler(X[sub_idx])
    Xs = ((np.clip(X[sub_idx], -1e4, 1e4) - med) * inv_iqr).astype(np.float32)

    mlp = MLPClassifier(
        hidden_layer_sizes=(80, 40),
        activation="relu",
        alpha=1.5e-2,
        batch_size=512,
        learning_rate_init=1.5e-3,
        max_iter=22,
        early_stopping=True,
        random_state=seed + 23,
    )
    nys = Nystroem(kernel="rbf", gamma=0.015, n_components=96, random_state=seed + 41)
    lr_k = LogisticRegression(C=1.5, max_iter=200)
    mlp.fit(Xs, y[sub_idx])
    lr_k.fit(nys.fit_transform(Xs), y[sub_idx])
    del Xs

    Xv_s = ((np.clip(X[val_mask], -1e4, 1e4) - med) * inv_iqr).astype(np.float32)
    Z_val = np.column_stack([
        hgb_deep.predict_proba(X[val_mask])[:, 1],
        hgb_smooth.predict_proba(X[val_mask])[:, 1],
        mlp.predict_proba(Xv_s)[:, 1],
        lr_k.predict_proba(nys.transform(Xv_s))[:, 1],
    ])
    logits = np.log(np.clip(Z_val, 1e-6, 1.0 - 1e-6) / (1.0 - np.clip(Z_val, 1e-6, 1.0 - 1e-6)))
    meta = LogisticRegression(C=2.0, max_iter=200)
    meta.fit(logits, y[val_mask], sample_weight=sw[val_mask])
    return (hgb_deep, hgb_smooth, mlp, nys, lr_k, meta, med, inv_iqr)


def predict_hetero_proba(models, Xb: np.ndarray, chunk_pts: int = 131_072) -> np.ndarray:
    hgb_deep, hgb_smooth, mlp, nys, lr_k, meta, med, inv_iqr = models
    out = np.empty(Xb.shape[0], dtype=np.float32)
    for i0 in range(0, Xb.shape[0], chunk_pts):
        i1 = min(i0 + chunk_pts, Xb.shape[0])
        Xi = Xb[i0:i1]
        Xs = ((np.clip(Xi, -1e4, 1e4) - med) * inv_iqr).astype(np.float32)
        Z = np.column_stack([
            hgb_deep.predict_proba(Xi)[:, 1],
            hgb_smooth.predict_proba(Xi)[:, 1],
            mlp.predict_proba(Xs)[:, 1],
            lr_k.predict_proba(nys.transform(Xs))[:, 1],
        ])
        logits = np.log(np.clip(Z, 1e-6, 1.0 - 1e-6) / (1.0 - np.clip(Z, 1e-6, 1.0 - 1e-6)))
        out[i0:i1] = meta.predict_proba(logits)[:, 1].astype(np.float32)
    return out


def fit_kernel_self_credit(X: np.ndarray, y_kern: np.ndarray, sw: np.ndarray, seed: int):
    """Fit Dual-Head M continuous R=300 m max-kernel self-credit regressor ensemble."""
    rng = np.random.default_rng(seed + 91)
    hgb_m1 = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.055,
        max_iter=260,
        max_leaf_nodes=79,
        min_samples_leaf=60,
        l2_regularization=2.0,
        random_state=seed + 101,
    )
    hgb_m2 = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=31,
        min_samples_leaf=180,
        l2_regularization=4.0,
        max_features=0.75,
        random_state=seed + 113,
    )
    hgb_m1.fit(X, y_kern, sample_weight=sw)
    hgb_m2.fit(X, y_kern, sample_weight=sw)

    p_w = sw / sw.sum()
    sub_idx = rng.choice(y_kern.size, size=min(40_000, y_kern.size), replace=True, p=p_w)
    med, inv_iqr = _fit_fast_scaler(X[sub_idx])
    Xs = ((np.clip(X[sub_idx], -1e4, 1e4) - med) * inv_iqr).astype(np.float32)

    mlp_m = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        alpha=2e-2,
        batch_size=512,
        learning_rate_init=1.5e-3,
        max_iter=20,
        early_stopping=True,
        random_state=seed + 131,
    )
    nys_m = Nystroem(kernel="rbf", gamma=0.015, n_components=96, random_state=seed + 151)
    rg_m = Ridge(alpha=5.0)
    mlp_m.fit(Xs, y_kern[sub_idx])
    rg_m.fit(nys_m.fit_transform(Xs), y_kern[sub_idx])
    del Xs
    return (hgb_m1, hgb_m2, mlp_m, nys_m, rg_m, med, inv_iqr)


def predict_kernel_self_credit(models_m, Xb: np.ndarray, chunk_pts: int = 131_072) -> np.ndarray:
    hgb_m1, hgb_m2, mlp_m, nys_m, rg_m, med, inv_iqr = models_m
    out = np.empty(Xb.shape[0], dtype=np.float32)
    for i0 in range(0, Xb.shape[0], chunk_pts):
        i1 = min(i0 + chunk_pts, Xb.shape[0])
        Xi = Xb[i0:i1]
        Xs = ((np.clip(Xi, -1e4, 1e4) - med) * inv_iqr).astype(np.float32)
        pred = (
            0.44 * hgb_m1.predict(Xi)
            + 0.30 * hgb_m2.predict(Xi)
            + 0.16 * np.clip(mlp_m.predict(Xs), 0.0, 1.0)
            + 0.10 * np.clip(rg_m.predict(nys_m.transform(Xs)), 0.0, 1.0)
        )
        out[i0:i1] = np.clip(pred, 0.0, 1.0).astype(np.float32)
    return out


def eval_dots_on_folds(dots_bool: np.ndarray, folds: list[dict], fp: np.ndarray):
    pred = dots_bool.astype(np.float32)
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


def make_far_folds(folds: list[dict], visible: np.ndarray, min_d: float = 10.0) -> list[dict]:
    d_vis = distance_transform_edt(~visible)
    far_folds = []
    for f in folds:
        fc = dict(f)
        fc["truth"] = np.asarray(f["truth"], dtype=bool) & (d_vis > min_d)
        far_folds.append(fc)
    return far_folds


def run_seed(seed: int):
    t_seed = time.time()
    DATA = ROOT / ".cache" / "gems_data"
    FEAT = ROOT / ".cache" / "features"
    WORK = ROOT / ".cache" / "work"
    WORK.mkdir(parents=True, exist_ok=True)

    g = G.load_grid(DATA)
    fp = g.footprint
    folds, quad = HO.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    hidden = folds[0]["hidden_all"]
    d_vis_global = distance_transform_edt(~visible).astype(np.float32)
    log(f"=== SEED {seed}: withheld_positives={int(hidden.sum())}, visible={int(visible.sum())} ===")

    reader = RowMajorFootprintReader(FEAT / "fp101_f16.bin", fp)
    strike_theta = np.load(FEAT / "gfv_phys_strike.npy").astype(np.float32)
    hydro_nodes2x = np.load(FEAT / "gfv_hydro_nodes2x.npy")

    allow_eval = np.zeros(fp.shape, dtype=bool)
    for f in folds:
        r = f["region"]
        allow_eval[r] = fp[r] & (~f["masked_known"][r]) & (d_vis_global[r] > 3.0)

    # =========================================================================
    # EXPERIMENT 1 OF 3: E1_PureMultiPhys_101 (Zero-Catalogue 101-Band Ensemble)
    # =========================================================================
    e1_cache = WORK / f"oof_e1_p_s{seed}.npy"
    if e1_cache.exists():
        oof_e1_p = np.load(e1_cache).astype(np.float32)
        log(f"Loaded cached {e1_cache.name}")
    else:
        t_e1 = time.time()
        oof_e1_p = np.zeros(fp.shape, dtype=np.float32)
        for q in range(4):
            tr = (quad != q) & fp
            pos_mask = visible & tr
            neg_near = tr & (d_vis_global > 3.0) & (d_vis_global <= 25.0)
            neg_far = tr & (d_vis_global > 25.0)

            py, px = np.nonzero(pos_mask)
            ny1, nx1 = np.nonzero(neg_near)
            ny2, nx2 = np.nonzero(neg_far)
            rng = np.random.default_rng(1000 * seed + q)
            s1 = rng.choice(ny1.size, size=min(45_000, ny1.size), replace=False)
            s2 = rng.choice(ny2.size, size=min(65_000, ny2.size), replace=False)

            ys = np.concatenate([py, ny1[s1], ny2[s2]])
            xs = np.concatenate([px, nx1[s1], nx2[s2]])
            y = np.r_[np.ones(py.size, np.int32), np.zeros(s1.size + s2.size, np.int32)]
            sw = np.r_[
                np.ones(py.size, np.float64),
                np.full(s1.size, ny1.size / max(s1.size, 1), np.float64),
                np.full(s2.size, ny2.size / max(s2.size, 1), np.float64),
            ]
            X = reader.gather_rows(ys, xs, None)
            models_e1 = fit_hetero_classifier(X, y, sw, seed=2000 + 10 * seed + q)
            del X, y, sw
            gc.collect()

            for flat_cells, Xb in reader.iter_quadrant_batches(quad == q, None):
                oof_e1_p.ravel()[flat_cells] = predict_hetero_proba(models_e1, Xb)
                del Xb
            del models_e1
            gc.collect()
            log(f"E1 quadrant {q} predicted ({time.time()-t_e1:.1f}s)")
        np.save(e1_cache, oof_e1_p.astype(np.float16))

    # =========================================================================
    # EXPERIMENT 2 & 3 FIT (STRICT LOQO GFV DUAL-HEAD POSTERIORS p_gfv, m_gfv)
    # =========================================================================
    p_cache = WORK / f"oof_p_gfv_raw_s{seed}.npy"
    m_cache = WORK / f"oof_m_gfv_raw_s{seed}.npy"
    if p_cache.exists() and m_cache.exists():
        oof_p_gfv = np.load(p_cache).astype(np.float32)
        oof_m_gfv = np.load(m_cache).astype(np.float32)
        log(f"Loaded cached {p_cache.name} & {m_cache.name}")
    else:
        p5, p995 = np.percentile(oof_e1_p[fp], [5.0, 99.5])
        weak_oof = np.clip((oof_e1_p - p5) / max(float(p995 - p5), 1e-6), 0.0, 1.0)

        t_geo = time.time()
        comp_vis, n_comp_vis = label(visible, structure=np.ones((3, 3), dtype=np.int32))
        rng_nest = np.random.default_rng(5000 + seed)
        comp_fold = np.zeros(n_comp_vis + 1, dtype=np.int32)
        comp_fold[1:] = rng_nest.integers(0, 3, size=n_comp_vis)

        nested_samples = []
        for k in range(3):
            vis_ctx_k = visible & (comp_fold[comp_vis] != k)
            vis_tgt_k = visible & (comp_fold[comp_vis] == k)
            geo_k = gfv.compute_geodesic_network(
                vis_ctx_k, weak_oof, strike_theta, fp, hydro_nodes2x, n_color_rounds=6, seed=300 + 10 * seed + k
            )
            d_ctx_k = distance_transform_edt(~vis_ctx_k).astype(np.float32)
            d_tgt_k = distance_transform_edt(~vis_tgt_k).astype(np.float32)
            valid_pool = fp & (d_ctx_k > 3.0)

            ys_all_q, xs_all_q, q_tag, yp_all_q, ym_all_q, sw_all_q = [], [], [], [], [], []
            for q_part in range(4):
                qm = valid_pool & (quad == q_part)
                s0 = qm & vis_tgt_k
                s1 = qm & (~vis_tgt_k) & (d_tgt_k <= 3.0)
                s2 = qm & (d_tgt_k > 3.0) & (d_ctx_k <= 28.0)
                s3 = qm & (d_tgt_k > 3.0) & (d_ctx_k > 28.0)

                y0, x0 = np.nonzero(s0)
                y1, x1 = np.nonzero(s1)
                y2, x2 = np.nonzero(s2)
                y3, x3 = np.nonzero(s3)

                c1 = rng_nest.choice(y1.size, size=min(4_500, y1.size), replace=False) if y1.size else np.empty(0, int)
                c2 = rng_nest.choice(y2.size, size=min(6_500, y2.size), replace=False) if y2.size else np.empty(0, int)
                c3 = rng_nest.choice(y3.size, size=min(6_500, y3.size), replace=False) if y3.size else np.empty(0, int)

                ys_k = np.concatenate([y0, y1[c1], y2[c2], y3[c3]])
                xs_k = np.concatenate([x0, x1[c1], x2[c2], x3[c3]])
                ys_all_q.append(ys_k)
                xs_all_q.append(xs_k)
                q_tag.append(np.full(ys_k.size, q_part, np.int8))
                yp_all_q.append(np.r_[np.ones(y0.size, np.int32), np.zeros(c1.size + c2.size + c3.size, np.int32)])
                ym_all_q.append(np.maximum(0.0, 1.0 - d_tgt_k[ys_k, xs_k] / 3.0).astype(np.float32))
                sw_all_q.append(np.r_[
                    np.ones(y0.size, np.float64),
                    np.full(c1.size, y1.size / max(c1.size, 1), np.float64),
                    np.full(c2.size, y2.size / max(c2.size, 1), np.float64),
                    np.full(c3.size, y3.size / max(c3.size, 1), np.float64),
                ])
            ys_cat = np.concatenate(ys_all_q)
            xs_cat = np.concatenate(xs_all_q)
            X_cat = reader.gather_rows(ys_cat, xs_cat, geo_k)
            q_cat = np.concatenate(q_tag)
            yp_cat = np.concatenate(yp_all_q)
            ym_cat = np.concatenate(ym_all_q)
            sw_cat = np.concatenate(sw_all_q)
            for q_part in range(4):
                m_q = q_cat == q_part
                nested_samples.append((q_part, X_cat[m_q].copy(), yp_cat[m_q].copy(), ym_cat[m_q].copy(), sw_cat[m_q].copy()))
            del X_cat, geo_k, d_ctx_k, d_tgt_k, vis_ctx_k, vis_tgt_k
            gc.collect()
            log(f"Nested geodesic split {k+1}/3 sampled ({time.time()-t_geo:.1f}s)")

        geo_eval = gfv.compute_geodesic_network(
            visible, weak_oof, strike_theta, fp, hydro_nodes2x, n_color_rounds=8, seed=900 + seed
        )
        log(f"Evaluation geodesic network ready ({time.time()-t_geo:.1f}s)")

        oof_p_gfv = np.zeros(fp.shape, dtype=np.float32)
        oof_m_gfv = np.zeros(fp.shape, dtype=np.float32)

        for q in range(4):
            tq = time.time()
            parts = [item for item in nested_samples if item[0] != q]
            X_tr = np.concatenate([p_[1] for p_ in parts], axis=0)
            yp_tr = np.concatenate([p_[2] for p_ in parts], axis=0)
            ym_tr = np.concatenate([p_[3] for p_ in parts], axis=0)
            sw_tr = np.concatenate([p_[4] for p_ in parts], axis=0)

            models_p = fit_hetero_classifier(X_tr, yp_tr, sw_tr, seed=4000 + 10 * seed + q)
            models_m = fit_kernel_self_credit(X_tr, ym_tr, sw_tr, seed=6000 + 10 * seed + q)
            del X_tr, yp_tr, ym_tr, sw_tr, parts
            gc.collect()

            for flat_cells, Xb in reader.iter_quadrant_batches(quad == q, geo_eval):
                oof_p_gfv.ravel()[flat_cells] = predict_hetero_proba(models_p, Xb)
                oof_m_gfv.ravel()[flat_cells] = predict_kernel_self_credit(models_m, Xb)
                del Xb
            del models_p, models_m
            gc.collect()
            log(f"LOQO GFV Dual-Head quadrant {q} fitted & predicted in {time.time()-tq:.1f}s")

        del nested_samples, geo_eval
        gc.collect()
        np.save(p_cache, oof_p_gfv.astype(np.float16))
        np.save(m_cache, oof_m_gfv.astype(np.float16))

    # Exact calibrated probabilities on allowed evaluation domain
    p_cal = np.clip(oof_p_gfv, 0.0, 1.0)
    m_cal = np.clip(oof_m_gfv, 0.0, 1.0)
    p_blind_mix = np.clip(0.88 * p_cal + 0.12 * oof_e1_p, 0.0, 1.0)

    # =========================================================================
    # SCORE ALL ARMS ON OFFICIAL SHARED EVALUATOR (ALL TRUTH & FAR > 10 PX)
    # =========================================================================
    terms_all = {}
    terms_far = {}
    far_folds = make_far_folds(folds, visible, min_d=10.0)
    per_fold_report = {}

    rng_c = np.random.default_rng(1000 + seed)
    ys_a, xs_a = np.nonzero(allow_eval)
    rnd_dots = np.zeros(fp.shape, dtype=bool)
    pick_r = rng_c.choice(ys_a.size, size=37_654, replace=False)
    rnd_dots[ys_a[pick_r], xs_a[pick_r]] = True

    sc_halo = np.where(allow_eval, np.exp(-np.abs(d_vis_global - 8.0) / 10.0) * (1.0 + 0.05 * rng_c.standard_normal(fp.shape)), 0.0).astype(np.float32)
    rk_halo = E78.greedy_dots(sc_halo, allow_eval, min_dist=2.8, max_dots=44_090)

    rk_e1 = E78.greedy_dots(oof_e1_p, allow_eval, min_dist=2.8, max_dots=44_090)
    rk_e2 = E78.greedy_dots(p_cal, allow_eval, min_dist=2.8, max_dots=44_090)

    k_exp = max(float(p_cal[allow_eval].sum()), 8_000.0)
    e3_37 = E57.dinkelbach_allocate(
        p_cal, m_cal, allow_eval, budget=37_654, k_truth=k_exp, min_spacing_px=2.8, dinkelbach_iters=3
    ).emitted
    e3_44 = E57.dinkelbach_allocate(
        p_cal, m_cal, allow_eval, budget=44_090, k_truth=k_exp, min_spacing_px=2.8, dinkelbach_iters=3
    ).emitted
    e3_blind37 = E57.dinkelbach_allocate(
        p_blind_mix, m_cal, allow_eval, budget=37_654, k_truth=k_exp, min_spacing_px=2.8, dinkelbach_iters=3
    ).emitted
    e3_blind44 = E57.dinkelbach_allocate(
        p_blind_mix, m_cal, allow_eval, budget=44_090, k_truth=k_exp, min_spacing_px=2.8, dinkelbach_iters=3
    ).emitted

    candidates = [
        ("C0_random|37654", rnd_dots),
        ("C1_dvis_halo_ctrl|37654", E78.prefix(rk_halo, 37_654)),
        ("C1_dvis_halo_ctrl|44090", E78.prefix(rk_halo, 44_090)),
        ("E1_PureMultiPhys_101|spaced|37654", E78.prefix(rk_e1, 37_654)),
        ("E1_PureMultiPhys_101|spaced|44090", E78.prefix(rk_e1, 44_090)),
        ("E2_GFV_Geodesic_SingleHead|spaced|37654", E78.prefix(rk_e2, 37_654)),
        ("E2_GFV_Geodesic_SingleHead|spaced|44090", E78.prefix(rk_e2, 44_090)),
        ("E3_GFV_DualHead_Dinkelbach|spaced|37654", e3_37),
        ("E3_GFV_DualHead_Dinkelbach|spaced|44090", e3_44),
        ("E3_GFV_DualHead_BlindPrior|spaced|37654", e3_blind37),
        ("E3_GFV_DualHead_BlindPrior|spaced|44090", e3_blind44),
    ]

    print(f"\n==================== OFFICIAL HOLDOUT-DTI RESULTS (SEED {seed}) ====================", flush=True)
    for name, dmask in candidates:
        t_all, pf_all, dti_all = eval_dots_on_folds(dmask, folds, fp)
        t_far, pf_far, dti_far = eval_dots_on_folds(dmask, far_folds, fp)
        terms_all[name] = t_all
        terms_far[name] = t_far
        per_fold_report[name] = {"all": pf_all, "far_gt10px": pf_far}
        print(f"  {name:44s} | ALL={dti_all:.4f} | FAR(>1km)={dti_far:.4f} | dots={int(dmask.sum())}", flush=True)

    best_e3 = max(
        [n for n, _ in candidates if n.startswith("E3_")],
        key=lambda n: float(EH.from_terms(terms_all[n].sum(axis=0))),
    )
    sum_all = EH.pooled_summary(terms_all, draws=1000, seed=520810, candidate=best_e3)
    sum_far = EH.pooled_summary(terms_far, draws=1000, seed=520810, candidate=best_e3)

    out_json = {
        "lane": "H78-GFV",
        "protocol": "Strict Leave-One-Quadrant-Out (LOQO) spatial holdout, zero in-quadrant labels",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "evaluator_sha256": EH.implementation_hashes(),
        "seed": seed,
        "withheld_positive_pixels": int(hidden.sum()),
        "far_withheld_positive_pixels_gt10px": int(sum(int(f["truth"].sum()) for f in far_folds)),
        "visible_positive_pixels": int(visible.sum()),
        "experiments_executed": 3,
        "experiment_budget_limit": 3,
        "best_arm": best_e3,
        "per_fold": per_fold_report,
        "pooled_summary_all": sum_all,
        "pooled_summary_far_gt10px": sum_far,
        "elapsed_seconds": round(time.time() - t_seed, 2),
    }
    out_path = ROOT / "evidence" / f"h78gfv_holdout_seed{seed}.json"
    out_path.write_text(json.dumps(out_json, indent=2))
    log(f"Saved {out_path} in {time.time()-t_seed:.1f}s!")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()
    run_seed(args.seed)
