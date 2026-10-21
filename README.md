# GEMSDOE78 — DOE GEMS competition 306

**Read `PROMPT.md` at the start of every session.** It is the specification: unique GeoTIFF, obvious OK / not-OK, hide-and-recover holdout, no unlabeled numbers, no copied submission, three experiments then stop.

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE78/ · **Status feed:** `docs/data/status.json` · **This session's run card:** `evidence/h78spy_run_card.json`

## Status (2026-10-21, this session) — OK TO SUBMIT: NO

| Item | Value |
|---|---|
| New file | `docs/downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif` |
| sha256 | `0a0767f2986ba13462440ae72340ea7e089860b18d469edfb0ab05689f0168f3` |
| OK to submit | **NO.** Verdict `negative`. Do not upload it. |
| Why | HOLDOUT-DTI **0.1808** [0.1623, 0.1985] (evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives) vs reproduced control **0.1826**. Paired delta −0.0018 [−0.0069, +0.0037]. 92.45% of deployment dots lie within 3 px of H78-A (limit 0.70): duplicate, stop. |
| ORGANIZER-CONFIRMED | none |
| Weekly slots used by the agent | 0 |
| Format | Independent `scripts/verify_tif.py`: all checks passed (finite, [0, 1], EPSG:32611, 3730×3292, sample transform, nodata unset). Format validity is not a clearance. |

Two hypotheses were preregistered and run. **H78-TOOTH** (across-strike missing-tooth kernel) is falsified: withheld faults sit at median 0.39 of the local spacing, not 1, and the location-proxy features collapsed the learner onto the mapped traces (`evidence/h78tooth_negative.json`). **H78-SPY** (Liu drop-and-refit) is the file above. Neither beat the holdout best. No projection is written as a score.

The family's 0.2778 figure remains an **owner-report**. Re-measured this session from the pinned H33 raster: 37,654 dots, exact subset of D2.8, 6,436 removed dots all 1.0–2.0 px from the catalogue, median distance to catalogue 19.6 px, nearest-neighbour median 3.0 px. GEMSDOE32's own page, re-fetched 2026-10-21, says no organiser score exists for that file (IR-78-17). Beating that owner-report needs a better off-catalogue field, which these two experiments did not produce.

---

# Previous session — Lane H78-A (not regenerated; not this session's submission)

## Core Values (Arena) — read before anything else
1. **Maximize P(Win).** Every hour goes to the thing most likely to raise the organizer-confirmed score; a negative result that saves a submission slot counts.
2. **Own the Outcome.** No manual steps, no unlabelled numbers, no hidden irregularities. If a tool is wrong, fix it in the shared template and say so.

## Status (2026-10-21, session 1)

| Item | Value |
|---|---|
| Shipped file | `docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif` (+ `.zip`, + receipt `.json`) |
| sha256 | `6815eac5ff08d913207fa725b7be8ce79c0493d480d17591b7415ab0062acc54` |
| OK to submit | **Previous-session gate only: YES** for that older file (canary, uniqueness, validator). It is not this session's new submission. The live homepage does not clear a new slot. Halo risk IR-78-09 still applies. |
| Submission name | `gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros` |
| Note (120 chars) | `GEMSDOE78 H78-A strike-steered HGB, 44090 dots >=283m apart, flank<=3px pruned; HOLDOUT-DTI 0.1826 s20; not a projection` |
| HOLDOUT-DTI | **0.1826** [0.1628, 0.2004] (evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives) |
| Controls (same folds) | A2 B2 0.1586 · A1 isotropic 0.1462 · A0 raw-19 0.1376 · registry D2.8 0.0919 · registry H33 0.0037 (structurally capped) |
| ORGANIZER-CONFIRMED | none — the file has not been uploaded. A holdout number is never a projection. |
| Open risk | IR-78-09: dots concentrate nearer the catalogue than H33 (median 6 px vs 19.6 px). See the home page box and `evidence/h78_distance_diagnostic.json`. |

## How to submit
The live homepage banner is the decision. It currently says **OK TO SUBMIT: NO** for the new file. Do not upload a file whose page says NO. Steps, the portal [0, 1] failure mode, and the earlier H78-A file are on `docs/executive-summary.html`. Record any future portal score in `registry/live_scores.csv` as ORGANIZER-CONFIRMED. A holdout number is never that score.

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

## Second independent lane (parallel session, merged additively): H78-MPC monogenic phase congruency

A separate parallel session ran a distinct lane and it is preserved as a **second promoted candidate**
(not a replacement for the H78-A primary above). Selector guidance: **H78-A first** (HOLDOUT-DTI 0.1826);
H78-MPC is the diverse second file for a separate slot (mutual 3-px dot overlap vs H78-A = **0.3552 ≤ 0.70**,
`evidence/h78mpc_vs_h78a_overlap.json`).

| Item | Value |
|---|---|
| Page / guide | [`docs/h78mpc.html`](docs/h78mpc.html) · [`docs/h78mpc-executive-summary.html`](docs/h78mpc-executive-summary.html) |
| File | `docs/downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif` (+ `.zip`, receipt) |
| sha256 | `c7932fbda98120b5abce37247852220befe1798dac4828fd58f785534e081256` |
| OK to submit | **YES** — verdict `promote` (preregistered gate; see caveats) |
| Name / note (111) | `gems78-h78mpc-monogenic-pc-spaced-37654-20261021` / `H78-MPC monogenic phase-congruency LOQO HGB, spaced 2.5px emit; HOLDOUT-DTI 0.098 vs 0.094 H33 ctrl; 37654 dots` |
| HOLDOUT-DTI | **0.0977** [0.078, 0.116] (same evaluator/seed/11,321 withheld; H33 fold-fair control 0.0939; paired +0.0038 [−0.012, +0.020] n.s.; vs no-MPC ablation +0.0121 [0.0027, 0.0217] significant) |
| Method | Riesz monogenic phase-congruency features (σ=1/2/4) + Frangi over a 48-band stack, LOQO HGB, spaced 37,654 dots; canaries 80/80 PASS; uniqueness ρmax 0.1546, mutual 0.4879 vs 74 registry rasters |
| Disclosure | IR-78-EMIT-01: Pass-1 allocator emitted contiguous dot runs (HOLDOUT-DTI 0.0471); Pass-2 re-emitted frozen surfaces spaced (no retraining) → 0.0977. Both readings in `evidence/h78mpc_*.json`; run card `evidence/h78mpc_run_card.json`. Note: this lane's arms exclude visible-network context features, which is why its holdout trails H78-A — the significant MPC ablation is the transferable result |
| Reproduce | `scripts/build_features.py` → `run_experiments.py` → `pass2_spaced_emission.py` → `build_production.py` → `pass2_rebuild_production.py` → `make_figures.py` / `build_run_card_mpc.py` / `build_site_mpc.py` (data: `scripts/restore_data.py`, manifest `registry/data_manifest_gems73.json`) |
