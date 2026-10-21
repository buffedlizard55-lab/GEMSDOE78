# GEMSDOE78 - New Geological Hypotheses for Beating 0.3195

**Date:** 2026-10-21  
**Session:** Arena/fd05e152-gemsdoe78  
**Status:** Ready for Implementation  
**Target:** Generate submissions scoring > 0.3195, ultimately > 0.4413

---

## 🎯 Hypothesis Generation Methodology

### Analysis of Current State

From `docs/why-h33.md` and `research/knowledge.md`:

1. **Emission Optimization is Maxed Out**
   - H33 achieved 0.2778 through emission geometry alone
   - Dotted emission at 2.83px spacing + 2px flank pruning
   - Further thinning provides diminishing returns (near break-even at 0.056 credit/dot)

2. **Detector Improvement is the Path Forward**
   - Need better ranking of candidate pixels
   - Current best holdout-DTI: 0.1826 (H78-A strike-steered)
   - Gap to leaderboard: 0.4413 - 0.1826 = **0.2587 DTI points to close**

3. **What's Been Tried**
   - Raw 19 bands (A0): 0.1376 holdout-DTI
   - Rotation-invariant derivatives (A1): 0.1462 holdout-DTI
   - Strike-steered features (A2): 0.1586 holdout-DTI
   - With 3px flank pruning (B3): 0.1826 holdout-DTI
   - Monogenic phase congruency (MPC): 0.0977 holdout-DTI
   - Various ensemble and multi-physics approaches: 0.001-0.28

4. **Key Insight from Leaderboard**
   - Top scores (0.4413, 0.3904) are **~2x our current holdout-DTI**
   - These likely use **supervised learning with network context**
   - Must maintain **leakage-safe features** (no catalogue location in training)

---

## 🔬 5 New Candidate Hypotheses

### Ranking Criteria
- **Expected DTI Gain:** Based on geological reasoning and analogy to successful approaches
- **Implementation Cost:** Low (can reuse existing infrastructure) to High (requires new data)
- **Novelty:** Must differ from all ~90 family submissions
- **Feasibility:** Can be implemented in this sandbox (only github.com/pypi.org accessible)

---

## 🥇 HYPOTHESIS 1: H78-NET - Network-Aware Lineament Context (TOP CANDIDATE)

**Status:** ⭐ **SELECTED FOR IMPLEMENTATION**  
**Expected DTI Gain:** HIGH (+0.08-0.15 holdout-DTI)  
**Implementation Cost:** MEDIUM (2-4 hours, reuses existing features)  
**Risk:** LOW (leakage-safe by design)

### Description
Unmapped faults are most likely to occur in **structural gaps** within the visible fault network. 
Instead of treating each pixel independently, we compute **network-aware context features** 
that capture the spatial relationship between candidate lineaments and the visible catalogue.

### Layers Involved
- **Primary:** All 19 GeoDAWN bands (topography, magnetics, gravity, radiometrics)
- **Catalogue-Derived (location-free):**
  - Distance to nearest visible fault (used only for feature engineering, NOT as a feature)
  - Regional strike field φ(x) from visible catalogue (σ=4km structure tensor)
  - Fault density heatmap (Gaussian kernel, σ=4km) from visible catalogue

### Physical Signature
- **Distance-to-Network Context:** For each pixel, compute features based on its position 
  relative to the visible fault network topology
- **Structural Gap Detection:** Identify areas where the structural trend continues but 
  the catalogue has gaps
- **Junction Proximity:** Faults often occur at intersections and step-overs

### Why It Catches Missing Faults

In the Basin and Range province:
1. **Blind Faults Under Cover:** Faults continue beneath alluvial cover but aren't mapped
2. **Unmapped Strands:** In fault arrays, not all parallel strands are mapped at 1:250k scale
3. **Relay Ramps:** Connecting faults between en-echelon segments are often missed
4. **Tip Propagation:** Fault tips may extend beyond mapped traces

