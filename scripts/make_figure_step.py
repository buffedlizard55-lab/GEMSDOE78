#!/usr/bin/env python3
"""Figure for lane H78-STEP: HOLDOUT-DTI bars (all arms, 95% CI) + production surface/dots.

Every number plotted is read from evidence/h78step_holdout_seed20.json; the map
panels show the production score surface (data/processed/score_full_CAND_STEP.npy)
and the emitted dots from the run card's TIFF. Output docs/assets/fig_h78step_holdout.png.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
hold = json.loads((ROOT / "evidence/h78step_holdout_seed20.json").read_text())
rc = json.loads((ROOT / "evidence/h78step_run_card.json").read_text())
s = hold["pooled_summary_B3_primary"]["scores"]
order = ["ABL_A0|B3|44090", "ABL_STEPO|B3|44090", "CAND_STEP|B3|44090", "CTRL_A2|B3|44090"]
labels = ["ABL_A0\nraw19", "ABL_STEPO\nSTEP only", "CAND_STEP\nraw19+STEP", "CTRL_A2\nH78-A (repo best)"]
vals = [s[k]["dti"] for k in order]
err = [[v - s[k]["ci95"][0] for k, v in zip(order, vals)],
       [s[k]["ci95"][1] - v for k, v in zip(order, vals)]]
score = np.load(ROOT / "data/processed/score_full_CAND_STEP.npy", mmap_mode="r")
with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
    fp = np.isfinite(ds.read(1))
with rasterio.open(ROOT / "docs/downloads" / rc["raster"]["file"]) as ds:
    dots = ds.read(1) > 0

fig = plt.figure(figsize=(13.5, 4.6))
ax = fig.add_subplot(1, 3, 1)
colors = ["#8a94a6", "#5b8db8", "#1e9e57" if rc["ok_to_submit"] else "#c0392b", "#34495e"]
ax.bar(range(4), vals, yerr=err, capsize=4, color=colors)
ax.axhline(0.1826, ls="--", lw=1, color="#34495e")
ax.text(-0.45, 0.187, "repo best 0.1826", fontsize=7, va="bottom", ha="left", color="#34495e")
ax.set_xticks(range(4), labels, fontsize=7.5)
ax.set_ylabel("HOLDOUT-DTI (gems57-pooled-hide-v2, seed 20,\n11,321 withheld positives, B3/44,090)", fontsize=8)
ax.set_title("Hide-and-recover holdout by arm", fontsize=10)
for i, v in enumerate(vals):
    ax.text(i, v, f"{v:.4f}", ha="center", va="bottom", fontsize=8)
ax.set_ylim(0, max(vals) * 1.35 + 0.02)

ax2 = fig.add_subplot(1, 3, 2)
surf = np.asarray(score[::4, ::4], np.float32)
fpd = fp[::4, ::4]
hi = np.percentile(surf[fpd], 99.5) if fpd.any() else 1.0
img = np.where(fpd, np.clip(surf / max(hi, 1e-9), 0, 1), np.nan)
ax2.imshow(img, cmap="magma", interpolation="nearest")
ax2.set_title("CAND_STEP production score surface", fontsize=10)
ax2.set_xticks([]); ax2.set_yticks([])

ax3 = fig.add_subplot(1, 3, 3)
ys, xs = np.nonzero(dots[::2, ::2])
ax3.scatter(xs, -ys, s=0.15, c="#1a5276")
ax3.set_title(f"Emitted dots ({rc['raster']['dots']:,}, ≥2.8 px, B3)", fontsize=10)
ax3.set_xticks([]); ax3.set_yticks([])

fig.tight_layout()
out = ROOT / "docs/assets/fig_h78step_holdout.png"
fig.savefig(out, dpi=110)
print("wrote", out)
