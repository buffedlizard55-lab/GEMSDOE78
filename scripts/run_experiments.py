#!/usr/bin/env python3
"""H78-MPC preregistered 3-experiment suite on gems57-pooled-hide-v2 (seed 20).

E1_BASE vs E2_MPC vs E3_MPC_ONLY + controls (h33_analogue_foldfair reproduced
per GEMSDOE73, random). LOQO HGB, visible-only positives, leakage canaries
first, vendor greedy_allocate emission (+ exact marginal-gain top-up to
37,654), vendor evaluate_holdout scoring with paired block bootstrap.
Outputs: evidence/experiments.json, .cache/work/{oof surfaces, dots}.npz
"""
from __future__ import annotations
import gc, json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import evaluate_holdout, grid as grid_mod, holdout, metric  # noqa
from gems57.emit import greedy_allocate, expected_credit  # noqa

DATA = ROOT / ".cache" / "gems_data"
FEAT = ROOT / ".cache" / "features"
WORK = ROOT / ".cache" / "work"; WORK.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"; EV.mkdir(exist_ok=True)
BUDGET = 37654
KCAL = 7905.0

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

H, W = 3730, 3292
g = grid_mod.load_grid(DATA)
fp, cat = g.footprint, g.catalogue
folds, quad = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
hidden = folds[0]["hidden_all"]; visible = folds[0]["visible"]
log("withheld", int(hidden.sum()), "visible", int(visible.sum()), "cat", int(cat.sum()))
assert int(hidden.sum()) == 11321, "instrument precondition failed"

names_meta = json.loads((FEAT / "names.json").read_text())
names, n_base = names_meta["names"], names_meta["n_base"]
stack = np.lib.format.open_memmap(FEAT / "stack.npy", mode="r")
log("stack", stack.shape, "base", n_base)

d_cat = distance_transform_edt(~cat).astype(np.float32)
d_vis = distance_transform_edt(~visible).astype(np.float32)

# fold-fair allowed masks (GEMSDOE73 construction)
allow25 = fp.copy(); allow_ctrl = fp.copy()
for f in folds:
    r = f["region"]
    allow25[r] = fp[r] & (~f["masked_known"][r]) & (d_vis[r] > 2.5)
    allow_ctrl[r] = fp[r] & (~f["masked_known"][r]) & (d_vis[r] > 2.0)

fp_idx = np.flatnonzero(fp)

# ---------------- canaries (before any fitting) ----------------
log("canaries...")
rng = np.random.default_rng(7)
neg_pool = np.flatnonzero((d_cat > 5.0).ravel()[fp_idx])
neg_sub = np.sort(rng.choice(neg_pool, size=200_000, replace=False))
del neg_pool; gc.collect()
def at(band, sub_pos_in_fp):
    return stack[band].ravel()[fp_idx[sub_pos_in_fp]]
pos_cat = np.flatnonzero(cat.ravel()[fp_idx]); pos_hid = np.flatnonzero(hidden.ravel()[fp_idx])
sub_cat = np.concatenate([pos_cat, neg_sub]); y_cat = np.r_[np.ones(pos_cat.size), np.zeros(neg_sub.size)]
sub_hid = np.concatenate([pos_hid, neg_sub]); y_hid = np.r_[np.ones(pos_hid.size), np.zeros(neg_sub.size)]
canaries = []
for i, nm in enumerate(names):
    vc = np.nan_to_num(at(i, sub_cat).astype(np.float64), nan=-999.0)
    vh = np.nan_to_num(at(i, sub_hid).astype(np.float64), nan=-999.0)
    if np.ptp(vc) == 0:
        ac = ah = 0.5
    else:
        ac = float(roc_auc_score(y_cat, vc)); ah = float(roc_auc_score(y_hid, vh))
    sym = max(ac, 1 - ac, ah, 1 - ah)
    canaries.append({"feature": nm, "auc_catalogue": round(ac, 4), "auc_withheld": round(ah, 4),
                     "symmetric_auc": round(sym, 4), "passed": bool(sym <= 0.90)})
max_sym = max(c["symmetric_auc"] for c in canaries)
log("canary max symmetric AUC", max_sym, "worst:", max(canaries, key=lambda c: c["symmetric_auc"])["feature"])
(EV / "canaries.json").write_text(json.dumps({"max_symmetric_auc": max_sym, "features": canaries}, indent=1))
assert max_sym <= 0.90, "LEAKAGE CANARY STOP"