The USGS/INGENIOUS catalogue (1:250k compilation) **systematically misses** these features because:
- Limited resolution of source data
- Conservative mapping approach
- Focus on certain fault types (e.g., Quaternary faults)

### Non-Fault Mimics
- **Drainage Networks:** May parallel structural trends (mitigation: use geophysical signatures)
- **Lithologic Contacts:** Can have similar linear expressions (mitigation: multi-physics corroboration)
- **Anthropogenic Features:** Roads, canals (mitigation: footprint masking)

### Novelty vs Existing Approaches

| Aspect | H78-NET | Existing Family Approaches |
|--------|---------|----------------------------|
| **Context** | Network-aware features | Pixel-independent features |
| **Catalogue Use** | Location-free context (strike, density) | Only orientation (H78-A) or none |
| **Gap Detection** | Explicit structural gap features | Implicit through steering |
| **Junction Features** | Yes - intersection proximity | No |
| **Similarity** | Most similar to GEMSDOE77's context features | Different from all H78 variants |

**Key Difference:** We compute **leakage-safe context features** that describe the 
*structural position* of each pixel relative to the visible network, without revealing 
the location of hidden faults.

### Implementation Plan

#### Feature Engineering (Leakage-Safe)
```python
# From visible catalogue only (no hidden truth used)

# 1. Regional strike field (already implemented in H78-A)
strike_field = compute_structure_tensor(visible_catalogue, sigma_px=40)

# 2. Fault network density (Gaussian heatmap)
density = gaussian_filter(visible_catalogue.astype(float), sigma_px=40)

# 3. Distance to network (for feature binning, NOT as a feature)
dist_to_network = distance_transform(~visible_catalogue)

# 4. Structural gap features
#    - Along-strike gap length (distance between visible fault ends)
#    - Across-strike position (normalized distance from nearest visible fault)
#    - Junction proximity (distance to nearest fault intersection)

# 5. Network topology features
#    - Number of visible faults within 5km
#    - Orientation coherence of nearby visible faults
#    - Fault segment length statistics in neighborhood
```

#### Model Training
- **Algorithm:** HGB (HistGradientBoosting) - same as H78-A for consistency
- **Features:** 103 base features + ~20 new network context features = ~123 total
- **Training:** On visible catalogue only, with negatives sampled >2px from visible cells
- **Leakage Check:** Single-feature AUC on holdout truth (must be <0.90 for all features)

#### Emission
- **Geometry:** Greedy max-score packing, min separation 2.8px
- **Flank Pruning:** Exclude dots within 3px of visible catalogue (IR-78-01b amendment)
- **Budget:** 44,090 dots (matching D2.8/H33 live-validated scale)

### Expected Results

Based on sibling repository evidence:
- GEMSDOE77: Network context features achieved **0.1900 holdout-DTI** (single seed)
- GEMSDOE73: Similar approach with submodular allocation: **0.1599 holdout-DTI**
- Our H78-A (steered only): **0.1826 holdout-DTI**

**Conservative Estimate:** Adding network context to H78-A steered features
- Base (A2 steered): 0.1826
- Network context gain: +0.05-0.10 (from GEMSDOE77 analogy)
- **Expected: 0.23-0.28 holdout-DTI**

**Aggressive Estimate:** If network context + steered features are multiplicative
- **Expected: 0.25-0.30 holdout-DTI**

### Validation Strategy
1. Run on seed 20 holdout (buffered component draw)
2. Compare against A2_h78_steered baseline
3. Check paired difference CI excludes 0
4. Verify leakage canary (all features <0.90 AUC)
5. Check uniqueness vs registry rasters

---

## 🥈 HYPOTHESIS 2: H78-DEPTH - Depth-to-Basement Anomaly Detection

**Status:** Candidate (Requires feature verification)  
**Expected DTI Gain:** MODERATE-HIGH (+0.05-0.12 holdout-DTI)  
**Implementation Cost:** LOW (1-2 hours, uses existing depth_to_base_surf band)

### Description
Faults often express as **abrupt changes in basement depth**. In the Basin and Range, 
faults can juxtapose basement highs against sedimentary basins. We compute 
**edge detection and curvature features specifically on the depth-to-basement surface**.

