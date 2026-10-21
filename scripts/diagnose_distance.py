#!/usr/bin/env python3
"""Post-hoc diagnostic (no retuning): does the holdout reward catalogue-halo placement,
and does the candidate's advantage survive on withheld truth FAR from visible faults?"""
import json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"vendor")); sys.path.insert(0, str(ROOT/"src"))
from gems57 import evaluate_holdout as EH, holdout as HO, grid as G, metric as M
from gems78 import emit as E
g = G.load_grid(ROOT/"data/bridge"); fp = g.footprint
folds, _ = HO.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
vis = folds[0]["visible"]; hid = folds[0]["hidden_all"]
dvis = ndi.distance_transform_edt(~vis)
out = {"withheld_truth_distance_to_visible_px": {f"p{q}": float(np.percentile(dvis[hid], q)) for q in (10,25,50,75,90)},
       "withheld_truth_frac_within_10px_of_visible": float((dvis[hid] <= 10).mean())}
print(out)
def dots_for(arm, bpx, n):
    s = np.load(ROOT/f"data/processed/score_seed20_{arm}.npy")
    return E.prefix(E.greedy_dots(s, fp & ~E.flank_mask(vis, bpx), 2.8, 60000, 1_500_000), n)
with rasterio.open(ROOT/"data/registry/d28_44090_nan.tif") as ds: a = ds.read(1)
sets = {"A2_h78_steered|B2|44090": dots_for("A2_h78_steered", 2.0, 44090), "A1_iso|B2|44090": dots_for("A1_iso", 2.0, 44090),
        "A0_std19|B2|44090": dots_for("A0_std19", 2.0, 44090), "A2_h78_steered|B3|44090": dots_for("A2_h78_steered", 3.0, 44090),
        "registry_D2.8": np.isfinite(a) & (a > 0)}
strata = {"all": np.ones(fp.shape, bool), "near_le10px": dvis <= 10, "far_gt10px": dvis > 10, "far_gt20px": dvis > 20}
res = {}
for sname, smask in strata.items():
    terms = {}
    for k, d in sets.items():
        t = None
        for f in folds:
            f2 = dict(f); f2["truth"] = f["truth"] & smask
            if not f2["truth"].any(): continue
            _, tt = EH.evaluate(d.astype(np.float32), f2, fp, block_side=200, origin=(0,0), global_shape=fp.shape)
            t = tt if t is None else t + tt
        terms[k] = t
    ps = EH.pooled_summary(terms, draws=500, seed=1, candidate="A2_h78_steered|B2|44090")
    res[sname] = dict(n_truth=ps["scores"]["A2_h78_steered|B2|44090"]["withheld_positive_pixels"],
                      dti={k: round(v["dti"],4) for k,v in ps["scores"].items()},
                      paired_vs_candidate={k: [round(v["delta"],4), [round(x,4) for x in v["ci95"]]] for k,v in ps["paired_differences"].items()})
    print(sname, json.dumps(res[sname]))
# credit per dot vs distance to visible catalogue, candidate dots, holdout truth
d = sets["A2_h78_steered|B2|44090"]; truth = hid & fp
dt = ndi.distance_transform_edt(~truth); k_self = M.kernel(dt)
dd = dvis[d]; kk = k_self[d]
bins = [(2,3),(3,5),(5,10),(10,20),(20,1e9)]
out["candidate_dot_self_credit_by_distance_to_visible"] = {f"{lo}-{hi}px": dict(n=int(((dd>=lo)&(dd<hi)).sum()), mean_kernel_credit=float(kk[(dd>=lo)&(dd<hi)].mean())) for lo,hi in bins}
out["break_even_credit_0.2xDTI"] = 0.2*0.1586
out["strata"] = res
print(json.dumps(out["candidate_dot_self_credit_by_distance_to_visible"], indent=1))
(ROOT/"evidence/h78_distance_diagnostic.json").write_text(json.dumps(out, indent=2, default=float))
