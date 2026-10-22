# GEMSDOE78 knowledge store — verified facts only

Every entry carries a provenance class: **MEASURED** (computed in this repo from SHA-256-pinned files; script named),
**OFFICIAL** (organizer / agency document; URL given, fetch status stated), **FAMILY** (a statement from a sibling
GEMSDOE repo — a claim, not independently authenticated), **LITERATURE** (peer-reviewed / agency science, URL given).
This sandbox can only reach github.com, so every non-GitHub URL is listed for *manual* review; none was re-fetched here
unless stated. `registry/sources.json` is the machine-readable twin of this file.

## 1 Competition mechanics

| Fact | Class | Evidence / link |
|---|---|---|
| Grid: EPSG:32611, 3730 × 3292 px, 100 m, transform (100, 0, 243350, 0, −100, 4508550) | MEASURED | read from `data/bridge/sample_submission.tif` (`scripts/verify_tif.py`); CRS definition https://epsg.io/32611 |
| Scoring footprint 5,167,373 px; catalogue 60,988 px in 3,199 8-connected components | MEASURED | `evidence/forensics_h33_vs_d28.json` |
| Metric: DTI = TPw / (TPw + α·FPw + β·FNw), α = 0.2, β = 0.8, triangular kernel k(d) = max(1 − d/300 m, 0) | OFFICIAL (transcribed) | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ; implemented and brute-force-tested in `vendor/gems57/metric.py` |
| Known USGS/INGENIOUS fault pixels are masked from scoring; "new fault" = any fault pixel not already in the catalogue | OFFICIAL (staff posts, FAMILY-fetched) | https://community.drivendata.org/t/11516 , https://community.drivendata.org/t/11536 (quoted in GEMSDOE32 knowledge base, fetched there 2026-10-03) |
| Submission: single-layer 100 m GeoTIFF (or zip), values in [0, 1]; previous portal rejection text "Predicted values must be in range [0, 1]" | OFFICIAL + user report | rules PDF https://docs.nlr.gov/docs/fy26osti/96647.pdf ; prompt (PROMPT.md) |
| Weekly submission cap and single final selection across prize rounds | OFFICIAL | rules PDF §3.4–3.6 (cited via GEMSDOE32 `research/official-rules-review-2026-10-03.md`) |
| Organizer reference solution: U-Net with Monte-Carlo cross-validation (Prof. John Lipor) | OFFICIAL | https://github.com/drivendataorg/gems-prize-reference-solution — README fetched 2026-10-21 |
| Public leaderboard 2026-10-21 (concurrent session's snapshot): #1 xiaofanhu 0.4413, #2 cfld__ 0.3904; prompt's 0.3195 is stale | OFFICIAL snapshot (not a receipt; observed by sibling session, not re-fetched here) | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (login; not reachable here) |

**Metric consequences (derived, MEASURED by algebra on the official formula):** a dot of credit c changes DTI by
≈ (c − 0.2·DTI·(1−c)) / denominator, so an emitted pixel helps only when its max-credit exceeds ≈ 0.2 × DTI (0.032 at DTI 0.16; 0.056 at 0.28). Max-credit per truth pixel means a second dot within 300 m of the same truth adds cost and no credit → sparse dots ≥ 2.83 px apart dominate dense lines (the D1.5 → D2.8 → H33 chain).

## 2 Why H33-2-B2 scored 0.2778 (FAMILY score, MEASURED structure)

* H19-5 solid: 121,131 line pixels, owner-report 0.1922. D2.8: 44,090 binary dots placed on those lines with NN spacing min 2.83 / median 3.0 px, owner-report 0.2600. H33-2-B2: the exact 37,654-dot subset of D2.8 obtained by deleting every dot ≤ 2 px from the catalogue (6,436 dots), owner-report 0.2778. SHA-256s: H33 c55bafc4…, D2.8 91eae1ca…, H19-5 ec1f9b56… (`evidence/forensics_h33_vs_d28.json`).
* The whole 0.19 → 0.28 climb is emission geometry on one unchanged detector. By the formula above, the 6,436 removed near-flank dots earned mean credit < 0.055 each, i.e. less than 40 % of the average dot — the near flank of mapped faults is poor live truth territory.
* Ceiling reasoning: at 0.2778 with ~37.6k dots the average dot credit is ≈ 0.13; to pass 0.32 the same budget needs ≈ 0.16 per dot, which requires a better *ranking* of candidate pixels (detector), not more thinning — hence lane H78 changes the detector and keeps the emission grammar.

## 3 Geology that motivates lane H78

| Fact | Class | Link |
|---|---|---|
| Great Basin geothermal systems concentrate at fault step-overs, terminations, relay ramps and intersections of sub-parallel normal-fault arrays; strands within an array share regional strike | LITERATURE | Faulds et al., OSTI 1110517 https://www.osti.gov/servlets/purl/1110517 |
| GeoDAWN: USGS airborne magnetic and radiometric survey, NW Great Basin (source of the magnetic/radiometric bands) | OFFICIAL | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and |
| INGENIOUS (GBCGE) and the GDR 1391 data package (fault catalogue, geodetic strain, conductivity, basement depth) | OFFICIAL | https://gbcge.org/current-projects/ingenious/ , https://gdr.openei.org/submissions/1391 |
| Catalogue strike field in the footprint is coherent at the 4 km scale (median coherence 0.56 of the σ = 40 px structure tensor) | MEASURED | `evidence/h78_run_card.json["features"]["coherence_median"]` |
| No free public catalogue supplies new faults: GDR QFaults v2 lies within 300 m of the competition catalogue for 59,064 / 59,065 px; SGMC contacts score 0.05 off-catalogue | FAMILY (GEMSDOE32 §7) | GEMSDOE32 knowledge base |

## 4 What this repo measured (HOLDOUT-DTI, evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives)

* Leakage canary clean: max single-feature AUC 0.586 (threshold 0.90).
* A2 steered vs A1 isotropic vs A0 raw-19, all B2 @ 44,090 dots: 0.1586 / 0.1462 / 0.1376; paired Δ A2−A1 +0.0124 [+0.0032, +0.0223]; A2−A0 +0.0210 [+0.0107, +0.0326].
* Flank radius: B3 @ 44,090 = 0.1826 [0.1628, 0.2004], Δ vs B2 +0.0240 [+0.0196, +0.0281]. Candidate dots 2–3 px from visible faults earn mean credit 0.014 (break-even 0.032).
* Far-truth stratum (> 10 px from any visible fault, 5,150 positives): A2 0.066 vs A1 +0.0147 [+0.006, +0.024], vs A0 +0.0283 [+0.017, +0.040]; on par with D2.8.
* Distance-to-catalogue profile of the shipped primary: median 6.0 px, 43 % ≤ 5 px (H33: 19.6 px, 15 %). Open risk IR-78-09.

## 5 H78-MPC audit correction (2026-10-21)

The downloadable H78-MPC raster is **research/education only; not OK to submit**. The measurements below were already present in the repository; this review added no model experiment and spent no submission slot.

* **HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, 11,321 withheld positives, seed 20; 95% CI): H78-MPC spaced candidate 0.0977 [0.0780, 0.1163]. Its paired difference from the fold-fair H33 analogue is +0.0038 [-0.0120, +0.0200], not statistically distinguishable from zero. The no-MPC ablation difference is +0.0121 [+0.0027, +0.0217], a feature-family ablation signal, not evidence that the candidate beats the project's best.
* **HOLDOUT-DTI** (same evaluator/seed/withheld count; 95% CI): highest recorded same-instrument value in the current evidence is `A2_h78_steered|nms0_B3|50000` at 0.1843 [0.1658, 0.2015]. This is a different H78-A arm; its comparison with H78-MPC is descriptive only (no paired cross-lane CI was computed). H78-MPC does not beat the current repository holdout best.
* **REGISTRY-MEASUREMENT:** pre-placement max absolute sampled Spearman rho is 0.1546 (limit 0.90, pass). Final-dot forward overlap within 3 px is 0.730 against the non-spacefilling GEMSDOE70 raster and 0.9914 against the R13 lattice (limit 0.70, both fail). The prior code/card used mutual overlap and an exception for space-filling rasters; that does not implement the literal `PROMPT.md` criterion. The comparison covers 74 locally accessible rasters and is not a global completeness claim. Details: `evidence/h78mpc_uniqueness.json`, `evidence/h78mpc_duplicate_stop.json`, IR-78-14.
* The TIFF itself remains locally format-valid (float32, EPSG:32611, 3730×3292, sample transform, all finite in [0,1], no NaN, nodata=None); that is **not** organizer acceptance or uniqueness clearance. Its local SHA-256 is `c7932fbda98120b5abce37247852220befe1798dac4828fd58f785534e081256`.
* Result: verdict `negative`, `ok_to_download=true` for research only, `ok_to_submit=false`, weekly slots used = 0. The hard duplicate-stop rule means no replacement TIF or further H78-MPC experiment is produced in this review.

