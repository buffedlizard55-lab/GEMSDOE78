# GEMSDOE78 — Lane H78: strike-steered lineament learning (DOE GEMS, DrivenData competition 306)

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE78/ · **Run card:** `evidence/h78_run_card.json` · **Prompt (read every session):** `PROMPT.md`

## Core Values (Arena) — read before anything else
1. **Maximize P(Win).** Every hour goes to the thing most likely to raise the organizer-confirmed score; a negative result that saves a submission slot counts.
2. **Own the Outcome.** No manual steps, no unlabelled numbers, no hidden irregularities. If a tool is wrong, fix it in the shared template and say so.

## Historical H78-A status (2026-10-21, session 1; not current clearance)

| Item | Value |
|---|---|
| Shipped file | `docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif` (+ `.zip`, + receipt `.json`) |
| sha256 | `6815eac5ff08d913207fa725b7be8ce79c0493d480d17591b7415ab0062acc54` |
| Historical run-card verdict | `promote` under that prior lane's gates; current review status is **NOT CLEARED** under the literal all-registry rule because the stored audit covers only three lineage rasters (IR-78-16). |
| Submission name | `gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros` |
| Note (120 chars) | `GEMSDOE78 H78-A strike-steered HGB, 44090 dots >=283m apart, flank<=3px pruned; HOLDOUT-DTI 0.1826 s20; not a projection` |
| HOLDOUT-DTI | **0.1826** [0.1628, 0.2004] (evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives) |
| Controls (same folds) | A2 B2 0.1586 · A1 isotropic 0.1462 · A0 raw-19 0.1376 · registry D2.8 0.0919 · registry H33 0.0037 (structurally capped) |
| ORGANIZER-CONFIRMED | none — the file has not been uploaded. A holdout number is never a projection. |
| Open risk | IR-78-09: dots concentrate nearer the catalogue than H33 (median 6 px vs 19.6 px). See the home page box and `evidence/h78_distance_diagnostic.json`. |

## Current review status (session 2)

Read `PROMPT.md` and this README before any project work. Neither historical lane is cleared for upload under this review: H78-A is **not cleared** because its stored uniqueness audit does not cover the full accessible registry (IR-78-16); H78-MPC is **negative / duplicate-stop** under the literal forward-overlap rule (IR-78-14 / IR-78-15). Both files remain downloadable for research/education only. This review selected nothing, used 0 new model experiments, and spent 0 competition slots.

## Submission workflow (only for a future cleared candidate; details on the site's *Executive summary* page)
1. Proceed only when the current home-page banner and run card both say **OK TO SUBMIT: YES** / `ok_to_submit: true`. 2. Download the exact `.tif` (or permitted `.zip`) linked from that eligible card. 3. DrivenData → competition 306 → *New submission* → upload. 4. Copy the exact name and note only from the eligible run card; **do not use the historical H78-A metadata above**. 5. Record the returned submission-page receipt and score in `registry/live_scores.csv` as ORGANIZER-CONFIRMED.
The historical H78-A file passed local format/range checks (single-band float32, EPSG:32611, 3730 × 3292, sample geotransform, all finite, binary values, zeros outside the footprint). That local check is not current uniqueness clearance or organizer acceptance, and it does not guarantee that a future upload will be accepted.

## What was done (3 experiments + 1 declared diagnostic, ~1 h 45 m)
* **Forensics** of the family's best file (why 0.2778): `scripts/forensics_h33.py` → `evidence/forensics_h33_vs_d28.json`; narrative in `research/h78_hypotheses.md` §0 and the site's *Hypotheses* page.
* **Hypotheses H78-A…E** ranked by expected DTI gain × cost (`research/h78_hypotheses.md`); top candidate H78-A = steer multi-scale derivative filters of topography, magnetics, gravity, basement depth, conductivity, radiometrics into the regional catalogue-strike frame (orientation only, never location). Preregistered in `registry/preregistration.json`.
* **Exp 1–2** (`scripts/run_holdout.py --seed 20`): spatially-blocked hide-and-recover holdout (whole components hidden, 3 px buffer, visible faults masked pixel-exactly, pooled DTI α 0.2 β 0.8, 300 m kernel), three arms, leakage canary, budget sweep, registry comparators. Paired block-bootstrap CIs: `scripts/pooled_ci.py`.
* **Exp 3** (`scripts/build_submission.py`): fit A2 on the full catalogue, emit 44,090 dots ≥ 2.8 px apart with the ≤ 3 px catalogue flank removed, uniqueness audit before placement and on final dots, writer + independent validator, run card.
* **Diagnostic** (`scripts/diagnose_distance.py`): credit-per-dot by distance to visible faults; far-truth stratum test. Led to amendment IR-78-01b (B3 primary).
* **Site** (`scripts/build_site.py` → `docs/`), **tests** (`pytest tests`), **knowledge store** (`research/knowledge.md`), **sources/irregularities** (`registry/*.json`).

## Reproduce
```bash
pip install -r requirements.txt            # add --break-system-packages on Debian images
bash scripts/restore_data.sh               # SHA-256-pinned inputs from the family's GitHub mirrors (needs gh auth)
python scripts/forensics_h33.py
python scripts/run_holdout.py --seed 20    # ~14 min on 2 CPUs, 4 GB
python scripts/pooled_ci.py
python scripts/build_submission.py         # ~3 min with cached features
python scripts/diagnose_distance.py
python scripts/build_site.py && python -m pytest -q tests
```
Deterministic: two builds produced byte-identical rasters (same sha256).

