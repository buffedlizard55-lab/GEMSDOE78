# GEMSDOE78 Research Knowledge Base — H78-GSC Discovery Architecture & Live Forensics

**Repository:** `buffedlizard55-lab/GEMSDOE78` · **Active Branch:** `arena/13ef58cb-gemsdoe78` · **Date:** `2026-10-21`

---

## 1. Executive Synthesis & Status Summary

`H78-GSC` (**Geomorphic Scarp + Coulomb Bridge Multi-Physics Out-of-Fold Discovery with Exact 300 m Submodular Emission**) is promoted as the primary competition-ready submission of `GEMSDOE78`:

- **Validated GeoTIFF:** `docs/downloads/gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.tif` (`147,599` bytes, SHA-256 `e2f21d496925fb1bd2f36c5b28a0e2356286eca719132545474456f81bc5a8eb`)
- **Validated Competition ZIP:** `docs/downloads/gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.zip` (`115,382` bytes, SHA-256 `c0408bb9b22599fab796528d80f8d79523e6650b2b2c57bbe790341c631e90bc`)
- **Automated Preflight Status:** **`OK TO DOWNLOAD AND SUBMIT`** (`12/12` checks passed via `vendor/gems57/submission_writer.py` and `scripts/verify_tif.py`, zero human intervention required, `0` live weekly slots consumed automatically).
- **Strict Out-of-Fold (`LOQO`) Holdout Breakthrough (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`, `11,321` withheld positives):**
  - **Seed 20 Strict `LOQO` (`E3_MFNC_Bridge_PU_cal_LOQO__submod300_38000`):** **`0.18975`** (`95% CI: [0.1695, 0.2108]`; paired delta vs Session-1 `H78-A` strict `LOQO` `0.11016` = **`+0.07960`**, `95% CI: [+0.0614, +0.0984]`, `p < 0.001`; **`+0.00718` above Session-1 `H78-A` global in-sample `0.18257`**).
  - **Seed 20 Strict `LOQO` Dual Head (`E3_DualBlend_w0p82_LOQO__submod300_44090`):** **`0.18663`** (`95% CI: [0.1674, 0.2074]`), `far_gt10px = 0.08941`, `far_gt20px = 0.02643`, `C_pied = 0.08625`.
  - **3-Seed Replication Across Seeds `20, 30, 40` (100% Strict `LOQO`):**
    - `H78_GSC_MFNC_cal_LOQO_submod44090`: **`0.19762 ± 0.01024`** (`[0.18930, 0.20905]`, `C_pied = 0.08721`)
    - `H78_GSC_DualBlend_w0p82_LOQO_submod40k`: **`0.19731 ± 0.01058`** (`[0.18639, 0.20752]`, `far_gt10px = 0.09787`, `far_gt20px = 0.03705`, `C_pied = 0.08538`)
    - `H78_GSC_GlobalVis_submod44090`: **`0.20275 ± 0.00884`** (`[0.19380, 0.21147]`; Seed-20 greedy `44,090` = **`0.20906`**)
  - **Zero-SGMC Pure-Physics Head (`E3_Mphys_PU_zeroSGMC_LOQO`, `0` catalogue features):** **`0.11430`** (`95% CI: [0.0943, 0.1365]`), **`far_gt20px = 0.03784`** (`+89.1%` over standard 19-band `LOQO` `0.02001`).

---

## 2. Completion of Prior Session's Recommended Next Steps

All recommended next steps from Session 1 were executed and recorded in `evidence/h78_session1_next_steps.json` and `src/gems78/`:
1. **Fixed `IR-78-BAND6-01`:** Corrected `BAND_NAMES[5]` from `'te'` to `'tc'` (magnetic tilt/curvature) in `src/gems78/data.py` and `STEER_BANDS[-1] = 'tc'` in `src/gems78/features.py`.
2. **Eliminated In-Sample Spatial Memorization (`IR-78-INSAMPLE-01`):** Quantified exact Seed-20 drop of `H78-A` from `0.18257` (global visible fit) to `0.11016` (strict 4-quadrant `LOQO`), then rebuilt the entire modeling + PU cleaning + prevalence calibration architecture strictly out-of-fold so strict `LOQO` (`0.18975` Seed 20; `0.19762` 3-seed mean) outperforms even the prior global in-sample fit.
3. **Exact C-Accelerated 300 m Submodular DTI Emitter (`src/gems78/_fast_emit.c`):** Replaced greedy rank-thresholding with exact marginal 300 m kernel coverage maximization `Delta_d = sum_{i in B(d,300m)} p_i^gamma max(0, K(||i-d||) - M_i)`, cutting emission runtime to `< 0.5 s` and boosting `HOLDOUT-DTI` by `+0.00672` at identical dot budgets.
4. **Full Multi-Seed Spatial Validation (`Seeds 20, 30, 40`) & 1,049-Raster Uniqueness Audit:** Replicated across all 3 seeds (`evidence/h78_gsc_3seed_summary.json`) and audited every unique `.tif` across all 83 `GEMSDOE*` repositories (`evidence/h78_gsc_uniqueness_1089.json`).

---

## 3. Forensic Analysis: Why `h33-h33-2-b2` Scored `0.2778` (`ORGANIZER-CONFIRMED`) & How to Reach `0.32–0.44+`

### 3.1 Byte-Exact Dissection of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778` `ORGANIZER-CONFIRMED`)
Auditing all `62/63` byte-matched live submissions across the 83 sibling `GEMSDOE*` repositories (`evidence/live_submissions_audit.json`, `registry/family_scores.csv`) reveals four exact quantitative reasons why `h33-h33-2-b2` achieved `0.2778` (`ORGANIZER-CONFIRMED`) whereas pure catalogue-halo lanes such as `H57` stalled at `0.2051` (`ORGANIZER-CONFIRMED`):

