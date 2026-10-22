# GEMSDOE78 — Hidden Geothermal Fault Detection (`H78-MGHD` & Consolidated Audit)

> ## **TOP-OF-REPO SUBMISSION STATUS: `OK TO DOWNLOAD: YES · OK TO SUBMIT: NO`**
> - **Latest Session-5 Candidate (`H78-MGHD`):** [`docs/downloads/gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.tif`](docs/downloads/gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.tif) ([single-TIFF `.zip`](docs/downloads/gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.zip) · [Run Card JSON](evidence/h78mghd_run_card.json))
> - **GeoTIFF SHA-256:** `44429c439118a6e20f77f6da821ecd4e46697da0545314d20b65e81766d8b698` (`158,254` bytes)
> - **Single-TIFF ZIP SHA-256:** `c26586a32dcf42a284ac96c5c83f9984fdaa85d77e25b79ab86dede4256cdd44` (`126,951` bytes)
> - **Submission Note (`102 / 140` chars):** `NOT OK TO SUBMIT: H78-MGHD 44090 dots; HOLDOUT-DTI 0.1934 vs 0.1826; blocked by sibling overlap >0.70.`
> - **Automated Programmatic Validation (`scripts/verify_tif.py` — 0 human-inspector deferral):** **13/13 PASS** — `count=1`, `float32`, `EPSG:32611`, `3730 × 3292`, affine `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`, `nodata=None`, zero NaN/Inf anywhere, binary `{0.0, 1.0}` strictly in `[0, 1]`, `44,090` positive dots inside footprint, `0` on mapped catalogue (`"Predicted values must be in range [0, 1]"` error mathematically impossible).
> - **Why `OK TO DOWNLOAD: YES` & `OK TO SUBMIT: NO`:** `H78-MGHD` beats the incumbent control on **both** spatial holdout seeds (`seed=20` and zero-retune `seed=30`, pooled `HOLDOUT-DTI = 0.197059` vs `0.183004`, `Δ = +0.014056`, 95% CI `[+0.007047, +0.021139]`), passes surface uniqueness across **all 1,103 accessible rasters** (`max |ρ| = 0.7677 <= 0.90`), and passes `<= 0.70` forward 3-px overlap across **all 801/801 sparse dot submissions (`<= 65,000` dots)** in all `84` accessible repos (`max = 0.6800`, vs `H78-A = 0.6698`). Under the **unchanged literal all-rasters gate** (`vendor/gems57/uniqueness.py:binding_duplicate_decision`, zero exemptions), 81 continuous space-filling rasters (`1.0000 > 0.70`) and 32 wide range-front corridor rasters (`0.9158 > 0.70`) trigger an automatic stop (`verdict = "negative"`, `weekly_slots_used_by_agent = 0`, `ORGANIZER-CONFIRMED: None`).

---

## Navigation & Published Artifacts

- **GitHub Pages Site (`docs/`):**
  - [`docs/index.html`](docs/index.html) — Top-of-page readiness status (`OK TO DOWNLOAD: YES · OK TO SUBMIT: NO`), one-click GeoTIFF & ZIP downloads, validator badge receipt, all-candidate audit table, and H33 summary.
  - [`docs/executive-summary.html`](docs/executive-summary.html) — Executive summary & step-by-step DrivenData verification/submission how-to guide.
  - [`docs/h78mghd.html`](docs/h78mghd.html) — Complete Session-5 `H78-MGHD` evidence page, 2-seed bootstrap tables, and 84-repository (`1,103`-raster) uniqueness tables.
  - [`docs/why-h33.md`](docs/why-h33.md) — Exact forensic proof of why `GEMSDOE32` (`H33`: `0.2778` reported) outperformed `D2.8` (`0.2600` reported) and relation to reported `0.3195` / `0.4413` scores.
  - [`docs/review-release.md`](docs/review-release.md) — 5 ranked geological hypotheses, Pass 1 -> Pass 2 -> Pass 3 audit log, verified sources, irregularities, limitations, and next steps.
- **Machine-Readable JSON Evidence (`evidence/` & `registry/`):**
  - [`evidence/h78mghd_run_card.json`](evidence/h78mghd_run_card.json) & [`run_card_h78mghd.json`](run_card_h78mghd.json) — Session-5 Run Card.
  - [`evidence/h78mghd_holdout_seed20.json`](evidence/h78mghd_holdout_seed20.json) & [`evidence/h78mghd_holdout_seed30.json`](evidence/h78mghd_holdout_seed30.json) — Exact `gems57-pooled-hide-v2` holdout results & 123-feature leakage canary (`max symmetric AUC = 0.6048 <= 0.90`).
  - [`evidence/h78mghd_uniqueness_summary.json`](evidence/h78mghd_uniqueness_summary.json) & [`registry/accessible_registry_2026-10-22.json`](registry/accessible_registry_2026-10-22.json) — Complete 84-repository (`1,103` unique SHA-256 GeoTIFF) audit.
  - [`registry/preregistration_h78_mghd.json`](registry/preregistration_h78_mghd.json) & [`registry/shared_template_review_2026-10-22.json`](registry/shared_template_review_2026-10-22.json) — Preregistration & shared `vendor/gems57` bug report.
  - [`evidence/release_audit.json`](evidence/release_audit.json) — Consolidated fail-closed audit across all 7 repository GeoTIFFs.

---

## Key Measured Results (`HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED`)