# ---------------- LOQO training ----------------
def sample_xy(q, band_idx, pos_mask, rng_seed):
    tr = (quad != q) & fp
    py, px = np.nonzero(pos_mask & tr)
    neg_cand = tr & (d_cat > 3.0)
    ny_, nx_ = np.nonzero(neg_cand)
    rng = np.random.default_rng(rng_seed)
    sel = rng.choice(ny_.size, size=min(4 * py.size, ny_.size), replace=False)
    ys = np.concatenate([py, ny_[sel]]); xs = np.concatenate([px, nx_[sel]])
    y = np.r_[np.ones(py.size, np.int32), np.zeros(sel.size, np.int32)]
    X = np.empty((ys.size, len(band_idx)), np.float32)
    for j, b in enumerate(band_idx):
        X[:, j] = stack[b][ys, xs]
    return X, y

def loqo_oof(band_idx, pos_mask, label):
    oof = np.zeros((H, W), np.float32)
    for q in range(4):
        X, y = sample_xy(q, band_idx, pos_mask, 7800 + q)
        clf = HistGradientBoostingClassifier(learning_rate=0.06, max_iter=400,
                    max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0,
                    random_state=7800 + q)
        clf.fit(X, y); del X, y; gc.collect()
        qmask = (quad == q)
        rows = np.flatnonzero(qmask.any(axis=1))
        for r0 in range(rows[0], rows[-1] + 1, 200):
            r1 = min(r0 + 200, rows[-1] + 1)
            sub = qmask[r0:r1]
            if not sub.any(): continue
            Xb = np.empty((int(sub.sum()), len(band_idx)), np.float32)
            for j, b in enumerate(band_idx):
                Xb[:, j] = stack[b][r0:r1][sub]
            oof[r0:r1][sub] = clf.predict_proba(Xb)[:, 1].astype(np.float32)
            del Xb
        del clf; gc.collect()
        log(label, "quadrant", q, "done")
    return oof

base_idx = list(range(n_base))
all_idx = list(range(len(names)))
oof1 = loqo_oof(base_idx, visible, "E1_BASE")
np.save(WORK / "oof_e1.npy", oof1)
oof2 = loqo_oof(all_idx, visible, "E2_MPC")
np.save(WORK / "oof_e2.npy", oof2)

# E3: unsupervised mean percentile rank of PC across 4 sources (footprint ranks, sampled ranks via sort of fp values)
pc_idx = [names.index(f"mpc_{s}_pc") for s in ["rtp", "iso_grav_anom", "det_elev", "depth_to_base_surf"]]
surf3 = np.zeros((H, W), np.float32)
for b in pc_idx:
    band = np.array(stack[b])
    vals = band[fp]
    order = np.argsort(np.argsort(vals)).astype(np.float32) / max(vals.size - 1, 1)
    tmp = np.zeros((H, W), np.float32); tmp[fp] = order
    surf3 += tmp / len(pc_idx); del band, tmp, order; gc.collect()
np.save(WORK / "surf_e3.npy", surf3)
log("E3 surface done")

# ---------------- emission ----------------
OFF_DY, OFF_DX, OFF_K = metric.OFF_DY, metric.OFF_DX, metric.OFF_K
def topup(p, dots, allowed, want):
    """Batched exact marginal-gain top-up to `want` dots."""
    n = int(dots.sum())
    if n >= want: return dots
    cover = metric.kernel(distance_transform_edt(~dots)).astype(np.float32)
    ek = expected_credit(p)
    cand = allowed & ~dots & (ek > 0)
    ys, xs = np.nonzero(cand)
    ord_ = np.argsort(-ek[ys, xs], kind="stable")[:300_000]
    ys, xs = ys[ord_].astype(np.int64), xs[ord_].astype(np.int64)
    alive = np.ones(ys.size, bool)
    while n < want:
        idxs = np.flatnonzero(alive)[:60_000]
        if idxs.size == 0: break
        gains = np.zeros(idxs.size, np.float64)
        for dy, dx, k in zip(OFF_DY, OFF_DX, OFF_K):
            yy = ys[idxs] + dy; xx = xs[idxs] + dx
            ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
            yy_c = np.clip(yy, 0, H - 1); xx_c = np.clip(xx, 0, W - 1)
            gv = p[yy_c, xx_c] * np.maximum(k - cover[yy_c, xx_c], 0.0)
            gains += np.where(ok, gv, 0.0)
        take = min(2000, want - n, idxs.size)
        best = idxs[np.argpartition(-gains, take - 1)[:take]] if take < idxs.size else idxs
        # sequential accept within batch (cover updated dot by dot)
        order_b = best[np.argsort(-gains[np.searchsorted(idxs, best)])] if False else best
        for i in order_b:
            if n >= want: break
            y, x = int(ys[i]), int(xs[i])
            if dots[y, x]: alive[i] = False; continue
            dots[y, x] = True; n += 1; alive[i] = False
            for dy, dx, k in zip(OFF_DY, OFF_DX, OFF_K):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and cover[yy, xx] < k: cover[yy, xx] = k
    log("topup ->", n)
    return dots