### Layers Involved
- **Primary:** depth_to_base_surf (band 15) - already in feature stack
- **Derived Features:**
  - Sobel edge magnitude on basement depth
  - Laplacian of Gaussian (LoG) at σ=1,2,4 pixels
  - Depth gradient magnitude and direction
  - Depth curvature (profile and planar)
  - Depth step detection (Canny-like with adaptive threshold)

### Physical Signature
Faults create **discontinuities in basement depth** through:
1. **Vertical Displacement:** Faults offset the basement surface
2. **Juxtaposition:** Different basement blocks brought into contact
3. **Flexure:** Bending of basement near fault zones

### Why It Catches Missing Faults

The USGS/INGENIOUS catalogue misses faults where:
1. **Subtle Surface Expression:** Minimal topographic scarp (<5m) but significant basement offset
2. **Buried Faults:** Completely covered by alluvium but basement offset visible in gravity/magnetics
3. **Older Faults:** Pre-Quaternary faults with eroded surface expression but preserved basement structure

**Depth-to-basement data** (from INGENIOUS) captures these deep structural features that 
may not have clear surface expression.

### Non-Fault Mimics
- **Igneous Intrusions:** Can create local basement depth anomalies (mitigation: multi-physics)
- **Sedimentary Basins:** Gradual depth changes (mitigation: edge detection)
- **Data Artifacts:** Interpolation errors in depth estimation (mitigation: smoothing)

### Novelty vs Existing Approaches

| Aspect | H78-DEPTH | Existing Approaches |
|--------|-----------|---------------------|
| **Focus** | Basement depth discontinuities | Multi-band lineaments |
| **Features** | Depth-specific edge/curvature | Generic derivatives |
| **Target** | Buried/old faults | All fault types |
| **Similarity** | No direct equivalent | h61o-vardepth (0.0751) used depth variance |

**Key Difference:** We apply **dedicated edge detection to basement depth**, not just 
including it as a raw band. This targets the specific structural signature of faults 
in the depth domain.

### Implementation Plan

#### Feature Engineering
```python
from skimage.filters import sobel, gaussian
from scipy.ndimage import gaussian_laplace

# Load basement depth (band 15)
depth = features[:, :, 14]  # 0-indexed

# Edge detection
edge_sobel = sobel(depth)
edge_log_1 = gaussian_laplace(depth, sigma=1)
edge_log_2 = gaussian_laplace(depth, sigma=2)
edge_log_4 = gaussian_laplace(depth, sigma=4)

# Curvature (2nd derivatives)
depth_xx = gaussian(depth, sigma=1, order=[0,2])
depth_yy = gaussian(depth, sigma=1, order=[2,0])
curvature = depth_xx + depth_yy

# Gradient
depth_grad_x = gaussian(depth, sigma=1, order=[0,1])
depth_grad_y = gaussian(depth, sigma=1, order=[1,0])
grad_mag = np.sqrt(depth_grad_x**2 + depth_grad_y**2)

# Add to feature stack: ~10 new features
```

#### Model Training
- Same HGB configuration as H78-A
- Add depth-specific features to existing 103 features
- Train on visible catalogue

### Expected Results
- **Conservative:** +0.03-0.05 holdout-DTI (depth captures orthogonal signal)
- **Aggressive:** +0.05-0.10 holdout-DTI (if depth is highly diagnostic)
- **Total Expected: 0.21-0.28 holdout-DTI** (on top of H78-A base)

---

## 🥉 HYPOTHESIS 3: H78-MAG - Magnetic Anomaly Lineament Enhancement

**Status:** Candidate  
**Expected DTI Gain:** MODERATE (+0.04-0.08 holdout-DTI)  
**Implementation Cost:** LOW (1-2 hours, uses existing magnetic bands)

### Description
Magnetic data is highly sensitive to **fault-related structural discontinuities** through:
1. **Magnetic Contrast:** Different rock types on either side of a fault
2. **Fault Zone Magnetization:** Alteration along fault zones
3. **Structural Disruption:** Faults offset magnetic layers

