#!/usr/bin/env python3
"""Production build for the promoted H78 arm: LOQO retrain on the FULL
catalogue, emit exactly 37,654 dots at EDT(catalogue)>2.5px, audit uniqueness
(surface rho pre-placement + final-dot overlap) vs the local registry set,
then package via vendor submission_writer (fail-closed validator).

Usage: python3 scripts/build_production.py --bands all|base
Registry rasters are read from the sibling checkouts listed in REGISTRY_DIRS
(re-clone instructions in README); every compared file's sha256 is recorded.
"""
from __future__ import annotations
import argparse, gc, hashlib, json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, holdout, metric, submission_writer  # noqa
from gems57.emit import greedy_allocate, expected_credit  # noqa
from gems57 import uniqueness as UQ  # noqa

DATA = ROOT / ".cache" / "gems_data"
FEAT = ROOT / ".cache" / "features"
WORK = ROOT / ".cache" / "work"
DL = ROOT / "docs" / "downloads"; DL.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"
BUDGET, KCAL, H, W = 37654, 7905.0, 3730, 3292
REGISTRY_DIRS = [Path("/tmp/GEMSDOE32-sp/docs/downloads"), Path("/tmp/GEMSDOE36-sp/docs/downloads"),
                 Path("/tmp/GEMSDOE70-sp/docs/downloads"), Path("/tmp/g73/docs/downloads"),
                 DATA / "scored"]

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

ap = argparse.ArgumentParser(); ap.add_argument("--bands", choices=["all", "base"], required=True)
args = ap.parse_args()

g = grid_mod.load_grid(DATA); fp, cat = g.footprint, g.catalogue
folds, quad = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)  # quad only
names_meta = json.loads((FEAT / "names.json").read_text())
names, n_base = names_meta["names"], names_meta["n_base"]
band_idx = list(range(len(names))) if args.bands == "all" else list(range(n_base))
stack = np.lib.format.open_memmap(FEAT / "stack.npy", mode="r")
d_cat = distance_transform_edt(~cat).astype(np.float32)

# ---- LOQO on full catalogue ----
oof = np.zeros((H, W), np.float32)
for q in range(4):
    tr = (quad != q) & fp
    py, px = np.nonzero(cat & tr)
    ny_, nx_ = np.nonzero(tr & (d_cat > 3.0))
    rng = np.random.default_rng(7800 + q)
    sel = rng.choice(ny_.size, size=min(4 * py.size, ny_.size), replace=False)
    ys = np.concatenate([py, ny_[sel]]); xs = np.concatenate([px, nx_[sel]])
    y = np.r_[np.ones(py.size, np.int32), np.zeros(sel.size, np.int32)]
    X = np.empty((ys.size, len(band_idx)), np.float32)
    for j, b in enumerate(band_idx): X[:, j] = stack[b][ys, xs]
    clf = HistGradientBoostingClassifier(learning_rate=0.06, max_iter=400, max_leaf_nodes=63,
                min_samples_leaf=40, l2_regularization=1.0, random_state=7800 + q)
    clf.fit(X, y); del X, y; gc.collect()
    qmask = (quad == q); rows = np.flatnonzero(qmask.any(axis=1))
    for r0 in range(rows[0], rows[-1] + 1, 200):
        r1 = min(r0 + 200, rows[-1] + 1); sub = qmask[r0:r1]
        if not sub.any(): continue
        Xb = np.empty((int(sub.sum()), len(band_idx)), np.float32)
        for j, b in enumerate(band_idx): Xb[:, j] = stack[b][r0:r1][sub]
        oof[r0:r1][sub] = clf.predict_proba(Xb)[:, 1].astype(np.float32); del Xb
    del clf; gc.collect(); log("prod quadrant", q)
np.save(WORK / "oof_production.npy", oof)

# ---- registry inventory ----
reg_files = []
for d in REGISTRY_DIRS:
    if d.is_dir():
        for p in sorted(d.glob("*.tif")):
            if "FORMAT_TEST" in p.name or "_staging" in p.name: continue
            reg_files.append(p)
