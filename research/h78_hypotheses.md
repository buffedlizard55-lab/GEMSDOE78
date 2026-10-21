# Lane H78 — candidate hypotheses (written 2026-10-21, before any holdout result was read)

Every claim below is tagged: **[official]** organizer text, **[measured-here]** reproduced in
this checkout (`evidence/forensics_h33_vs_d28.json`), **[owner-report]** a score copied from the
family's own ledger (never an organizer receipt), or **[inference]**.

## 0. Why `h33-h33-2-b2 … -zeros` is the family's best file (0.2778 [owner-report])

1. **The metric is a budget, not a segmentation score.** [official] DTI = TPw / (TPw + 0.2·FPw +
   0.8·FNw) with a 300 m triangular kernel and *max* credit per truth pixel. Because FNw = |G| − TPw,
   a second dot inside another dot's kernel earns nothing and still pays 0.2. The DTI of a soft field
   is a ratio of two functions that are linear in each pixel value, so for any fixed geometry the
   optimum is a vertex: **every emitted pixel should be exactly 0 or 1**. All three top files are
   binary [measured-here: one distinct positive value, 1.0].
2. **The family's chain of gains is entirely emission-side on one field.** [measured-here] H19-5
   solid = 121,131 line pixels; D2.8 = 44,090 dots, all of them on the H19-5 lines, nearest-neighbour
   spacing min √8 = 2.83 px / median 3.0 px; H33 = an exact 37,654-dot subset of D2.8 whose 6,436
   removed dots all lie 1.0–2.0 px from the catalogue. Owner-reported scores along that chain:
   0.1922 → 0.2600 → 0.2778. Nothing about the detector changed; mass that the metric charges 0.2
   per pixel for was removed.
3. **Why the ≤2 px flank prune helped.** [official, forum 11516] catalogue pixels are masked out of
   scoring; a dot 1–2 px from a mapped trace can only earn credit from an *unmapped* fault within
   300 m of a mapped one. The live gain says that population is thin: hidden faults in the test set
   are mostly > 200 m from the catalogue. [inference] H33's dots sit at median 19.6 px (≈2 km) from
   the catalogue; p10 = 4 px.
4. **What the chain cannot do.** The same field cannot be thinned further for free — the budget is
   near the metric's own break-even (0.2·DTI ≈ 0.056 credit per added dot). To go above 0.2778 the
   *field* must put more kernel credit per dot on unmapped faults. That is a detector problem.
5. **What the registry says about detectors.** Of ~90 owner-reported scores, every physics-first
   field built without learning from the catalogue scored 0.00–0.16; every file ≥ 0.23 is an
   out-of-fold learner trained on the catalogue and emitted as sparse dots. [inference] The hidden
   test faults are drawn from the *same mapping process* as the catalogue (expert mapping of the
   same lidar/geophysics), so the Bayes-optimal field is P(fault | features) learned from the
   catalogue — with the catalogue's *location* kept out of the features (so the model is not paid
   to crowd known traces) and the metric's sparse-dot emission applied.

**Answer to "can we beat 0.2778?"** Only with a field whose top-ranked ~35–45 k dots carry more
credit toward unmapped faults than H19-5's do, validated on a leakage-safe hide-and-recover holdout
against the *same model class under the same emitter*. Nothing in this repository is a leaderboard
projection; the only way to know is an organizer receipt.

## 1. Candidate hypotheses not yet run in the GEMSDOE family

