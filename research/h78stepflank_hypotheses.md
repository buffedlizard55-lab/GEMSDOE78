# Session 2026-10-22 (branch arena/2a6915e5-gemsdoe78) — why 0.2778, and five ranked hypotheses

> **Merge rename (2026-10-22):** this lane was preregistered and run as "H78-STEP".
> A parallel session (arena/faf23883) independently chose the same top hypothesis,
> lane name and file names and merged first (PR #19; their operator is
> `src/gems78/xstep.py`, HOLDOUT-DTI 0.1730 vs the same control). To preserve both
> records, this session's artifacts were renamed `h78step → h78stepflank` at merge;
> contents are otherwise unchanged. The two implementations independently replicate
> the negative (Δ −0.0096 and −0.0164 vs CTRL_A2) and duplicate each other's dots
> (forward 3-px overlap 0.79). See `evidence/h78stepflank_merge_dedupe.json`.

Provenance tags: **[measured-here]** computed in a GEMSDOE78 checkout from SHA-256-pinned
files, **[official]** organizer/agency text (URL for manual review; this sandbox reaches
only github.com / pypi hosts, so non-GitHub pages were not re-fetched this session),
**[owner-report]** a score from the family ledger in the prompt (never an organizer
receipt), **[inference]** judgement. No number in this repository is ORGANIZER-CONFIRMED:
nothing built here has a submission-page receipt in evidence.

## 0. Why `h33-h33-2-b2 … -zeros` (0.2778 [owner-report]) is the family's best file — and what beating it requires

1. **The metric rewards sparse binary geometry, not coverage.** [official formula as
   implemented in `vendor/gems57/metric.py`] Pooled DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw),
   triangular kernel max(1 − d/300 m, 0), *max* credit per truth pixel. DTI is a ratio of
   functions linear in each pixel value, so at fixed geometry the optimum is binary
   (0 or 1); a non-redundant dot helps only if its realised kernel credit exceeds
   ≈ 0.2·DTI (0.056 at DTI 0.2778); a second dot inside the same truth pixel's kernel
   earns nothing and still costs 0.2. Sparse dots ≥ 2.83 px apart therefore dominate
   solid lines and soft fields. H33 is exactly that [measured-here:
   `evidence/forensics_h33_vs_d28.json`, 37,654 dots, values {0,1}].
2. **The 0.19 → 0.28 family climb is emission on one unchanged detector.**
   [measured-here] H19-5 solid 121,131 line px (0.1922 [owner-report]) → D2.8: 44,090
   dots *on those same lines*, NN spacing min √8 px (0.2600) → H33: the exact subset
   deleting all 6,436 dots within ≤ 2 px of the catalogue (0.2778). No new geology
   entered at either step; each step removed prediction mass the formula charges for.
3. **The flank prune is the chain's only live-tested geological statement.** Catalogue
   pixels are masked from scoring [official, staff posts quoted in
   `research/knowledge.md`], so a dot 1–2 px from a mapped trace can only earn from an
   *unmapped* fault within 300 m of a mapped one. Deleting those dots gained live
   [owner-report], which says that population is thin relative to its cost. In this
   repo's hide-and-recover instrument the same effect is measurable directly
   [measured-here, `evidence/h78_distance_diagnostic.json`]: candidate dots 2–3 px from
   a *visible* fault earn mean kernel credit 0.014, 3–5 px earn 0.032, 5–20 px earn
   0.045–0.047, against a break-even of 0.2·DTI ≈ 0.032–0.037 at this repo's holdout
   operating point. H33's shipped dots sit at median 19.6 px from the catalogue;
   this repo's H78-A at median 6 px — H78-A's field crowds the catalogue far more
   (open risk IR-78-09, still unresolved because H78-A was never uploaded).
4. **Thinning is exhausted; beating 0.2778 is a detector problem.** At 37,654 dots and
   DTI 0.2778 the mean dot credit is ≈ 0.13 [inference on the official formula];
   reaching ≈ 0.32 at the same budget needs ≈ 25 % more kernel credit per dot — i.e. a
   better *ranking* of candidate pixels by true-fault probability, not a better
   emitter. The family ledger supports this [owner-report]: every file ≥ 0.23 is an
   out-of-fold learner trained on the catalogue emitted as sparse dots; every
   no-learner physics field scored ≤ 0.16. The learnable target is
   P(mappable fault | features), with catalogue *location* kept out of the features
   (the H78-TOOTH collapse, `evidence/h78tooth_negative.json`, shows what happens
   otherwise: location proxies let the learner memorise the positives exactly).
