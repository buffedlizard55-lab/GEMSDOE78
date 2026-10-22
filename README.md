# GEMSDOE78 — DOE Geothermal GEMS Hidden Fault Detection (`DrivenData #306`)

> ## IMMEDIATE SUBMISSION READINESS & DOWNLOAD STATUS (AUTOMATED VERIFICATION — ZERO HUMAN DEFERRAL)
>
> | Candidate Artifact (`docs/downloads/`) | Automated Format / `[0, 1]` Check | Scientific & Registry Uniqueness Gate | Status |
> |---|---|---|---|
> | **`gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.tif`** (`.zip`: `114,126 B`, SHA-256 `a8790f0a...`) | **PASS (`12/12` checks, `float32`, finite in `[0.0, 1.0]`, `40,000` binary dots, `0` on catalogue)** | **PASS (`30 / 30 = 100%` operative + expanded `G4 v2` checks, `HOLDOUT-DTI 0.1898` Seed 20 / `0.1976` 3-Seed Mean)** | **OK TO DOWNLOAD: YES · OK TO SUBMIT: YES (Primary Slot Candidate)** |
> | **`gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.tif`** (`158,254 B`, `.zip`: `126,951 B`, SHA-256 `44429c439118a6e20f77f6da821ecd4e46697da0545314d20b65e81766d8b698`) | **PASS (`13/13` checks, `float32`, `EPSG:32611`, `3730×3292`, finite in `[0.0, 1.0]`, `44,090` binary dots, `0` on catalogue)** | **Single-model `HOLDOUT-DTI` high-water mark (`0.1952` `d=2.8` / `0.1934` `d=3.01` Seed 20; `0.2007` Seed 30; `0.1971` pooled)** & passes all `801` external sparse dot submissions (`max = 0.6800 <= 0.70`; `0.5587` vs `H78-GSC`), **STOP (`0.7359 > 0.70`) vs parallel `H79-LS-50k`** & literal saturation (`1.0000`) | **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO (Research / Inspection Only)** |
> | All other 16 historical / parallel inspection artifacts (`H78-A`, `H78-MPC`, `H78-CS`, `H78-SPY`, `H78-CROSSLAYER`, `H78-STEP`, `H78-STEP-FLANK`, `H78-FW`, `H78-FWTILT`, `H78-SIGX`, `H79-LR/LS`) | **PASS (`verify_tif.py` portal-safe `[0.0, 1.0]`)** | Superseded or blocked by holdout / overlap stop rules (see [`docs/index.html`](docs/index.html) & [`evidence/release_audit.json`](evidence/release_audit.json)) | **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO** |
>
> - **Weekly competition slots consumed automatically by agent:** **`0`** (`ORGANIZER-CONFIRMED` scores generated in this repository: **`None`**; selector owns final portal upload within verified weekly cap).
> - **Top-of-site pages:** [`docs/index.html`](docs/index.html) · [`docs/executive-summary.html`](docs/executive-summary.html) · [`docs/h78gsc.html`](docs/h78gsc.html) · [`docs/h78mghd.html`](docs/h78mghd.html) · [`docs/h78mghd-executive-summary.html`](docs/h78mghd-executive-summary.html) · [`docs/why-h33.md`](docs/why-h33.md) · [`docs/review-release.md`](docs/review-release.md)

---

## 1. Ready-to-Use Submission Metadata & Reproducible Commands

### A. Primary Cleared Competition Submission (`Lane H78-GSC`)
- **Competition ZIP:** `docs/downloads/gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.zip`
- **Raw GeoTIFF:** `docs/downloads/gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.tif` (`sha256 = e5d6293d35c470b5c7f7c92a49c0e60027a571316328a1241a8302400147f69a`)
- **Independent Gate Receipt:** [`evidence/h78gsc_gate_report.json`](evidence/h78gsc_gate_report.json) (`G1_format`, `G2_canary`, `G3_holdout`, `G4_uniqueness` `30/30` including `H78-MGHD`, `G5_emission` ALL PASS)

### B. Session-5 Multi-Scale Geodetic–Hydrothermal–LiDAR Dual-Cover Artifact (`Lane H78-MGHD` — Research / Inspection Only)
- **Inspection ZIP:** `docs/downloads/gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.zip` (`sha256 = c26586a32dcf42a284ac96c5c83f9984fdaa85d77e25b79ab86dede4256cdd44`)
- **Inspection GeoTIFF:** `docs/downloads/gems78-h78mghd-dualcover-44090dots-20261022T032500Z-1045873e-DO-NOT-SUBMIT.tif` (`sha256 = 44429c439118a6e20f77f6da821ecd4e46697da0545314d20b65e81766d8b698`)
- **Note (`102 / 140` chars):** `NOT OK TO SUBMIT: H78-MGHD 44090 dots; HOLDOUT-DTI 0.1934 vs 0.1826; blocked by sibling overlap >0.70.`
- **Run Card & Complete `84`-Repo (`1,114`-Raster) Audit:** [`evidence/h78mghd_run_card.json`](evidence/h78mghd_run_card.json) · [`run_card_h78mghd.json`](run_card_h78mghd.json) · [`evidence/h78mghd_uniqueness_summary.json`](evidence/h78mghd_uniqueness_summary.json)

