# GEMSDOE78 — automated submission-readiness review

**Start every session here, then read [the archived user prompt excerpt](PROMPT.md), [current candidate hypotheses](research/2026-10-22-hypotheses.md), and [the historical scientific review](docs/review-release.md).** The complete extremely long user message is present in the conversation, not verbatim in this repo; the sibling list is transcribed in `registry/family_scores.csv`. Maximize P(Win): refuse weak or duplicate slot candidates. Own the Outcome: automate validation and publish an unambiguous status.

## Latest run (2026-10-22): YES to download · **NO to submit**

A new cross-layer RTP-magnetics × gravity × basement-depth profile-step TIFF was independently generated **from the pinned feature stack**, not copied from any earlier submission. [Download the inspection TIFF and see the status at the top of the site](docs/index.html). Name: `gems78-crosslayer-step-20261022T005245Z-bf9c0b4c20-DO-NOT-SUBMIT`; SHA-256: `0b9cbb580dd8f94474744bf87a72abb602403cdccf8c6289bbe9625f4ffe75c3`. Submission note: `NOT OK TO SUBMIT: cross-layer step candidate; inspect negative/duplicate gate in run card.` **Do not upload.**

- **HOLDOUT-DTI** `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives: **0.0478 [0.0366, 0.0589]** (95% spatial-block CI). Historical incumbent on the same seed, but different dot budget: **HOLDOUT-DTI 0.1843 [0.1658, 0.2015]**, same evaluator and withheld count. Descriptive, not a paired difference. The new model fails the holdout gate.
- Registry full-footprint pre-placement surface |Spearman ρ| maximum **0.0492** among nine local comparators; final **99.898%** of its dots fall within 3 px of the SHA-256-pinned dense lattice comparator, above the literal 70% duplicate stop. This is a **literal duplicate witness** even though overlap with earlier H78-A is only 22.03%. Do not silently exempt dense rasters. The nine-comparator audit is NOT a complete sibling inventory. No organizer receipt; no ORGANIZER-CONFIRMED score. Zero weekly slots used.
- Independent [validator output and complete JSON run card](evidence/crosslayer_run_card.json): one float32 band, EPSG:32611, 3730×3292, pinned transform, all finite including the footprint, values in [0,1], zeros outside footprint and on mapped faults; ZIP contains exactly the TIFF. [Machine-readable current status](docs/data/status.json) is a static, not live, snapshot; the consolidated release audit now revalidates **all six** published TIFFs. [This run's three-pass review](research/2026-10-22-run-review.md) and [the concurrent consolidated review](docs/review-2026-10-22.md) record their distinct scopes.
- Review with `.venv/bin/python scripts/publish_crosslayer.py` and `.venv/bin/python scripts/verify_tif.py docs/downloads/gems78-crosslayer-step-20261022T005245Z-bf9c0b4c20-DO-NOT-SUBMIT.tif`. The one-shot `scripts/run_crosslayer.py` intentionally refuses to rerun after its duplicate-stop card exists; to reproduce the experiment, use a separate checkout **from before this run**, with SHA-pinned inputs restored by `bash scripts/restore_data.sh`. No weekly upload. Provenance: owner mirror hashes, not organizer authentication.

## Historical download status: YES to download · NO to submit

**Every TIFF in this repository is downloadable for inspection, and none is approved for a competition slot.**
The automatic release audit overrides previous promotion claims for H78-A and H78-MPC. A later session generated one new inspection raster, H78-SPY, and that file is also blocked: it lost to its holdout control and 92.45% of its dots lie within 3 px of H78-A. Do not rename or perturb a blocked file and call it new.

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

Historical run cards under `evidence/` are preserved, not silently rewritten. Their `promote` verdicts are **superseded** by `evidence/release_audit.json`. They are not current upload authorizations. All remaining historical analyses must be read with the current review.

## Current evidence and disposition

- **H78-MPC HOLDOUT-DTI:** 0.097684 [0.077985, 0.116303] (evaluator `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives). The paired difference against the fold-fair H33 analogue is +0.003823 [−0.012033, +0.019985], not significant. The stored same-instrument repository best is H78-A B3 at 0.184312 [0.165785, 0.201451]; the cross-lane comparison is descriptive, not a paired test.
- **H78-MPC uniqueness:** pre-placement maximum sampled |ρ| = 0.1546 (passes 0.90); one-way forward 3-px overlap = 0.730 against a non-spacefilling registry raster and 0.9914 against the literal all-raster witness (both fail the 0.70 stop threshold). The local 74-raster set is not claimed to be globally exhaustive.
- **H78-A:** current status is **not cleared** because its historical audit covers only three lineage rasters, not the full locally accessible inventory. This is an evidence gap, not a measured duplicate.
- Both historical files pass local format/range checks and remain available for research/education. **No organizer receipt exists; no file in this repo has an ORGANIZER-CONFIRMED score.** The release review itself ran no new model experiment and spent no slot. The later tooth/spy session did run two experiments and wrote one inspection TIFF; that TIFF is the blocked H78-SPY row above, not a clearance.
- **H78-CS (session 3, preregistered `registry/preregistration_h78cs.json`):** 15 along-strike path-integral features on the H78-A stack add nothing on either seed (paired deltas above); its production dots duplicate H78-A (forward 0.8908; score-surface ρ vs control 0.952/0.955). Two transferable measurements: the reproduced A2 control is stable across seeds (B3/44,090: 0.1826 seed 20, 0.1834 seed 30 — the second-seed item in earlier next-work lists, for this model class), and feature-append variants of A2 are the same lane as H78-A and must not be re-proposed as distinct lanes. Full record: `research/h78cs_hypotheses.md`, `evidence/h78cs_*.json`, IR-78CS-01…06.

## Mandatory starting point for every session

Read this README, [PROMPT.md](PROMPT.md), and [the current review](docs/review-release.md) before running experiments. `PROMPT.md` contains an **excerpt**, not the entire user prompt; the sibling ledger is in `registry/family_scores.csv`. Do not claim that this repository contains a verbatim full prompt.

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

## Reproduce the release review

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# Restore pinned inputs; this historical command also fetches large training data:
bash scripts/restore_data.sh
.venv/bin/python scripts/audit_release.py
.venv/bin/python -m pytest -q tests
```

For a format-only review, just the `sample_submission` and `existing_faults` entries in `registry/data_manifest.json` are needed. They were restored and SHA-256 verified in this session. Both historical site generators now end with the common release audit, so rebuilding cannot restore a false green banner.

The audit reports a negative result rather than uploading anything. Missing reference data fails validation closed. No GPU is required for this audit; the official reference implementation also supports CPU training.

## Next work and limitations

1. Resolve the literal duplicate stop condition and assign a single lane before any new experiment. The current review contains three deferred hypotheses, not promised score gains.
2. Build a hash-pinned, complete accessible registry inventory and audit surfaces as well as final dots with the exact requested statistics. Preserve scope: accessible owner repositories are not the organizer's complete submission registry.
3. Then evaluate the top authorized candidate against the current best on matched folds with an independent seed and paired confidence intervals. The existing estimates are single-seed and do not establish live improvement.
4. Obtain organizer receipt evidence and verify the weekly cap through the official submission page before a separate selector considers an upload. No DrivenData connection is available here and the host is outside the sandbox network allowlist.
5. Official literature/rules/data hosts outside GitHub were not fetched. The pinned official reference README was retrieved; mirror hashes establish file identity, not organizer provenance.

Previous reproduction instructions, results, and caveats are retained in [the historical README](research/history/README-before-release-audit.md); its promotion guidance is obsolete.