We compute **magnetic-specific lineament features** that enhance fault detection.

### Layers Involved
- **Primary:** rtp (reduced-to-pole magnetics, band 2) - already in feature stack
- **Derived Features:**
  - Analytic signal amplitude (ASA) of magnetics
  - Tilt-angle derivative (TDR) of magnetics
  - Vertical derivative of magnetics
  - Horizontal derivatives (N-S, E-W)
  - 3D structure tensor on magnetics
  - Magnetic edge detection (Canny, Sobel)

### Physical Signature
Faults in magnetic data appear as:
- **Linear magnetic highs/lows** (lithologic contrast)
- **Magnetic gradient zones** (structural boundaries)
- **Disrupted magnetic patterns** (offset layers)

### Why It Catches Missing Faults

Magnetic methods detect faults that:
1. **Lack Topographic Expression:** Faults with no surface scarp
2. **Are Covered:** Buried under alluvium
3. **Have Subtle Surface Features:** <5m scarps not visible in DEM
4. **Cut Magnetic Layers:** Even with no surface expression

The USGS/INGENIOUS catalogue, being primarily **topography-based**, misses many of these.

### Non-Fault Mimics
- **Igneous Dikes/Sills:** Linear magnetic anomalies (mitigation: multi-physics corroboration)
- **Lithologic Contacts:** Non-fault boundaries (mitigation: structural context)
- **Data Striping:** Survey artifacts (mitigation: directional filtering)

### Novelty vs Existing Approaches

| Aspect | H78-MAG | Existing Approaches |
|--------|---------|---------------------|
| **Focus** | Magnetic-specific lineaments | Generic multi-band |
| **Features** | ASA, TDR, magnetic derivatives | Raw magnetic bands |
| **Target** | Faults with magnetic expression | All detectable faults |
| **Similarity** | No direct equivalent | Some lanes use magnetics but not specialized features |

**Key Difference:** We apply **magnetic-specific processing** (ASA, TDR) that are 
standard in mineral exploration for fault detection, but not used in the family.

### Implementation Plan

#### Feature Engineering
```python
from scipy.ndimage import gaussian_filter
import numpy as np

# Load magnetics (band 2: rtp)
mag = features[:, :, 1]  # rtp is band index 1

# Analytic Signal Amplitude (ASA)
# ASA = sqrt(RTP_x^2 + RTP_y^2 + RTP_z^2)
# We approximate with available derivatives
mag_x = gaussian_filter(mag, sigma=1, order=[0,1])
mag_y = gaussian_filter(mag, sigma=1, order=[1,0])
# For RTP, vertical derivative can be approximated
mag_z = gaussian_filter(mag, sigma=1, order=[0,0]) - mag  # Simplified
asa = np.sqrt(mag_x**2 + mag_y**2 + mag_z**2)

# Tilt-angle derivative (TDR)
# TDR = arctan(vertical_derivative / horizontal_derivative)
tdr = np.arctan2(mag_z, np.sqrt(mag_x**2 + mag_y**2))

# Add to feature stack: ~8 new features
```

### Expected Results
- **Conservative:** +0.02-0.04 holdout-DTI
- **Aggressive:** +0.04-0.08 holdout-DTI (if magnetics are diagnostic)
- **Total Expected: 0.20-0.26 holdout-DTI**

---

## 4️⃣ HYPOTHESIS 4: H78-RADON - Radon Transform Fault Detection

**Status:** Candidate (Requires scikit-image)  
**Expected DTI Gain:** MODERATE (+0.04-0.07 holdout-DTI)  
**Implementation Cost:** MEDIUM (2-3 hours, new algorithm)

### Description
The **Radon transform** is specifically designed to detect **linear features** in images. 
It projects the image along different angles and computes the integral along lines. 
Faults appear as **peaks in Radon space** at specific angles.

### Layers Involved
- **Primary:** All 19 GeoDAWN bands (applied per-band)
- **Process:** Radon transform at multiple angles, then reconstruct