seen, registry = set(), []
for p in reg_files:
    h = sha(p)
    if h in seen: continue
    seen.add(h); registry.append({"file": str(p), "name": p.name, "sha256": h})
log("registry unique rasters:", len(registry))

# ---- pre-placement surface uniqueness (sampled Spearman, fixed seed) ----
rng = np.random.default_rng(78078)
sample_mask = np.zeros((H, W), bool)
fp_flat = np.flatnonzero(fp)
sample_mask.ravel()[rng.choice(fp_flat, size=300_000, replace=False)] = True
surf_rows = []
for r in registry:
    with rasterio.open(r["file"]) as s:
        a = s.read(1)
    if a.shape != (H, W): continue
    m = oof[sample_mask].astype(np.float64); t = np.nan_to_num(a[sample_mask].astype(np.float64), nan=0.0)
    rho = float(spearmanr(m, t).statistic) if np.ptp(t) > 0 else 0.0
    surf_rows.append({"name": r["name"], "sha256": r["sha256"][:12], "sampled_spearman_rho": round(rho, 4)})
    del a; gc.collect()
max_rho = max(abs(r["sampled_spearman_rho"]) for r in surf_rows)
log("pre-placement max |rho| =", max_rho)

# ---- emission (production allowed) ----
def topup(p, dots, allowed, want):
    n = int(dots.sum())
    if n >= want: return dots
    cover = metric.kernel(distance_transform_edt(~dots)).astype(np.float32)
    ek = expected_credit(p)
    ys, xs = np.nonzero(allowed & ~dots & (ek > 0))
    ord_ = np.argsort(-ek[ys, xs], kind="stable")[:300_000]
    ys, xs = ys[ord_].astype(np.int64), xs[ord_].astype(np.int64)
    alive = np.ones(ys.size, bool)
    while n < want:
        idxs = np.flatnonzero(alive)[:60_000]
        if idxs.size == 0: break
        gains = np.zeros(idxs.size, np.float64)
        for dy, dx, k in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
            yy = np.clip(ys[idxs] + dy, 0, H - 1); xx = np.clip(xs[idxs] + dx, 0, W - 1)
            ok = (ys[idxs] + dy >= 0) & (ys[idxs] + dy < H) & (xs[idxs] + dx >= 0) & (xs[idxs] + dx < W)
            gains += np.where(ok, p[yy, xx] * np.maximum(k - cover[yy, xx], 0.0), 0.0)
        take = min(2000, want - n, idxs.size)
        best = idxs[np.argpartition(-gains, take - 1)[:take]] if take < idxs.size else idxs
        for i in best:
            if n >= want: break
            y, x = int(ys[i]), int(xs[i])
            if dots[y, x]: alive[i] = False; continue
            dots[y, x] = True; n += 1; alive[i] = False
            for dy, dx, k in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and cover[yy, xx] < k: cover[yy, xx] = k
    return dots

p = np.where(fp, np.clip(oof, 0, None), 0).astype(np.float32)
p = np.clip(p * np.float32(KCAL / max(float(p[fp].sum()), 1e-12)), 0, 1)
allowed = fp & (d_cat > 2.5)
alloc = greedy_allocate(p, allowed, KCAL, floor=0.0005, max_dots=BUDGET, candidate_cap=600_000)
dots = alloc.emitted.copy(); log("greedy dots", alloc.n_dots)
if alloc.n_dots < BUDGET: dots = topup(p, dots, allowed, BUDGET)
log("final dots", int(dots.sum()), "on-cat", int((dots & cat).sum()),
    "min d_cat", float(d_cat[dots].min()))
assert int(dots.sum()) == BUDGET and not (dots & cat).any()
np.save(WORK / "production_dots.npy", dots)
del oof, p; gc.collect()

