# Why h33-h33-2-b2 scored 0.2778, and what beating it requires

All live scores below are **ORGANIZER-CONFIRMED as user-reported receipts** (copied from the
user's ledger of submission-page results, 2026-10-21). All holdout numbers are **HOLDOUT-DTI**
on `gems57-pooled-hide-v2` (seed 20, 11,321 withheld positives) measured in this repo unless
marked sibling-published. Projections are labelled MODEL and never written as scores.

## The scoring law (verified)

DTI(α=0.2, β=0.8, R=300 m triangular) per the organiser problem description
(DrivenData #306, page 967). Binary-dot algebra (`vendor/gems57/metric.py`, tested vs brute force):

`DTI = T / (0.2·(T + n − M) + 0.8·|G|)`, and one more non-redundant dot helps iff `k > 0.2·DTI`.

At 0.2778 the bar is **0.0556 expected kernel credit per dot**. DTI is therefore a *budget-allocation*
problem first and a *detection* problem second: ranking quality at the emitted mass is everything.

## The live-score ladder that explains H33 (user-reported)

| Step | Submission | Live | Lesson |
|---|---|---|---|
| continuous parent | h19-5 powerlaw-budget multiline-corroborated | 0.1922 | best continuous parent surface of the era |
| dot it, d=1.5 | h25-1-dotted-h19-5-d1-5 | 0.2477 | thinning alone: +0.0555 |
| dot it, d=2.8 | dotted-h19-5-d2-8 | 0.2600 | spacing ≈ kernel packing: +0.0123 |
| solo d2.8 re-emit | h27-4-r1-solo-d2-8 | 0.2708 | cleaner emission of same geometry |
| **+ B=2 flank prune** | **h33-h33-2-b2 (37,654 dots)** | **0.2778** | deleting zero-credit on/near-catalogue mass: +0.0070 |
| near-clone variant | anderson-geothermal-pinn-38854 | 0.2750 | confirms the basin: H33-neighbourhood ≈ 0.27–0.28 |
| divergent lanes (lidar, Euler, radon, SGMC-pure, hydro, ensembles…) | ~40 submissions | 0.001–0.16 | new *detectors* so far have all had lower credit density than h19-5 |

Three multiplicative ingredients: **(1) parent credit density** (multi-physics lineament *corroboration*,
not any single transform), **(2) kernel-matched dotted emission** at the empirically optimal mass
≈37–39k dots, **(3) catalogue-flank exclusion** (organiser masks mapped faults pixel-exactly, so
on/near-catalogue dots pay 0.2 and earn 0).

## What beating 0.2778 (and the user-reported 0.4413 leaderboard top) requires

At fixed mass 37,654, score ≈ mean realised credit per dot. Leaderboard 0.4413 ⇒ ≈59% higher mean
credit/dot than H33. No emission trick supplies that; only a ranking whose top 37k cells are
genuinely closer to the hidden faults. The sibling holdout tournament (GEMSDOE73: 0.1599 vs 0.0939
control; GEMSDOE77: up to 0.1900 single-seed — all HOLDOUT-DTI, none organizer-scored) shows the
ingredients that raise holdout credit density: supervised LOQO models **with visible-fault-network
context features** + exact 300 m submodular allocation. Whether holdout gains transfer to live is
unproven until a selector spends slots on them.

## This lane's measured contribution (HOLDOUT-DTI, this repo)

- MPC features add real signal: E2−E1 paired Δ = **+0.0121 [0.0027, 0.0217]** (spaced emission;
  +0.0105 [0.0029, 0.0187] under the original emitter — emitter-independent), surface AUC vs withheld
  0.696 vs 0.674 without them.
- **IR-78-EMIT-01:** Pass 1's preregistered allocator emitted contiguous dot runs (98.9% of dots with a
  neighbour ≤1.5 px; control median spacing 3.16 px), scoring E2 = 0.0471 ≈ random. Re-emitting the
  frozen surfaces with the control's spaced emitter (Pass-2 defect correction, no retraining) gives
  E2 = **0.0977 [0.078, 0.116]** vs control 0.0939 [0.080, 0.107] — paired Δ +0.0038 [−0.012, +0.020],
  a point-estimate win that is **not statistically significant**. Emission geometry was worth ~2× the
  detector effect — the sharpest confirmation yet of the H33 ladder's lesson (2).
- Verdict: **promote** under the preregistered gate with the corrected emission, caveats disclosed in
  the run card. Rational next test (new preregistration required): MPC features *added to* a
  visible-network-context LOQO model (the sibling 0.16–0.19 holdout recipe) with per-quadrant mass
  quotas — E2 still allocates 13,325 dots to SW vs 4,543 to NE (control: 10,596/10,203).
