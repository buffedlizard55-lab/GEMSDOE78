# GEMSDOE78 — GEMS research and submission project

> **Session status (2026-10-21): NO submission generated; NOT OK TO SUBMIT.** At review start, this checkout contained only the original README. The review added this project brief and one audit note, but no competition rasters, cached feature stack, registry, holdout evaluator, writer, validator, project code, or website. The requested lane paragraph was not identified in the supplied brief. Under the mandatory lane/holdout/uniqueness gates, fabricating a TIFF from guessed values or copying an older raster would be unsafe and would not be a validated submission. No competition slot was used.

Read this standing brief before project work. The current session record and source audit are in [`docs/review-2026-10-21.md`](docs/review-2026-10-21.md).

## Standing project brief

Build an auditable, scientific, repeatable system to identify previously unmapped geological faults in the DOE GEMS Prize area, which may support geothermal and critical-mineral exploration. Optimize the probability of a valid and useful competition result, but do not confuse a model projection or a local holdout with an organizer score. Own failures as well as successes. Use official, publicly available sources where possible and cite claims so they can be checked.

### Non-negotiable parallel-run protocol

1. **One preregistered method lane per session.** Stay inside the assigned method paragraph. Before placement and after placement, compare the candidate raster against every available registry raster: rank-correlation >0.90 or >70% of prediction dots within 3 pixels of one registry raster means duplicate—record and stop. Do not silently switch lanes. If no method paragraph or complete registry is available, stop before experimentation.
2. **Reuse the shared template.** Use its cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; do not create a private fork. The holdout must hide whole fault segments with a buffer, derive catalogue-based features only from visible faults, mask visible faults pixel-exactly, and use pooled DTI with α=0.2, β=0.8, and a 300 m triangular kernel. Fix shared-tool defects in the shared template and report them.
3. **Label every numerical result.** A holdout result must say **HOLDOUT-DTI**, evaluator version, number of withheld positives, and 95% CI. A competition result must say **ORGANIZER-CONFIRMED** and point to a submission-page receipt. A projection is not a score.
4. **Leakage canary.** Test each feature by itself on the spatial holdout first. AUC >0.90 is presumed leakage until investigated and disproved.
5. **Candidate gate.** Before implementation, rank 3–5 testable geological hypotheses. For each, state input layers, targeted physical signature, why it could identify an uncatalogued fault, distinction from prior methods, implementation cost, and any new data requirement. For external data, name an official free source and verify availability. Test the leading candidate on holdout; do not use a competition slot unless it beats the retained holdout best.
6. **Budget and selection.** Stop after 3 experiments or 2 hours. The experimenter must not choose/promote a competition submission; selection is a separate selector step subject to the current weekly cap.
7. **Run card.** Finish each experiment with one JSON card containing hypothesis, mechanism, named non-fault mimic, HOLDOUT-DTI + CI, registry correlation/overlap, raster SHA-256, validator output (no NaN in footprint, values in [0,1], CRS/shape/transform match), unique submission name, ≤140-character note, and `promote` or `negative` verdict. Negative findings are valid deliverables.
8. **Submission file.** A direct-download TIF must be clearly marked both **OK TO DOWNLOAD** and **OK TO SUBMIT** (or inspection-only / not submit). Never label a research/negative raster submit-ready. Validate its actual bytes before linking it.

### Required product direction

The public-facing project should make the executive summary and download/submission path obvious, include a concise how-to for the DrivenData upload form and short note field, provide a clean source/evidence ledger, explain known limitations, and keep any current-results feed timestamped and source-attributed. A file is only a valid submission if it meets the competition's current format requirements and passes the shared local validator. Do not claim that a GitHub Pages site, an inferred score, or a format check is organizer acceptance.

### Anchors and primary sources

- [Competition overview and problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — task, new-fault labels, metric, and submission format.
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/).
- [Competition data download page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — login may be required.
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [USGS GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/).
- [EPSG:32611](https://epsg.io/32611).
- [DOE/NREL GEMS report (PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — check live page and retain a dated receipt before calling a score organizer-confirmed.

## Forensic note: GEMSDOE32 H33-2-B2

The supplied historical result `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is reported in the request as **OWNER-REPORT: 0.2778**; this checkout has no organizer receipt and cannot authenticate that value. The name suffix `zeros` is **not** an all-zero prediction. The public GEMSDOE32 artifact audit describes a binary raster with **37,654 positive pixels** and zero-valued background/fill; its audit reports all pixels within the footprint finite and within [0,1]. Thus “zeros” denotes the raster's outside-footprint encoding variant, not a no-fault prediction.

The same archived audit says H33-2-B2 takes a reported 0.2708 base and deletes candidate dots within 2 pixels of the catalogue, leaving 37,654 dots and none within 100 m or 200 m of the catalogue. Its archived **projected leaderboard DTI is 0.274673**—a projection, not an organizer score. The stored internal diagnostics do not provide the required evaluator version, withheld-positive count, or 95% CI, so they are **not a compliant HOLDOUT-DTI result** under this project's protocol. This gap matters: do not explain 0.2778 as scientifically proven by that local validation. The reported leaderboard result can only be attributed to the actual submission and organizer scoring if a receipt is produced.

A plausible, metric-grounded mechanism is that a sparse, spatially distributed set of high-confidence pixels can earn distance-weighted true-positive credit when within the 300 m triangular tolerance of previously unmapped faults, while the metric weights false negatives four times as heavily as false positives (β=0.8, α=0.2). Pruning dots close to known faults may also shift budget toward off-catalogue terrain. These are mechanisms consistent with the method and published metric, not verified causal explanations for the reported score. The official problem statement says evaluation targets newly identified faults absent from the existing USGS database; it does **not** establish that a particular catalogue-distance rule is generally superior. The archived projection (0.274673) and owner-reported score (0.2778) differ, reinforcing the need for receipts and an appropriately blocked, calibrated holdout.

## Integrity rules for records

- Values in the long historical score lists supplied in the 2026-10-21 request are **OWNER-REPORT** unless an organizer receipt is archived beside them.
- The request contains two different statements for the current leaderboard high score (0.3195 and 0.4413). Neither is treated as current/confirmed here; check and capture the live leaderboard before relying on either.
- A TIF being byte-unique or format-valid is not evidence that it is scientifically useful, not a duplicate, beats holdout, or should be submitted.
- Missing data/authentication are blockers to be reported—not permission to make up values or use a previous submission as a substitute.
