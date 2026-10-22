# Session 2026-10-22 (branch arena/faf23883-gemsdoe78) — why 0.2778, and five ranked hypotheses

Provenance tags: **[measured-here]** computed in this checkout from SHA-256-pinned files
on 2026-10-22, **[official]** organizer/agency text (URL for manual review; this sandbox
reaches github.com / pypi hosts and github.io via the page fetcher only),
**[owner-report]** a score from the family's own ledger in the prompt (never an organizer
receipt), **[inference]** judgement. No number below is ORGANIZER-CONFIRMED for this repo:
nothing built here has been uploaded by this session, and no DrivenData receipt is on file.

## 0. Why `h33-h33-2-b2 … -zeros` is the family's best-listed file (0.2778 [owner-report])

**Irregularity flagged first (IR-78STEP-01).** The source site itself contradicts the
prompt's attribution. The GEMSDOE32 page
(https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html, re-fetched 2026-10-22)
says, verbatim in substance: H33-2-B2 is "projected live DTI 0.2747 (a MODEL, not a
score)" and "NO ORGANISER SCORE EXISTS for this or any artifact in this repository";
its own submission note ends "UNSCORED". Therefore 0.2778 is an **owner-report in the
prompt that is not backed by an organizer receipt on the source site.** It may be a
later upload recorded only in the owner's ledger; from this sandbox it cannot be
verified. All reasoning below is about the *structure* that makes a high score
plausible if the owner-report is real — not proof that it scored 0.2778. The prompt
also lists two different leaderboard highs (0.4413 and 0.3195); neither was fetched
from the login-walled leaderboard here, so neither is ORGANIZER-CONFIRMED in this repo.

**Structure, re-measured here 2026-10-22 [measured-here]** (pinned rasters:
H19-5 `ec1f9b56…`, D2.8 `91eae1ca…`, H33 `c55bafc4…`, catalogue `7ba308cc…`):

* H19-5 = 121,131 line pixels; D2.8 = 44,090 binary dots, **every one on the H19-5
  lines**; H33 = 37,654 dots and an **exact subset of D2.8**. The 6,436 removed dots
  all lie 1.0–2.0 px from the catalogue (median 1.0 px). H33 dots: NN spacing min
  √8 = 2.83 px, median 3.0 px; median distance to catalogue 19.6 px, p10 = 4 px;
  0 dots on the catalogue; values exactly {0, 1}, all finite.

**Why that wins under the official metric [official formula + inference].**
DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw), α = 0.2, β = 0.8, 300 m triangular kernel,
max credit per truth pixel (implemented and tested in `vendor/gems57/metric.py`;
formula source: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
— not re-fetched here, host outside sandbox allowlist).

1. A second dot inside a truth pixel's 300 m kernel adds ~0 credit but still pays the
   0.2 false-positive charge. Dense lines are therefore wasteful; ≥2.83 px spaced
   binary dots are (near-)optimal emission for any fixed ranking — the DTI of a soft
   field is a ratio of functions linear in each pixel value, so the optimum is at a
   vertex (0 or 1).
2. Catalogue pixels are masked from scoring [official forum, family-fetched], so a dot
   1–2 px from a mapped trace can only earn from an *unmapped* fault within 300 m of a
   mapped one. Deleting exactly those 6,436 dots tests that population; the
   owner-reported chain 0.1922 → 0.2600 → 0.2778 along H19-5 → D2.8 → H33 says that
   population's mean credit was below break-even (≈ 0.2·DTI) — i.e. near-catalogue
   dots were cost without credit.
3. **Nothing about the detector changed along the chain.** All three files are one
   field (H19-5) emitted three ways. The climb is emission geometry, not new
   geological detection.

**Can we beat 0.2778? [inference]** Not by thinning H19-5 further — it is already
near the metric's break-even per dot. Beating it requires a *ranking* whose top
~35–45 k dots put more kernel credit on unmapped faults. In this repo the only legal
pre-slot test of that is the buffered hide-and-recover holdout, and the bar there is
the repo best already measured on the same instrument: CTRL_A2 (H78-A steered)
HOLDOUT-DTI 0.1826 [0.1628, 0.2004] at B3/44,090 (evaluator `gems57-pooled-hide-v2`,
seed 20, 11,321 withheld positives; 0.1843 at 50,000 dots), reproduced exactly by a
later session on two seeds (0.1826 / 0.1834). A holdout win is **not** a leaderboard
projection; only an organizer receipt can say whether 0.2778 was beaten.

