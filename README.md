# GEMSDOE78 — automated submission-readiness review

## Download status: YES to download · NO to submit

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
| H78-STEP paired flank step, 2026-10-22 (newest generated TIF) | Format-valid; independent `verify_tif.py` 12/12 passed; values exactly {0,1} | **Blocked / negative + duplicate dots:** HOLDOUT-DTI seed 20 0.1662 [0.1483, 0.1852] vs reproduced control 0.1826, paired delta −0.0164 [−0.0235, −0.0090]; forward 3-px overlap 0.79 vs H78-A/H78-CS/H78-SPY (0.33–0.44 vs older registry). Filename ends in `DO-NOT-SUBMIT`. Page: [`docs/h78step.html`](docs/h78step.html), card `evidence/h78step_run_card.json`. |

Historical run cards under `evidence/` are preserved, not silently rewritten. Their `promote` verdicts are **superseded** by `evidence/release_audit.json`. They are not current upload authorizations. All remaining historical analyses must be read with the current review.

## Current evidence and disposition

- **H78-MPC HOLDOUT-DTI:** 0.097684 [0.077985, 0.116303] (evaluator `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives). The paired difference against the fold-fair H33 analogue is +0.003823 [−0.012033, +0.019985], not significant. The stored same-instrument repository best is H78-A B3 at 0.184312 [0.165785, 0.201451]; the cross-lane comparison is descriptive, not a paired test.
- **H78-MPC uniqueness:** pre-placement maximum sampled |ρ| = 0.1546 (passes 0.90); one-way forward 3-px overlap = 0.730 against a non-spacefilling registry raster and 0.9914 against the literal all-raster witness (both fail the 0.70 stop threshold). The local 74-raster set is not claimed to be globally exhaustive.
- **H78-A:** current status is **not cleared** because its historical audit covers only three lineage rasters, not the full locally accessible inventory. This is an evidence gap, not a measured duplicate.
- Both historical files pass local format/range checks and remain available for research/education. **No organizer receipt exists; no file in this repo has an ORGANIZER-CONFIRMED score.** The release review itself ran no new model experiment and spent no slot. The later tooth/spy session did run two experiments and wrote one inspection TIFF; that TIFF is the blocked H78-SPY row above, not a clearance.
- **H78-CS (session 3, preregistered `registry/preregistration_h78cs.json`):** 15 along-strike path-integral features on the H78-A stack add nothing on either seed (paired deltas above); its production dots duplicate H78-A (forward 0.8908; score-surface ρ vs control 0.952/0.955). Two transferable measurements: the reproduced A2 control is stable across seeds (B3/44,090: 0.1826 seed 20, 0.1834 seed 30 — the second-seed item in earlier next-work lists, for this model class), and feature-append variants of A2 are the same lane as H78-A and must not be re-proposed as distinct lanes. Full record: `research/h78cs_hypotheses.md`, `evidence/h78cs_*.json`, IR-78CS-01…06.
- **H78-STEP (2026-10-22, preregistered `registry/preregistration_h78step.json`):** replaced all pointwise derivatives with 54 paired cross-strike flank-step features (±4/±9 px patches; `src/gems78/step.py`). HOLDOUT-DTI 0.1662 vs control 0.1826 (paired −0.0164, CI excludes 0); tie vs isotropic control; STEP-only is second-best on far truth but weak overall; appending STEP to A2 adds nothing (diagnostic Δ −0.0036, ρ 0.929). Its strongest single feature beats every pointwise feature on the canary (AUC 0.6027) yet the field localises worse inside the 300 m kernel. Production dots still land within 3 px of H78-A-lineage dots 79% of the time — four different operators now converge on the same lineaments. Transferable: detection is not the bottleneck, sub-kernel localisation is; flank B5 < B3 for both arms; the A2 control reproduced exactly a third time. Also flagged IR-78STEP-01: band 6's GeoTIFF description is a magnetic tilt/curvature derivative, not the radiometric total count its code label claims. Full record: `research/h78step_hypotheses.md`, `evidence/h78step_*.json`.

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
