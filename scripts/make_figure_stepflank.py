#!/usr/bin/env python3
"""Quick-look figure for lane H78-STEP: production score surface + emitted dots.

Display only (downsampled x4); all validation is numeric. Reads
data/processed/score_full_CAND_STEP.npy and the written TIF named in the run card.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
rc = json.loads((ROOT / "evidence/h78stepflank_run_card.json").read_text())
score = np.load(ROOT / "data/processed/score_full_CAND_STEP.npy")
with rasterio.open(ROOT / "docs/downloads" / rc["raster"]["file"]) as ds:
    dots = ds.read(1)
with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
    fp = np.isfinite(ds.read(1))
k = 4
sd = np.where(fp, score, np.nan)[: score.shape[0] // k * k, : score.shape[1] // k * k]
sd = np.nanmean(sd.reshape(sd.shape[0] // k, k, sd.shape[1] // k, k), axis=(1, 3))
ys, xs = np.nonzero(dots > 0)
fig, ax = plt.subplots(1, 2, figsize=(13, 6))
im = ax[0].imshow(sd, cmap="magma", vmin=0, vmax=np.nanpercentile(sd, 99.5))
ax[0].set_title(f"H78-STEP score surface (mean x{k})")
fig.colorbar(im, ax=ax[0], fraction=0.046)
ax[1].imshow(sd, cmap="gray_r", vmin=0, vmax=np.nanpercentile(sd, 99.5))
ax[1].scatter(xs / k, ys / k, s=0.4, c="red", linewidths=0)
ax[1].set_title(f"{ys.size:,} emitted dots (verdict: {rc['verdict']})")
for a in ax:
    a.set_xticks([])
    a.set_yticks([])
out = ROOT / "docs/assets/fig_h78stepflank_surface_and_dots.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.tight_layout()
fig.savefig(out, dpi=130)
print("WROTE", out)