## 6 Standing rules for every session
Read PROMPT.md and README.md first. Label every score. Never write a projection as a score. Check the literal forward uniqueness criterion before placement and on final dots. Fix shared tools in the template, never fork. Three experiments or two hours, then stop and write the run card.

## 7 Session 2026-10-21 tooth/spy (MEASURED)

* H78-TOOTH negative. Withheld d/λ p50 0.385; gap1 mean 0.118 on withheld vs 0.191 on background; symmetric AUC 0.514. Learner scores >0.5 on exactly the 48,340 visible training positives. `evidence/h78tooth_negative.json`. IR-78-17.
* H78-SPY HOLDOUT-DTI 0.1808 [0.1623, 0.1985] vs reproduced A2 control 0.1826; paired delta −0.0018 [−0.0069, +0.0037]; evaluator gems57-pooled-hide-v2, 11,321 withheld. Deployment forward 3 px overlap vs H78-A = 0.9245. Verdict negative, duplicate, not OK to submit. `evidence/h78spy_run_card.json`. IR-78-18.
* The inspection builder first stored a boolean NaN check and compared it to 0, so its own `passed` flag was false on a format-valid file. Independent `scripts/verify_tif.py` is the binding pass. IR-78-19.
* GEMSDOE32 page fetched 2026-10-21 says no organiser score exists for H33-2-B2 (IR-78-20). 0.2778 stays an owner-report.
* Control reproduction on sklearn 1.9.1 matched the published B3 budgets: 0.1778 / 0.1826 / 0.1843 at 37,654 / 44,090 / 50,000 dots.

