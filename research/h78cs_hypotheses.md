# Session 3 (2026-10-21, branch arena/431f4c40-gemsdoe78) — why 0.2778, and five ranked hypotheses

Provenance tags: **[measured-here]** computed in a GEMSDOE78 checkout from SHA-256-pinned
files, **[official]** organizer/agency text (URL for manual review; this sandbox can only
reach github.com / pypi hosts, so non-GitHub pages were not re-fetched this session),
**[owner-report]** a score from the family's own ledger in the prompt (never an organizer
receipt), **[inference]** judgement. No number below is ORGANIZER-CONFIRMED for this repo:
nothing built here has been uploaded.

## 0. Why `h33-h33-2-b2 … -zeros` (0.2778 [owner-report]) is the family's best file

This restates the prior session's forensics (`evidence/forensics_h33_vs_d28.json`,
`research/h78_hypotheses.md` §0), which this session re-verified as internally consistent
with the pinned rasters restored today (H33 sha256 `c55bafc4…`, D2.8 `91eae1ca…`,
H19-5 `ec1f9b56…`, all OK in `scripts/restore_data.sh` output):

1. **The metric pays for geometry, not for coverage.** [official] Pooled DTI
   = TPw / (TPw + 0.2·FPw + 0.8·FNw), triangular kernel max(1 − d/300 m, 0), *max* credit
   per truth pixel. Since FNw = |G| − TPw, DTI is a ratio of functions linear in each pixel
   value, so the optimum at fixed geometry is binary (0 or 1); a dot helps only if its
   realised max-credit exceeds ≈ 0.2·DTI (0.056 at DTI 0.2778); a second dot inside the same
   truth pixel's kernel earns nothing and still costs 0.2. Hence sparse binary dots
   ≥ 2.83 px apart dominate both solid lines and soft fields. H33 is exactly that
   [measured-here: 37,654 dots, values {0,1}].
2. **The whole 0.19 → 0.28 climb is emission on one unchanged detector.** [measured-here]
   H19-5 solid 121,131 line px (0.1922 [owner-report]) → D2.8: 44,090 dots *on those same
   lines*, NN spacing min √8 px (0.2600) → H33: the exact subset deleting all 6,436 dots
   within ≤ 2 px of the catalogue (0.2778). No new geology entered; pure removal of mass
   the formula charges for.
3. **The flank prune is the only live-validated geological statement in the chain.**
   [official, staff posts quoted in `research/knowledge.md`] catalogue pixels are masked
   from scoring, so a dot 1–2 px from a mapped trace can only earn from an *unmapped* fault
   within 300 m of a mapped one. The live gain from deleting them says that population is
   thin: hidden test faults are mostly > 200 m from the catalogue. H33's dots sit median
   19.6 px (≈2 km) from the catalogue [measured-here, prior session].
4. **Why thinning is exhausted, and what beating 0.2778 requires.** [inference on the
   official formula] At 37,654 dots and DTI 0.2778 the mean dot credit is ≈ 0.13; reaching
   ~0.32 at the same budget needs ≈ 0.16 — a ~25 % better *ranking* of candidate pixels by
   true-fault probability. That is a detector problem, not an emitter problem. The family
   ledger supports this: every file ≥ 0.23 [owner-report] is an out-of-fold learner trained
   on the catalogue emitted as sparse dots; every no-learner physics field scored ≤ 0.16.
   The hidden faults were presumably mapped from the same data by the same process that
   made the catalogue, so the learnable target is P(mappable fault | features) — with
   catalogue *location* excluded from features so the model must learn the signature, not
   the halo.
