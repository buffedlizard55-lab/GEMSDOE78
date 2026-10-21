# Release review — 2026-10-21

## Decision and scope

**Negative. Downloadable historical files are not approved for submission.** No new TIFF, training experiment, or competition upload was performed. The literal duplicate stop rule takes precedence over the request to generate another candidate. A new filename or small perturbation would not solve this scientifically.

The current prompt supplies no identifiable single method paragraph. The repository contains two already-run lanes. This review does not invent a third lane. It audits existing work and corrects publication safety. The original prompt archive is an excerpt, not a full verbatim transcription; the README now makes that limitation explicit.

## Findings verified against checked-in code and evidence

* H78-A's builder checks just three historical rasters (`scripts/build_submission.py:REGISTRY`). This does not establish uniqueness against the full family registry.
* MPC's recorded forward overlaps include 0.9914 against the lattice and 0.7300 against `gems70-p5-submodular-multiphysics-hydro-54000-20261020.tif`. These are **REGISTRY-MEASUREMENTS**, not scores, copied from `evidence/h78mpc_uniqueness.json`. Both exceed the user's literal 0.70 rule, even without relying solely on a dense lattice objection. The previous use of minimum(forward, reverse) is not the requested statistic.
* Independent recheck: downloaded GEMSDOE70 Git blob `cd915f3f67ba82aa7f99412fc10f1586b49bfab1`, SHA-256 `00e8e1cb6ea34dbe2f6dc0ba3b7cc0d8d18ae2b0aaec11552bfa3ef11f1ea9f2`. Exact recomputation confirms MPC forward overlap **0.7300154034099963**, reverse overlap **0.4172777777777778**, and rank correlation **0.03388743035326935**. These are REGISTRY-MEASUREMENTS, not scores. H78-A forward overlap with this comparator is **0.4675890224540712**, which does not establish completeness. See `evidence/rechecked_overlap.json`.
* The MPC evidence itself says `unique_vs_informative_registry: false` and `unique_literal_all_rasters: false`, while its historical run card and site promoted it. The current authoritative gate is `data/release_audit.json`; historical evidence remains unchanged for traceability.
* Preplacement MPC correlations were sampled, not exact full-footprint measurements. H78-A's surface audit has only three comparators. Neither establishes a complete surface audit.
* H78-A selected a flank after inspecting results and ran only one holdout seed. MPC does not demonstrate improvement over the current H78-A best on a matched experiment; their model/evaluation setup differences prevent a direct causal comparison.
* The supplied claim that a GPU is mandatory is incorrect: the official reference README explicitly supports CPU execution. GPU training may be much faster.
* Reopened TIFF format validation is run in this review against hash-verified sample and catalogue mirrors. Mirror hashes prove identity, not organizer authentication. File-format PASS does not override a failed scientific gate.

## H33 explanation: evidence versus inference

The local forensic record compares the H33 binary raster with the D2.8 family raster and documents the sparse-dot geometry and flank pruning. The physical detection evidence still comes from inherited geophysical/topographic structure. Sparse predictions can reduce redundant false-positive mass under the implemented distance-tolerant Tversky metric; deleting poor-credit pixels can improve that ratio without discovering new structure.

This is a plausible explanation of the owner-reported result, not an independently verified causal experiment. Only pixel-exact catalogue cells are masked; near-catalogue dots can still earn credit against unknown faults. The historical narrative's assertion that all near-catalogue predictions earn zero and the claimed proportional mapping from leaderboard score to credit per dot were unjustified. The denominator changes with overlap and coverage, so the metric is not generally linear in mean credit.

The prompt's leaderboard numbers are **unverified user reports**, not ORGANIZER-CONFIRMED receipts. No basis exists here to promise a higher organizer score. A holdout improvement is a testable objective, not a leaderboard projection.

## Ranked hypotheses for a future authorized H78-A experiment

