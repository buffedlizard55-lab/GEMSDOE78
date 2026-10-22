# Why H33-2-B2 appears first in the family ledger — evidence vs inference

Short answer: H33 is D2.8 with the 6,436 near-catalogue dots deleted — an
emission-pruning change on an unchanged detector, not a new geothermal or
structural discovery. The plausible metric mechanism is removed false-positive
mass; no causal organizer-score improvement is established because no
submission-page receipt exists.

## 1. Measured structure (RASTER-GEOMETRY-DIAGNOSTIC, not a score)

Reproduced in this checkout (`evidence/h33_geometry_review_2026-10-22.json`,
`evidence/forensics_h33_vs_d28.json`; inputs SHA-pinned in
`registry/data_manifest.json`):

- H19-5 solid = 121,131 binary line pixels (owner-report 0.1922).
- D2.8 = 44,090 binary dots, all on the H19-5 lines, nearest-neighbour spacing
  min √8 ≈ 2.83 px / median 3.0 px (owner-report 0.2600).
- H33 = 37,654 binary dots and is **exactly** D2.8 minus every dot within 2 px
  (200 m at the 100 m grid) of the catalogue: 6,436 removed dots, all 1–2 px
  from mapped traces. Verified by `python scripts/review_h33.py`.
- All three are binary {0, 1}, zero on the catalogue, zero outside the
  5,167,373-cell footprint; grid EPSG:32611, 3730×3292, sample transform.

## 2. Score provenance (what the numbers actually are)

- The pinned GEMSDOE32 owner page (commit `f62038b…`, `docs/index.html`) calls
  H33-2-B2 `projected 0.2747; UNSCORED` on a `0.2708 base`. It is a projection
  on an owner page, not a submission-page receipt.
- The `0.2778` figure in the prompt is a user-supplied owner report with no
  receipt exposed in any repo (IR-78-13 / IR-78FW-01). Likewise the prompt's
  `0.3195` and `0.4413` leaderboard figures conflict with each other and with
  the sibling-observed 2026-10-21 snapshot (#1 xiaofanhu 0.4413); none was
  re-fetched here because DrivenData is outside the sandbox network allowlist.
- **No number in this repo is ORGANIZER-CONFIRMED.** `registry/live_scores.csv`
  is empty by design until a receipt exists.

## 3. Metric mechanism (PhD-level inference from the official DTI form)

Competition DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw) with a 300 m triangular
kernel, max credit per truth pixel, and mapped-catalogue pixels masked
(problem page §967; staff forum 11516; implemented in
`vendor/gems57/metric.py`). Consequences:

1. **Binary sparse dots are optimal for a fixed ranking.** DTI is a ratio of
   functions linear in each pixel value, so the optimum over values is a
   vertex: every emitted pixel should be 0 or 1. All top family files are
   binary.
2. **A dot helps only if its kernel credit exceeds ≈0.2·DTI** (≈0.056 at
   DTI 0.28). A second dot within 300 m of already-credited truth earns
   nothing (max-credit) but still pays 0.2 — hence sparse ≥2.83 px emission
   beats dense lines (H19-5 solid 121k px → D2.8 44k dots).
3. **The ≤2 px flank prune plausibly removed below-break-even mass.** A dot
   1–2 px from a mapped trace can only earn credit from an *unmapped* fault
   within 300 m of a mapped one; the family chain's reported gains say that
   population is thin — hidden test faults lie mostly >200 m from the
   catalogue (H33 dots sit at median 19.6 px ≈ 2 km; p10 = 4 px).
4. **Direction is not guaranteed.** Removing dots can also remove recall; the
   DTI denominator moves with both coverage and prediction mass, so a
   leaderboard value cannot be linearly converted into mean per-dot credit,
   and no new-detector conclusion follows from pruning alone.

## 4. Can we score higher than 0.2778?

Only with a *field* whose top ~35–45k dots carry more kernel credit on
unmapped faults than H19-5's — a detector problem, since the emission grammar
is near its break-even. The family pattern (owner reports) is that every file
≥0.23 is an out-of-fold learner trained on the catalogue and emitted as sparse
dots, while every physics-first field without catalogue learning scored
0.00–0.16: hidden test faults appear drawn from the same mapping process as
the catalogue, so P(fault|features) learned from the catalogue — with
catalogue *location* excluded — is the Bayes-relevant target. This repo's
hide-and-recover instrument tests exactly that (H78-A 0.1826 vs unsupervised
≈0.05), but the holdout rewards near-catalogue placement (withheld truth
median 9 px from visible faults) while H33-style live strength sits far from
the catalogue — so holdout numbers must not be read as live mirrors. The only
way to know a live score is an organizer receipt.

Earlier narrative versions of this page are superseded by
[the scientific release review](review-release.md) and, for the current
protocol status, [the 2026-10-22 review](review-2026-10-22.md). No new external
literature was verified from this sandbox; links above are for manual review.