### C. Reproducible End-to-End Commands
```bash
# 1. Restore SHA-256-pinned core, external physics, and registry rasters + build v2 stack19 memmap
bash scripts/download_competition_data.sh

# 2. Run Session-5 H78-MGHD two-seed spatial holdout + 1,103-raster uniqueness audit + GeoTIFF emission
.venv/bin/python -u scripts/run_mghd_pipeline.py --stage holdout
.venv/bin/python -u scripts/run_mghd_pipeline.py --stage production

# 3. Publish H78-MGHD pages, re-verify H78-GSC 30/30 gates, rebuild release_audit.json, and run full test suite
.venv/bin/python scripts/publish_mghd.py
.venv/bin/pytest -q tests
```

---

## 2. Shared Template Fixes (`vendor/gems57/uniqueness.py` — Never Forked Privately)

Documented in [`registry/shared_template_review_2026-10-22.json`](registry/shared_template_review_2026-10-22.json):
1. **`IR-78-VENDOR-UNIQ-01` (Silent duplicate pass bug):** `compare_array_to_registry` previously returned key `forward_overlap_mine_in_theirs3px` without `forward_overlap`, causing `binding_duplicate_decision(rows)` (`row.get("forward_overlap")`) to silently return `duplicate=False` on real duplicate rows! Fixed in `vendor/gems57/uniqueness.py` with unit regression test `tests/test_mghd.py::test_vendor_uniqueness_rows_feed_binding_decision_directly`.
2. **`IR-78-VENDOR-UNIQ-02` (Asymmetric Spearman sign check):** Fixed `rho > RHO_LIMIT` to `abs(rho) > RHO_LIMIT` so strongly inverted continuous surfaces (`rho = -1.0`) cannot slip past Gate 1A.
3. **`IR-78-VENDOR-UNIQ-03` (15× faster exact Euclidean disk dilation):** Replaced generic 2D structuring-element `binary_dilation` inside `_near` with a mathematically identical row-interval + column-max separable decomposition (`tests/test_mghd.py::test_separable_near_matches_scipy_binary_dilation_exact`), enabling full exact `1,114`-raster scanning across all `84` accessible sibling repositories.

---

## 3. Limitations & Next Steps

1. **Sandbox network boundary:** `www.drivendata.org` cannot be fetched directly inside this sandbox, so weekly submission slot count and live leaderboard receipts must be confirmed directly on the competition portal when uploading `gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.zip`.
2. **Next-week ensemble opportunity (`H78-MGHD + H78-GSC`):** `H78-MGHD` (`Seed 20: 0.1952`, `Seed 30: 0.2007`, pure 123-col geodetic + hydrothermal + 1 m LiDAR + 400 m gravity) and `H78-GSC` (`Seed 20 OOF: 0.1898`, `3-Seed OOF: 0.1976`, 150-col PU scarp + Coulomb relay bridges) have score-surface correlation `Spearman rho = +0.0888` and dot overlap `0.5587 <= 0.70`, making their out-of-fold stack with `36,000–39,000` `min_dist=3.01` submodular dots the prime candidate for the next weekly submission window.

---

## 4. Embedded Governing Prompt, Protocol & User Instructions (Verbatim Reference)

```text
Review `/home/user/GEMSDOE78`, study why `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778`)
outperformed earlier GEMSDOE submissions and how it relates to higher reported scores (`0.3195`, `0.4413`),
and deliver an end-to-end, 3-pass verified competition repository and GitHub Pages site:

- MUST generate a unique single-band float32 GeoTIFF submission matching sample_submission.tif CRS (EPSG:32611),
  shape (3730x3292), and geotransform; finite values strictly in [0, 1] (never NaN inside footprint; prevent
  "Predicted values must be in range [0, 1]" error); automated validation with zero deferral to a human inspector;
  unique submission name and <=140-char note; unmistakable top-of-site OK TO DOWNLOAD / OK TO SUBMIT status.
- Parallel-Run Protocol:
  1. Single assigned method lane; check surface before placement (|Spearman rho| > 0.90 stops) and final dots
     against registry rasters (forward 3-px overlap > 0.70 stops).
  2. Reuse shared cached feature stack, shared evaluate_holdout.py, and submission_writer.py; fix shared bugs once
     in vendor/gems57 with a report — never keep a private fork.
  3. Buffered whole-segment hide-and-recover spatial holdout; label every score HOLDOUT-DTI (evaluator version,
     withheld positive count, 95% CI) or ORGANIZER-CONFIRMED (receipt-backed); never write projections as scores.
  4. Single-feature leakage canary on every feature (symmetric AUC > 0.90 = leakage until proven otherwise).
  5. Propose & rank 3-5 novel geological hypotheses naming layers, transform, hidden-fault physics, non-fault mimic,
     and difference from existing repo code.
  6. Stop within <=3 experiments and <=2 hours; emit JSON Run Card; execute Pass 1 -> Pass 2 -> Pass 3; open PR and merge onto main.
```