| Rank | ID | Layers | Physical signature / transform | Why it should catch faults *missing* from USGS/INGENIOUS | Named non-fault mimic | How it differs from prior lanes | Expected gain | Cost |
|---|---|---|---|---|---|---|---|---|
| **1 (run)** | **H78-A strike-steered lineament learning** | det_elev (12), rtp (2), iso_grav_anom (13), depth_to_base_surf (15), cond_surf (17), band 6 (radiometric total count); catalogue used **only** for its orientation | Regional structural-strike field φ(x) from the doubled-angle structure tensor of the *visible* catalogue (σ = 4 km); Gaussian derivative filters at σ = 150 m and 300 m projected onto that frame: across-strike 2nd derivative H_nn, along-strike H_tt, across-strike step g_n, \|g_t\|; HGB learner on raw + rotation-invariant + steered features | Basin-and-Range / Walker Lane faults form sub-parallel arrays; the unmapped strand is the one parallel to its mapped neighbours but too subtle (< 5 m scarp, piedmont, intrabasin) for 1:250k compilations. Steering turns "is there a lineament" into "is there a lineament *with the regional structural grain*", which is what an expert does with lidar | Bedding / lithologic contacts and alluvial-fan drainage that also parallel range fronts; dune ridges | Template `strike_zone.py` and lanes h67a-orientip (0.0356), h79-orient (negative) used catalogue strike as a *post-hoc gate or zone*; no lane steered the filter bank as learner inputs, and no lane withheld all catalogue *location* features while keeping its *orientation* | small–moderate | low (done here) |
| 2 | H78-H label-noise-robust (PU) refit | same features | Two-stage "spy" cleaning: fit, drop the top-k % highest-scoring negatives (likely unmapped faults), refit | The catalogue is incomplete by definition, so plain training suppresses exactly the targets | none (modelling change) | h20 nnPU (0.1890) used a different estimator; no iterative negative cleaning in the family | small–moderate | low |
| 3 | H78-B across-strike spacing ("missing tooth") prior | catalogue + any ridge field | Along the strike-normal, dominant spacing of catalogue crossings within ±10 km; candidate gaps at integer multiples, gated by field evidence | Domino arrays have quasi-regular spacing set by brittle-layer thickness | regularly spaced incised drainage, dune fields | h33d tip/step-over (0.2632) and GEMSDOE27 gap closure (0.2449) act *along* strike; this acts *across* strike | low–moderate | medium |
| 4 | H78-C′ cover-regime-specific learners | depth_to_base_surf (15) as the regime switch | Separate models for exposed/piedmont (< 100 m cover) vs basin (> 300 m) | Fault expression changes from scarp to potential-field step under cover | basin facies changes, inversion smoothing | ovtr-ml-cover (0.1426) and GEMSDOE74 tri-regime (unscored) are close; partially tried | small | medium |
| 5 | H78-G 2020 Mw 6.5 Monte Cristo Range coseismic rupture | external: USGS data release of the mapped surface rupture / ARIA InSAR | Rupture traces on largely unmapped Candelaria-system faults inside the footprint | A ruptured-but-uncatalogued fault is exactly hidden truth | none | never fetched by any lane | unknown, local | high; **not obtainable from this sandbox** (only github/pypi hosts reachable) — source: USGS ScienceBase / SRL 92(2A) field response; verify before proposing as viable |

Ranking is by expected DTI gain per unit implementation cost; it is a judgement, not a measurement.

## 2. Validation plan for H78-A (preregistered; see `registry/preregistration.json`)

* Holdout: `vendor/gems57/holdout.buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3)`
  — whole components withheld inside label-blind eroded quadrants, 3-px feature collar, catalogue
  masked pixel-exactly; scored by `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`,
  unmodified, sha256 `ad86640b…`), pooled DTI α 0.2 / β 0.8 / 300 m kernel, 95 % CI by paired
  20-km-block bootstrap.
* Arms (same folds, same emitter, same budget): A0 raw 19 bands (the lineage's base model class);
  A1 raw + rotation-invariant derivatives (controls for "more derivatives"); A2 = A1 + steered
  (the hypothesis). The paired A2 − A1 difference isolates steering.
* Emission: greedy max-score packing at ≥ √8 px (D2.8 geometry) with the ≤ 2 px visible-catalogue
  flank excluded; budget swept 25 k–60 k. Variants on A2 only: flank 0/2/3 px, ridge-NMS on/off.
* Leakage canary: single-feature AUC on withheld truth vs. active background for all 103 features,
  flag > 0.90.
* Uniqueness: Spearman ρ of the final field vs. each registry raster on the footprint, and the
  fraction of final dots within 3 px of D2.8 / H33 / H19-5 positives; stop if ρ > 0.90 or
  overlap > 0.70.

## 3. Outcome (filled in after the runs; all numbers HOLDOUT-DTI, evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives)

* **H78-A supported.** A2 steered 0.1586 vs A1 isotropic 0.1462 vs A0 raw-19 0.1376 (all B2 @ 44,090 dots); paired Δ A2−A1 +0.0124 [+0.0032, +0.0223], A2−A0 +0.0210 [+0.0107, +0.0326]. Both preregistered tests pass; canary clean (max AUC 0.586).
* **Emission.** Flank 3 px beats 2 px by +0.0240 [+0.0196, +0.0281]; dots at 2–3 px from visible faults earn mean credit 0.014 (break-even 0.032). Shipped primary = A2 · B3 · 44,090 dots = **0.1826 [0.1628, 0.2004]** (amendment IR-78-01b). Ridge-NMS hurts above 37 k dots. Budget keeps rising to 50 k (0.1843); 44,090 kept to stay inside the live-validated D2.8 geometry.
* **Far-truth check** (truth > 10 px from any visible fault, 5,150 positives): A2 0.066, Δ vs A1 +0.0147 [+0.006, +0.024], Δ vs A0 +0.0283 [+0.017, +0.040]; on par with D2.8 (+0.005 [−0.004, +0.016]). The steering gain is not a catalogue-halo artefact, but the absolute level far from the catalogue is low for every arm.
* **Open risk IR-78-09:** the shipped field is closer to the catalogue (median 6 px, 43 % ≤ 5 px) than H33 (19.6 px, 15 %). Live score unknown until uploaded.
* H78-H, H78-B, H78-C′, H78-G: **not run** (budget). H78-G needs a USGS/ARIA download that this sandbox cannot reach; confirmed obtainable only in principle.