5. **Where this repo already stands.** [measured-here] Lane H78-A (strike-steered pointwise
   derivatives → HGB → B3 dots) reached HOLDOUT-DTI 0.1826 [0.1628, 0.2004] (evaluator
   gems57-pooled-hide-v2, seed 20, 11,321 withheld), beating its isotropic control by
   +0.0124 [+0.0032, +0.0223] at matched B2 emission; lane H78-MPC (monogenic phase
   congruency, LOQO) reached 0.0977 with a significant MPC ablation. Neither has an
   ORGANIZER-CONFIRMED score. The prompt's leaderboard figures (0.4413 current #1; 0.3195
   in an older paragraph) are **[owner-report/prompt claims]**, not re-fetched here
   (leaderboard requires login: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

**Can a new file beat 0.2778 live?** Only an organizer receipt can say. What can be done
here is narrower and honest: beat this repo's holdout best (0.1826) with a mechanism that
also makes live sense (far-from-catalogue truth included), keep the proven emission
grammar, and ship a file whose OK-to-submit status is computed, not asserted.

## 1. Five candidate hypotheses not yet run in this repo, ranked

Ranking = expected HOLDOUT-DTI gain ÷ implementation cost on this 2-CPU / 3 GB sandbox,
penalised for lane-uniqueness risk (ρ ≤ 0.90, 3-px dot overlap ≤ 0.70 vs shipped rasters).
All five reuse the pinned 19-band stack (`data/raw/training_features.tif` sha256
`4371c82e…`), `vendor/gems57/evaluate_holdout.py` and `submission_writer.py` unmodified.

| # | ID | Layers | Signature / transform | Why it catches *missing* faults | Non-fault mimic | Differs from H78-A / H78-MPC | Cost |
|---|---|---|---|---|---|---|---|
| **1 (RUN)** | **H78-CS collinear support** | det_elev, rtp, depth_to_base_surf; visible catalogue for strike angle only | 1.1 km & 3.1 km along-strike path means of σ=3 px steered \|Hnn\|, \|gn\| + weaker-side continuation statistic (15 features) added to the 103 H78-A features | Faint piedmont/intrabasin strands below per-pixel threshold still integrate coherently over 1–3 km; matched-filter SNR gain | Lahontan shorelines (topo line, no mag/basement step — hence 3 physics kept separate for the learner) | Both shipped lanes are pointwise (σ ≤ 4 px); no along-strike integration anywhere in this repo; family worm/radon used continuity standalone, never ablated as learner features vs identical control | low–med |
| 2 | H78-H PU "spy" cleaning | same 103 features | fit → drop top-scoring negatives (likely unmapped faults) → refit (prior session's unrun rank-2) | Catalogue incompleteness puts true faults inside the negative class, teaching the model to suppress exactly the target signature | — (modelling change; risk is instead self-confirming drift) | No iterative negative cleaning in repo (h20 nnPU family-wide used a different estimator) | low — **but surface ρ vs H78-A likely > 0.90 → duplicate-lane risk; not run as this session's lane** |
| 3 | H78-CTX km-scale context | all 19 bands + steered responses | Gaussian context means σ = 10/25/50 px (1/2.5/5 km) as extra features: range-front / basin-margin / fault-array-corridor position | Expert mappers use geomorphic setting (a lineament *at a range front* is a fault candidate; the same lineament mid-playa is a shoreline); per-pixel σ ≤ 300 m features cannot express setting | Basin-margin facies/shoreline benches share the setting | No > 400 m context features in either shipped lane (family ctx lanes h25-ctx 0.1280, autoctx 0.0437 [owner-report] were standalone fields, not A2+context ablations) | medium |
| 4 | H78-B across-strike "missing tooth" | visible catalogue + any score field | dominant across-strike catalogue spacing within ±10 km; bonus where a gap ≈ integer multiple coincides with field evidence | Domino-style normal-fault arrays have quasi-regular spacing set by brittle-layer thickness; the missing strand sits in the over-wide gap | regularly spaced drainage / dune ridges | h33d & GEMSDOE27 act *along* strike (tips/gaps); this acts *across* strike; introduces a catalogue-location-derived feature (visible-only + buffer discipline required) | med–high |
| 5 | H78-G Monte Cristo coseismic rupture | external only | mapped 2020 Mw 6.5 surface-rupture traces as extra positive evidence inside the footprint | ruptured-but-uncatalogued faults are hidden truth by definition | none | never fetched by any lane | **NOT VIABLE FROM THIS SANDBOX**: needs a USGS ScienceBase / journal-supplement download; outbound hosts here are github.com/pypi only, and no SHA-pinned GitHub mirror of that dataset exists in either repo manifest. Specific source to obtain on an unrestricted machine: the USGS ScienceBase data release for the 2020 Monte Cristo Range earthquake surface rupture (search https://www.sciencebase.gov/catalog/ — item ID *not* asserted here because it could not be fetched/verified; do not propose as viable until downloaded, hashed and licence-checked) |

Considered and rejected before ranking: cover-regime split models (family ovtr-ml-cover
0.1426 [owner-report], GEMSDOE74 tri-regime unscored — partially tried, lane-distinctness
weak); "add the external lidar/radiometric bands" (already inside H78-MPC's 48-band base
in this repo — not new); submodular/DTI-optimal re-emission of an existing field (family
live results 0.07–0.25 [owner-report], all ≤ their input fields — emission on an old field
is the exhausted direction of §0.4); U-Net à la the organizer reference solution
(https://github.com/drivendataorg/gems-prize-reference-solution) — the strongest known
model class, but no GPU here and a CPU U-Net cannot be trained+validated inside the
3-experiment / 2-hour budget; recorded as the top recommendation for a GPU session.

## 2. Validation plan for H78-CS (preregistered: `registry/preregistration_h78cs.json`)

Seed-20 buffered-component holdout, evaluator gems57-pooled-hide-v2 unmodified (sha256
`ad86640b…` verified today), arms CTRL_A2 (103) vs CAND_CS (103+15) vs ABL_A0CS (19+15),
identical training rows / HGB params / B3 greedy emitter (pool 1.5 M) / budgets
(37,654 · 44,090 · 50,000; primary 44,090), 118-feature leakage canary (symmetric AUC
≤ 0.90), far-truth (> 10 px) secondary stratum, uniqueness vs six registry/shipped
rasters on surface *and* final dots. Promote iff CAND > CTRL and > 0.1826 with paired
95 % CI lower bound > 0, canary clean, uniqueness pass, validator pass. Otherwise the
verdict is **negative** and the file is published for inspection with OK TO SUBMIT: NO.

## 3. Outcome (quoted from `evidence/h78cs_*.json`; all values HOLDOUT-DTI, evaluator gems57-pooled-hide-v2)

**Verdict: negative** (run card `evidence/h78cs_run_card.json`). Three experiments, as budgeted:

* **Exp 1 — seed 20 (11,321 withheld positives), B3/44,090:** CAND_CS **0.1791** [0.1609, 0.1961]
  vs CTRL_A2 **0.1826** [0.1628, 0.2004] vs ABL_A0CS 0.1634 [0.1453, 0.1816]; paired
  Δ(CAND−CTRL) = **−0.0035 [−0.0086, +0.0017]**. Far-truth (> 10 px, 5,150 positives):
  CAND 0.0725 vs CTRL 0.0778, Δ −0.0053 [−0.0102, −0.0005] (significantly worse).
  The CTRL rerun reproduces the shipped H78-A evidence exactly (B3 0.1826, B2 0.1586,
  B3@50k 0.1843), so the instrument is not the explanation. Canary clean (max symmetric
  AUC 0.6022 — `cs_det_elev_gn_L5_mean`, the single strongest feature univariately, yet
  multivariately redundant). Score-surface Spearman ρ(CAND, CTRL) = **0.9520**.
* **Exp 2 — seed-30 replication of the negative (amendment IR-78CS-01, declared before the
  run; could not promote):** 11,342 withheld; CAND **0.1838** [0.1628, 0.2048] vs CTRL
  **0.1834** [0.1622, 0.2049]; Δ **+0.0004 [−0.0053, +0.0058]**. Two-seed paired deltas:
  −0.0035 and +0.0004 → the collinear-support effect on this model class is ≈ 0.
  CTRL_A2 across seeds: 0.1826 / 0.1834 (the repo's first across-seed spread for its best
  model; block-bootstrap CIs within a draw are ~±0.02, the across-draw point spread is 0.001 —
  paired deltas remain the right comparator). ρ(CAND, CTRL) seed 30 = 0.9547.
* **Exp 3 — production:** `gems78-h78cs-collinear-44090dots-20261022T002927Z-0ca477e0-zeros.tif`
  (sha256 `5fa189f6…`, 44,090 binary dots, B3). Gate: 2/6 pass (canary, validator);
  fails candidate-beats-control, beats-0.1826, paired-CI, **and uniqueness**: 89.1 % of its
  dots lie within 3 px of the shipped H78-A primary (0.8311 vs altB2; ≤ 0.4382 vs
  H19-5/D2.8/H33/H78-MPC; max surface |ρ| 0.1376) — a duplicate lane by protocol rule #1.
  Independent verifier: 12/12 pass (portal-safe format), but **OK TO SUBMIT: NO**.
  Two production builds produced byte-identical rasters (same sha256; the first crashed
  after the writer committed — orphan trio hashed, removed, rerun; `evidence/h78cs_build.log`).

**Interpretation [inference]:** straight along-strike means are (near-)linear re-summaries of
evidence the σ = 3 px steered derivatives already give the HGB at every pixel of the strand,
so they add split competition without new information; where the σ = 40 px strike field is
extrapolated far from the catalogue the straight-tangent path also leaves curved strands.
Continuity may still matter, but it needs a model class that *uses* spatial structure
nonlinearly (U-Net / path-openings with curvature), not 15 more per-pixel columns.
H78-H (PU cleaning), H78-CTX (km-scale context), H78-B (spacing) and H78-G (Monte Cristo,
still not obtainable here) were **not run** (budget).
