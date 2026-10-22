#!/usr/bin/env python3
"""Overview figure for lane H78-SIGX: production surface (4x block mean),
emitted dots (subsampled for legibility) and the mapped catalogue."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import grid as G  # noqa: E402

g = G.load_grid(ROOT / "data/bridge")
fp = g.footprint
cat = np.asarray(g.catalogue, bool)
surf = np.load(ROOT / "data/processed/surface_full_FUSE.npy")
prod = __import__("json").loads((ROOT / "evidence/h78sig_production.json").read_text())
with rasterio.open(ROOT / "docs/downloads" / prod["submission_file"]) as ds:
    dots = ds.read(1) > 0

b = 4
h, w = fp.shape
small = np.where(fp, surf, np.nan)[:h // b * b, :w // b * b].reshape(h // b, b, w // b, b)
small = np.nanmean(small, axis=(1, 3))
fig, axes = plt.subplots(1, 2, figsize=(11, 6.2))
axes[0].imshow(small, cmap="magma", vmin=0, vmax=np.nanpercentile(small, 99))
axes[0].set_title("H78-SIGX production rank-fusion surface\n(percentile rank, 400 m blocks)")
ys, xs = np.nonzero(dots)
rng = np.random.default_rng(0)
sel = rng.choice(ys.size, size=6000, replace=False)
cy, cx = np.nonzero(cat)
csel = rng.choice(cy.size, size=6000, replace=False)
axes[1].scatter(xs[sel], ys[sel], s=0.6, c="#d7301f", label="emitted dots (6k of 44,090 shown)")
axes[1].scatter(cx[csel], cy[csel], s=0.4, c="#225ea8", alpha=0.6,
                label="mapped catalogue (6k px shown)")
axes[1].set_xlim(0, w); axes[1].set_ylim(h, 0); axes[1].set_aspect("equal")
axes[1].set_title("Emitted dots (>500 m from catalogue) vs catalogue")
axes[1].legend(markerscale=6, fontsize=7, loc="lower left")
for ax in axes:
    ax.set_xticks([]); ax.set_yticks([])
fig.tight_layout()
out = ROOT / "docs/assets/fig_h78sig_surface_and_dots.png"
fig.savefig(out, dpi=130)
print(out)