### Physical Signature
- **Linear Fault Traces:** Appear as strong responses in Radon space
- **Fault Arrays:** Multiple parallel faults show as families of peaks
- **Intersections:** Appear at crossing angles

### Why It Catches Missing Faults

Radon transform is particularly good at detecting:
1. **Subtle Linear Features:** <5m scarps not visible in raw DEM
2. **Discontinuous Faults:** Faults with gaps or offsets
3. **Parallel Fault Arrays:** Multiple sub-parallel strands
4. **Low-Contrast Faults:** Faults with minimal expression

### Non-Fault Mimics
- **Drainage Patterns:** Linear drainage (mitigation: multi-band, only where geophysics support)
- **Vegetation Lines:** Tree rows, etc. (mitigation: footprint masking)
- **Data Artifacts:** Survey line artifacts (mitigation: angle filtering)

### Novelty vs Existing Approaches

| Aspect | H78-RADON | Existing Approaches |
|--------|-----------|---------------------|
| **Method** | Radon transform | Gradient/Hessian based |
| **Target** | Linear features specifically | General lineaments |
| **Similarity** | No direct equivalent | h67a-orientip used orientation |

**Key Difference:** Radon transform is **explicitly designed for line detection**, 
whereas current approaches use general edge/curvature detection.

### Implementation Plan

#### Feature Engineering
```python
from skimage.transform import radon, iradon
import numpy as np

# For each band, compute Radon features
angles = np.linspace(0, 179, 180)  # All angles
radon_features = []

for band in bands:
    # Compute Radon transform
    R = radon(band, theta=angles, circle=False)
    
    # Features from Radon space
    # 1. Max projection at each angle
    max_proj = R.max(axis=0)
    
    # 2. Peak detection in Radon space
    peaks = find_peaks(max_proj)[0]
    
    # 3. Reconstruct only the strongest angles
    strongest_angles = angles[peaks]
    
    # 4. Inverse Radon for reconstruction
    reconstructed = iradon(R, theta=angles)
    
    # Add features: max_proj, peak locations, reconstructed
```

### Expected Results
- **Conservative:** +0.03-0.05 holdout-DTI
- **Aggressive:** +0.04-0.07 holdout-DTI
- **Total Expected: 0.21-0.25 holdout-DTI**

---

## 5️⃣ HYPOTHESIS 5: H78-ENSEMBLE - Multi-Physics Weighted Ensemble

**Status:** Candidate  
**Expected DTI Gain:** MODERATE-HIGH (+0.05-0.12 holdout-DTI)  
**Implementation Cost:** HIGH (3-4 hours, multiple models)

### Description
Train **separate models on different physics domains**, then combine their predictions 
using a **learned weighting** based on local reliability.

### Layers Involved
- **Model 1:** Topography-only (bands 0-11: DEM derivatives)
- **Model 2:** Magnetic-only (band 2: rtp)
- **Model 3:** Gravity-only (bands 3-14: gravity anomalies)
- **Model 4:** Radiometric-only (bands 15-18: radiometrics)
- **Model 5:** Multi-physics (all bands)

### Physical Signature
Each physics domain detects different fault expressions:
- **Topography:** Surface scarps, linear valleys
- **Magnetics:** Lithologic contrast, alteration
- **Gravity:** Density contrast, basement offset
- **Radiometrics:** Radioactive element concentration changes

### Why It Catches Missing Faults
Different fault types have different expressions:
1. **Young Active Faults:** Strong topographic expression
2. **Old/Buried Faults:** Strong gravity/magnetic expression
3. **Mineralized Faults:** Strong radiometric expression
4. **Complex Faults:** Multiple expressions

By **specializing models per domain**, we capture faults that might be weak in one 
domain but strong in another.

### Non-Fault Mimics
- Each domain has its own mimics (see above hypotheses)
- **Mitigation:** Weighting based on local agreement between domains

### Novelty vs Existing Approaches