> **ORGANIZER-CONFIRMED Scores:** `None` (no DrivenData portal upload performed; no submission-page receipt retrieved in this sandbox). All numbers below are locally computed **`HOLDOUT-DTI`** (`evaluator_version = "gems57-pooled-hide-v2"`, 20% whole-segment buffered withholding, 3-px collar, pixel-exact visible fault mask, $\alpha=0.2, \beta=0.8$, 300 m kernel, 1,000-draw 20 km spatial-block bootstrap).

| Experiment / Evaluation Split | Withheld Positives | `H78-MGHD` (44,090 dots) [95% CI] | Incumbent `CTRL_A2_v2` (44,090 dots) [95% CI] | Paired $\Delta$ (`Cand - Ctrl`) [95% CI] |
| --- | ---: | --- | --- | --- |
| **E1** (`seed=20`, matched `min_dist=2.8`) | `11,321` | **`0.195210`** `[0.176501, 0.214135]` | `0.182575` `[0.163306, 0.199996]` | **`+0.012635`** `[+0.004088, +0.021111]` |
| **E2** (`seed=20`, selected `min_dist=3.01`) | `11,321` | **`0.193393`** `[0.176040, 0.210917]` | `0.182575` `[0.163306, 0.199996]` | **`+0.010818`** `[+0.002291, +0.019736]` |
| **E3** (`seed=30`, zero-retune replication, `min_dist=3.01`) | `11,342` | **`0.200714`** `[0.180475, 0.220262]` | `0.183432` `[0.162300, 0.204353]` | **`+0.017282`** `[+0.004937, +0.029344]` |
| **Pooled Two-Seed** (`seeds 20 + 30`, `min_dist=3.01`) | `22,663` | **`0.197059`** `[0.184840, 0.209875]` | `0.183004` `[0.169980, 0.195610]` | **`+0.014056`** `[+0.007047, +0.021139]` |

---

## Reproducible Commands

```bash
# 1. Restore SHA-256-verified core, bridge, external, and scored inputs into .cache/ behind data/ symlinks
bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py

# 2. Rebuild complete 84-repository accessible GeoTIFF inventory (1,103 unique SHA-256 rasters)
.venv/bin/python scripts/build_accessible_registry.py

# 3. Run H78-MGHD holdout validation (seed=20 E1/E2 + untouched zero-retune seed=30 E3) & deployment build
.venv/bin/python -u scripts/run_mghd_pipeline.py --stage all

# 4. Validate GeoTIFF + single-TIFF ZIP independently (zero human-inspector deferral) & publish site
.venv/bin/python scripts/verify_tif.py docs/downloads/gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.tif
.venv/bin/python scripts/publish_mghd.py

# 5. Run full test suite
.venv/bin/pytest -q tests
```

---

## Embedded Governing Instructions & Parallel-Run Protocol

Per project requirements, the governing prompt, acceptance criteria, and Parallel-Run Protocol under which this repository and release were executed and verified are embedded verbatim below:

```text
Task & Governing Acceptance Criteria:
1. Review GEMSDOE78, study why GEMSDOE32 (h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778)
   outperformed earlier GEMSDOE submissions and how it relates to higher reported scores (0.3195, 0.4413).
2. Generate a brand-new, unique single-band float32 GeoTIFF submission (never copied or renamed from
   an existing TIF; prior TIFs strictly for learning/education) matching sample_submission.tif CRS
   (EPSG:32611), shape (3730x3292), and geotransform, with finite values strictly in [0, 1], no NaNs
   inside footprint, automated programmatic validation without deferring to a human inspector, unique
   submission name, <=140-character note, SHA-256 digest, one-click download, and unmistakable
   OK TO DOWNLOAD / OK TO SUBMIT banner at the very top of docs/index.html and docs/executive-summary.html.
3. Parallel-Run Protocol:
   - Single method lane per session.
   - Check continuous surface before placement (|Spearman rho| > 0.90 -> stop) and final dots against
     accessible registry rasters (forward 3-px dot overlap > 0.70 -> log duplicate and stop).
   - Reuse cached feature stack, shared vendor/gems57/evaluate_holdout.py, and shared
     vendor/gems57/submission_writer.py; fix any shared-tool bug once in vendor/gems57 with report
     (never keep a private fork).
   - Hide-and-recover holdout: withhold whole fault segments + buffer, derive all catalogue features
     from visible faults only, mask visible faults pixel-exactly, score pooled DTI (alpha=0.2, beta=0.8,
     300 m triangular kernel).
   - Strict score labeling: label every score HOLDOUT-DTI (with evaluator version, withheld positive
     count, 95% CI) or ORGANIZER-CONFIRMED (backed by submission-page receipt); never write projections
     as scores; zero hallucinations; flag irregularities and inaccessible links explicitly.
   - Single-feature leakage canaries: symmetric ROC AUC > 0.90 blocks training until proven non-leaky.
   - Emit one JSON Run Card containing: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI,
     correlation/overlap vs registry, raster sha256, validator output, submission name + <=140-char note,
     and verdict (promote / negative).
   - Respect <= 3 experiments and <= 2 hours experiment budget; do not upload directly to DrivenData
     (slot promotion is separate within verified weekly cap).
4. Workflow & Quality Passes:
   - Propose and rank 3-5 novel geological hypotheses naming layers, physical transform/signature,
     why missed by USGS/INGENIOUS catalogue, non-fault mimic, and difference from existing code
     (verifying obtainability of external data first).
   - Execute Pass 1 (implement + verify), Pass 2 (bug/edge-case audit + fixes), Pass 3 (full re-check),
     open a pull request on branch arena/abc72825-gemsdoe78, verify CI, and merge onto main.
```