## Layout
`src/gems78/` lane code · `vendor/gems57/` shared template, unmodified (pins in GEMSDOE77 `registry/template_pin.json`) · `scripts/` runnable steps · `evidence/` every JSON/log a number on the site comes from · `registry/` preregistration, sources, irregularities, data manifest, live scores · `research/` hypotheses + knowledge · `docs/` GitHub Pages site and downloads · `tests/`.

## Concurrent blocked review (same day)
A parallel session without data access published a *NOT READY* site and negative run card (PRs #3–#5). They are preserved verbatim under `docs/archive/blocked-review-2026-10-21/` and `docs/review-2026-10-21.md`; two of their observations are carried forward as IR-78-12 (leaderboard snapshot 0.4413 / 0.3904, 2026-10-21) and IR-78-13 (0.2778 provenance conflict between GEMSDOE32 and GEMSDOE71). This lane's state supersedes theirs because the inputs were restored and verified here (`data/restore_sha256.txt`).

## Limitations (honest list)
1. **Holdout ≠ live.** Withheld truth lies median 9 px from a visible fault; live truth may not. The catalogue-truth proxy over-rewards near-halo dots (GEMSDOE32 saw +0.010 holdout turn into −0.003 live for a coverage change). Mitigation: the candidate's advantage persists on withheld truth > 10 px from visible faults, but the absolute level there is low (0.066).
2. **One seed.** Only seed 20 was run; CIs are block-bootstrap within one draw, not across draws.
3. **Flank radius chosen after results** (IR-78-01b). Transparent, consistent with the live D2.8 → H33 step, but not preregistered.
4. **No organizer score** exists for anything in this repo; the 0.2778 / 0.3195 / 0.4413 figures are family or prompt claims.
5. **Not an organizer-strength detector.** HGB on hand-made filters, not the U-Net reference; CPU-only sandbox.
6. **External sources** outside github.com could not be re-fetched here; `registry/sources.json` states the fetch status of each link for manual review.

## Next session
* Seed 30 (and 40) holdout replicate; report across-seed spread.
* Distance-stratified budget test (match H33's live distance profile) and a flank sweep 3–6 px — only on the holdout's far-truth stratum, to avoid the halo bias.
* Budget sweep 44–60 k dots with B3 (holdout keeps rising to 50 k: 0.1843).
* Detector upgrade: small U-Net over the 19 bands + steered features, trained with the same buffered-component folds (organizer reference solution as the baseline class).
* After the first upload: copy the ORGANIZER-CONFIRMED score into `registry/live_scores.csv` and re-run `build_site.py`.

---

## H78-MPC lane — negative result (research artifact only)

A prior parallel run generated an H78-MPC raster. Its original preregistered gate passed, but that gate used mutual overlap and a point-estimate control threshold; it did not satisfy the literal forward-overlap and current-best requirements in `PROMPT.md`. This review therefore corrects the prior promotion label. The required outcome is **negative / stop**: the TIF remains
available for research and education, but **do not upload it or spend a weekly slot**. No replacement raster was made.

| Item | Value |
|---|---|
| Page / guide | [`docs/h78mpc.html`](docs/h78mpc.html) · [`docs/h78mpc-executive-summary.html`](docs/h78mpc-executive-summary.html) |
| Research artifact | `docs/downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif` (+ `.zip`, receipt) |
| sha256 | `c7932fbda98120b5abce37247852220befe1798dac4828fd58f785534e081256` |
| Status | **OK TO DOWNLOAD: YES, research/education only · OK TO SUBMIT: NO** (`verdict: negative`) |
| HOLDOUT-DTI | 0.0977 [0.0780, 0.1163] (evaluator `gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives). Paired HOLDOUT-DTI candidate−H33-control difference +0.0038 [−0.0120, +0.0200], not significant. |
| Current repository best | HOLDOUT-DTI 0.1843 [0.1658, 0.2015] for H78-A `A2_h78_steered|nms0_B3|50000` (same evaluator/seed/withheld count; descriptive cross-lane comparison, no paired difference CI). |
| Literal uniqueness gate | Pre-placement max |ρ| = 0.1546 (passes 0.90); final forward 3-px overlap = **0.730** with a non-spacefilling registry raster and **0.9914** across the compared set (both exceed the 0.70 stop limit). The prior mutual-overlap rule was incorrect for this prompt. |
| Automated validator | PASS for local file format/range: float32, EPSG:32611, 3730×3292, exact sample transform, all finite, values [0,1], no NaN, nodata=None. This is not a uniqueness clearance or organizer acceptance. |
| Evidence / irregularities | [`evidence/h78mpc_run_card.json`](evidence/h78mpc_run_card.json) · [`evidence/h78mpc_duplicate_stop.json`](evidence/h78mpc_duplicate_stop.json) · IR-78-14 / IR-78-15 |
| Slot / experiment count | This review spent 0 slots and ran 0 new model experiments. The previous lane already reached its three-arm budget plus the disclosed emission correction. |
