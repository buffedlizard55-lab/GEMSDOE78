#!/usr/bin/env python3
"""Rebuild production dots from the frozen full-catalogue OOF surface with the
corrected spaced emitter (IR-78-EMIT-01), re-audit uniqueness, repackage.
The defective clustered production file is removed and its sha recorded."""
from __future__ import annotations
import gc, hashlib, json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, submission_writer  # noqa
from gems57 import uniqueness as UQ  # noqa
DATA = ROOT / ".cache/gems_data"; WORK = ROOT / ".cache/work"
DL = ROOT / "docs/downloads"; EV = ROOT / "evidence"
H, W, BUDGET = 3730, 3292, 37654
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

old = json.loads((EV / "production.json").read_text())
g = grid_mod.load_grid(DATA); fp, cat = g.footprint, g.catalogue
oof = np.load(WORK / "oof_production.npy")
d_cat = distance_transform_edt(~cat).astype(np.float32)
allowed = fp & (d_cat > 2.5)

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

dots = greedy_dots(oof, allowed)
ys, xs = np.nonzero(dots); pts = np.c_[ys, xs].astype(float)
dd, _ = cKDTree(pts).query(pts, k=2)
spacing = {"frac_nn_le_1p5": float((dd[:, 1] <= 1.5).mean()), "median_nn": float(np.median(dd[:, 1]))}
log("dots", int(dots.sum()), "on-cat", int((dots & cat).sum()), "min d_cat", float(d_cat[dots].min()), spacing)
assert int(dots.sum()) == BUDGET and not (dots & cat).any() and spacing["frac_nn_le_1p5"] == 0.0
np.save(WORK / "production_dots_spaced.npy", dots)
del oof; gc.collect()

# uniqueness vs same registry dirs
REGISTRY_DIRS = [Path("/tmp/GEMSDOE32-sp/docs/downloads"), Path("/tmp/GEMSDOE36-sp/docs/downloads"),
                 Path("/tmp/GEMSDOE70-sp/docs/downloads"), Path("/tmp/g73/docs/downloads"), DATA / "scored"]
seen, registry = set(), []
for d in REGISTRY_DIRS:
    if d.is_dir():
        for p in sorted(d.glob("*.tif")):
            if "FORMAT_TEST" in p.name or "_staging" in p.name: continue
            h = sha(p)
            if h in seen: continue
            seen.add(h); registry.append({"file": str(p), "name": p.name, "sha256": h})
mine = dots.astype(np.float32)
rows = []
for r in registry:
    with rasterio.open(r["file"]) as s: a = s.read(1)
    if a.shape != (H, W): continue
    a = np.nan_to_num(a, nan=0.0)
    td = np.isfinite(a) & (np.abs(a - 1.0) < 1e-6); cnt = int(td.sum())
    e = {"name": r["name"], "sha256": r["sha256"][:12], "their_dots": cnt}
    if cnt:
        e["forward_overlap_mine_in_theirs3px"] = round(UQ.dot_overlap(mine, a), 4)
        e["reverse_overlap_theirs_in_mine3px"] = round(UQ.dot_overlap(a, mine), 4)
        e["mutual"] = round(min(e["forward_overlap_mine_in_theirs3px"], e["reverse_overlap_theirs_in_mine3px"]), 4)
        e["their_3px_halo_fp_fraction"] = round(float(UQ._near(td)[fp].mean()), 4)
    rows.append(e); del a; gc.collect()
prev = json.loads((EV / "uniqueness_production.json").read_text())
informative = [r for r in rows if r.get("their_dots", 0) > 0 and r.get("their_3px_halo_fp_fraction", 0) < 0.70]
literal_worst_fwd = max(r["forward_overlap_mine_in_theirs3px"] for r in rows if "forward_overlap_mine_in_theirs3px" in r)
audit = {"registry_count": len(registry), "informative_count": len(informative),
         "preplacement_max_abs_sampled_rho": prev["preplacement_max_abs_sampled_rho"],
         "surface_rows": prev["surface_rows"],
         "worst_mutual_informative": max(r["mutual"] for r in informative),
         "worst_forward_informative": max(r["forward_overlap_mine_in_theirs3px"] for r in informative),
         "worst_forward_literal_all_rasters": literal_worst_fwd,
         "dot_rows": sorted([r for r in rows if "mutual" in r], key=lambda r: -r["forward_overlap_mine_in_theirs3px"]),
         "spacing": spacing, "emission": "greedy_dots spaced min_dist 2.5 (IR-78-EMIT-01 correction)"}
