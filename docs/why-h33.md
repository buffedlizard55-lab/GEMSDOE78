# Forensic Study — Why `h33-h33-2-b2` Reached `0.2778`, How It Relates to Higher Reported Scores, and What `H78-GSC` & `H78-MGHD` Prove

**Score provenance discipline:**
- In `evidence/live_submissions_audit.json` (cross-referenced across sibling repositories), `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is logged at **`0.2778`**, `D2.8` (`44,090` dots) at **`0.2600`**, and `H19-5` (`1,100,000` dots) at **`0.1304`**. Higher user-quoted figures (**`0.3195`**, **`0.4413`**) appear in prompt context without an independently retrieved DrivenData HTML/screenshot receipt inside this network-restricted sandbox (`www.drivendata.org` is unreachable; outbound access is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`). Every internal model measurement in this repository is strictly labeled **`HOLDOUT-DTI`** (`gems57-pooled-hide-v2`, `alpha=0.2, beta=0.8`, 300 m kernel, 20 km spatial-block bootstrap CI) and **never** projected onto the live leaderboard scale.

---

## 1. Exact Pixel-Level Forensics of `H19-5 -> D2.8 -> H33 (37,654 Dots)`

Direct inspection of SHA-256-pinned `data/registry/h33_2_b2_37654_zeros.tif` (`sha256 = e5eb6e7ee646c542cd2171235b2a0ebaa8878b9ab2377d70091fd442146c31f0`) reveals why `H33` jumped over `H19-5` and `D2.8`:

1. **Exact DTI Tversky Marginal-Inclusion Threshold (`alpha = 0.2, beta = 0.8`)**:
   $$\mathrm{DTI}(p, g) = \frac{\mathrm{TP}_w}{\mathrm{TP}_w + 0.2\,\mathrm{FP}_w + 0.8\,\mathrm{FN}_w}$$
   Differentiating with respect to a newly added isolated unit dot at current score $S$ shows that a new dot improves $\mathrm{DTI}$ if and only if its expected kernel-weighted true-positive mass exceeds:
   $$\Delta \mathrm{TP}_w > \tau^*(S) = \frac{\alpha S}{1 - \beta S} = \frac{0.2 S}{1 - 0.8 S}$$
   - At $S = 0.1304$: $\tau^*(0.1304) = 0.0291$ — blanket rasters with $1.10\text{M}$ positive pixels inject $\sim 10^6$ false-positive pixels and collapse the denominator ($0.2\,\mathrm{FP}_w$).
   - At $S = 0.2778$: $\tau^*(0.2778) = 0.0714$ — spaced binary dots separated by $\approx 280\text{–}301\text{ m}$ capture the full 300 m triangular kernel halo ($K(d) = \max(0, 1 - d/300\text{ m})$) while paying the false-positive cost at only one pixel per halo ($\sim 16\times$ fewer FP pixels than continuous bands).
   - At $S = 0.3195$: $\tau^*(0.3195) = 0.0858$.
   - At $S = 0.4413$: $\tau^*(0.4413) = 0.1364$.

2. **Catalogue-Flank Removal (`37,654 = 44,090 - 6,436` Dots)**:
   - `D2.8` placed `44,090` spaced binary dots (`0.853%` of footprint), including `6,436` dots (`14.6%` of its entire budget) within $\le 2\text{ px}$ ($\le 200\text{ m}$) of mapped `existing_faults.tif`.
   - `H33` used the **exact same base classifier** as `D2.8` and changed **only one rule**: deleting those `6,436` near-catalogue flank dots (`37,654` remaining dots, `0.729%` of footprint) where mapped traces had already saturated 300 m kernel coverage.

3. **Why `0.2778` Still Hit a Ceiling Below `0.3195` / `0.4413`**:
   - Both `D2.8` and `H33` trained on raw 19-band pixel features without cross-scale geodetic strain, self-steered potential-field/topographic geometry, 1 m LiDAR scarp asymmetry, geothermal/magnetotelluric fluid-conduit physics, or submodular 300 m kernel packing.
   - Across `62` byte-matched live submissions, zero-fit piedmont-scarp concentration correlates strongly with reported live DTI ($\rho = +0.5890, p = 7.41\times 10^{-7}$), while range-interior volcanic calderas, playa desiccation margins, and bedrock bedding ridges create systematic false positives in isotropic gradient models.

---

## 2. How `H78-GSC` and `H78-MGHD` Advance Beyond `H33` on Locked Spatial Holdouts

| Lane | Core Physical Mechanism | Seed 20 `HOLDOUT-DTI` (`11,321` px) | Multi-Seed `HOLDOUT-DTI` | Registry Uniqueness Status | Upload Status |
|---|---|---:|---:|---|---|
| `CTRL_A2_v2` (Incumbent) | 103-col strike-steered 19-band GBDT (`d=2.8`, `44,090` dots) | `0.182575` `[0.1633, 0.2000]` | `0.183004` (2-seed) | `0.7690 > 0.70` vs `GEMSDOE53` | **NO** |
| **`H78-GSC` (`PR #26`)** | 4-quadrant OOF multi-physics + PU scarp + Coulomb relay bridges + 300 m submodular `40,000` dots | **`0.1898`** `[0.1695, 0.2108]` | **`0.1976`** (3-seed OOF mean) | **PASS `30 / 30` G4 v2** (`max mutual 0.70`) | **YES — CLEARED** |
| **`H78-MGHD` (`PR #27`)** | Pure 123-col Multi-Scale Geodetic–Hydrothermal–LiDAR Dual-Cover (`0/103` A2 cols, `0` cat cols) | **`0.195210`** (`d=2.8`) / **`0.193393`** (`d=3.01`) | **`0.200714`** (`Seed 30` 0-retune) / **`0.197059`** (pooled 2-seed) | Passes all `801` external sparse dot files (`0.6800 <= 0.70`) & `H78-GSC` (`0.5587`), **STOP `0.7359 > 0.70` vs `H79-LS-50k`** | **NO — RESEARCH / NEXT-WEEK STACK** |

### Why `H78-MGHD + H78-GSC` Is the Strongest Next-Week Research Direction
`H78-MGHD` shares **zero feature columns** with `H78-A`, zero catalogue proximity features, and has a continuous surface correlation of only **$\rho = +0.0888$** (`forward 3-px dot overlap = 0.5587 <= 0.70`) against cleared `H78-GSC`, making an out-of-fold ensemble of `H78-MGHD + H78-GSC` with `36,000–39,000` `min_dist=3.01` submodular dots the clearest path toward the `0.32–0.44` regime once weekly slot budget is refreshed.
