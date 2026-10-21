"""Per-pixel feature extraction for lane H78-NET (Network-Aware).

This extends the H78 feature set with network context features that describe
each pixel's position relative to the visible fault network, enabling the
model to learn structural patterns like fault gaps, junctions, and step-overs.

Feature families:
* ``raw``      -- the 19 official bands (log1p on heavy-tailed ones)
* ``iso``      -- rotation-invariant multi-scale Hessian eigenvalues and gradient
                  magnitude on six line-expressing bands (control arm A1)
* ``steered``  -- derivatives projected onto regional catalogue-strike frame
                  (H78-A candidate features)
* ``network``  -- network context features: density, junctions, gaps, etc.

All features are derived ONLY from visible catalogue (no hidden truth leakage).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .data import BAND_NAMES
from .network import network_context_features

STEER_BANDS = ["det_elev", "rtp", "iso_grav_anom", "depth_to_base_surf", "cond_surf", "tc_totalcount"]
SCALES = (1.5, 3.0)


def feature_names_net(iso: bool = True, steered: bool = True, network: bool = True) -> list[str]:
    """Return feature names for H78-NET feature set."""
    names = list(BAND_NAMES)
    
    # ISO features
    if iso:
        for b in STEER_BANDS:
            for s in SCALES:
                names += [f"{b}_s{s}_l1", f"{b}_s{s}_l2", f"{b}_s{s}_gm"]
    
    # Steered features
    if steered:
        for b in STEER_BANDS:
            for s in SCALES:
                names += [f"{b}_s{s}_Hnn", f"{b}_s{s}_Htt", f"{b}_s{s}_gn", f"{b}_s{s}_agt"]
    
    # Network context features
    if network:
        # These will be computed dynamically, but we know the count
        network_names = [
            'network_fault_density',
            'network_junction_proximity',
            'network_segment_length',
            'network_across_strike_position',
            'network_along_strike_variation',
            'network_gap_coherence',
            'network_dist_bin_on_fault',
            'network_dist_bin_0-5px',
            'network_dist_bin_5-10px',
            'network_dist_bin_10-20px',
            'network_dist_bin_20-50px',
            'network_dist_bin_50-100px',
            'network_dist_bin_100px+',
            'network_strike_coherence',
            'network_strike_energy_norm',
            'network_strike_variability',
        ]
        names.extend(network_names)
    
    return names


def extract_with_network(stack, idx_sets, phi=None, iso: bool = True, 
                        steered: bool = True, network: bool = True,
                        visible: np.ndarray = None, sigma_region: float = 40.0):
    """Return feature matrices with network context features.
    
    This is the extended version of extract() that includes network features.
    
    Args:
        stack: The 19-band feature stack
        idx_sets: List of (ys, xs) index tuples
        phi: Strike field (required if steered=True)
        iso: Include rotation-invariant features
        steered: Include steered features
        network: Include network context features
        visible: Visible catalogue (required if network=True)
        sigma_region: Sigma for network feature computation
        
    Returns:
        List of feature matrices, one per index set
    """
    if steered and phi is None:
        raise ValueError("steered features need the strike field phi")
    if network and visible is None:
        raise ValueError("network features need the visible catalogue")
    
    # Start with raw + iso + steered features (same as original extract)
    cols = [[] for _ in idx_sets]
    for b in range(len(BAND_NAMES)):
        band = stack[b]
        for k, (ys, xs) in enumerate(idx_sets):
            cols[k].append(np.asarray(band[ys, xs], np.float32))
    
    if not (iso or steered or network):
        return [np.stack(c, axis=1) for c in cols]
    
    # ISO features
    if iso or steered:
        if steered:
            cph = [np.cos(phi[ys, xs]).astype(np.float32) for ys, xs in idx_sets]
            sph = [np.sin(phi[ys, xs]).astype(np.float32) for ys, xs in idx_sets]
        
        for bname in STEER_BANDS:
            a = np.ascontiguousarray(stack[BAND_NAMES.index(bname)], dtype=np.float32)
            for s in SCALES:
                gx = ndi.gaussian_filter(a, s, order=(0, 1))
                gy = ndi.gaussian_filter(a, s, order=(1, 0))
                gxx = ndi.gaussian_filter(a, s, order=(0, 2))
                gyy = ndi.gaussian_filter(a, s, order=(2, 0))
                gxy = ndi.gaussian_filter(a, s, order=(1, 1))
                s1, s2 = np.float32(s), np.float32(s * s)
                for k, (ys, xs) in enumerate(idx_sets):
                    Gx, Gy = gx[ys, xs] * s1, gy[ys, xs] * s1
                    Gxx, Gyy, Gxy = gxx[ys, xs] * s2, gyy[ys, xs] * s2, gxy[ys, xs] * s2
                    if iso:
                        half_tr = 0.5 * (Gxx + Gyy)
                        disc = np.sqrt((0.5 * (Gxx - Gyy)) ** 2 + Gxy ** 2)
                        cols[k] += [half_tr + disc, half_tr - disc, np.hypot(Gx, Gy)]
                    if steered:
                        c, sn = cph[k], sph[k]
                        hnn = c * c * Gxx + 2 * sn * c * Gxy + sn * sn * Gyy
                        htt = sn * sn * Gxx - 2 * sn * c * Gxy + c * c * Gyy
                        gn = c * Gx + sn * Gy
                        gt = -sn * Gx + c * Gy
                        cols[k] += [hnn, htt, gn, np.abs(gt)]
                del gx, gy, gxx, gyy, gxy
            del a
    
    # Network features
    if network:
        # Compute network features on full grid
        feature_arrays, _ = network_context_features(
            visible, 
            np.ones(visible.shape, bool),  # Compute on full grid
            sigma_region=sigma_region
        )
        
        # Extract for each index set
        for feat_array in feature_arrays:
            for k, (ys, xs) in enumerate(idx_sets):
                cols[k].append(np.asarray(feat_array[ys, xs], np.float32))
    
    return [np.stack(c, axis=1).astype(np.float32) for c in cols]