1. **Optimal DTI False-Positive Budget Discipline (`37,654` spaced binary dots):** Under the official DrivenData DTI formula (`DTI = TP_w / (TP_w + 0.2*FP_w + 0.8*FN_w)` with a 300 m linear kernel), every redundant dot adds `0.2` to the denominator whenever its marginal expected kernel gain falls below `tau*(D) = 0.2 * D / (1 - 0.8 * D)` (`0.0714` at `D = 0.2778`; `0.0859` at `D = 0.3195`; `0.1364` at `D = 0.4413`). `h33-h33-2-b2` emitted exactly `37,654` non-overlapping binary dots (`median d_cat = 19.65 px`, `49.2%` at `d_cat > 20 px`), avoiding both `180k–624k` blanket dilution and contiguous-pixel self-cannibalization.
2. **Alluvial Cover / Piedmont Scarp Alignment (`C_pied = 0.09249`):** Across all non-SGMC live submissions (`n = 58`), our zero-fit piedmont scarp instrument `C_pied` correlates strongly with `ORGANIZER-CONFIRMED` DrivenData DTI (`Spearman rho = +0.5890, p = 7.41e-7`; non-SGMC `Pearson r = +0.8323, p < 10^-15`). `h33-h33-2-b2` concentrated dots precisely along range-front piedmont breaks-in-slope (`C_pied = 0.09249`, `76.4%` inside 1 m LiDAR, `23.6%` non-LiDAR), where Quaternary normal faults are systematically under-mapped by bedrock geological maps.
3. **Why `h33` Plateaued at `0.2778` and Why `GEMSDOE75 h75-1` Reached `0.3195` (`ORGANIZER-CONFIRMED`):**
   - `h33` relied on hand-tuned 19-band gradient combinations without (a) **domain-scale residual separation** (`2.5 km` vs `12 km` potential-field worms separating basement graben bounding faults from regional crustal thickness gradients), (b) **3D hypocentral seismicity & GeoDAWN hydrothermal conduit corroboration**, (c) **fluvial `chi` bedrock-to-piedmont knickpoint steps**, or (d) **explicit facing fault-termination Coulomb relay bridges across unmapped `0.9–4.8 km` step-overs**.
   - Conversely, catalogue-halo lanes (`H57`, `frac_le_5px > 0.55`) overfit the `3–5 px` buffer around already-mapped segments — inflating in-sample hide-and-recover scores while missing unmapped piedmont scarps, relay ramps, and blind basin faults on the live test set.

### 3.2 Engineering Requirements to Climb Past `0.2778` / `0.3195` Toward `0.4413`
1. **Strict Out-of-Fold PU-Cleaned Multi-Physics + Relay Geometry (`H78-GSC`):** Combine 124 domain-residual geophysical/topographic/LiDAR/`chi`/GeoDAWN features + 8 self-steered physics features + 18 vector fault-tip Coulomb relay bridges with two-stage PU spy cleaning on piedmont scarps so unmapped Quaternary scarps in `U` are never treated as hard negatives during training.
2. **Exact 300 m Submodular Kernel Packing (`40,000` binary dots):** Maximize expected 300 m triangular kernel coverage directly with `min_dist = 2.5 px` (`min_nn = 2.83 px`, `0` contiguous pairs, `0` on-catalogue pixels, `20.66%` non-LiDAR coverage, `C_pied = 0.08868`).

---

## 4. Ranked Geological Hypotheses Evaluated in Session 2