def emit(surface, allowed):
    p = np.where(fp, np.clip(surface, 0, None), 0).astype(np.float32)
    s = float(p[fp].sum())
    p *= np.float32(KCAL / max(s, 1e-12))
    p = np.clip(p, 0, 1)
    alloc = greedy_allocate(p, allowed, KCAL, floor=0.0005, max_dots=BUDGET, candidate_cap=600_000)
    dots = alloc.emitted.copy()
    log("greedy_allocate dots", alloc.n_dots, "surrogate", round(alloc.surrogate_dti, 4))
    if alloc.n_dots < BUDGET:
        dots = topup(p, dots, allowed, BUDGET)
    return dots

def greedy_dots(surface, allowed, budget=BUDGET, pool=600_000, min_dist=2.5):
    """GEMSDOE73 compatibility emitter (src/gems73/emit.py) for the fold-fair control."""
    DISK = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if (dy*dy+dx*dx) ** 0.5 < min_dist]
    surf = np.asarray(surface, np.float32)
    idx = np.flatnonzero(allowed); vals = surf.ravel()[idx]
    if idx.size > pool:
        part = np.argpartition(vals, idx.size - pool)[idx.size - pool:]
        idx, vals = idx[part], vals[part]
    order = np.lexsort((idx, -vals)); idx = idx[order]
    ys = (idx // W).astype(np.int64); xs = (idx % W).astype(np.int64)
    blocked = np.zeros((H, W), bool); dots = np.zeros((H, W), bool); n = 0
    for y, x in zip(ys.tolist(), xs.tolist()):
        if blocked[y, x]: continue
        dots[y, x] = True; n += 1
        if n >= budget: break
        for dy, dx in DISK:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W: blocked[yy, xx] = True
    return dots

arms = {}
arms["E1_BASE"] = emit(oof1, allow25); del oof1; gc.collect()
arms["E2_MPC"] = emit(oof2, allow25); del oof2; gc.collect()
arms["E3_MPC_ONLY"] = emit(surf3, allow25); del surf3; gc.collect()
with rasterio.open(DATA / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif") as s19:
    a19 = s19.read(1); h19sup = np.isfinite(a19) & (a19 > 0.5); del a19
arms["h33_analogue_foldfair"] = greedy_dots(h19sup.astype(np.float32), allow_ctrl & h19sup)
rngc = np.random.default_rng(73)
arms["random_control"] = greedy_dots(rngc.random((H, W), dtype=np.float32), allow_ctrl)
for k, v in arms.items(): log(k, int(v.sum()))
np.savez_compressed(WORK / "arm_dots.npz", **{k: v for k, v in arms.items()})

# ---------------- scoring ----------------
terms, per_fold = {}, {}
for name, dots in arms.items():
    pred = dots.astype(np.float32); tot = None; per_fold[name] = []
    for f in folds:
        res, t = evaluate_holdout.evaluate(pred, f, fp)
        per_fold[name].append({"fold": f["receipt"]["fold"], "dti": round(res["dti"], 5),
                               "n_truth": res["n_truth"], "n_emitted": res["n_emitted"]})
        tot = t if tot is None else tot + t
    terms[name] = tot
    del pred; gc.collect()

out = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
       "evaluator_hashes": evaluate_holdout.implementation_hashes(),
       "withheld_positive_pixels": int(hidden.sum()),
       "canary_max_symmetric_auc": max_sym, "per_fold": per_fold, "summaries": {}}
for cand in ["E2_MPC", "E1_BASE", "E3_MPC_ONLY"]:
    s = evaluate_holdout.pooled_summary(terms, draws=1000, seed=78078, candidate=cand)
    out["summaries"][cand] = s
    log(cand, {k: round(v["dti"], 4) for k, v in s["scores"].items()})
(EV / "experiments.json").write_text(json.dumps(out, indent=1, default=float))
log("DONE")
