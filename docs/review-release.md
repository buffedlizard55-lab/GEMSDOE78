# GEMSDOE78 Scientific Review, 5 Ranked Novel Geological Hypotheses & 84-Repository Uniqueness Audit

**Review Date:** `2026-10-22` · **Active Branch:** `arena/abc72825-gemsdoe78`  
**Top-Line Gate Status:** **`OK TO DOWNLOAD: YES · OK TO SUBMIT: NO`** (`weekly_slots_used_by_agent = 0`, `ORGANIZER-CONFIRMED: None`)

---

## 1. Five Ranked Novel Geological Hypotheses (Proposed & Verified Obtainable Before Implementation)

All external datasets referenced below were verified present and SHA-256-pinned in `registry/data_manifest_gems73.json` prior to training, while leaky fault layers (`sgmc_faults_100m.tif`, `derived_sgmc_faults_100m_u8.tif`, `gdr_qfaults_traces.csv`, and `*fault*` CSV columns) were fail-closed blocked in `src/gems78/mghd.py`.

| Rank | Hypothesis ID | Physical Layers Used | Physical Transform & Signature | Why Missed by USGS/INGENIOUS Catalogue | Primary Non-Fault Mimic | How It Differs From Prior Repo Code |
| :---: | --- | --- | --- | --- | --- | --- |
| **1 (Implemented)** | **`H78-MGHD`** *(Multi-Scale Geodetic–Hydrothermal–LiDAR Dual-Cover)* | Core 19 stack + 3DEP 1 m LiDAR (`lidar_scarp_features_u8.tif`), 10 m DEM & stream $\chi$ (`topo_10m_derived_100m_u8.tif`, `dem10_chi_100m_i16.tif`), USGS GeoDAWN (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`), DOE GDR-1391 (`Paleo_geothermal_final.csv`, `2m_temperature_probe_INGENIOUS_regional_data.zip`) | Broad 600–1,200 m cross-strike flank warp $(u(\mathbf{x}+h\hat{\mathbf{n}})-u(\mathbf{x}-h\hat{\mathbf{n}}))$, local background residualization $(u - G_{25}*u)$, 1 m scarp height & strike-tangent coherence $-\cos(2(\theta_{\text{lidar}}-\phi))$ with `NaN` routing where `valid==0`, masked stream $\chi$ knickpoints, GeoDAWN $K/Th$ potassium-argillic alteration, and multi-bandwidth thermal vent/probe kernels; dual trace+kernel learner with `min_dist=3.01 px` non-overlapping 300 m kernel centers | Concealed basin-interior faults lack 100 m DEM scarps; subtle range-front splays have 0.5–2 m scarps blurred by 100 m gridding or express only through hydrothermally altered $K$-enrichment and stream $\chi$ steps | Pleistocene Lake Lahontan / Bonneville shorelines, welded tuff cooling-unit rims, down-gradient travertine outflow aprons | Prior `H78-A`/`CS`/`SPY` used only 19 core layers + short-scale derivatives (`min_dist=2.8`); `H78-MGHD` uses zero `H78-A` columns, adds 4 independent external physics datasets, fixes PU self-suppression & NaN/angle encoding, and enforces exact 301 m kernel spacing |
| **2** | **`H78-SHORE`** *(Paleoshoreline-Deconvolved Scarp & Drainage Offset Detector)* | 1 m LiDAR scarp height/orientation + `det_elev` + 10 m stream $\chi$ | Iso-elevation contour parallelism filter penalizing scarps running at constant elevation (`|\nabla z \cdot \hat{\mathbf{t}}| \approx 0`) along Lahontan/Bonneville highstands (`~1,330 m`, `~1,580 m`) while rewarding scarps cutting across elevation contours with $\Delta\chi$ jumps | Quarter-quadrangle mapping frequently confuses wave-cut benches with tectonic scarps or omits oblique relay ramps crossing fan heads | Resistant dipping carbonate/basalt hogbacks cutting fan contours | Existing code has no elevation-contour tangency discriminator to suppress pluvial shoreline mimics |
| **3** | **`H78-EULER3D`** *(Multi-Depth Structural Euler Deconvolution & Gravity-Magnetic Dip Vector Alignment)* | `tmi`, `TMI_up150`, `iso_grav_anom`, horizontal/vertical derivatives (`hg`, `vg`), `depth_to_base_surf` | 3D Euler structural index ($SI \in [0, 0.5]$ for contact/fault step) depth estimation $(z_0 = (x - x_0)\partial_x T + \dots)$ paired with gravity-magnetic horizontal gradient vector dot product $\nabla_{\perp} g \cdot \nabla_{\perp} M$ | Blind intrabasinal horst/graben bounding faults buried beneath 200–1,500 m of Plio-Quaternary fill have zero topographic expression | Plutonic intrusive margins and caldera ring-fracture density contacts | `H78-CROSSLAYER` computed unsigned surface alignments on 3 layers without upward continuation or Euler depth filtering |
| **4** | **`H78-WALKER`** *(Transtensional Riedel & Relay-Breach Strain Partitioning)* | `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv`, `deq_n100a15`, `ieq_n100a15`, visible fault tips | Principal strain orientation vs local visible strike obliquity + fault-tip Coulomb stress-lobe templates at mapped segment terminations | Walker Lane & Humboldt Structural Zone host unmapped synthetic/antithetic R/R' shears and unbreached relay zones where slip transfers between echelon strands | Regional GPS interpolation artifacts between sparse stations and mining-induced microseismicity | `H78-CS` measured symmetric collinear support along mapped traces rather than oblique transtensional tip stress lobes |
| **5** | **`H78-INSAR`** *(Hydrothermal Clay Alteration Halo & Shallow Conductive Upflow Coupling)* | GeoDAWN `K`, `Th`, `U`, core `cond_surf`, `cond_mid`, GDR-1391 2 m temperature probes | Coupled high `cond_surf / cond_mid` smectite clay cap + high radiometric `K/Th` adularia-illite outflow + positive 2 m probe thermal anomaly | Blind geothermal upflow zones often seal their surface trace with hydrothermal silica/clay while maintaining active permeable damage zones at 100–500 m depth | Evaporite playabasin brines and altered Tertiary volcanic ash beds | Never combined radiometric `K/Th` alteration with MT electrical conductivity ratios and 2 m probe surveys in repository code |

---

## 2. Complete Three-Pass Audit & Irregularities Log (`Pass 1 -> Pass 2 -> Pass 3`)

### Pass 1 — Full Data Inspection, Pipeline Implementation & Initial Execution
- Restored all core, bridge, external, and scored inputs into snapshot-excluded `.cache/` directories behind `data/` symlinks using `codeload.github.com` streaming (`IR-78-RESTORE-01`, immune to GitHub REST API 403 rate limits).
- Built the first complete SHA-256 registry across **all 84 accessible `buffedlizard55-lab` repositories** (`registry/accessible_registry_2026-10-22.json`: **`1,103` unique GeoTIFFs**, `0` scan errors).
- Caught three physical data hazards before building `src/gems78/mghd.py`:
  1. `lidar_scarp_features_u8.tif` band 12 (`valid == 0` on `24.6%` of cells) -> converted to native `NaN` so trees route missing 1 m tiles cleanly to 100%-coverage 10 m DEM & stream $\chi$ features.
  2. Strike tangent vs normal convention: `strike_field()` returns fault normal $\phi$, whereas `lidar_scarp_features_u8.tif` band 11 encodes tangent $\phi + \pi/2$, so parallel alignment is $-\cos(2(\theta_{\text{lidar}}-\phi))$.
  3. `dem10_chi_100m_i16.tif` non-channel sentinel `-32768` -> masked (`> -30000`) prior to Gaussian smoothing.

### Pass 2 — Bug & Edge-Case Audit + Empirical Fixes
- **`IR-78-MGHD-01` (HGB Inverse-Sampling Weight Hessian Distortion):** In Pass 1 on `seed=20` (before `seed=30` was ever run), passing `sample_weight ≈ 20.5` on negatives directly into `HistGradientBoosting` split Hessians + 25 km hole deletion suppressed recall (`0.1394` greedy / `0.1415` submodular). Preserved the exact Pass-1 diagnostic reading in `evidence/h78mghd_holdout_seed20.json` and added unweighted dual fitting (`fit_mghd_dual`) with post-hoc Bayes prior-odds calibration — lifting `seed=20` `HOLDOUT-DTI` to **`0.193393`** (`min_dist=3.01`) / **`0.195210`** (`min_dist=2.8`) and replicating cleanly with **zero retuning** on untouched `seed=30` at **`0.200714`** (`Δ = +0.017282`, 95% CI `[+0.004937, +0.029344]`).
- **`IR-78-VENDOR-UNIQ-01` (Silent Key Mismatch in Shared `vendor/gems57/uniqueness.py`):** Discovered that `compare_array_to_registry()` emitted `'my_dots_within_3px_of_theirs'` without `'forward_overlap'`, causing `binding_duplicate_decision(rows)` to silently return `duplicate=False` when passed raw `compare_array_to_registry` output! Fixed once in `vendor/gems57/uniqueness.py` and logged in `registry/shared_template_review_2026-10-22.json`.
- **`IR-78-VENDOR-UNIQ-02` (One-Sided Spearman Check in `vendor/gems57/uniqueness.py`):** Fixed `'duplicate_by_rho'` to check `abs(rho) > RHO_LIMIT` rather than `rho > RHO_LIMIT`, plus guarded constant-raster `spearman_full_footprint = None` across all 1,103 rasters.
- **File permissions fix:** Normalized `submission_writer.py` output files to `0644` so web servers / artifacts never ship `0600` files.

### Pass 3 — Full End-to-End Requirement, Gate & CI Re-Verification
- Re-verified all JSON artifacts parse with strict `parse_constant` rejection (zero `NaN`/`Infinity` tokens).
- Re-verified `gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.tif` + `.zip` via `scripts/verify_tif.py` (`all_passed: true`), `scripts/audit_release.py`, `scripts/publish_mghd.py`, and the complete `pytest` suite.

---

## 3. Verified Sources, Sandbox Network Scope, Remaining Limitations & Next Steps

### Verified Sources & Reachability Classification
- **Directly fetched & verified inside sandbox (`github.com` / `codeload.github.com`):**
  - Official reference metric & problem repository: <https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b>
  - All `84` accessible `buffedlizard55-lab` repositories pinned by 40-hex commit SHA and 64-hex GeoTIFF SHA-256 in `registry/accessible_registry_2026-10-22.json`.
- **External reference links (not reachable inside sandbox network allowlist — explicitly flagged, never claimed fetched live):**
  - DrivenData Competition 306 portal & submission page: <https://www.drivendata.org/competitions/306/competition-doe-gems/> and <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
  - USGS GeoDAWN airborne magnetic & radiometric release: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
  - NLR / DOE Geothermal technical report: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>

### Remaining Limitations & Concrete Next Steps
1. **Selector Policy Decision Needed on Dense Sibling Priors:** Across all `801` sparse dot submissions (`<= 65,000` positive pixels) in all `84` accessible repos, `H78-MGHD` is **100% unique (`max overlap = 0.6800 <= 0.70`, `max |ρ| = 0.7677 <= 0.90`)** AND strictly dominates historical `H78-A` both on `HOLDOUT-DTI` (`+0.0141` pooled, $>4\sigma$) and on sparse uniqueness (`0.6800` vs `H78-A`'s `0.7690`). Only dense continuous surfaces (`17GEMSDOE`, `1.0000`) and `624k`-pixel wide corridors (`GEMSDOE3`, `0.9158`) trigger the literal `theirs > 0` stop. If the portfolio selector clarifies that uniqueness applies to actually submitted DrivenData entries or sparse `<= 65k` dot lanes (after verifying remaining weekly DrivenData slots), re-emit the identical locked `H78-MGHD` model without the `-DO-NOT-SUBMIT` guard.
2. **Next Scientific Iteration (`H78-SHORE` + `H78-EULER3D`):** Add paleoshoreline iso-contour tangency features (`|\nabla z \cdot \hat{\mathbf{t}}|`) around `1,330 m` (Lahontan) and `1,580 m` (Bonneville) highstands plus 3D Euler structural-index depth filtering to cut false positives on pluvial shorelines in the Carson Sink and Black Rock Desert.
3. **Authenticate Core Stack Against Direct DrivenData Download:** Before any live competition slot is ever consumed externally, hash-compare `data/raw/sample_submission.tif` against a freshly downloaded copy from the login-gated DrivenData data page.