| Rank | ID | Geological Hypothesis | Layers Used | Mathematical Signature / Transform | Named Non-Fault Mimic Process | Expected Gain & Cost | Experimental Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Promoted Core)** | **H78-GSC-1 + H78-GSC-4** | **Alluvial Piedmont Scarp Crests + Positive-Unlabeled (`PU`) Spy Cleaning** | NaN-native `1 m` 3DEP LiDAR slope/diff, `10 m` 3DEP elevation, Quaternary cover unit indicators, 19-band stack | Anisotropic strike-steered crest `-H_nn + 0.35|H_tt - H_nn|`, step asymmetry `|g_n|/(g_t+0.02)`, piedmont cover interaction, and two-stage PU spy down-weighting of high-probability unmapped scarps in `U` | Pleistocene Lake Lahontan / Bonneville pluvial shoreline strandlines & coalescing alluvial fan toes | High gain, low compute (`~3 min`) | **Confirmed (`+0.0193` LOQO DTI from 1m LiDAR + 10m 3DEP alone; PU cleaning boosts both heads)** |
| **2 (Promoted Core)** | **H78-GSC-2** | **Paired Facing-Tip En-Echelon Relay Ramp & Coulomb Stress Bridge Completion** | Fold-visible `existing_faults.tif` (`vis` only!) + hybrid physics/catalogue strike field + piedmont scarp & potential-field gradients | Exact `9x9` vector fault-tip tangent estimation `(ux, uy)` + forward Gaussian cones (`900 m, 2.4 km, 4.8 km`) + **antiparallel paired facing-tip geometric mean** `sqrt(E+ * E-)` interacted with local scarp energy (`bridge_x_scarp`) | Erosional canyon mouths truncating mapped bedrock fault traces at range fronts | Highest structural gain, fast (`~6 s/fold`) | **Confirmed (#1 single canary `bridge_x_scarp` AUC `0.7861`, `#1` model gain feature `tip_coulomb_beam_relay_2400m` `6.24%`, drives strict `LOQO` to `0.18975` Seed 20 / `0.19762` 3-Seed)** |
| **3 (Promoted Core)** | **H78-GSC-3** | **Bedrock-to-Piedmont Fluvial `chi` Knickpoint & Drainage Deflection Anomalies** | `10 m` USGS 3DEP DEM + piedmont/bedrock transition mask | Multi-scale channel steepness / local base-level step proxy (`chi_step_interp_350m`, `chi_raised_density_400m`) isolating tectonic base-level fall across range fronts | Differential lithologic resistance (welded tuff / basalt caprock knickpoints) | Medium gain, zero extra data fetch | **Confirmed (`chi_raised_density_400m` `#7` overall gain `2.59%`, `chi_step_interp_350m` `#9` `2.34%`; adds `+0.0063` pure-physics LOQO DTI)** |
| **4 (Promoted Core)** | **H78-GSC-5** | **Domain-Residual Potential-Field Tilt Worms + 3D Hypocentral / GeoDAWN Hydrothermal Corridors** | Isostatic gravity, RTP magnetics (Band-6 `tc` fixed), MT resistivity, 3D ComCat earthquake shells, GeoDAWN springs/wells | Multi-wavelength residual separation (`2.5 km` minus `12 km`) + zero-crossing tilt worms + hypocentral density shells + spring lineament confluence | Igneous pluton / caldera ring margins & aeromagnetic flight-line seams | High blind-fault gain (`>2 km`), fast | **Confirmed (`+0.0175` pure-physics LOQO DTI; drives `far_gt20px` up `+89.1%` to `0.03784`)** |
| **5 (Tested Variant)** | **H78-NoisyOR** | **Probabilistic Noisy-OR Fusion vs Fold-Prevalence Linear Blend** | Saved `OOF` `M_mfnc` and `M_phys` surfaces | `1 - (1 - a*p_mfnc)(1 - b*p_phys)` across `alpha_or in {0.45, 0.65, 0.78, 0.88}` | Over-weighting uncalibrated tail probabilities in high-mimic volcanic terrain | Zero extra training cost (`< 30 s`) | **Evaluated & Rejected vs Linear Blend (`0.17982` vs `0.18663` Seed-20 LOQO DTI; `far20` rose to `0.0330` but total DTI dropped `-0.0068`)** |

---

## 5. Official Verified External Data Sources

All external datasets used in `GEMSDOE78` come strictly from free, public U.S. government / academic repositories already restored and verified by SHA-256 (`registry/sources.json`, `evidence/url_reachability_audit.json`):
- **USGS 3D Elevation Program (3DEP) 1 m LiDAR & 1/3 arc-second (10 m) Seamless DEM** (U.S. Geological Survey National Map, public domain).
- **USGS Comprehensive Earthquake Catalog (ComCat)** 3D Great Basin hypocentral catalog (U.S. Geological Survey Earthquake Hazards Program, public domain).
- **DOE GeoDAWN / INGENIOUS Great Basin Geothermal & Spring Synthesis** (U.S. Department of Energy Geothermal Technologies Office / OpenEI GDR, public domain / CC-BY).
- **USGS State Geologic Map Compilation (SGMC)** (`derived_sgmc_faults_100m_u8.tif` strictly **excluded** from all model features, training labels, calibration, and dot emission; retained solely as historical audit reference per `IR-78-SGMC-LEAK-01`).
