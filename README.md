# GEMSDOE78 — automated submission-readiness review

**Start every session here, then read [the complete current request](research/USER_REQUEST_2026-10-22.md), [the current protocol/scientific review](docs/review-2026-10-22.md), [the H78-FW session review](research/2026-10-22-h78fw-run-review.md), and [the historical review](docs/review-release.md).** The full current task text is also embedded at the end of this README. User-reported scores in the archive are not organizer receipts. Maximize P(Win): refuse weak or duplicate slot candidates. Own the Outcome: automate validation and publish an unambiguous status.

**No new nonempty TIFF can pass the literal parallel-run rule as written.** A freshly restored, SHA-pinned GEMSDOE17 probability raster is positive across the entire footprint; every allowed dot has forward overlap **1.0**, above the **0.70** stop limit. The shared template produced a grid-checked impossibility certificate. This is a registry diagnostic, not a competition score.

All **fourteen** downloadable TIFFs (six historical plus the parallel H78-STEP and H78-STEP-FLANK lanes, this session's new H78-FW inspection file generated from the pinned stack — not copied — and five H79 lidar research files fail-closed as unindexed) were independently revalidated, and all fourteen are blocked: **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO.** Format-valid does not mean scientifically eligible or organizer-accepted. This session ran **one** preregistered model experiment (H78-FW, verdict negative), generated one new inspection TIFF, and used zero weekly slots. The prompt supplies no assigned single method paragraph; this session defined one new lane (H78-FW) and stayed inside it. Neither blocker is silently waived.

- **[Current review: proof, ranked hypotheses, fixes and limitations](docs/review-2026-10-22.md)**
- **[Automatic protocol preflight/run card](evidence/protocol_preflight.json)**
- **[Pinned input/witness provenance](registry/preflight_inputs.json)**

Historical evidence below remains useful, but the current protocol certificate takes precedence over every earlier promotion or partial-uniqueness claim.

## H78-FW session artifact (2026-10-22): new unique lane, negative result

This session generated a **new, unique** catalogue-blind flank-warp TIFF from the pinned 19-band stack (new bytes, new method — not a copy, rename, or perturbation of any prior submission). [Lane page with downloads and gates](docs/h78fw.html) · [executive submission guide](docs/h78fw-executive-summary.html) · [run card](evidence/h78fw_run_card.json). Name: `gems78-h78fw-flankwarp-44090dots-20261022T013114Z-21656430-DO-NOT-SUBMIT`; SHA-256: `a18160d5b7d7d28eef47521262e1e3b537d2716960313166e96fab2c0fd617fd`. Submission note (67/140 chars): `NOT OK TO SUBMIT: H78-FW flank-warp inspection; see run card gates.` **Do not upload.**

- **HOLDOUT-DTI** `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives: **0.0482 [0.0363, 0.0607]** — far below the stored same-draw best (H78-A B3/50k **0.1843 [0.1658, 0.2015]**; B3/44k 0.1826 [0.1628, 0.2004]) and significantly below D2.8 on identical folds/terms (paired Δ −0.0437 [−0.0584, −0.0293]). Canary clean (max symmetric AUC 0.5585). Registry comparators reproduced exactly (D2.8 0.0919, H33 0.0037 — H33's collapse is structural: far-field pruning vs near-halo withheld truth). Fails the holdout gate.
- Pre-placement surface |ρ| max **0.2256** vs the dense witness (passes 0.90); final-dot forward overlap **1.0** vs the dense witness (literal duplicate, binding — expected under the proven impossibility certificate) and max **0.4083** vs dot-field rasters (informative reading passes). Verdict **negative**; one experiment charged; zero slots used.
- Hypotheses ranked before implementation: [five candidates](research/2026-10-22-h78fw-hypotheses.md) (flank warp tested; throw-polarity, texture-break, conductivity-edge, stepover deferred). [Preregistration](registry/preregistration_h78fw.json) was written before results. Why-H33 analysis: [docs/why-h33.md](docs/why-h33.md).

## Parallel-session artifact (2026-10-22): historical inspection only

A separate parallel session independently generated a cross-layer RTP-magnetics × gravity × basement-depth profile-step TIFF **from the pinned feature stack**, not copied from any earlier submission. [Download the inspection TIFF and see the status at the top of the site](docs/index.html). Name: `gems78-crosslayer-step-20261022T005245Z-bf9c0b4c20-DO-NOT-SUBMIT`; SHA-256: `0b9cbb580dd8f94474744bf87a72abb602403cdccf8c6289bbe9625f4ffe75c3`. Submission note: `NOT OK TO SUBMIT: cross-layer step candidate; inspect negative/duplicate gate in run card.` **Do not upload.**

- **HOLDOUT-DTI** `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives: **0.0478 [0.0366, 0.0589]** (95% spatial-block CI). Historical incumbent on the same seed, but different dot budget: **HOLDOUT-DTI 0.1843 [0.1658, 0.2015]**, same evaluator and withheld count. Descriptive, not a paired difference. That parallel-session model fails the holdout gate.
- Registry full-footprint pre-placement surface |Spearman ρ| maximum **0.0492** among nine local comparators; final **99.898%** of its dots fall within 3 px of the SHA-256-pinned dense lattice comparator, above the literal 70% duplicate stop. This is a **literal duplicate witness** even though overlap with earlier H78-A is only 22.03%. Do not silently exempt dense rasters. The nine-comparator audit is NOT a complete sibling inventory. No organizer receipt; no ORGANIZER-CONFIRMED score. Zero weekly slots used.
- Independent [validator output and complete JSON run card](evidence/crosslayer_run_card.json): one float32 band, EPSG:32611, 3730×3292, pinned transform, all finite including the footprint, values in [0,1], zeros outside footprint and on mapped faults; ZIP contains exactly the TIFF. [Machine-readable current status](docs/data/status.json) is a static, not live, snapshot; the consolidated release audit now revalidates **all six** published TIFFs. [This run's three-pass review](research/2026-10-22-run-review.md) and [the concurrent consolidated review](docs/review-2026-10-22.md) record their distinct scopes.
- Review with `.venv/bin/python scripts/publish_crosslayer.py` and `.venv/bin/python scripts/verify_tif.py docs/downloads/gems78-crosslayer-step-20261022T005245Z-bf9c0b4c20-DO-NOT-SUBMIT.tif`. The one-shot `scripts/run_crosslayer.py` intentionally refuses to rerun after its duplicate-stop card exists; to reproduce the experiment, use a separate checkout **from before this run**, with SHA-pinned inputs restored by `bash scripts/restore_data.sh`. No weekly upload. Provenance: owner mirror hashes, not organizer authentication.

## Second parallel-session artifact (2026-10-22, merged after the review above): H78-STEP, inspection only

Another parallel session (branch `arena/faf23883-gemsdoe78`) independently implemented the same deferred hypothesis family as a **catalogue-trained learner**: 54 paired cross-strike flank-step (±300/600/1000 m) + cross-layer throw-concordance features (det_elev/rtp/iso_grav_anom/depth_to_base_surf/cond_surf) with the 19 raw bands and zero H78-A feature columns, preregistered in `registry/preregistration_h78step.json` (five ranked hypotheses: `research/h78step_hypotheses.md`). Name: `gems78-h78step-xstrike-44090dots-20261022T011826Z-e6e72188-zeros-DO-NOT-SUBMIT`; SHA-256: `f76ad302fd8889899b1d1c04c340c5beca0dcabea50c63d4100461a0609f8c07`. Submission note (140 chars): `GEMSDOE78 H78-STEP xstrike-step HGB 44090 dots B3; HOLDOUT-DTI 0.1730 s20 vs CTRL 0.1826; NEGATIVE-DUPLICATE-do-not-submit; not a projection`. **Do not upload.** Lane page: [`docs/h78step.html`](docs/h78step.html); card: [`evidence/h78step_run_card.json`](evidence/h78step_run_card.json).

- **HOLDOUT-DTI** `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives, B3/44,090 (matched folds/emitter, paired): candidate **0.1730 [0.1559, 0.1903]** vs reproduced CTRL_A2 **0.1826**, paired Δ −0.0096 [−0.0176, −0.0025]; ablations raw19 0.1586 and STEP-only 0.1199 (candidate beats raw19 by +0.0144 [+0.0031, +0.0257]); far-truth (>10 px) 0.0696 vs 0.0778; 157-feature leakage canary clean (max symmetric AUC 0.6150). Seed 30 was not run (preregistration forbids seed-shopping after a failed seed 20).
- **Duplicate:** continuous score-surface ρ vs control 0.9013 and forward 3-px dot overlap vs H78-A primary 0.8167 (≤0.4527 vs H19-5/D2.8/H33/GEMS70/H78-MPC; pre-placement surface |ρ| ≤ 0.1310 vs the frozen 9-raster registry). Gate 3/8, verdict negative. Versus the cross-layer file above the two step implementations are **not** duplicates of each other (forward overlap 0.1699 / 0.2116, `evidence/h78step_vs_crosslayer_overlap.json`) — the unsigned physics field (HOLDOUT-DTI 0.0478) and the signed-step learner place largely disjoint dots; neither is cleared, and the universal full-support witness above blocks both anyway.
- Format: shared writer + re-read + independent `verify_tif.py` passed (values exactly {0,1}, all finite, EPSG:32611 3730×3292 sample transform). With this merge the consolidated release audit revalidates **all seven** published TIFFs and lists H78-STEP as blocked. Full record: `evidence/h78step_*.json`, IR-78STEP-01…07. Two experiments (holdout, production); zero weekly slots; no ORGANIZER-CONFIRMED score.

## Historical download status: YES to download · NO to submit


- [Download and validation dashboard](https://buffedlizard55-lab.github.io/GEMSDOE78/)
- [Executive submission guide](docs/executive-summary.html)
- [Authoritative machine-readable release card](evidence/release_audit.json)
- [Scientific review, ranked hypotheses, sources and next steps](docs/review-release.md)

| Candidate | Format | Scientific eligibility |
|---|---|---|
| H78-A strike-steered | Automatically revalidated against pinned grid | **Blocked:** only three registry comparators; complete uniqueness not established |
| H78-MPC monogenic phase congruency | Automatically revalidated against pinned grid | **Duplicate / stop:** recorded forward overlap exceeds the literal threshold |
| H78-SPY inspection, 2026-10-21 | Format-valid; independent `verify_tif.py` passed | **Blocked:** HOLDOUT-DTI 0.1808 [0.1623, 0.1985] vs reproduced control 0.1826; paired delta −0.0018 [−0.0069, +0.0037]; forward overlap vs H78-A 0.9245. Filename ends in `DO-NOT-SUBMIT`. |
| H78-CS collinear support, session 3 (merged after this audit) | Format-valid; independent `verify_tif.py` 12/12 passed | **Blocked / duplicate:** HOLDOUT-DTI seed 20 0.1791 [0.1609, 0.1961] vs reproduced control 0.1826, paired delta −0.0035 [−0.0086, +0.0017]; seed-30 replication delta +0.0004 [−0.0053, +0.0058]; forward overlap vs H78-A 0.8908. Note contains `NEGATIVE-DUPLICATE-do-not-submit`. Page: [`docs/h78cs.html`](docs/h78cs.html), card `evidence/h78cs_run_card.json`. |
| H78-STEP cross-strike step-offset, parallel session 2026-10-22 | Format-valid; writer + re-read + independent `verify_tif.py` passed | **Blocked / duplicate:** HOLDOUT-DTI 0.1730 [0.1559, 0.1903] vs matched control 0.1826, paired delta −0.0096 [−0.0176, −0.0025] (evaluator `gems57-pooled-hide-v2`, seed 20, 11,321 withheld); surface ρ vs control 0.9013; forward overlap vs H78-A 0.8167. Filename contains `DO-NOT-SUBMIT`. Page: [`docs/h78step.html`](docs/h78step.html), card `evidence/h78step_run_card.json`. |
| H78-FW broad flank warp, this session | Format-valid; independent `verify_tif.py` 13/13 passed + ZIP roundtrip | **Blocked / duplicate + negative:** HOLDOUT-DTI seed 20 0.0482 [0.0363, 0.0607] vs repo best 0.1843; paired Δ vs D2.8 −0.0437 [−0.0584, −0.0293]; forward overlap 1.0 vs dense witness (binding), 0.4083 max vs dot fields. Filename ends in `DO-NOT-SUBMIT`. Page: [`docs/h78fw.html`](docs/h78fw.html), card `evidence/h78fw_run_card.json`. |
| H78-STEP-FLANK paired flank step, second parallel session 2026-10-22 (renamed at merge) | Format-valid; independent `verify_tif.py` 12/12 passed; values exactly {0,1} | **Blocked / negative + duplicate dots:** HOLDOUT-DTI 0.1662 [0.1483, 0.1852] vs matched control 0.1826, paired delta −0.0164 [−0.0235, −0.0090] (evaluator `gems57-pooled-hide-v2`, seed 20, 11,321 withheld); forward overlap 0.79 vs H78-A lineage and 0.79 vs H78-STEP. Independent replication of the H78-STEP negative with a different operator implementation (±4/±9 px patches, 6 bands). Page: [`docs/h78stepflank.html`](docs/h78stepflank.html), card `evidence/h78stepflank_run_card.json`. |
| **H78-FWTILT 67-feature antisymmetric flank-warp & tilt-block flexure (2026-10-22)** | Format-valid; independent `verify_tif.py` 13/13 passed; values `{0.0, 1.0}` | **Blocked / negative + literal-witness blocked:** Passed all 10 discriminating sparse dot/line comparators (max 3-px forward overlap **0.6542 ≤ 0.70**, max \|ρ\| **0.1188 ≤ 0.90**), verified `CTRL_A2` (**HOLDOUT-DTI 0.182583**) on the `nearest-exact-mask-v2` stack, and beat raw-band `CTRL_A0` on far-truth (`>1 km`, **0.0586 vs 0.0482**), but trailed `CTRL_A2` on pooled holdout (**0.1481 [0.1299, 0.1655] vs 0.1826**, paired Δ **−0.0345 [−0.0453, −0.0227]**) and is blocked by the literal space-filling witnesses (`13GEMSDOE` 0.9967, `17GEMSDOE` 1.0000). Page: [`docs/h78fwtilt.html`](docs/h78fwtilt.html), card [`evidence/h78fwtilt_run_card.json`](evidence/h78fwtilt_run_card.json), report [`research/h78fwtilt_hypotheses.md`](research/h78fwtilt_hypotheses.md). |

Historical run cards under `evidence/` are preserved, not silently rewritten. Their `promote` verdicts are **superseded** by `evidence/release_audit.json`. They are not current upload authorizations. All remaining historical analyses must be read with the current review.

## Current evidence and disposition

- **H78-MPC HOLDOUT-DTI:** 0.097684 [0.077985, 0.116303] (evaluator `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives). The paired difference against the fold-fair H33 analogue is +0.003823 [−0.012033, +0.019985], not significant. The stored same-instrument repository best is H78-A B3 at 0.184312 [0.165785, 0.201451]; the cross-lane comparison is descriptive, not a paired test.
- **H78-MPC uniqueness:** pre-placement maximum sampled |ρ| = 0.1546 (passes 0.90); one-way forward 3-px overlap = 0.730 against a non-spacefilling registry raster and 0.9914 against the literal all-raster witness (both fail the 0.70 stop threshold). The local 74-raster set is not claimed to be globally exhaustive.
- **H78-A:** current status is **not cleared** because its historical audit covers only three lineage rasters, not the full locally accessible inventory. This is an evidence gap, not a measured duplicate.
- Both original historical files pass local format/range checks and remain available for research/education. **No organizer receipt exists; no file in this repo has an ORGANIZER-CONFIRMED score.** The release review itself ran no new model experiment and spent no slot. The later tooth/spy session did run two experiments and wrote one inspection TIFF; that TIFF is the blocked H78-SPY row above, not a clearance.
- **H78-CS (session 3, preregistered `registry/preregistration_h78cs.json`):** 15 along-strike path-integral features on the H78-A stack add nothing on either seed (paired deltas above); its production dots duplicate H78-A (forward 0.8908; score-surface ρ vs control 0.952/0.955). Two transferable measurements: the reproduced A2 control is stable across seeds (B3/44,090: 0.1826 seed 20, 0.1834 seed 30 — the second-seed item in earlier next-work lists, for this model class), and feature-append variants of A2 are the same lane as H78-A and must not be re-proposed as distinct lanes. Full record: `research/h78cs_hypotheses.md`, `evidence/h78cs_*.json`, IR-78CS-01…06.
- **H78-STEP (parallel session 2026-10-22, preregistered `registry/preregistration_h78step.json`):** standalone replacement (not append) of the steered derivatives by 54 cross-strike step/throw-concordance features still loses to CTRL_A2 (−0.0096 paired) and still converges to its dots (forward 0.8167, surface ρ 0.9013) despite zero shared columns — with CS and SPY, the third demonstration that per-pixel feature families on this stack + HGB are one lane, now additionally blocked for every candidate by the full-support witness above. The step block itself is real signal (beats raw19 +0.0144; top canary feature AUC 0.6150; STEP-only far-truth 0.0753 vs CTRL 0.0778). Full record: `research/h78step_hypotheses.md`, `evidence/h78step_*.json`, IR-78STEP-01…07.
- **H78-STEP-FLANK (second parallel session 2026-10-22, preregistered `registry/preregistration_h78stepflank.json`; renamed at merge):** independently implemented the same deferred step hypothesis as 54 paired flank-patch features at ±4/±9 px on six bands (`src/gems78/step.py`) and replicated the H78-STEP negative: HOLDOUT-DTI 0.1662 vs the same control 0.1826 (paired −0.0164, CI excludes 0), tie vs isotropic control, STEP-only second-best on far truth, appending STEP to A2 adds nothing (diagnostic Δ −0.0036, ρ 0.929), flank B5 < B3 for both arms, production dots duplicate H78-A lineage (0.79) and H78-STEP (0.79) while differing from H78-CROSSLAYER (0.17). Also flagged IR-78STEP-01 (this session's numbering): band 6's GeoTIFF description is a magnetic tilt/curvature derivative, not the radiometric total count its code label claims. Full record: `research/h78stepflank_hypotheses.md`, `evidence/h78stepflank_*.json`.

## Mandatory starting point for every session

Read this README, [PROMPT.md](PROMPT.md), and [the current review](docs/review-2026-10-22.md) before running experiments. `PROMPT.md` preserves the earlier excerpt. The **complete current task text** is archived in [research/USER_REQUEST_2026-10-22.md](research/USER_REQUEST_2026-10-22.md) and embedded below for every future session. Its score and access claims are user statements, not independently confirmed evidence. The sibling ledger is in `registry/family_scores.csv`.

### Current user requirements (operational restatement, not verbatim)

- Generate genuinely new, single-band GeoTIFF predictions, never copy or rename an old submission as new. Use the cached feature stack, shared evaluator and writer.
- Remain in one explicitly assigned method lane. This session's prompt did not identify a distinct method paragraph; do not infer permission to mix the two historical lanes.
- Before placement and on final dots, check the complete indexed registry. Rank correlation above 0.90 or **forward** 3-pixel dot overlap above 70% means duplicate: log and stop. Do not substitute mutual overlap or exclude inconvenient comparators.
- Whole-segment buffered hide-and-recover; catalogue-derived features from visible faults only; exact visible-fault mask; pooled DTI with alpha 0.2, beta 0.8 and 300 m triangular kernel. Test each feature alone; AUC above 0.90 blocks pending leakage investigation.
- Every measured competition-performance result must identify HOLDOUT-DTI with evaluator version, withheld positives and 95% CI, or ORGANIZER-CONFIRMED with a submission-page receipt. Unverified owner reports are not confirmed scores; projections are not scores. Diagnostic counts, hashes and overlaps are not DTI scores.
- Propose and rank three to five geological hypotheses before implementation. Name layers, transform, missing-fault mechanism and non-fault mimic. Compare against current best on matched holdout, not only a weak control. No new external-data dependency is viable until availability is verified.
- Stop after three experiments or two hours. Slot selection is separate and must respect a freshly verified weekly cap. No competition upload was authorized or performed here.
- Automatically validate decoded TIFF values, finiteness, footprint, CRS, shape and transform. Give an obvious download/status panel, executive submission guide, unique name, note of at most 140 characters, SHA-256 and final JSON run card.
- Preserve official-source provenance and explicitly flag inaccessible sources and conflicting leaderboard claims. No fabricated acceptance, live feed, literature verification or leaderboard prediction.
- Review in three passes: implementation, defect/edge-case review, and final requirement audit. Open and merge a PR on completion; document limitations and next work.

## Core values

**Maximize P(Win):** prioritize evidence that improves the probability of success, including negative results that save scarce slots. **Own the Outcome:** correct false readiness claims end to end, preserve audit trails, and do not shift automated validation to a human inspector.

## Reproduce the current automatic review

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
# Only 3 pinned inputs; does not restore the 400 MB training stack or use a slot:
.venv/bin/python scripts/preflight.py --restore
# Expected exit code: 2 (BLOCKED, with structured JSON, not a crash).
.venv/bin/python scripts/audit_release.py
.venv/bin/python -m pytest -q tests
```

`--restore` uses the configured GitHub connection and verifies SHA-256 before using mirror bytes. It requires no DrivenData login. All historical site builders finish with the common release audit. The current status is a dated local audit, **not** a live organizer feed. CI repeats the preflight, validators and regression tests without training or uploading. Existing reference TIFFs are small; the probability witness is about 25 MB and is kept out of Git.

The cache fill fix invalidates older unversioned feature caches. Historical holdout results have **not** been rerun after this fix and must not be described as new corrected-model performance.

## Next work and limitations

1. Explicitly resolve the now-proven full-support registry contradiction and assign a single lane before any new experiment. The current review contains three deferred hypotheses, not promised score gains. Do not propose another per-pixel feature family on the 19-band stack + HGB (three attempts converged to the A2 dots); a distinct future lane needs different data (e.g. the manifest's unused 1 m-lidar-derived bands as primary signal), a spatial model class on GPU, or a different emission stratum (IR-78STEP-04, README next-work history).
2. Build a hash-pinned, complete accessible registry inventory and audit surfaces as well as final dots with the exact requested statistics. Preserve scope: accessible owner repositories are not the organizer's complete submission registry.
3. Then evaluate the top authorized candidate against the current best on matched folds with an independent seed and paired confidence intervals. Some lanes have a second draw, but historical holdout estimates do not establish live improvement or validate the corrected cache.
4. Obtain organizer receipt evidence and verify the weekly cap through the official submission page before a separate selector considers an upload. No DrivenData connection is available here and the host is outside the sandbox network allowlist.
5. Official literature/rules/data hosts outside GitHub were not fetched. The pinned official reference README and notebook were retrieved; mirror hashes establish file identity, not organizer provenance.

Previous reproduction instructions, results, and caveats are retained in [the historical README](research/history/README-before-release-audit.md); its promotion guidance is obsolete.


<details>
<summary>Complete task text for this session — read at the start of future work</summary>

> Archived user instructions, not verified competition results. Current audit decisions above take precedence over historical readiness assertions.

# User request — 2026-10-22

The task text below is archived for subsequent sessions. Arena branch-status metadata is not part of the task text. The original Markdown links are preserved.

---

Review the repo.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.  DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.  BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION.  IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.  Read the entire prompt.  A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.

1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.

2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_[holdout.py](http://holdout.py) and submission_[writer.py](http://writer.py). Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.

3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.

4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.

5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.

6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

The following sites should serve as a starting point for understanding how to generate TIF submissions.  These websites are researched, and tested and have generated TIF submissions.  But we need to generate high scoring submissions.

Here are the results from submissions into the competition, separated by ....:

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)

gems-submission-20260925T001403Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)

gems6_hgb88-topk03_33cec71ff0: 0.0286

....

[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)

pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193

pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830

pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)

gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560

....

[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)

gems-submission-20260926T163915Z-237f0063: 0.0343

....

[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)

gems-submission-20260926T175114Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)

lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461

....

[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)

Hedge-v2_submission: 0.1563

....

[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)

2314b599: 0.0107

....

[https://buffedlizard55-lab.github.io/11GEMSDOE/](https://buffedlizard55-lab.github.io/11GEMSDOE/)

gems-structural-area06-v1: 0.0202

....

[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)

r7-nms3-dem10-scarp_0c9199f14e62:0.1294

r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294

....

[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)

gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782

....

[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)

GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020

....

[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)

17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187

....

[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)

H19-C_20260930T212401Z_c11e495e: 0.0297

....

[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)

h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894

h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

....

[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)

h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461

h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921

H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280

h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839

....

[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)

20261001_r13-lattice-s5_v2_nan-outside:0.0904

....

[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)

h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855

h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976

h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360

....

[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)

h19-4-reference-20260930-691e4dfa: 0.1894

....

[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)

h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890

h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan: 0.1859

....

[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)

h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002

h23-b-dti-optimal-emission-10pct-20261002-86176698-nan: 0.0748

....

[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)

h30-arrangement-matched-habitat-20261002-0d4e02e8-nan: 0.1352

....

[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)

h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477

....

[https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/)

dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE26/](https://buffedlizard55-lab.github.io/GEMSDOE26/)

dilcond-oof-v1-20261003-47629f496133-nan: 0.1223

....

[https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/)

topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449

....

[https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/)

d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)

h27-4-solo-d28-20261004-8acb75e1-nan:0.2708

....

[https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/)

h33d-analog-tip-stepover-r30-20261004-cb490425926e: 0.2632

....

[https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html)

h34-scatter-q50-arr-matched-20261004T223317Z: 0.0778

....

[https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html)

h35-06-aaa86efb25-20261004T225420098147Z-candidate: 0.0418

....

[https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)

anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros: 0.2750

....

[https://buffedlizard55-lab.github.io/GEMSDOE37/](https://buffedlizard55-lab.github.io/GEMSDOE37/)

h6-physics-dotted-80k-20261005T055000Z-0bef9211631c: 0.1193

....

[https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html)

D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero: 0.0763

....

[https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html)

xscale-worm-persistence-20261006T000541Z-nan: 0.0581

....

[https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html)

sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan: 0.0424

....

[https://buffedlizard55-lab.github.io/GEMSDOE45/](https://buffedlizard55-lab.github.io/GEMSDOE45/)

h51-km-faultzone-20261006-zeros: 0.0106

....

[https://buffedlizard55-lab.github.io/GEMSDOE49/](https://buffedlizard55-lab.github.io/GEMSDOE49/)

gate_ortho_w0.25-40k-20261006T213721Z-nan: 0.2376

....

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

....

[https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/)

h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan: 0.2708

h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan: 0.2649

h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan: 0.2710

h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan: 0.2707

....

[https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html)

efd28-repro-20261003-1cc7dc534d51-nan: 0.2600

repo-c0-habitat-emission-20261003-a4d439b07426-nan: 0.0041

sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan: 0.0512

wormrank-d28-20261003-59dcaf6dd11d-zeros:0.2560

wormsurv-filter-20261003-921f10960d6e-zeros: 0.0532

xfit-c0-habitat-20261003-ca879db0089a-zeros:0.0439

xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros: 0.0356

....

[https://buffedlizard55-lab.github.io/GEMSDOE46/](https://buffedlizard55-lab.github.io/GEMSDOE46/)

r11f-scarp-radiometric-fusion-00e049b51218-zeros:0.1589

r12-scarp-rad-concordance-23e807e2de9f-zeros: 0.0843

....

[https://buffedlizard55-lab.github.io/GEMSDOE39/](https://buffedlizard55-lab.github.io/GEMSDOE39/)

h40-e-disc-h40e-30k-zeros: 0.0339

....

[https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html)

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1: 0.0355

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1-hard: 0.0397

h45-eulerdepthreadcluster-20261006-f28e5cff6826-zeros: 0.0984

....

[https://buffedlizard55-lab.github.io/GEMSDOE41/](https://buffedlizard55-lab.github.io/GEMSDOE41/)

h42-submission-primary: 0.0245

....

[https://buffedlizard55-lab.github.io/GEMSDOE44/docs/](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/)

h46-twostageAB_20261006T160000Z_b0cfe956-zeros: 0.0715

....

[https://buffedlizard55-lab.github.io/GEMSDOE47/](https://buffedlizard55-lab.github.io/GEMSDOE47/)

h60-lidarscarp-s2p0-20261007-nanoutside: 0.0430

....

[https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html)

h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8: 0.2296

....

[https://buffedlizard55-lab.github.io/GEMSDOE50/](https://buffedlizard55-lab.github.io/GEMSDOE50/)

h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite: 0.0764

....

[https://buffedlizard55-lab.github.io/GEMSDOE51/](https://buffedlizard55-lab.github.io/GEMSDOE51/)

h53-twostage-20261008T040951Z-9a0b32c871: 0.1047

....

[https://buffedlizard55-lab.github.io/GEMSDOE52/](https://buffedlizard55-lab.github.io/GEMSDOE52/)

h97b-candidate: 0.0856

....

[https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html)

h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522-zeros: 0.0159

....

[https://buffedlizard55-lab.github.io/GEMSDOE54/docs/](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/)

h54c-manifest-edge-20261009T025732Z-73454bc5:0.0449

....

[https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html)

tensor_full-n16000-sep3-20261009T211747Z-nan: 0.0290

....

[https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html)

h56-final-dotted-ridge-d2p8-20261009T190421Z:0.0658

....

[https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html)

h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1-zeros: 0.0254

....

[https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html)

ml-binary-ridge-20261012T000000Z: 0.0180

....

[https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html)

h59j-coherence-consensus-dotted-20261011T043000Z: 0.0499

....

[https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html)

h73-chi-coherent-corridor-12000-20261011T195818Z-zeros: 0.0351

....

[https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html)

h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b-zeros: 0.0009

h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea-zeros-zeros:0.0751

....

[https://buffedlizard55-lab.github.io/62GEMSDOE/](https://buffedlizard55-lab.github.io/62GEMSDOE/)

datum-lahontan-strain-gauge-defensible-440dots-zeros: 0.0000

....

[https://buffedlizard55-lab.github.io/GEMSDOE63/](https://buffedlizard55-lab.github.io/GEMSDOE63/)

cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-zeros: 0.2303

....

[https://buffedlizard55-lab.github.io/GEMSDOE64/](https://buffedlizard55-lab.github.io/GEMSDOE64/)

h64-lidar-scarp-cv-20261011T220000Z:0.0383

....

[https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html)

sar-em-propensity-half-20261011T223500Z-5e4660cd-zeros:0.0431

....

[https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html)

gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros:0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE67/](https://buffedlizard55-lab.github.io/GEMSDOE67/)

h67a-orientip-lane-29447dots-20261012T021226Z-allfinite:0.0356

ovtr-ml-cover-tau3p0-20261012-nan:0.1426

....

[https://buffedlizard55-lab.github.io/GEMSDOE68/](https://buffedlizard55-lab.github.io/GEMSDOE68/)

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-nan:0.0437

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-zeros: 0.0437

....

[https://buffedlizard55-lab.github.io/GEMSDOE69/](https://buffedlizard55-lab.github.io/GEMSDOE69/)

h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5:0.0053

....

[https://buffedlizard55-lab.github.io/GEMSDOE70/](https://buffedlizard55-lab.github.io/GEMSDOE70/)

gems70-p5-dual-submod300-oof38k-20261020:0.2478

....

[https://buffedlizard55-lab.github.io/GEMSDOE71/](https://buffedlizard55-lab.github.io/GEMSDOE71/)

gems71-hydro-conduit-38800-20261020T120000Z-zeros: 0.0558

....

[https://buffedlizard55-lab.github.io/GEMSDOE72/](https://buffedlizard55-lab.github.io/GEMSDOE72/)

gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros: 0.0492

....

[https://buffedlizard55-lab.github.io/GEMSDOE73/](https://buffedlizard55-lab.github.io/GEMSDOE73/)

gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE74/](https://buffedlizard55-lab.github.io/GEMSDOE74/)

gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE75/](https://buffedlizard55-lab.github.io/GEMSDOE75/)

gems75-trlt-radon-loco-ridge-20261021-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE76/](https://buffedlizard55-lab.github.io/GEMSDOE76/)

gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros:

gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE77/](https://buffedlizard55-lab.github.io/GEMSDOE77/)

gems85-h85-edti-collar35-skel-r33-20261021-d97b248e-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE78/](https://buffedlizard55-lab.github.io/GEMSDOE78/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE79/](https://buffedlizard55-lab.github.io/GEMSDOE79/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE80/](https://buffedlizard55-lab.github.io/GEMSDOE80/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE81/](https://buffedlizard55-lab.github.io/GEMSDOE81/)

gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE82/](https://buffedlizard55-lab.github.io/GEMSDOE82/)

gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE83/](https://buffedlizard55-lab.github.io/GEMSDOE83/)

gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros:

....

The following is the leaderboard for the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)

See below for more links and information related to the competition:

[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)

[https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)

[https://gbcge.org/current-projects/ingenious/](https://gbcge.org/current-projects/ingenious/)

[https://epsg.io/32611](https://epsg.io/32611)

[https://en.wikipedia.org/wiki/Tversky_index](https://en.wikipedia.org/wiki/Tversky_index)

We need to quickly look at the results and results from the GEMSDOE websites above.

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above.  We need to come up with distinct and unique strategies to score higher in this competition leaderboard.  We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents.  We should store all of our information and knowledge that we can gather from official verified sources.  This will serve as a starting point for other projects as well.  We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for.  So it's important to be contrarian but be smart about it.  We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents.  We need to do deep research and critical thinking and come up with new hypothesis to test.

0.3195	is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website.  It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use.  It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

Review the repo.

The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.

Our Core Values

Maximize P(Win)

“Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.

Own the Outcome

We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.



Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We need to focus on being able to generate a submission into the competition.

The site should be able to generate a TIF file that is required for submission.  It should be as easy as download to click a File to submit into the competition.  This needs to be in the executive summary or the very beginning of the site.  it should be obvious when you visit the site.

I tried to submit the document that i downloaded from the site but it returned this error on the submission form:

"Predicted values must be in range [0, 1]"

Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Here is the submission page when i click submit file

New submission

File to submitNo file chosen

You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.

Note (optional)

A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Create a executive summary subpage that explains exactly how to make a submission into the contest.

Work on the next steps from the previous sessions first.

The goal of this project is to place top of the leaderboard in this competition.  The following is the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)

We need to create a project that can compete and place top of the leaderboard.  We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.

This is the guidelines we need to follow.[https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/)

Get familiar with the problem through the overview and problem description,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). You might also want to reference additional resources available on the about page,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/).

Download the data from the data,[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), tab.

Create and train your own model. This reference solution,[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) implements a simple approach.

Use your model to generate predictions that match the submission format.

Tell me what are you limitations and what you need access to during this project.  We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.

this pdf outlines how submissions must be entered into the competition.

[https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information.  this must be done autonomously and must be constantly reviewed and improved upon.  Provide suggestions and improvements and implement them.

❌ No DrivenData auth → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (verified redirect to login)

See below for links from the above site.  See attached files for links from the above site.

[https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)

Download competition data from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (requires login) to data/

See links below for competition data:

[https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;st=wz4kofki&amp;dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0)

[https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;st=8junzdyw&amp;dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0)

[https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;st=rnino7ya&amp;dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0)

[https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;st=zj1lag1r&amp;dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0)

[https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;st=srhhir10&amp;dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Site creation

Create a github page for this repo that has clean ui, user friendly, simple and easy to use.  It should be organized and clean.

It should include all relevant information in an easy to read format with official verified links as sources for review.  Work line by line verify everything no hallucinations.

**The single remaining blocker to training is data placement**: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).

you need to complete the above task by yourself.  Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Run this task through multiple passes.

Pass 1: Implement the task completely and verify the result.

Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.

Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.

Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request.  Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.  It should be worked on in this next session or the next session.  Work line by line verify everything no hallucinations.

</details>
