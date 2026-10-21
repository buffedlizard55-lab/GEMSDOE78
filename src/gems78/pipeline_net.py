"""Pipeline for lane H78-NET (Network-Aware Lineament Context).

This extends pipeline.py with network context features and the A3 arm.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from . import features_net as F
from .data import PROC, load_stack
from .emit import flank_mask
from .strike import strike_field
from .network import network_context_features

# Arm configurations
ARMS = {
    "A0_std19": dict(iso=False, steered=False, network=False),
    "A1_iso": dict(iso=True, steered=False, network=False),
    "A2_h78_steered": dict(iso=True, steered=True, network=False),
    "A3_h78_net": dict(iso=True, steered=True, network=True),  # NEW: Network-aware
}


def arm_columns(arm: str) -> np.ndarray:
    """Column indices of the full (raw+iso+steered+network) matrix used by an arm."""
    full = F.feature_names_net(iso=True, steered=True, network=True)
    want = F.feature_names_net(**ARMS[arm])
    pos = {n: i for i, n in enumerate(full)}
    return np.array([pos[n] for n in want], np.int64)


def footprint_index(footprint: np.ndarray):
    ys, xs = np.nonzero(footprint)
    return ys.astype(np.int32), xs.astype(np.int32)


def build_feature_matrix_net(tag: str, footprint: np.ndarray, visible: np.ndarray,
                           n_blocks: int = 4, force: bool = False) -> tuple[Path, dict]:
    """Full feature matrix for H78-NET with network context features.
    
    Written as a float32 memmap ``data/processed/feats_net_<tag>.npy`` of shape
    (n_footprint, n_features) in footprint row-major order.
    
    This includes:
    - 19 raw bands
    - 18 ISO features (3 per band × 6 bands × 2 scales)
    - 24 steered features (4 per band × 6 bands × 2 scales)
    - 20 network context features
    - Total: 81 features
    """
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"feats_net_{tag}.npy"
    meta_p = PROC / f"feats_net_{tag}.json"
    
    if out.exists() and meta_p.exists() and not force:
        return out, json.loads(meta_p.read_text())
    
    t0 = time.time()
    stack = load_stack()
    ys, xs = footprint_index(footprint)
    n = ys.size
    
    # Get feature names
    names = F.feature_names_net(iso=True, steered=True, network=True)
    
    # Compute strike field and network features
    phi, coh, energy = strike_field(visible)
    
    # Pre-compute network features on full grid
    net_feats, net_meta = network_context_features(visible, footprint, sigma_region=40.0)
    
    # Build memmap
    mm = np.lib.format.open_memmap(out, mode="w+", dtype=np.float32, shape=(n, len(names)))
    bounds = np.linspace(0, n, n_blocks + 1).astype(int)
    
    for b in range(n_blocks):
        lo, hi = bounds[b], bounds[b + 1]
        
        # Extract raw + iso + steered features
        mats = F.extract_with_network(
            stack, 
            [(ys[lo:hi], xs[lo:hi])], 
            phi=phi, 
            iso=True, 
            steered=True, 
            network=False,  # We'll add network separately
            visible=visible,
            sigma_region=40.0
        )
        
        # Start with raw + iso + steered
        block_feats = mats[0]
        
        # Add network features
        net_feats_block = np.stack([feat[ys[lo:hi], xs[lo:hi]] for feat in net_feats], axis=1)
        
        # Combine
        mm[lo:hi] = np.concatenate([block_feats, net_feats_block], axis=1).astype(np.float32)
        
        del mats, block_feats, net_feats_block
        mm.flush()
    
    del mm
    
    meta = dict(
        tag=tag, 
        n_footprint=int(n), 
        n_features=len(names), 
        names=names,
        strike_sigma_region_px=40.0,
        strike_sigma_line_px=1.5,
        visible_catalogue_px=int(np.asarray(visible, bool).sum()),
        network_features=net_meta,
        seconds=round(time.time() - t0, 1)
    )
    meta_p.write_text(json.dumps(meta, indent=2))
    np.save(PROC / f"phi_net_{tag}.npy", phi)
    
    return out, meta


def training_sample(footprint, visible, n_neg: int, seed: int, flank_px: float = 2.0):
    """Positives: every visible catalogue cell. Negatives: random footprint cells
    farther than ``flank_px`` from any visible cell."""
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


def fit_arm_net(feats_path: Path, rows_pos: np.ndarray, rows_neg: np.ndarray, arm: str,
               seed: int = 0, params: dict | None = None):
    """Train HGB model for a specific arm."""
    cols = arm_columns(arm)
    mm = np.load(feats_path, mmap_mode="r")
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    X = np.asarray(mm[rows[order]][:, cols], np.float32)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    
    p = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
             l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=seed)
    if params:
        p.update(params)
    
    clf = HistGradientBoostingClassifier(**p)
    t0 = time.time()
    clf.fit(X, y)
    info = dict(arm=arm, n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), 
                n_features=int(cols.size), params=p, fit_seconds=round(time.time() - t0, 1))
    return clf, info


def score_grid_net(clf, feats_path: Path, arm: str, footprint: np.ndarray, chunk: int = 600_000) -> np.ndarray:
    """Model probability on every footprint cell; zeros elsewhere (finite, in [0,1])."""
    cols = arm_columns(arm)
    mm = np.load(feats_path, mmap_mode="r")
    n = mm.shape[0]
    out_fp = np.zeros(n, np.float32)
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        X = np.asarray(mm[lo:hi][:, cols], np.float32)
        out_fp[lo:hi] = clf.predict_proba(X)[:, 1].astype(np.float32)
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out_fp
    return grid
