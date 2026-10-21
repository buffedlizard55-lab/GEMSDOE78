"""Network-aware context features for lane H78-NET.

Hypothesis H78-NET: Unmapped faults are most likely to occur in structural gaps
within the visible fault network. This module computes leakage-safe context
features that describe each pixel's position relative to the visible catalogue,
without using the catalogue's location to directly guide prediction.

All features are derived ONLY from the visible catalogue (withheld components
and their buffer are removed before feature computation in hide-and-recover folds).

Leakage rule (parallel-run protocol #2): in a hide-and-recover fold this must be
called with the fold's ``visible`` catalogue, never with the full catalogue.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree


def fault_density(visible: np.ndarray, sigma_px: float = 40.0) -> np.ndarray:
    """Gaussian-smoothed fault density from visible catalogue.
    
    Returns a float32 grid where each cell contains the density of visible
    fault pixels within a Gaussian kernel of sigma_px pixels.
    
    This is a leakage-safe context feature: it describes the local abundance
    of mapped faults without revealing the location of hidden faults.
    """
    return ndi.gaussian_filter(
        np.asarray(visible, np.float32),
        sigma=sigma_px,
        mode='constant',
        cval=0.0
    )


def distance_to_network(visible: np.ndarray) -> np.ndarray:
    """Euclidean distance transform from visible catalogue.
    
    Returns a float32 grid where each cell contains the distance (in pixels)
    to the nearest visible fault pixel. This is used internally for feature
    binning but is NOT exposed as a learner feature (to avoid direct distance
    leakage).
    """
    return ndi.distance_transform_edt(
        ~np.asarray(visible, bool)
    ).astype(np.float32)


def junction_proximity(visible: np.ndarray, sigma_px: float = 40.0) -> np.ndarray:
    """Proximity to fault junctions (intersections) in the visible catalogue.
    
    Fault junctions are defined as pixels where the catalogue has a
    cross-like pattern (high connectivity in multiple directions).
    We compute this by detecting pixels where the distance transform
    has low values in multiple orthogonal directions.
    
    Returns a float32 grid where high values indicate proximity to junctions.
    """
    # Compute distance transform
    dist = ndi.distance_transform_edt(~np.asarray(visible, bool))
    
    # Compute distance in 4 directions (N, S, E, W)
    dist_n = np.roll(dist, 1, axis=0)
    dist_s = np.roll(dist, -1, axis=0)
    dist_e = np.roll(dist, 1, axis=1)
    dist_w = np.roll(dist, -1, axis=1)
    
    # A junction pixel has low distance in at least 3 directions
    # (indicating it's at an intersection)
    is_junction = ((dist <= 1.5) & (dist_n <= 1.5) & (dist_s <= 1.5)) | \
                  ((dist <= 1.5) & (dist_e <= 1.5) & (dist_w <= 1.5)) | \
                  ((dist_n <= 1.5) & (dist_s <= 1.5) & (dist_e <= 1.5)) | \
                  ((dist_n <= 1.5) & (dist_s <= 1.5) & (dist_w <= 1.5)) | \
                  ((dist_e <= 1.5) & (dist_w <= 1.5) & (dist_n <= 1.5)) | \
                  ((dist_e <= 1.5) & (dist_w <= 1.5) & (dist_s <= 1.5))
    
    # Smooth the junction indicator
    junction_smoothed = ndi.gaussian_filter(
        is_junction.astype(np.float32),
        sigma=sigma_px,
        mode='constant',
        cval=0.0
    )
    
    return junction_smoothed


def structural_gap_features(visible: np.ndarray, sigma_region: float = 40.0) -> dict:
    """Compute structural gap features from visible catalogue.
    
    These features capture the idea that unmapped faults are likely to occur
    in gaps between mapped fault segments that share the same structural
    trend.
    
    Returns a dictionary with:
    - 'along_strike_gap': Gap length along the dominant strike direction
    - 'across_strike_position': Normalized position between fault strands
    - 'gap_coherence': How well-defined the gap is structurally
    """
    # Get strike field (reusing existing method)
    from .strike import strike_field
    phi, coh, energy = strike_field(visible, sigma_region=sigma_region)
    
    # Compute distance to network
    dist = distance_to_network(visible)
    
    # For each pixel, project distance onto strike-normal direction
    # This gives position between fault strands
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    
    # Compute gradient of distance field
    dist_x = ndi.gaussian_filter(dist, 1.0, order=(0, 1))
    dist_y = ndi.gaussian_filter(dist, 1.0, order=(1, 0))
    
    # Project onto strike-normal (across-strike) and strike-parallel (along-strike)
    across_dist = cos_phi * dist_x + sin_phi * dist_y
    along_dist = -sin_phi * dist_x + cos_phi * dist_y
    
    # Normalize across-strike distance by local fault spacing
    # Fault spacing is approximated by the distance between visible fault strands
    # We use the median distance in the local neighborhood
    local_dist = ndi.generic_filter(
        dist,
        lambda x: np.median(x[x > 0]) if np.any(x > 0) else 0.0,
        size=2 * int(sigma_region) + 1,
        mode='constant',
        cval=0.0
    )
    
    normalized_across = np.zeros_like(across_dist)
    valid = local_dist > 0
    normalized_across[valid] = across_dist[valid] / local_dist[valid]
    
    # Gap coherence: how consistent is the gap structure?
    # High coherence means the gap is well-defined (two clear fault strands)
    gap_coherence = coh * (energy / (energy.max() + 1e-12))
    
    return {
        'across_strike_position': normalized_across,
        'along_strike_variation': along_dist,
        'gap_coherence': gap_coherence,
    }


def fault_segment_length(visible: np.ndarray, sigma_px: float = 40.0) -> np.ndarray:
    """Compute local fault segment length statistics.
    
    For each pixel, compute the length of the nearest visible fault segment.
    Longer segments may indicate more mature faults, while shorter segments
    may indicate fault tips where unmapped continuation is likely.
    
    Returns a float32 grid with the length of the nearest fault segment.
    """
    from scipy.ndimage import label
    
    # Label connected components in visible catalogue
    labeled, n_labels = label(np.asarray(visible, bool))
    
    # Compute size of each component
    component_sizes = np.bincount(labeled.ravel())[1:]  # Skip 0 (background)
    
    # Map component labels to sizes
    size_map = np.zeros(n_labels + 1, dtype=np.float32)
    size_map[1:] = component_sizes
    
    # For each pixel, get the size of its nearest fault component
    # Use distance transform to find nearest component
    dist, indices = ndi.distance_transform_edt(
        ~np.asarray(visible, bool),
        return_distances=False,
        return_indices=True
    )
    
    # Get the label of the nearest fault pixel
    nearest_label = labeled[indices[0], indices[1]]
    
    # Map to sizes
    segment_length = size_map[nearest_label]
    
    # Smooth the result
    segment_length_smoothed = ndi.gaussian_filter(
        segment_length,
        sigma=sigma_px,
        mode='constant',
        cval=0.0
    )
    
    return segment_length_smoothed


def network_context_features(visible: np.ndarray, footprint: np.ndarray, 
                            sigma_region: float = 40.0) -> tuple[list, dict]:
    """Compute all network context features.
    
    Returns a tuple of:
    - List of feature arrays (each of shape footprint) for the footprint cells
    - Dictionary with feature names and metadata
    
    All features are derived ONLY from the visible catalogue and are designed
    to be leakage-safe (no information about hidden faults is used).
    """
    # Ensure we only compute on footprint
    vis = np.asarray(visible, bool) & footprint
    
    # Feature 1: Fault density
    density = fault_density(vis, sigma_px=sigma_region)
    
    # Feature 2: Junction proximity
    junction = junction_proximity(vis, sigma_px=sigma_region)
    
    # Feature 3: Fault segment length
    seg_length = fault_segment_length(vis, sigma_px=sigma_region)
    
    # Feature 4-6: Structural gap features
    gap_feats = structural_gap_features(vis, sigma_region=sigma_region)
    across_pos = gap_feats['across_strike_position']
    along_var = gap_feats['along_strike_variation']
    gap_coh = gap_feats['gap_coherence']
    
    # Feature 7: Distance-to-network bins (categorical, one-hot encoded)
    # We create bins of distance to network
    dist = distance_to_network(vis)
    dist_bins = np.digitize(dist, bins=[0, 5, 10, 20, 50, 100, np.inf])
    
    # One-hot encode the bins (6 bins = 6 features)
    dist_bin_features = np.zeros((7, *dist.shape), dtype=np.float32)
    for i in range(7):
        dist_bin_features[i] = (dist_bins == i).astype(np.float32)
    
    # Feature 8-13: Orientation statistics in neighborhood
    # Compute local orientation coherence and variability
    from .strike import strike_field
    phi, coh, energy = strike_field(vis, sigma_region=sigma_region)
    
    # Local strike variability (standard deviation of strike in neighborhood)
    phi_deg = np.degrees(phi)
    phi_smoothed = ndi.gaussian_filter(phi_deg, sigma=sigma_region)
    phi_var = ndi.generic_filter(
        phi_deg,
        lambda x: np.std(x[x > 0]) if len(x[x > 0]) > 1 else 0.0,
        size=2 * int(sigma_region) + 1,
        mode='constant',
        cval=0.0
    )
    
    # Collect all features
    feature_arrays = [
        density,
        junction,
        seg_length,
        across_pos,
        along_var,
        gap_coh,
    ]
    
    # Add distance bin features
    for i in range(7):
        feature_arrays.append(dist_bin_features[i])
    
    # Add orientation features
    feature_arrays.extend([
        coh,  # coherence (already computed)
        energy / (energy.max() + 1e-12),  # normalized energy
        phi_var,
    ])
    
    # Feature names
    feature_names = [
        'network_fault_density',
        'network_junction_proximity',
        'network_segment_length',
        'network_across_strike_position',
        'network_along_strike_variation',
        'network_gap_coherence',
    ]
    
    # Distance bin feature names
    for i in range(7):
        if i == 0:
            bin_name = 'on_fault'
        elif i == 6:
            bin_name = 'far_from_network'
        else:
            bin_name = f'dist_{int((i-1)*5 + 2.5)}px'
        feature_names.append(f'network_dist_bin_{bin_name}')
    
    # Orientation feature names
    feature_names.extend([
        'network_strike_coherence',
        'network_strike_energy_norm',
        'network_strike_variability',
    ])
    
    metadata = {
        'n_features': len(feature_names),
        'sigma_region_px': sigma_region,
        'feature_names': feature_names,
        'leakage_safe': True,
        'description': 'Network-aware context features derived from visible catalogue only'
    }
    
    return feature_arrays, metadata


def extract_network_features(stack, idx_sets, visible, sigma_region: float = 40.0):
    """Extract network context features for given index sets.
    
    This mirrors the extract() function in features.py for integration.
    
    Args:
        stack: The 19-band feature stack (not used here, but kept for API consistency)
        idx_sets: List of (ys, xs) index tuples
        visible: Boolean array of visible catalogue
        sigma_region: Sigma for regional smoothing
        
    Returns:
        List of feature matrices, one per index set
    """
    # Compute all network features on the full grid
    feature_arrays, metadata = network_context_features(
        visible, 
        np.ones(visible.shape, bool),  # Compute on full grid
        sigma_region=sigma_region
    )
    
    # Extract for each index set
    cols = [[] for _ in idx_sets]
    for feat_array in feature_arrays:
        for k, (ys, xs) in enumerate(idx_sets):
            cols[k].append(np.asarray(feat_array[ys, xs], np.float32))
    
    return [np.stack(c, axis=1).astype(np.float32) for c in cols], metadata