| Aspect | H78-ENSEMBLE | Existing Approaches |
|--------|--------------|---------------------|
| **Approach** | Domain-specialized ensemble | Single multi-physics model |
| **Combination** | Learned weighting | Simple union/average |
| **Similarity** | GEMSDOE2 used dual-family union | But not learned weighting |

**Key Difference:** We train **specialized models per physics domain** and combine 
with **learned reliability weights**, rather than just concatenating features.

### Implementation Plan

#### Model Training
```python
# Train 5 separate HGB models
domains = {
    'topo': [0,1,2,3,4,5,6,7,8,9,10,11],  # DEM and derivatives
    'mag': [2],  # RTP magnetics
    'grav': [3,4,5,6,7,8,9,10,11,12,13,14],  # Gravity anomalies
    'rad': [15,16,17,18],  # Radiometrics
    'all': list(range(19))  # All bands
}

models = {}
for domain, band_indices in domains.items():
    # Select features for this domain
    domain_features = feature_matrix[:, band_indices]
    
    # Train HGB
    models[domain] = train_hgb(domain_features, labels)
    
    # Predict on full grid
    preds[domain] = models[domain].predict_proba(domain_features)[:, 1]

# Combine with learned weights
# Option 1: Simple average
ensemble_simple = np.mean([preds[d] for d in ['topo', 'mag', 'grav', 'rad', 'all']], axis=0)

# Option 2: Weight by local variance (low variance = high confidence)
local_variance = np.var([preds[d] for d in ['topo', 'mag', 'grav', 'rad']], axis=0)
weights = 1.0 / (local_variance + 1e-6)  # Inverse variance weighting
ensemble_weighted = np.average([preds[d] for d in ['topo', 'mag', 'grav', 'rad']], 
                               axis=0, weights=weights)
```

### Expected Results
- **Conservative:** +0.04-0.06 holdout-DTI (domain specialization helps)
- **Aggressive:** +0.06-0.12 holdout-DTI (if domains capture complementary signals)
- **Total Expected: 0.22-0.30 holdout-DTI**

---

## 📊 HYPOTHESIS COMPARISON TABLE

| Rank | ID | Expected DTI Gain | Cost | Novelty | Feasibility | Notes |
|------|-----|------------------|------|---------|-------------|-------|
| **1** | **H78-NET** | **HIGH (+0.08-0.15)** | MEDIUM | HIGH | HIGH | ⭐ **SELECTED** - Network context, leakage-safe |
| 2 | H78-DEPTH | MOD-HIGH (+0.05-0.12) | LOW | HIGH | HIGH | Depth-specific features |
| 3 | H78-ENSEMBLE | MOD-HIGH (+0.05-0.12) | HIGH | HIGH | MEDIUM | Domain-specialized models |
| 4 | H78-MAG | MODERATE (+0.04-0.08) | LOW | MODERATE | HIGH | Magnetic-specific features |
| 5 | H78-RADON | MODERATE (+0.04-0.07) | MEDIUM | HIGH | MEDIUM | Radon transform for lines |

---

## 🎯 IMPLEMENTATION DECISION

### Selected: H78-NET (Network-Aware Lineament Context)

**Rationale:**
1. **Highest Expected Gain:** +0.08-0.15 holdout-DTI (could reach 0.26-0.33 total)
2. **Medium Cost:** 2-4 hours, reuses existing infrastructure
3. **High Novelty:** Network context features not used in family
4. **Leakage-Safe:** Uses only visible catalogue for context, not location
5. **Validated Concept:** GEMSDOE77 achieved 0.1900 with similar approach
6. **Path to Leaderboard:** 0.26-0.33 holdout-DTI could translate to 0.30-0.40+ live

### Implementation Steps

1. **Feature Engineering** (scripts/build_features_net.py)
   - Add network context features to existing 103 features
   - Compute: distance-to-network bins, junction proximity, fault density
   - Ensure all features are leakage-safe (no hidden truth used)

2. **Leakage Canary** (scripts/run_holdout.py)
   - Test each new feature alone on holdout
   - Flag any feature with AUC > 0.90
   - Remove or fix flagged features

