#!/usr/bin/env python3
"""Paired spatial-block bootstrap CIs for the exact configurations that are shipped
(re-uses the saved per-arm score grids and the deterministic seed-20 draw; no refit)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import evaluate_holdout as EH, holdout as HO, grid as G  # noqa: E402
from gems78 import emit as E  # noqa: E402

SEED = 20
CONFIGS = [  # (arm, flank_px, budget)
    ("A2_h78_steered", 2.0, 44_090), ("A1_iso", 2.0, 44_090), ("A0_std19", 2.0, 44_090),
    ("A2_h78_steered", 3.0, 44_090), ("A2_h78_steered", 2.0, 37_654), ("A2_h78_steered", 2.0, 50_000),
]


def main():
    g = G.load_grid(ROOT / "data/bridge")
    fp = g.footprint
    folds, _ = HO.buffered_component_draw(g, seed=SEED, hide_frac=0.20, buffer_px=3)
    visible = folds[0]["visible"]
    terms = {}
    ranks = {}
    for arm, bpx, n in CONFIGS:
        key = (arm, bpx)
        if key not in ranks:
            s = np.load(ROOT / f"data/processed/score_seed{SEED}_{arm}.npy")
            allowed = fp & ~E.flank_mask(visible, bpx)
            ranks[key] = E.greedy_dots(s, allowed, min_dist=2.8, max_dots=60_000, pool=1_500_000)
        dots = E.prefix(ranks[key], n).astype(np.float32)
        t = None
        for f in folds:
            _, tt = EH.evaluate(dots, f, fp, block_side=200, origin=(0, 0), global_shape=fp.shape)
            t = tt if t is None else t + tt
        name = f"{arm}|nms0_B{int(bpx)}|{n}"
        terms[name] = t
        print(name, round(float(EH.from_terms(t.sum(axis=0))), 4), "dots", int(dots.sum()))
    cand = "A2_h78_steered|nms0_B2|44090"
    summary = EH.pooled_summary(terms, draws=1000, seed=520810, candidate=cand)
    alt = EH.pooled_summary({k: v for k, v in terms.items() if k in (
        "A2_h78_steered|nms0_B3|44090", "A1_iso|nms0_B2|44090", "A0_std19|nms0_B2|44090", cand)},
        draws=1000, seed=520810, candidate="A2_h78_steered|nms0_B3|44090")
    out = dict(seed=SEED, candidate=cand, pooled_summary=summary, alternative_B3_summary=alt,
               note="greedy pool 1.5M candidates (holdout sweep used 400k); budgets are global dot counts")
    (ROOT / "evidence/h78_pooled_ci_seed20.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps({k: (v["dti"], v["ci95"]) for k, v in summary["scores"].items()}, indent=1))
    print(json.dumps({k: (v["delta"], v["ci95"]) for k, v in summary["paired_differences"].items()}, indent=1))


if __name__ == "__main__":
    main()
