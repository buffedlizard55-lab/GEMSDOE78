# Task & Protocol Reference (`GEMSDOE78`)

This document preserves the full competition engineering brief and Parallel-Run Protocol governing Session 2 of `buffedlizard55-lab/GEMSDOE78` (DrivenData Competition 306 — DOE GEMS Hidden Fault Discovery across the Great Basin).

## Core Objectives
1. **Execute Prior Session Next Steps First:** Resolve all open items from Session 1 (`IR-78-BAND6-01` Band-6 `tc` naming fix, strict 4-quadrant out-of-fold `LOQO` evaluation vs global in-sample overfitting, exact C-accelerated 300 m submodular dot emission, 3-seed spatial replication across `Seeds 20, 30, 40`, and full sibling-repository uniqueness auditing).
2. **PhD Forensic Investigation of Live Leaderboard Performance:**
   - Explain why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` achieved **`0.2778`** (`ORGANIZER-CONFIRMED`) on the live DrivenData evaluation metric.
   - Determine mathematically and geologically what is required to surpass `0.2778` and `0.3195` (`ORGANIZER-CONFIRMED`) toward the leaderboard top score **`0.4413`** (`ORGANIZER-CONFIRMED`).
3. **Novel Geological Hypotheses & Validation:**
   - Propose and rank 3–5 novel geological fault-discovery hypotheses naming specific physical layers, mathematical transforms, why they capture *missing* Quaternary/blind faults rather than already-mapped bedrock traces, named non-fault geological mimics, and expected gain vs compute cost.
   - Implement and test on the shared spatially-blocked hide-and-recover evaluator (`vendor/gems57/evaluate_holdout.py`, `gems57-pooled-hide-v2`).
4. **Competition-Ready Unique Submission & Unmistakable Status:**
   - Produce a genuinely unique `.tif` (and `.zip`) submission validated automatically without human intervention (`single-band float32`, `EPSG:32611`, `3730 x 3292`, sample transform, `nodata=None`, finite everywhere, values strictly in `[0, 1]`, `0` on-catalogue pixels).
   - State unmistakably on both `README.md` and GitHub Pages (`docs/`) whether the file is **`OK TO DOWNLOAD AND SUBMIT`**, with working download links, SHA-256 hashes, validator receipt, and copy-paste DrivenData `Name` and `Notes` (`<= 140` chars).
5. **Parallel-Run Protocol Gates:**
   - **Gate 1 (Lane Uniqueness):** Pre-placement surface `|Spearman rho| <= 0.90` AND dot-overlap `<= 0.70` (`3 px` radius) against registered lanes.
   - **Gate 2 (Shared Evaluator & Packaging):** Reuse `vendor/gems57/evaluate_holdout.py` and `vendor/gems57/submission_writer.py`.
   - **Gate 3 (Strict Evidence Labelling):** Every score explicitly tagged `HOLDOUT-DTI` (with evaluator version, withheld positive pixel count, and 95% CI) or `ORGANIZER-CONFIRMED` (live portal receipt). Never report a projection as a score.
   - **Gate 4 (Single-Feature Leakage Canary):** Every single feature tested alone on holdout (`symmetric AUC <= 0.90` required before trusting model scores).
   - **Gate 5 (Compliant Run Card JSON):** Hypothesis, mechanism, named non-fault mimic process, holdout DTI + 95% CI, registry correlation/overlap, raster SHA-256, validator output, submission name + note (`<= 140` chars), and verdict (`promote` / `negative`).
   - **Gate 6 (Budget Discipline):** At most 3 experiment stages within compute budget; never spend live weekly slots automatically; never promote without beating current repo holdout record (`0.18257`).
6. **Three Independent Verification Passes (`Pass 1`, `Pass 2`, `Pass 3`), PR Creation & Merge onto `main`.**
