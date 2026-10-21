#!/usr/bin/env python3
"""PASS-2 DEFECT CORRECTION (IR-78-EMIT-01), fully disclosed as post-hoc.

Finding: vendor greedy_allocate + top-up emitted contiguous runs (98.9% of dots
have a neighbour <=1.5 px; median NN = 1.0 px) instead of kernel-packed spaced
dots (control median NN = 3.16 px). Adjacent dots are near-redundant under the
300 m triangular kernel, so the preregistered E1/E2/E3 HOLDOUT-DTI values
confound surface quality with a defective emission geometry.

Correction: re-emit the FROZEN OOF surfaces (no retraining, no new features)
with the control's own spaced emitter (greedy_dots, min_dist 2.5 px, pool 600k)
and re-score on the identical instrument. Both readings are published; the
preregistered verdict stands unless the corrected arms clear the same gate,
in which case the run card records the post-hoc nature explicitly.
"""
from __future__ import annotations
import gc, json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import evaluate_holdout, grid as grid_mod, holdout  # noqa
DATA = ROOT / ".cache/gems_data"; WORK = ROOT / ".cache/work"; EV = ROOT / "evidence"
H, W, BUDGET = 3730, 3292, 37654
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

g = grid_mod.load_grid(DATA); fp, cat = g.footprint, g.catalogue
folds, quad = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
visible = folds[0]["visible"]
d_vis = distance_transform_edt(~visible).astype(np.float32)
allow25 = fp.copy(); allow_ctrl = fp.copy()
for f in folds:
    r = f["region"]
    allow25[r] = fp[r] & (~f["masked_known"][r]) & (d_vis[r] > 2.5)
    allow_ctrl[r] = fp[r] & (~f["masked_known"][r]) & (d_vis[r] > 2.0)

def greedy_dots(surface, allowed, budget=BUDGET, pool=600_000, min_dist=2.5):
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
for tag, fn_ in [("E1_BASE_SPACED", "oof_e1.npy"), ("E2_MPC_SPACED", "oof_e2.npy"), ("E3_MPC_ONLY_SPACED", "surf_e3.npy")]:
    s = np.load(WORK / fn_)
    arms[tag] = greedy_dots(s, allow25); del s; gc.collect()
    log(tag, int(arms[tag].sum()))
with rasterio.open(DATA / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif") as s19:
    a19 = s19.read(1); h19sup = np.isfinite(a19) & (a19 > 0.5); del a19
arms["h33_analogue_foldfair"] = greedy_dots(h19sup.astype(np.float32), allow_ctrl & h19sup)
rngc = np.random.default_rng(73)
arms["random_control"] = greedy_dots(rngc.random((H, W), dtype=np.float32), allow_ctrl)
np.savez_compressed(WORK / "arm_dots_spaced.npz", **arms)

terms, per_fold = {}, {}
for name, dots in arms.items():
    pred = dots.astype(np.float32); tot = None; per_fold[name] = []
    for f in folds:
        res, t = evaluate_holdout.evaluate(pred, f, fp)
        per_fold[name].append({"fold": f["receipt"]["fold"], "dti": round(res["dti"], 5),
                               "n_truth": res["n_truth"], "n_emitted": res["n_emitted"]})
        tot = t if tot is None else tot + t
    terms[name] = tot; del pred; gc.collect()
out = {"evidence_class": "HOLDOUT-DTI (post-hoc emission correction IR-78-EMIT-01; frozen surfaces, no retraining)",
       "evaluator_version": evaluate_holdout.VERSION, "withheld_positive_pixels": 11321,
       "per_fold": per_fold, "summaries": {}}
for cand in ["E2_MPC_SPACED", "E1_BASE_SPACED"]:
    s = evaluate_holdout.pooled_summary(terms, draws=1000, seed=78078, candidate=cand)
    out["summaries"][cand] = s
    log(cand, {k: round(v["dti"], 4) for k, v in s["scores"].items()})
(EV / "experiments_pass2_spaced.json").write_text(json.dumps(out, indent=1, default=float))
log("DONE")