5. **Where this repo stands, in HOLDOUT-DTI only** (evaluator
   `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives): H78-A strike-steered
   0.1826 [0.1628, 0.2004] at B3/44,090 (0.1843 at 50,000); its steering gain over the
   isotropic control is real on this instrument (+0.0124 [+0.0032, +0.0223] at matched
   B2). Three later attempts to improve it *by appending features or refitting the same
   stack* all failed and, critically, all produced dots duplicating H78-A
   (H78-CS surface ρ 0.952 / forward overlap 0.8908; H78-SPY forward 0.9245).
   **Lesson: any variant that keeps the 103-feature pointwise stack and adds a few
   columns is the H78-A lane, whatever it is named.** A promotable new lane must
   therefore *replace* the pointwise derivative operator with a different physical
   operator, not augment it. The prompt's leaderboard figures (0.4413 current #1,
   0.3195 in an older paragraph) conflict with each other and are **[owner-report]**;
   the leaderboard requires login
   (https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
   and was not fetched.

**Can a new file beat 0.2778 live?** Only an organizer receipt can say. The honest,
testable objective for this session is narrower: beat this repo's holdout best
(0.1826 at the preregistered primary configuration) with a *different operator* whose
dots are measurably not H78-A's, under the proven sparse-dot emission grammar, and ship
exactly one file whose OK-to-submit status is computed by the gates below.

## 1. Five candidate hypotheses not yet run in this repo, ranked

Ranking = expected HOLDOUT-DTI gain ÷ implementation cost on this 2-CPU / 3.8 GB
sandbox, penalised for lane-duplication risk (surface ρ ≤ 0.90 and forward 3-px dot
overlap ≤ 0.70 vs registry/shipped rasters). All reuse the pinned 19-band stack
(`data/raw/training_features.tif` sha256 `4371c82e…`, restored and verified this
session), `vendor/gems57/evaluate_holdout.py` and `submission_writer.py` unmodified.
No candidate below requires new external data except #5, which is therefore not viable.

| # | ID | Layers | Signature / transform | Why it catches *missing* faults | Non-fault mimic | Differs from H78-A / H78-MPC / H78-CS | Cost |
|---|---|---|---|---|---|---|---|
| **1 (RUN)** | **H78-STEP paired cross-strike flank step** | det_elev (12), rtp (2), iso_grav_anom (13), depth_to_base_surf (15), cond_surf (17), band 6 `tc` (see IR-78STEP-01); visible catalogue for strike angle only | For each band, strike-elongated patch means on the two flanks at ±4 px and ±9 px across strike (along-strike half-lengths 6/12 px): signed step, \|step\|, within-patch-noise-normalised step (t-like), centre-line deviation from the flank midpoint (step vs ridge discriminator), cross-scale step sharpness ratio. 54 features + raw 19, **replacing** all pointwise iso/steered derivatives | A normal fault is a *step* — basement depth, gravity and elevation change level across it and stay changed. Under basin fill the surface scarp (what Hnn detects) disappears, but the basement/gravity step persists and is broad: pointwise derivatives at σ ≤ 3 px see only a weak diffuse gradient, while flank means separated by 0.8–1.8 km measure the actual throw with patch averaging. Covered intrabasin strands are exactly what 1:250k surface compilations miss | Lithologic / intrusive contacts and basin-margin facies changes are also cross-strike level changes with no fault; the learner must separate them using the six-band joint pattern (a fault steps basement+gravity+elevation coherently) | H78-A measures curvature/gradient *at* the pixel; H78-CS integrated the *on-line* response along strike (negative); STEP contrasts the two *sides* — the response need not peak on the line at all. Feature family shares zero columns with the 84 derivative columns of H78-A | low–med |
| 2 | H78-CTX km-scale geomorphic context | all 19 bands + steered responses | Gaussian context means σ = 10/25/50 px (1/2.5/5 km): range-front / basin-margin / array-corridor position | Expert mappers use setting — a lineament at a range front is a fault candidate, the same lineament mid-playa is a shoreline; σ ≤ 300 m features cannot express setting | Basin-margin facies and shoreline benches share the setting | No > 400 m context in any shipped lane here. **Not run:** as an append to A2 it inherits the CS/SPY duplication failure (ρ ≈ 0.95); as a standalone it discards the only validated detector gain (steering). Revisit only as raw+CTX replacement lane | medium |
| 3 | H78-DIST distance-stratified emission prior | visible catalogue + any score field | Multiply scores by a preregistered weight w(d) of distance-to-visible-catalogue peaking at 5–20 px, or equivalently extend the flank cut from 3 px to 5 px | [measured-here] dots at 3–5 px earn 0.032 ≈ break-even while 5–20 px earn 0.045–0.047; a mapper who mapped one strand would usually have mapped a second strand 300–500 m away in the same exposure, so very-near-catalogue evidence is more likely halo/shoulder than a missed fault | Genuine close splays and damage-zone strands do exist near main faults (withheld truth median is 9 px from visible) — over-pruning throws these away | Emission-side, not a detector: **cannot be a lane by itself** (its dots are a reweighting of an existing field → duplicate). Tested this session only as a matched secondary flank sweep (B3 vs B5 on *both* arms), never as the claimed mechanism | low |
| 4 | Cover-regime residualised ranking | det_elev + depth_to_base_surf as regime switch; all bands | Separate learners (or local-percentile re-ranking) for exposed (< 100 m cover) vs buried (> 300 m) regimes | Global ranking is calibrated on high-relief exposed faults and systematically suppresses weak buried anomalies | Basin facies changes; inversion smoothing in the depth surface itself | Partially tried family-wide (ovtr-ml-cover 0.1426, GEMSDOE74 tri-regime unscored [owner-report]); halves training data per regime; distinctness from A2 weak if the same features are kept. Deferred | medium |
| 5 | H78-G 2020 Mw 6.5 Monte Cristo Range coseismic rupture traces | external only | Mapped surface-rupture traces as positive evidence inside the footprint | A ruptured-but-uncatalogued fault is hidden truth by definition | none | Never fetched by any lane. **NOT VIABLE FROM THIS SANDBOX:** needs the USGS ScienceBase data release for the 2020 Monte Cristo Range earthquake surface rupture (https://www.sciencebase.gov/catalog/ — item not asserted here because it could not be fetched or verified; outbound hosts here are github.com/pypi only). Do not propose as viable until downloaded, hashed and licence-checked on an unrestricted machine | high / blocked |

Considered and rejected before ranking: catalogue-location features of any kind
(distance, density, spacing, coherence as learner inputs) — falsified by H78-TOOTH's
exact-memorisation collapse; PU/"spy" negative cleaning — run as H78-SPY, negative and
duplicated H78-A; along-strike path integrals — run as H78-CS, negative on two seeds;
U-Net à la the organizer reference solution
(https://github.com/drivendataorg/gems-prize-reference-solution) — strongest known model
class, but cannot be trained and validated on CPU inside the 3-experiment budget;
recorded again as the top recommendation for a GPU session.

## 2. Validation plan for H78-STEP (preregistered: `registry/preregistration_h78stepflank.json`)

Seed-20 buffered whole-component hide-and-recover, evaluator `gems57-pooled-hide-v2`
unmodified (sha256 `ad86640b…` re-verified this session), strike field and all
catalogue-derived quantities from *visible* faults only, visible faults masked
pixel-exactly. Arms share folds, training rows, HGB hyperparameters and emitter:
CTRL_A2 (103 H78-A features, rerun control), A1_ISO (19 raw + 36 isotropic),
CAND_STEP (19 raw + 54 STEP), ABL_STEPONLY (54 STEP only, mechanism attribution).
Primary configuration: flank B3, 44,090 dots. Secondary: budgets 37,654 / 50,000,
flank B5 on both CTRL_A2 and CAND_STEP, far-truth (> 10 px) stratum. Leakage canary:
single-feature symmetric AUC ≤ 0.90 for all 157 features. Lane-distinctness: score-surface
Spearman ρ of CAND_STEP vs CTRL_A2 on the full footprint must be ≤ 0.90 (the CS lesson),
in addition to the registry surface/dot checks at production.

**Promote iff** CAND_STEP at B3/44,090 beats CTRL_A2 with paired 95 % CI lower bound
> 0 **and** exceeds 0.1826, canary clean, surface ρ vs CTRL ≤ 0.90 — then replicate on
seed 30 (CAND must again exceed CTRL point-estimate). Otherwise the verdict is
**negative**, the file is published for inspection with OK TO SUBMIT: NO, and no seed
shopping is permitted. Full rules in the preregistration JSON.

## 3. Irregularities flagged this session

* **IR-78STEP-01 (band-6 identity).** `src/gems78/data.py` names band 6
  `tc_totalcount`, and earlier repo documents call it "radiometric total count". The
  GeoTIFF's own band description, read this session, says: *"tc - Tilt angle or total
  curvature - magnetic field derivative for edge detection"*. The computation is
  unaffected (the label is only a name), but any geological interpretation of band 6
  as radiometrics in earlier documents is unsupported by the file itself. This lane
  treats band 6 as a magnetic-derivative edge band per the file description. The code
  label is deliberately not renamed mid-family, to keep historical feature names
  byte-stable; the discrepancy is flagged here for the template owner.
* **IR-78STEP-02 (no assigned method paragraph).** As in the CS session, the prompt
  says "your lane is the single method paragraph below" but contains no such
  paragraph. The lane was self-assigned as the top-ranked hypothesis above, written
  before any STEP result. If a parallel session was assigned paired-flank/step
  operators, dedupe against this lane's `evidence/h78step_*` files.
* **IR-78STEP-03 (leaderboard claims conflict).** The prompt states both 0.4413 and
  0.3195 as the current top score. Neither was fetched (login-gated, host outside the
  sandbox allowlist). Both are treated as unverified owner reports; no target in this
  repo depends on either number.

## 4. Outcome (quoted from `evidence/h78step_*.json`; all HOLDOUT-DTI, evaluator gems57-pooled-hide-v2, 11,321 withheld)

**Verdict: negative.** CAND_STEP **0.1662 [0.1483, 0.1852]** vs CTRL_A2 0.1826
[0.1628, 0.2004] at B3/44,090; paired Δ **−0.0164 [−0.0235, −0.0090]** — significantly
worse, not a near miss. Vs A1_ISO Δ −0.0038 [−0.0132, +0.0059] (tie): flank contrast
carries about as much usable signal as isotropic derivatives, less than strike-steered
pointwise derivatives. ABL_STEPONLY 0.1294 [0.1143, 0.1443] overall but second-best on
far truth (0.0726 vs CTRL 0.0778, CAND 0.0620). Canary clean; the single strongest
feature in the whole stack is `step_det_elev_d4_abs` (AUC 0.6027, above H78-A's best
0.5859) — flank steps *detect* well and *localise* poorly: patches ±4–9 px across
strike cannot place a line inside the 3-px credit kernel as precisely as on-line
curvature. Secondary flank B5 hurt both arms (CTRL 0.1779, CAND 0.1600): the 3→5 px
extension suggested by the earlier credit-by-distance diagnostic is falsified.

Experiment 2 (amendment IR-78STEP-A1, diagnostic only): CTRL+STEP (157 features)
= 0.1790, Δ vs CTRL −0.0036 [−0.0104, +0.0031], surface ρ vs CTRL 0.929 — appending
adds nothing and is inside the H78-A lane. STEP signal is largely redundant with
steered derivatives at this localisation precision.

Production file (`gems78-h78step-flankstep-44090dots-20261022T013740Z-5e78c1c6-DO-NOT-SUBMIT.tif`,
sha256 `5ce829b0…`) is format-valid (verify_tif 12/12) but **also fails the literal
uniqueness rule**: forward 3-px dot overlap 0.79 vs H78-A primary / H78-CS / H78-SPY
(0.33–0.44 vs H19-5 / D2.8 / H33 / GEMS70-P5; surface ρ ≤ 0.13 everywhere). Four
different operators in this repo now converge on essentially the same dot set,
because they find the same lineaments. OK TO SUBMIT: NO. No seed-30 run (preregistered
gate); 3 experiments charged; no slot touched.

**Transferable lessons for the next lane:** (1) detection is not the bottleneck —
sub-kernel localisation is; an operator whose response is not maximised *on* the line
pays for it at 300 m tolerance; (2) the dot-overlap rule, not surface correlation, is
the binding uniqueness constraint (surface ρ 0.88 / dot overlap 0.79 here) — a
promotable lane needs dots that are geometrically elsewhere, which in practice means
finding lineaments the H78-A lineage does *not* rank in its top 44k, or placing dots
with a different spatial grammar; (3) flank B3 > B5 and CTRL is stable
(0.1826/0.1778/0.1843 reproduced exactly a third time) — the instrument is solid;
(4) the strongest untried direction remains a learned segmentation model
(U-Net class, organizer reference) on GPU, preregistered fresh — every HGB variant on
hand-crafted per-pixel features in this repo now saturates at the same dot set.
