#!/usr/bin/env python3
"""Measured figures: (A) E2 OOF surface, (B) final spaced dots vs catalogue, (C) holdout bars (spaced)."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as gm  # noqa
g = gm.load_grid(ROOT / ".cache/gems_data"); fp, cat = g.footprint, g.catalogue
oof = np.load(ROOT / ".cache/work/oof_e2.npy")
dots = np.load(ROOT / ".cache/work/production_dots_spaced.npy")
exp = json.loads((ROOT / "evidence/experiments_pass2_spaced.json").read_text())
scores = exp["summaries"]["E2_MPC_SPACED"]["scores"]

def down(a, f=4):
    h, w = a.shape; return a[:h//f*f, :w//f*f].reshape(h//f, f, w//f, f).max(axis=(1, 3))

fig, ax = plt.subplots(1, 3, figsize=(16, 5.4))
s = np.where(fp, oof, np.nan)
ax[0].imshow(down(s), cmap="inferno", vmin=0, vmax=np.nanpercentile(s, 99.5))
ax[0].set_title("A  E2-MPC LOQO OOF surface (holdout-trained)")
dc, dd, df = down(cat.astype(np.float32)), down(dots.astype(np.float32)), down(fp.astype(np.float32))
rgb = np.zeros((*dc.shape, 3), np.float32)
rgb[df > 0] = (0.12, 0.12, 0.14); rgb[dc > 0] = (0.2, 0.8, 0.9); rgb[dd > 0] = (1.0, 0.75, 0.1)
ax[1].imshow(rgb); ax[1].set_title("B  Catalogue (cyan) vs final 37,654 spaced dots (gold)")
names = ["E3_MPC_ONLY_SPACED", "random_control", "E1_BASE_SPACED", "h33_analogue_foldfair", "E2_MPC_SPACED"]
labels = ["E3 MPC-only", "random", "E1 base (no MPC)", "H33 fold-fair control", "E2 MPC candidate"]
vals = [scores[n]["dti"] for n in names]
errs = [[v - scores[n]["ci95"][0] for n, v in zip(names, vals)],
        [scores[n]["ci95"][1] - v for n, v in zip(names, vals)]]
cols = ["#888", "#666", "#4a7fb5", "#2a9d8f", "#d98a16"]
ax[2].barh(range(len(names)), vals, xerr=errs, color=cols, capsize=3)
ax[2].set_yticks(range(len(names))); ax[2].set_yticklabels(labels, fontsize=8)
ax[2].set_xlabel("HOLDOUT-DTI (gems57-pooled-hide-v2, seed 20, n=11,321) ±95% CI")
ax[2].set_title("C  Spaced emission: E2 > control (n.s.), E2 > E1 (sig.)")
for a in ax[:2]: a.set_xticks([]); a.set_yticks([])
fig.tight_layout()
out = ROOT / "docs/assets"; out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / "fig1.png", dpi=130); print("saved", out / "fig1.png")