# ---- final-dot uniqueness ----
dot_rows = []
mine = dots.astype(np.float32)
for r in registry:
    with rasterio.open(r["file"]) as s:
        a = s.read(1)
    if a.shape != (H, W): continue
    a = np.nan_to_num(a, nan=0.0)
    tdots = np.isfinite(a) & (np.abs(a - 1.0) < 1e-6)
    cnt = int(tdots.sum())
    entry = {"name": r["name"], "sha256": r["sha256"][:12], "their_dots": cnt}
    if 0 < cnt:
        entry["forward_overlap_mine_in_theirs3px"] = round(UQ.dot_overlap(mine, a), 4)
        entry["reverse_overlap_theirs_in_mine3px"] = round(UQ.dot_overlap(a, mine), 4)
        entry["mutual"] = round(min(entry["forward_overlap_mine_in_theirs3px"],
                                     entry["reverse_overlap_theirs_in_mine3px"]), 4)
        # space-filling witness diagnostic: fraction of footprint within 3px of their dots
        entry["their_3px_halo_fp_fraction"] = round(float(UQ._near(tdots)[fp].mean()), 4)
    dot_rows.append(entry); del a; gc.collect()
informative = [r for r in dot_rows if r.get("their_dots", 0) > 0 and r.get("their_3px_halo_fp_fraction", 0) < 0.70]
worst_mutual = max((r["mutual"] for r in informative), default=0.0)
worst_fwd_inf = max((r["forward_overlap_mine_in_theirs3px"] for r in informative), default=0.0)
unique = bool(max_rho <= 0.90 and worst_fwd_inf <= 0.70)
audit = {"registry_count": len(registry), "informative_count": len(informative),
         "preplacement_max_abs_sampled_rho": max_rho, "worst_mutual_informative": worst_mutual,
         "worst_forward_informative": worst_fwd_inf, "unique_vs_informative_registry": unique,
         "surface_rows": sorted(surf_rows, key=lambda r: -abs(r["sampled_spearman_rho"])),
         "dot_rows": sorted([r for r in dot_rows if "mutual" in r], key=lambda r: -r["mutual"])}
(EV / "h78mpc_uniqueness.json").write_text(json.dumps(audit, indent=1))
log("uniqueness:", {k: audit[k] for k in ["registry_count", "informative_count",
    "preplacement_max_abs_sampled_rho", "worst_mutual_informative", "worst_forward_informative", "unique_vs_informative_registry"]})

# ---- package ----
exp = json.loads((EV / "h78mpc_experiments.json").read_text())
e2 = exp["summaries"]["E2_MPC"]["scores"]["E2_MPC"]["dti"]
name = "gems78-h78mpc-monogenic-pc-37654-20261021"
note = f"H78-MPC monogenic phase-congruency LOQO HGB + 300m submod emit; holdout-DTI {e2:.3f} (seed20 n=11321); 37654 dots"
assert len(note) <= 140, len(note)
stage = DL / "_staging_h78.tif"
for suf in [".tif", ".zip", ".json"]:
    q = stage.with_suffix(suf)
    if q.exists(): q.unlink()
receipt = submission_writer.write_submission(stage, mine, DATA / "sample_submission.tif", fp,
                                             note=note, name=name, catalogue=cat,
                                             metadata={"lane": "H78-MPC", "bands": args.bands,
                                                       "holdout_dti_e2": e2, "unique": unique})
short = receipt["sha256"][:8]
final_stem = f"gems78-h78mpc-monogenic-pc-37654dots-20261021T220000Z-{short}-zeros"
for suf in [".tif", ".zip", ".json"]:
    src = stage.with_suffix(suf); dst = DL / f"{final_stem}{suf}"
    if dst.exists(): dst.unlink()
    src.replace(dst)
log("FINAL", final_stem, receipt["sha256"])
(prod := {"final_stem": final_stem, "sha256": receipt["sha256"], "note": note, "name": name,
          "validator_all_passed": receipt["validator"]["all_checks_passed"], "unique": unique})
(EV / "h78mpc_production.json").write_text(json.dumps(prod, indent=1))
print(json.dumps(prod, indent=1))