3. **Holdout Evaluation** (scripts/run_holdout.py --seed 20)
   - Train HGB on visible catalogue with new features
   - Evaluate on withheld truth (11,321 positives)
   - Compare against A2_h78_steered baseline
   - Check paired difference CI

4. **Emission & Uniqueness** (scripts/build_submission_net.py)
   - Greedy max-score packing, 2.8px min separation
   - 3px flank pruning (IR-78-01b)
   - 44,090 dots budget
   - Check uniqueness vs registry rasters

5. **Validation & Run Card** (scripts/verify_tif.py)
   - Independent TIF verification
   - Check all submission requirements
   - Generate run card JSON

6. **Documentation & Site** (scripts/build_site_net.py)
   - Create executive summary page
   - Update README.md
   - Generate downloadable TIF and ZIP

---

## 📝 PREREGISTRATION

Before implementation, preregister H78-NET:

```json
{
  "lane": "H78-NET network-aware lineament context",
  "repository": "buffedlizard55-lab/GEMSDOE78",
  "branch": "arena/fd05e152-gemsdoe78",
  "written_utc": "2026-10-21T[time]Z",
  "written_before_results": true,
  "hypothesis": "Unmapped faults in the footprint are most likely to occur in structural gaps within the visible fault network. Network-aware context features that describe each pixel's position relative to the visible catalogue (distance, junction proximity, fault density) will raise the kernel credit per emitted dot on withheld fault segments, beyond what orientation-steered features alone can achieve.",
  "shared_tools_unmodified": "same as H78-A (vendor/gems57)",
  "holdout": {
    "draw": "gems57.holdout.buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3)",
    "evaluator": "gems57-pooled-hide-v2",
    "scoring": "pooled DTI alpha=0.2 beta=0.8 triangular 300 m; 95% CI paired 20 km block bootstrap",
    "training": "HGB on ALL visible catalogue cells; negatives sampled > 2 px from visible cells; withheld cells excluded from training"
  },
  "arms": {
    "A0_std19": "19 official bands (baseline)",
    "A1_iso": "A0 + rotation-invariant derivatives",
    "A2_h78_steered": "A1 + strike-steered features (H78-A)",
    "A3_net": "A2 + network context features (CANDIDATE)"
  },
  "emitter": "greedy max-score packing, min separation 2.8 px, visible-catalogue flank <= 3 px excluded; budget 44,090 dots",
  "canary": "single-feature AUC on withheld truth; > 0.90 = leakage",
  "uniqueness_rule": "Spearman rho vs any registry raster <= 0.90 AND fraction of final dots within 3 px of any registry dot set <= 0.70",
  "decision_rules": {
    "hypothesis_supported": "A3_net pooled HOLDOUT-DTI > A2_h78_steered with CI lower bound > 0",
    "ok_to_submit": "A3_net beats A0 and A2 with CI, canary clean, uniqueness pass, validator pass"
  },
  "budget": "3 experiments: E1 feature engineering+canary, E2 holdout evaluation, E3 final build+validation"
}
```

---

## 🎯 SUCCESS CRITERIA

### Minimum (Negative Result Acceptable)
- Holdout-DTI > 0.1826 (beat current best)
- All leakage canaries pass
- Uniqueness checks pass
- Valid TIF generated

### Target (Promote)
- Holdout-DTI > 0.20 (clear improvement)
- Paired difference vs A2 CI excludes 0
- All validation checks pass

### Stretch (Excellent)
- Holdout-DTI > 0.25 (approaching leaderboard)
- Significant improvement over all baselines
- Ready for organizer submission

---

## 📚 REFERENCES

All claims verified from:
- `research/knowledge.md` - Verified facts only
- `docs/why-h33.md` - H33 analysis
- `research/h78_hypotheses.md` - Existing hypotheses
- `registry/sources.json` - Official sources with fetch status

---

**Status:** Ready for implementation  
**Next Step:** Implement H78-NET in scripts/build_features_net.py  
**ETC:** 2-4 hours for full implementation and validation
