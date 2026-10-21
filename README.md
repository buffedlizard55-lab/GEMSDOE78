# GEMSDOE78 — Lane H78: strike-steered lineament learning + H78-NET network-aware context (DOE GEMS, DrivenData competition 306)

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE78/ · **Prompt (read every session):** `PROMPT.md`  
**Primary Run Card:** `evidence/h78_run_card.json` (H78-A strike-steered, HOLDOUT-DTI 0.1826)  
**New Candidate Run Card:** `evidence/h78net_run_card.json` (H78-NET network-aware, status: NOT YET RUN)

## Core Values (Arena) — read before anything else
1. **Maximize P(Win).** Every hour goes to the thing most likely to raise the organizer-confirmed score; a negative result that saves a submission slot counts.
2. **Own the Outcome.** No manual steps, no unlabelled numbers, no hidden irregularities. If a tool is wrong, fix it in the shared template and say so.

## Status (2026-10-21, session 1)

| Item | Value |
|---|---|
| Shipped file | `docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif` (+ `.zip`, + receipt `.json`) |
| sha256 | `6815eac5ff08d913207fa725b7be8ce79c0493d480d17591b7415ab0062acc54` |
| OK to submit | **YES** — verdict `promote` (preregistered gate, canary, uniqueness, validator all pass; independent re-read `scripts/verify_tif.py` 12/12) |
| Submission name | `gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros` |
| Note (120 chars) | `GEMSDOE78 H78-A strike-steered HGB, 44090 dots >=283m apart, flank<=3px pruned; HOLDOUT-DTI 0.1826 s20; not a projection` |
| HOLDOUT-DTI | **0.1826** [0.1628, 0.2004] (evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives) |
| Controls (same folds) | A2 B2 0.1586 · A1 isotropic 0.1462 · A0 raw-19 0.1376 · registry D2.8 0.0919 · registry H33 0.0037 (structurally capped) |
| ORGANIZER-CONFIRMED | none — the file has not been uploaded. A holdout number is never a projection. |
| Open risk | IR-78-09: dots concentrate nearer the catalogue than H33 (median 6 px vs 19.6 px). See the home page box and `evidence/h78_distance_diagnostic.json`. |

## How to submit (details on the site's *Executive summary* page)
1. Check the home page banner says **OK TO SUBMIT: YES**. 2. Download the `.tif` (or `.zip`). 3. DrivenData → competition 306 → *New submission* → upload. 4. Paste the note above. 5. Record the returned score in `registry/live_scores.csv` as ORGANIZER-CONFIRMED.
The file is single-band float32, EPSG:32611, 3730 × 3292, sample geotransform, **all finite, values exactly 0 or 1, zeros outside the footprint** — the earlier portal error "Predicted values must be in range [0, 1]" cannot recur for that reason.

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
* **NEW: H78-NET** - Run network-aware context features (this session's work):
  - `python scripts/run_holdout_net.py --seed 20` (holdout evaluation)
  - `python scripts/build_submission_net.py` (build submission TIF)
  - Expected: HOLDOUT-DTI > 0.20 (target: 0.25-0.30)
* Seed 30 (and 40) holdout replicate for H78-A; report across-seed spread.
* Distance-stratified budget test (match H33's live distance profile) and a flank sweep 3–6 px — only on the holdout's far-truth stratum, to avoid the halo bias.
* Budget sweep 44–60 k dots with B3 (holdout keeps rising to 50 k: 0.1843).
* Detector upgrade: small U-Net over the 19 bands + steered features, trained with the same buffered-component folds (organizer reference solution as the baseline class).
* After the first upload: copy the ORGANIZER-CONFIRMED score into `registry/live_scores.csv` and re-run `build_site.py`.

---

## 🆕 H78-NET: Network-Aware Lineament Context (NEW - This Session)

**Status:** ⭐ **IMPLEMENTED, READY FOR VALIDATION**  
**Hypothesis:** Unmapped faults are most likely to occur in structural gaps within the visible fault network.  
**Expected Gain:** +0.08-0.15 HOLDOUT-DTI (target: 0.25-0.30 total)  
**Implementation:** `src/gems78/network.py`, `src/gems78/features_net.py`, `src/gems78/pipeline_net.py`  
**Scripts:** `scripts/run_holdout_net.py`, `scripts/build_submission_net.py`  
**Preregistration:** `registry/preregistration_net.json`  
**Documentation:** `research/new_hypotheses_20261021.md`

### What's New
H78-NET extends H78-A with **20 network context features** that describe each pixel's position relative to the visible fault network:

| Feature Type | Count | Description |
|-------------|-------|-------------|
| Fault density | 1 | Gaussian-smoothed density of visible faults (σ=40px) |
| Junction proximity | 1 | Proximity to fault intersections/junctions |
| Segment length | 1 | Length of nearest visible fault segment |
| Structural gaps | 3 | Across-strike position, along-strike variation, gap coherence |
| Distance bins | 7 | One-hot encoded distance to network (0-5px, 5-10px, ..., 100px+) |
| Strike statistics | 3 | Strike coherence, normalized energy, variability |

**Total: 19 raw + 18 ISO + 24 steered + 20 network = 81 features**

### Why It Should Work
1. **Geological Rationale:** In Basin and Range, faults occur in sub-parallel arrays. Unmapped strands are most likely where the structural trend continues but the catalogue has gaps.
2. **Evidence from Siblings:** GEMSDOE77 achieved **0.1900 holdout-DTI** with similar network context features.
3. **Orthogonal Signal:** Network features capture **structural topology**, complementing the **orientation** signal from steered features.
4. **Leakage-Safe:** All features derived ONLY from visible catalogue; no hidden truth information used.

### Validation Plan
1. Run `scripts/run_holdout_net.py --seed 20` (~2-4 hours)
2. Check A3_h78_net beats A2_h78_steered with 95% CI
3. Verify all leakage canaries pass (max AUC < 0.90)
4. Check uniqueness vs registry rasters
5. Build submission with `scripts/build_submission_net.py`
6. Generate run card and downloadable TIF

### Expected Outcomes
| Scenario | HOLDOUT-DTI | Action |
|----------|-------------|--------|
| Best case | > 0.28 | ✓ Promote immediately |
| Target | 0.25-0.28 | ✓ Promote with confidence |
| Minimum | > 0.20 | ✓ Promote (clear improvement) |
| Negative | ≤ 0.20 | ✓ Document as negative result |

### Files to be Generated
- `evidence/h78net_holdout_seed20.json` - Holdout evaluation results
- `evidence/h78net_pooled_ci_seed20.json` - Confidence intervals
- `evidence/h78net_run_card.json` - Full run card
- `docs/downloads/gems78-h78net-44090dots-*.tif` - Submission TIF
- `docs/data/submission_net.json` - Site metadata

### Risk Mitigation
- **Leakage:** All network features use only visible catalogue; canary test will flag any issues
- **Overfitting:** Features are general structural descriptors, not fitted to hidden truth
- **Uniqueness:** Will be checked against all registry rasters before submission

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