# Preregistered gate (registry/preregistration_h78_mpc.json) is MUTUAL 3-px overlap <= 0.70
# (sibling precedent GEMSDOE70/73); forward readings are retained for disclosure.
audit["unique_vs_informative_registry"] = bool(audit["preplacement_max_abs_sampled_rho"] <= 0.90
                                                and audit["worst_mutual_informative"] <= 0.70)
audit["unique_literal_all_rasters"] = bool(audit["preplacement_max_abs_sampled_rho"] <= 0.90 and literal_worst_fwd <= 0.70)
(EV / "uniqueness_production.json").write_text(json.dumps(audit, indent=1))
log("uniqueness", {k: audit[k] for k in ["worst_forward_informative", "worst_mutual_informative",
                                          "worst_forward_literal_all_rasters", "unique_vs_informative_registry",
                                          "unique_literal_all_rasters"]})

# remove defective clustered file, package corrected
for suf in [".tif", ".zip", ".json"]:
    q = DL / f"{old['final_stem']}{suf}"
    if q.exists(): q.unlink()
exp2 = json.loads((EV / "experiments_pass2_spaced.json").read_text())
dti = exp2["summaries"]["E2_MPC_SPACED"]["scores"]["E2_MPC_SPACED"]["dti"]
name = "gems78-h78mpc-monogenic-pc-spaced-37654-20261021"
note = f"H78-MPC monogenic phase-congruency LOQO HGB, spaced 2.5px emit; HOLDOUT-DTI {dti:.3f} vs 0.094 H33 ctrl; 37654 dots"
assert len(note) <= 140, len(note)
stage = DL / "_staging_h78.tif"
for suf in [".tif", ".zip", ".json"]:
    q = stage.with_suffix(suf)
    if q.exists(): q.unlink()
receipt = submission_writer.write_submission(stage, mine, DATA / "sample_submission.tif", fp,
        note=note, name=name, catalogue=cat,
        metadata={"lane": "H78-MPC", "emission_correction": "IR-78-EMIT-01 spaced greedy_dots",
                  "superseded_clustered_sha256": old["sha256"], "holdout_dti_e2_spaced": dti,
                  "unique_informative": audit["unique_vs_informative_registry"]})
short = receipt["sha256"][:8]
final_stem = f"gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-{short}-zeros"
for suf in [".tif", ".zip", ".json"]:
    src = stage.with_suffix(suf); dst = DL / f"{final_stem}{suf}"
    if dst.exists(): dst.unlink()
    src.replace(dst)
# the writer ZIP names its member after the staging file; re-zip under the final name
import zipfile as _zf
_tif = DL / f"{final_stem}.tif"; _zip = DL / f"{final_stem}.zip"
_info = _zf.ZipInfo(_tif.name, date_time=(2026, 10, 8, 0, 0, 0)); _info.compress_type = _zf.ZIP_DEFLATED
with _zf.ZipFile(_zip, "w", compression=_zf.ZIP_DEFLATED) as _z: _z.writestr(_info, _tif.read_bytes())
with _zf.ZipFile(_zip) as _z: assert _z.namelist() == [_tif.name] and _z.read(_tif.name) == _tif.read_bytes()
prod = {"final_stem": final_stem, "sha256": receipt["sha256"], "note": note, "name": name,
        "validator_all_passed": receipt["validator"]["all_checks_passed"],
        "unique": audit["unique_vs_informative_registry"],
        "unique_literal_all_rasters": audit["unique_literal_all_rasters"],
        "superseded_clustered": old, "spacing": spacing}
(EV / "production.json").write_text(json.dumps(prod, indent=1))
log("FINAL", final_stem, receipt["sha256"])
print(json.dumps(prod, indent=1))