## 8 Session 3 (lane H78-CS, merged after the release audit) (2026-10-21, lane H78-CS) — MEASURED (scripts/run_holdout_cs.py, build_submission_cs.py; evidence/h78cs_*.json)

* Along-strike collinear support (15 path-integral features, 1.1/3.1 km, det_elev/rtp/depth_to_base_surf) added to the 103 H78-A features: HOLDOUT-DTI (gems57-pooled-hide-v2, B3/44,090) seed 20 CAND 0.1791 vs CTRL 0.1826, paired Δ −0.0035 [−0.0086, +0.0017] (11,321 withheld); seed 30 CAND 0.1838 vs CTRL 0.1834, Δ +0.0004 [−0.0053, +0.0058] (11,342 withheld). Effect ≈ 0. Far-truth (>10 px): seed 20 Δ −0.0053 [−0.0102, −0.0005]; seed 30 Δ +0.0038 [−0.0013, +0.0095].
* CTRL_A2 (exact H78-A rerun) reproduces shipped numbers to 4 dp on seed 20 (0.1826/0.1586/0.1843) and gives 0.1834 on seed 30: across-draw point spread 0.001 for this model class.
* Univariate strength does not imply multivariate value: cs_det_elev_gn_L5_mean is the top single feature (symmetric AUC 0.6022 seed 20) yet the 15-feature block adds nothing (ABL raw19+CS B2 = 0.1365 vs raw19 0.1376 seed 20).
* Lane-distance measurement: Cand-vs-Ctrl score-surface Spearman ρ = 0.9520 (s20) / 0.9547 (s30); production dot overlap (≤3 px) vs shipped H78-A primary 0.8908, vs altB2 0.8311, vs H19-5 0.4382, D2.8 0.3982, H33 0.3607, H78-MPC 0.3581; surface ρ vs the same binary rasters ≤ 0.1376. Feature-append lanes on A2 are duplicates of H78-A.


## 9 Session 2026-10-22 lane H78-FW (MEASURED — scripts/run_h78fw.py; evidence/h78fw_run_card.json)

* Catalogue-blind unsupervised surface: detrended-800 m Hessian curvature magnitude corroborated by 300 m RTP+gravity gradient geometric mean; composite sqrt(warp·central); no catalogue input, no learner. HOLDOUT-DTI (gems57-pooled-hide-v2, seed 20, 11,321 withheld, B3/44,090): **0.0482 [0.0363, 0.0607]**. Canary clean (max symmetric AUC 0.5585). Verdict negative.
* Identical-fold comparators reproduce stored values exactly: D2.8 0.0919, H33 0.0037 (paired FW−D2.8 Δ −0.0437 [−0.0584, −0.0293]). H33's near-zero is structural (far-field pruning vs near-halo withheld truth, IR-78FW-02), not a live statement.
* Unsupervised catalogue-blind surfaces cluster ≈0.05 (FW 0.0482, crosslayer 0.0478) vs ≈0.18 for catalogue-trained rankers on this instrument: learning P(fault|features) from the catalogue dominates any single unsupervised physics signal for hide-and-recover.
* Uniqueness: pre-placement surface |ρ| max 0.2256 (pass); final-dot forward 1.0 vs the dense 17GEMSDOE witness (literal duplicate, binding) and ≤0.4083 vs dot-field rasters (informative passes). File `gems78-h78fw-flankwarp-44090dots-20261022T013114Z-21656430-DO-NOT-SUBMIT.tif`, sha256 `a18160d5…`, 13/13 validator checks + ZIP roundtrip. Zero slots used.
* H33 score provenance re-verified via codeload: pinned GEMSDOE32 page says `projected 0.2747; UNSCORED`; prompt figures 0.2778/0.3195/0.4413 stay unreconciled user/owner reports (IR-78FW-01). Data restore survived a gh API 403 via codeload streaming with exact sha256 match (IR-78FW-04).