## 1. Five candidate hypotheses not yet run in this repo, ranked

Ranking = expected HOLDOUT-DTI gain ÷ implementation cost on this 2-CPU / ~4 GB
sandbox, penalised for lane-duplication risk (protocol: rank-ρ ≤ 0.90 and forward
3-px dot overlap ≤ 0.70 vs registry rasters; session-3 measurement showed any
small feature-append *on top of the 103 H78-A features* lands at surface ρ ≈ 0.95 vs
H78-A and dot overlap ≈ 0.89 — the same lane — so candidates below are specified as
**standalone model classes that do not append to A2**). All reuse the pinned 19-band
stack (`data/raw/training_features.tif` sha256 `4371c82e…`, restored and hash-verified
2026-10-22), `vendor/gems57/evaluate_holdout.py` and `submission_writer.py` unmodified.
No candidate needs new external data except #5, which is therefore not viable here.

| # | ID | Layers | Signature / transform | Why it catches *missing* faults | Non-fault mimic | Differs from prior lanes in this repo | Cost |
|---|---|---|---|---|---|---|---|
| **1 (RUN)** | **H78-STEP cross-strike step-offset concordance** | rtp (2), iso_grav_anom (13), depth_to_base_surf (15), det_elev (12), cond_surf (17); visible catalogue for strike angle only | Paired signed cross-strike profiles at ±3/±6/±10 px (300/600/1000 m), tangent-averaged (±3 px), normalised by local (σ=10 px) variability; per-band signed + \|step\|, centre-deviation; explicit cross-layer **concordance**: throw indicator (depth −elev −grav +cond)/4, pairwise signed products, weakest-concordant-component (54 features) + raw 19 bands, HGB learner | A buried/blind normal fault with no scarp still *offsets* basement: basement deepens, gravity and elevation drop, conductive fill thickens on the downthrown side — a broad **step**, not a narrow ridge. Lid­ar/scarp mapping and σ≤300 m ridge filters miss exactly this; a flank-to-flank step at 600–1000 m with multi-physics sign agreement is the buried-fault signature. Catalogue faults used for training also offset basement, so the signature is learnable from visible faults but does not require the fault to be near the catalogue (no location feature) | Intrusive/lithologic contact (magnetic+gravity step, no fault); basin-margin facies change; buried paleochannel (conductivity step) | H78-A: pointwise steered *derivatives* σ=1.5/3 px at the centre pixel (ridge/step at ≤300 m, unnormalised, no flank windows, no concordance). H78-CS: *along*-strike integrals of those derivatives (negative). H78-MPC: contrast-invariant phase edges (no offset amount, no throw direction). No lane here has computed paired flank means or required cross-layer sign compatibility. This is also deferred hypothesis #1 in `docs/review-release.md` — the repo's own stated next experiment | medium (new feature module + unit tests) |
| 2 | H78-RELIEF relief-conditioned residual scarp | det_elev (12), depth_to_base_surf (15) | Within local-relief strata (σ=25 px detrended-elevation range quantiles, strata fit on visible folds only), z-score the steered scarp evidence; learner sees the residual, not the raw amplitude | Global ranking spends the whole dot budget in high-relief range fronts; a weak scarp in a quiet basin is locally anomalous but globally invisible | Alluvial-fan incision in low-relief strata | No conditioning/residualisation anywhere in this repo; HGB could in principle learn the interaction, so expected marginal gain is uncertain — ranked below STEP | medium |
| 3 | H78-CTX km-scale geomorphic setting | all 19 bands | Gaussian context means σ=10/25/50 px (1/2.5/5 km) as setting features (range-front / basin-margin position) with raw19, no steered derivatives | Expert mappers promote a lineament *at* a range front and discount the same lineament mid-playa; per-pixel σ≤300 m features cannot express setting | Basin-margin shoreline benches share the setting | Family ctx lanes (h25-ctx 0.1280 [owner-report]) were standalone fields; not run in this repo. Ranked lower: context is smooth, so it modulates but cannot *localise* a dot to within the 300 m credit kernel | medium |
| 4 | H78-ASYM asymmetric flank persistence | cond_surf (17), tc_totalcount (6), rtp (2) | Signed flank-asymmetry ratio across the strike-normal at 3 scales, required to persist (same sign) across scales | A permeability/alteration boundary juxtaposes conductive or radiometrically distinct material with no topographic break | Clay-rich sediment boundary, saline groundwater front | Partially subsumed by STEP's cond_surf step + concordance — running both would not be independent lanes; kept as the fallback if STEP's concordance block (not its per-band steps) is what fails | medium |
| 5 | H78-G Monte Cristo coseismic rupture | external only | Mapped 2020 Mw 6.5 Monte Cristo Range surface-rupture traces as positive evidence | Ruptured-but-uncatalogued faults are hidden truth by definition | none | Never fetched by any lane | **NOT VIABLE FROM THIS SANDBOX**: needs the USGS ScienceBase data release for the 2020 Monte Cristo Range rupture (https://www.sciencebase.gov/catalog/ — host unreachable here, item ID therefore *not asserted*). Must be downloaded, hashed and licence-checked on an unrestricted machine before being proposed as viable |

Considered and rejected before ranking: any "A2 + extra features" variant (measured
duplicate lane, session 3); PU/"spy" negative cleaning (run: HOLDOUT-DTI 0.1808 vs
0.1826 control, duplicate 0.9245 — negative); across-strike "missing tooth" spacing
(run as H78-TOOTH: mechanism falsified, withheld faults at 0.39 spacings);
cover-regime split learners (family ovtr-ml-cover 0.1426 [owner-report], partially
tried); U-Net à la the organizer reference solution
(https://github.com/drivendataorg/gems-prize-reference-solution) — strongest known
model class but still not trainable + holdout-validatable on 2 CPUs inside the
3-experiment / 2-hour budget; remains the top recommendation for a GPU session.

## 2. Validation plan for H78-STEP (preregistered: `registry/preregistration_h78step.json`)

Seed-20 buffered-component holdout (assert 11,321 withheld), evaluator
`gems57-pooled-hide-v2` unmodified (sha256 `ad86640b…` verified 2026-10-22), arms
CTRL_A2 (103, exact reproduction control) vs CAND_STEP (19 raw + 54 STEP) vs
ABL_A0 (19) vs ABL_STEPO (54); identical training rows / HGB params / B3 greedy
emitter (pool 1.5 M) / budgets (37,654 · 44,090 · 50,000; primary 44,090);
157-feature leakage canary (symmetric AUC ≤ 0.90 blocks); far-truth (>10 px)
secondary stratum; uniqueness vs the frozen 9-raster indexed registry on the score
surface before placement *and* on final dots (literal forward overlap, no
exceptions); surface ρ(CAND, CTRL) on holdout score grids also reported and gated
≤ 0.90. **Promote iff** CAND > CTRL and > 0.1826 with paired 95% CI lower bound > 0
(and, if run, seed-30 replication delta point > 0), canary clean, uniqueness pass,
validator pass. Otherwise verdict **negative**: the new TIF is still written,
downloadable for inspection, bannered OK TO SUBMIT: NO, and no slot may be spent on
it. No number produced is a leaderboard projection.

## 3. Outcome (filled in after the runs, quoted from `evidence/h78step_*.json`)

**Verdict: negative** (run card `evidence/h78step_run_card.json`). Two experiments, as
budgeted/preregistered; all performance numbers HOLDOUT-DTI, evaluator
`gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives, B3/44,090 primary:

* **Exp 1 — holdout:** CAND_STEP **0.1730** [0.1559, 0.1903] vs CTRL_A2 **0.1826**
  [0.1633, 0.2000] vs ABL_A0 (raw19) 0.1586 [0.1396, 0.1777] vs ABL_STEPO (STEP only)
  0.1199 [0.1048, 0.1356]. Paired Δ(CAND−CTRL) = **−0.0096 [−0.0176, −0.0025]** —
  significantly worse than the repo best. Far-truth (>10 px, 5,150 positives): CAND
  0.0696 vs CTRL 0.0778, Δ −0.0082 [−0.0152, −0.0013]. CTRL_A2 reproduced the shipped
  instrument a third time exactly (0.1778 / 0.1826 / 0.1843 / 0.1586 across configs).
* The STEP block is nevertheless real signal, not noise: CAND − ABL_A0 =
  **+0.0144 [+0.0031, +0.0257]** (far-truth +0.0214 [+0.0096, +0.0328]); the strongest
  single feature in the clean 157-feature canary is `xs_det_elev_step3_absz`
  (symmetric AUC 0.6150; canary max overall 0.6150, nothing > 0.90); STEP-only alone
  reaches far-truth 0.0753, close to CTRL's 0.0778 there despite 0.1199 overall.
  Cross-strike steps exist at withheld faults — they are just a *weaker* detector of
  catalogue-like (scarp-bearing) withheld faults than pointwise steered derivatives.
* **Duplicate:** holdout score-surface ρ(CAND, CTRL) = **0.9013** (> 0.90), and
  production dots fall within 3 px of H78-A primary for **0.8167** of dots (altB2
  0.7598, H78-SPY 0.8049, H78-CS 0.8026; ≤ 0.4527 vs H19-5/D2.8/H33/GEMS70/H78-MPC;
  pre-placement surface |ρ| ≤ 0.1310 vs all nine binary registry rasters). CAND_STEP
  shares **zero** feature columns with A2, yet converges to its ranking/dots
  (IR-78STEP-04/05).
* Seed 30 **not run**: the preregistration allows it only after an Exp-1 pass
  (no seed-shopping). **Exp 2 — production:**
  `gems78-h78step-xstrike-44090dots-20261022T011826Z-e6e72188-zeros-DO-NOT-SUBMIT.tif`
  (sha256 `f76ad302…`, 44,090 binary dots, B3; writer + re-read + independent
  `verify_tif.py` 12/12 pass, so the "[0, 1]" portal error cannot fire on its
  values). Gate 3/8. **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO.** 0 slots used;
  ORGANIZER-CONFIRMED: none.

**Interpretation [inference].** (i) The holdout's truth is withheld *mapped* faults,
which are biased toward scarp-expressing strands; a buried-step detector is tested
here mostly on faults that had a scarp to map, so this instrument structurally
favours the scarp/ridge model class (the known holdout-blindness caveat; far-truth
does not rescue CAND either, though STEP-only is competitive there). This caveat
explains part of the gap but does **not** overturn the gate — no live claim can be
made for step-only faults without evidence this instrument cannot supply.
(ii) The catalogue-trained HGB on this 19-band stack is an attractor: append (CS),
reweight negatives (SPY) and full feature replacement (STEP) all return to the A2
ranking. The remaining ways to be both *better* and *genuinely distinct* are new
data (1 m lidar derivatives as primary signal), a spatial model class (U-Net), or a
different emission stratum — ranked in the README's next-work list. H78-RELIEF,
H78-CTX, H78-ASYM and H78-G were **not run** (budget; ASYM is partly subsumed by
STEP's cond step + concordance, which did not rescue the lane).

**Post-merge corrigendum (2026-10-22, at PR merge).** While this session ran, parallel
sessions merged (a) an independent implementation of the same deferred cross-strike-step
hypothesis family — H78-CROSSLAYER, an *unsigned physics-field* concordance with no
learner and no catalogue features, HOLDOUT-DTI 0.0478 [0.0366, 0.0589] per
`evidence/crosslayer_run_card.json` — and (b) a consolidated release audit proving a
stronger form of IR-78STEP-05: a SHA-pinned GEMSDOE17 probability raster is positive
across the *entire* footprint, so **every** nonempty candidate has literal forward
overlap 1.0 > 0.70 (`evidence/protocol_preflight.json`, `docs/review-2026-10-22.md`).
Consequences, none of which change this lane's measurements or verdict: the
consolidated audit (not this lane's site builder) now owns the homepage / executive
summary / status feed, and H78-STEP is integrated into it as a seventh blocked
candidate; the IR-78STEP-03 builder-chain fix is superseded by main's
"audit is the final publication step" design (`scripts/build_site_step.py` now writes
only the lane pages); `vendor/gems57/uniqueness.py` and `scripts/verify_tif.py` were
extended by the parallel sessions *after* this lane's evidence was generated with the
branch-point versions (thresholds 0.90 / 0.70 unchanged; hashes pinned in the
preregistration remain the provenance of `evidence/h78step_*.json`). Dedupe diagnostic
(REGISTRY-MEASUREMENT, `evidence/h78step_vs_crosslayer_overlap.json`): the two step
implementations are not duplicates of each other — forward dot overlap 0.1699 (STEP in
CROSSLAYER) / 0.2116 (reverse), binary surface ρ 0.0148 — but both are blocked
independently and by the universal witness. Selector: dedupe any future "cross-strike
step" assignment against both `evidence/h78step_*` and `evidence/crosslayer_*`.