These are untested proposals, not quantified expected gains or claims of novelty across every sibling repository. Local review found these specific interaction tests absent from the current steered-filter pipeline. All reuse the pinned numerical stack, avoiding a dependency on inaccessible external data. They remain deferred by the stop rule and need an explicit lane assignment. Ranking is qualitative scientific judgment, with uncertain transfer to withheld unmapped faults.

| Priority / cost | Layers and transform | Missing-fault mechanism | Named non-fault mimic | Difference from current local code |
|---|---|---|---|---|
| Highest / medium | Magnetics, gravity, depth-to-basement: paired signed cross-strike profiles and estimated step offsets | A buried basement discontinuity may persist where a surface scarp is absent; require compatible subsurface step geometry rather than mere edge magnitude | Intrusive or lithologic contact | Current pipeline uses local steered derivatives; this proposal tests cross-layer profile offset consistency |
| Second / medium | Elevation and basement depth: residualized scarp evidence conditioned on local relief, trained only on visible-fault folds | Low-relief buried strands are suppressed by global ranking; conditional residual ranking could recover weak anomalies | Alluvial-fan incision | Conditions the ranking on relief rather than simply adding derivatives |
| Third / medium-high | Conductivity, radiometric total count, magnetics: asymmetric flank contrast with multiscale persistence | A structural permeability boundary may juxtapose alteration/conductive material even without a mapped topographic break | Clay-rich sediment boundary or saline groundwater | Tests signed asymmetry jointly rather than isolated edge strength; does not equate conductivity with geothermal heat |

### Next experiment, only after stop condition is resolved

Freeze hypothesis one, one emitter and one budget before results. Restore and verify cached feature stack. Withhold complete segments plus buffer, derive strike/context only from visible faults, run each feature alone as a leakage canary (AUC above 0.90 blocks). Use the shared evaluator and writer unchanged. Compare the candidate and current best with identical folds and seeds, pooled HOLDOUT-DTI and paired spatial bootstrap confidence intervals. Require improvement over the current best, not a weaker ablation. Audit the complete indexed registry at the surface stage before dot placement and on final dots, with no forward-overlap exceptions. Stop on duplication; do not consume a slot. Three experiments or two hours maximum.

## Sources and access

| Source | Verification in this review | What it supports |
|---|---|---|
| [Official DrivenData reference repository](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | README retrieved through GitHub API; snapshot `evidence/organizer-reference-README.md` | Reference workflow; CPU/GPU support; data must be obtained separately |
| `registry/data_manifest.json` | Sample and existing-fault mirrors restored with matching SHA-256 | Local grid/catalogue validation, not official-source authentication |
| `evidence/h78mpc_uniqueness.json` | Parsed every recorded comparison row | Historical duplicate evidence, not a newly scanned complete registry |
| `evidence/forensics_h33_vs_d28.json` | Reviewed checked-in measurements | Historical raster geometry, not an organizer receipt |
| [Competition description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Not retrieved: host outside this sandbox's allowlist | Link for later verification; no claim of fresh official verification |
| [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [GDR](https://gdr.openei.org/submissions/1391) | Not retrieved here | No new external-data proposal depends on these being obtainable |

No live leaderboard feed, weekly cap verification, or organizer-authenticated acceptance was implemented. Do not label an owner ledger as organizer-confirmed. A future feed must preserve receipt provenance, retrieval date and failure/stale status, rather than silently presenting old values as current.

## Three passes

1. Audited code and historical measurements; implemented automatic fail-closed release audit and clear downloadable-but-not-submittable pages.
2. Added tests for exact threshold boundaries, asymmetric-overlap failures, file integrity, and rebuild safety. Fixed the verifier so ZIP mismatch also fails the overall result.
3. Rebuilt both historical site generators followed by the common release gate; rechecked outputs and all tests. The post-merge suite reports **21 passed**. Preserved historical evidence without relabelling it as a fresh experiment.
