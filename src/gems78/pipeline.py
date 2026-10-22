"""Shared pipeline pieces: fold-aware feature matrix on disk, learner, scoring grid."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from . import features as F
from .data import PROC, STACK, load_stack
from .emit import flank_mask
from .strike import strike_field


def drop_file_cache(path: Path) -> None:
    """Release Linux kernel page cache for large memmaps inside swapless cgroups."""
    try:
        if path.exists() and hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
            fd = os.open(str(path), os.O_RDONLY)
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            finally:
                os.close(fd)
    except OSError:
        pass

ARMS = {
    "A0_std19": dict(iso=False, steered=False),
    "A1_iso": dict(iso=True, steered=False),
    "A2_h78_steered": dict(iso=True, steered=True),
}


def arm_columns(arm: str) -> np.ndarray:
    """Column indices of the full (raw+iso+steered) matrix used by an arm."""
    full = F.feature_names(iso=True, steered=True)
    want = F.feature_names(**ARMS[arm])
    pos = {n: i for i, n in enumerate(full)}
    return np.array([pos[n] for n in want], np.int64)


def footprint_index(footprint: np.ndarray):
    ys, xs = np.nonzero(footprint)
    return ys.astype(np.int32), xs.astype(np.int32)


def build_feature_matrix(tag: str, footprint: np.ndarray, visible: np.ndarray,
                         n_blocks: int = 4, force: bool = False) -> tuple[Path, dict]:
    """Full feature matrix for every footprint cell, strike field from ``visible``.

    Written as a float32 memmap ``data/processed/feats_<tag>.npy`` of shape
    (n_footprint, n_features) in footprint row-major order.
    """
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"feats_{tag}.npy"
    meta_p = PROC / f"feats_{tag}.json"
    if out.exists() and meta_p.exists() and not force:
        return out, json.loads(meta_p.read_text())
    t0 = time.time()
    stack = load_stack()
    ys, xs = footprint_index(footprint)
    n = ys.size
    names = F.feature_names(iso=True, steered=True)
    phi, coh, energy = strike_field(visible)
    mm = np.lib.format.open_memmap(out, mode="w+", dtype=np.float32, shape=(n, len(names)))
    bounds = np.linspace(0, n, n_blocks + 1).astype(int)
    for b in range(n_blocks):
        lo, hi = bounds[b], bounds[b + 1]
        mats = F.extract(stack, [(ys[lo:hi], xs[lo:hi])], phi=phi, iso=True, steered=True)
        mm[lo:hi] = mats[0]
        del mats
        mm.flush()
        drop_file_cache(out)
        drop_file_cache(STACK)
    del mm, stack
    meta = dict(tag=tag, n_footprint=int(n), n_features=len(names), names=names,
                strike_sigma_region_px=40.0, strike_sigma_line_px=1.5,
                visible_catalogue_px=int(np.asarray(visible, bool).sum()),
                coherence_median=float(np.median(coh[footprint])),
                seconds=round(time.time() - t0, 1))
    meta_p.write_text(json.dumps(meta, indent=2))
    np.save(PROC / f"phi_{tag}.npy", phi)
    np.save(PROC / f"coh_{tag}.npy", coh)
    drop_file_cache(out)
    return out, meta


def training_sample(footprint, visible, n_neg: int, seed: int, flank_px: float = 2.0):
    """Positives: every visible catalogue cell. Negatives: random footprint cells
    farther than ``flank_px`` from any visible cell (withheld faults are *not*
    excluded -- in deployment the unmapped faults are also inside the negatives)."""
    rng = np.random.default_rng(seed)
    vis = np.asarray(visible, bool) & footprint
    neg_ok = footprint & ~flank_mask(vis, flank_px)
    pos = np.flatnonzero(vis.ravel())
    negs = np.flatnonzero(neg_ok.ravel())
    negs = rng.choice(negs, size=min(n_neg, negs.size), replace=False)
    return pos, negs


def flat_to_rows(flat_idx: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Map flat grid indices of footprint cells to rows of the feature matrix."""
    rowmap = np.full(footprint.size, -1, np.int64)
    rowmap[np.flatnonzero(footprint.ravel())] = np.arange(int(footprint.sum()))
    rows = rowmap[flat_idx]
    if (rows < 0).any():
        raise ValueError("index outside the footprint")
    return rows


def fit_arm(feats_path: Path, rows_pos: np.ndarray, rows_neg: np.ndarray, arm: str,
            seed: int = 0, params: dict | None = None, chunk: int = 50_000):
    cols = arm_columns(arm)
    mm = np.load(feats_path, mmap_mode="r")
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    sorted_rows = rows[order]
    # Read in slices so NumPy never materialises an un-sliced (N, all_cols) copy
    # on top of mmap page cache inside 3.8 GiB containers (IR-78-OOM-01).
    X = np.empty((sorted_rows.size, cols.size), np.float32)
    for lo in range(0, sorted_rows.size, chunk):
        hi = min(sorted_rows.size, lo + chunk)
        X[lo:hi] = mm[sorted_rows[lo:hi]][:, cols]
    del mm
    drop_file_cache(feats_path)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    p = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
             l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=seed)
    if params:
        p.update(params)
    clf = HistGradientBoostingClassifier(**p)
    t0 = time.time()
    clf.fit(X, y)
    del X, y
    info = dict(arm=arm, n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), n_features=int(cols.size),
                params=p, fit_seconds=round(time.time() - t0, 1))
    return clf, info


def score_grid(clf, feats_path: Path, arm: str, footprint: np.ndarray, chunk: int = 600_000) -> np.ndarray:
    """Model probability on every footprint cell; zeros elsewhere (finite, in [0,1])."""
    cols = arm_columns(arm)
    mm = np.load(feats_path, mmap_mode="r")
    n = mm.shape[0]
    out_fp = np.zeros(n, np.float32)
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        X = np.asarray(mm[lo:hi][:, cols], np.float32)
        out_fp[lo:hi] = clf.predict_proba(X)[:, 1].astype(np.float32)
    del mm
    drop_file_cache(feats_path)
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out_fp
    return grid
