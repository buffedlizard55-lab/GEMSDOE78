#!/usr/bin/env python3
"""Diagnostic figure for lane H78-FW: production score surface, emitted dots, and HOLDOUT-DTI CIs."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    rc = json.loads((ROOT / "evidence/h78fwtilt_run_card.json").read_text())
    score = np.load(ROOT / "data/processed/score_full_CAND_FW_PURE.npy")
    with rasterio.open(ROOT / "docs/downloads" / rc["raster"]["file"]) as ds:
        dots = ds.read(1)
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))

    k = 4
    sd = np.where(fp, score, np.nan)[: score.shape[0] // k * k, : score.shape[1] // k * k]
    sd = np.nanmean(sd.reshape(sd.shape[0] // k, k, sd.shape[1] // k, k), axis=(1, 3))
    ys, xs = np.nonzero(dots > 0)

    fig, ax = plt.subplots(1, 3, figsize=(16, 5.2), gridspec_kw={"width_ratios": [1.1, 1.1, 1.0]})

    im = ax[0].imshow(sd, cmap="magma", vmin=0, vmax=np.nanpercentile(sd, 99.5))
    ax[0].set_title(f"H78-FW score surface (mean x{k})")
    fig.colorbar(im, ax=ax[0], fraction=0.046)
    ax[0].set_xticks([])
    ax[0].set_yticks([])

    ax[1].imshow(sd, cmap="gray_r", vmin=0, vmax=np.nanpercentile(sd, 99.5))
    ax[1].scatter(xs / k, ys / k, s=0.35, c="#dc2626", linewidths=0)
    ax[1].set_title(f"H78-FW {ys.size:,} emitted dots (verdict: {rc['verdict']})")
    ax[1].set_xticks([])
    ax[1].set_yticks([])

    ho = rc["holdout"]
    arms = [
        ("CAND_FW_PURE\n(67 FW cols)", ho["candidate"]["dti"], ho["candidate"]["ci95"], "#38bdf8"),
        ("ABL_FW+A2\n(170 cols)", ho["ablation_fw_plus_a2"]["dti"], ho["ablation_fw_plus_a2"]["ci95"], "#f59e0b"),
        ("CTRL_A2\n(103 A2 cols)", ho["ctrl_a2"]["dti"], ho["ctrl_a2"]["ci95"], "#22c55e"),
        ("CTRL_A0\n(19 raw bands)", ho["ctrl_a0_raw19"]["dti"], ho["ctrl_a0_raw19"]["ci95"], "#94a3b8"),
    ]
    labels = [a[0] for a in arms]
    vals = [a[1] for a in arms]
    yerr = [[a[1] - a[2][0] for a in arms], [a[2][1] - a[1] for a in arms]]
    colors = [a[3] for a in arms]

    xpos = np.arange(len(arms))
    bars = ax[2].bar(xpos, vals, yerr=yerr, capsize=5, color=colors, edgecolor="#1e293b", width=0.58)
    ax[2].axhline(ho["ctrl_a2"]["dti"], color="#16a34a", linestyle="--", linewidth=1.2, label="CTRL_A2 (0.1826)")
    ax[2].set_xticks(xpos)
    ax[2].set_xticklabels(labels, fontsize=9)
    ax[2].set_ylabel("Pooled HOLDOUT-DTI (seed 20, 11,321 pos)")
    ax[2].set_title("HOLDOUT-DTI @ 44,090 B3 dots (95% CI)")
    ax[2].set_ylim(0, 0.23)
    for bar, v in zip(bars, vals):
        ax[2].text(bar.get_x() + bar.get_width() / 2, v + 0.022, f"{v:.4f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax[2].legend(loc="lower right", fontsize=8.5)

    out = ROOT / "docs/assets/fig_h78fwtilt_surface_and_dots.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print("WROTE", out)


if __name__ == "__main__":
    main()
