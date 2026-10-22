#!/usr/bin/env python3
"""Downsampled display figure for lane H78-FW (display only, not scored).

Recomputes the frozen FW surface from the pinned stack, then renders the
composite surface and the production dots at stride 4 with catalogue context.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems78 import data as D
from gems57 import grid as G
from run_h78fw import score_surface  # noqa: E402  (frozen FW surface, reused not forked)

STRIDE = 4


def main():
    g = G.load_grid(ROOT / 'data/bridge')
    fp = g.footprint
    stack = D.load_stack()
    score, feats, smeta = score_surface(stack, fp)
    del stack
    card = json.loads((ROOT / 'evidence/h78fw_run_card.json').read_text())
    tif = ROOT / 'docs/downloads' / (card['submission_name'] + '.tif')
    with rasterio.open(tif) as ds:
        dots = ds.read(1) > 0
    cat = g.catalogue
    fig, ax = plt.subplots(1, 2, figsize=(13, 7.2))
    im0 = ax[0].imshow(np.where(fp, score, np.nan)[::STRIDE, ::STRIDE], cmap='magma',
                       vmin=0, vmax=float(np.quantile(score[fp], 0.99)))
    ax[0].set_title(f"H78-FW composite surface (stride {STRIDE}, display only)\n"
                    f"HOLDOUT-DTI {card['holdout']['score']:.4f} "
                    f"[{card['holdout']['ci95'][0]:.4f}, {card['holdout']['ci95'][1]:.4f}] — negative")
    ax[0].axis('off')
    fig.colorbar(im0, ax=ax[0], shrink=0.7, label='sqrt(warp*central)')
    base = np.zeros((*fp.shape,), np.float32)
    base[fp] = 0.25
    ax[1].imshow(base[::STRIDE, ::STRIDE], cmap='Greys', vmin=0, vmax=1)
    yy, xx = np.nonzero(cat[::STRIDE, ::STRIDE])
    ax[1].scatter(xx, yy, s=0.4, c='cyan', label='mapped catalogue')
    yy, xx = np.nonzero(dots[::STRIDE, ::STRIDE])
    ax[1].scatter(xx, yy, s=0.6, c='red', label=f"FW dots ({int(dots.sum()):,})")
    ax[1].set_title('FW production dots vs mapped catalogue (stride 4, display only)')
    ax[1].axis('off')
    ax[1].legend(markerscale=6, loc='lower right', fontsize=8)
    fig.suptitle('H78-FW inspection — OK TO SUBMIT: NO (negative/duplicate). '
                 'See evidence/h78fw_run_card.json.', fontsize=10)
    fig.tight_layout()
    out = ROOT / 'docs/assets/fig_h78fw_surface_and_dots.png'
    fig.savefig(out, dpi=110)
    print('WROTE', out)


if __name__ == '__main__':
    main()
