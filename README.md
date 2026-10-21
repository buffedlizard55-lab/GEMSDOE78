# GEMSDOE78 — H78-MPC monogenic phase-congruency lane (DOE GEMS Prize, DrivenData #306)

## ⬇ ONE-CLICK SUBMISSION FILE — ✅ OK TO DOWNLOAD & SUBMIT (verdict: promote)

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE78/ — the download banner, exact submission
name, 140-char note, and step-by-step portal guide are at the top of the front page and in
[`docs/executive-summary.html`](docs/executive-summary.html).

| | |
|---|---|
| File | `gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif` |
| SHA-256 | `c7932fbda98120b5abce37247852220befe1798dac4828fd58f785534e081256` |
| Unique name | `gems78-h78mpc-monogenic-pc-spaced-37654-20261021` |
| Note (111/140) | `H78-MPC monogenic phase-congruency LOQO HGB, spaced 2.5px emit; HOLDOUT-DTI 0.098 vs 0.094 H33 ctrl; 37654 dots` |
| Download OK? | **YES** — all 12,279,160 cells finite in [0,1], 0 NaN, nodata=None (portal "[0,1]" error impossible), single-band float32, EPSG:32611, 3730×3292, transform = sample submission, 37,654 spaced binary dots, 0 on catalogue (min 2.83 px) |
| Submit OK? | **YES** — preregistered gate passed after disclosed emission-defect correction (below). 0 slots spent by this system; check the weekly cap on the submission page, upload once |
| Evidence | HOLDOUT-DTI **0.0977 [0.078, 0.116]** (`gems57-pooled-hide-v2`, seed 20, 11,321 withheld positives) vs fold-fair H33 control 0.0939 [0.080, 0.107] (paired +0.0038 [−0.012, +0.020], **not significant**) and vs no-MPC ablation 0.0856 (paired **+0.0121 [0.0027, 0.0217], significant**). No ORGANIZER-CONFIRMED score exists for this file; no projection is written as a score |

## Why H33 scored 0.2778 and how to beat it (one paragraph)

DTI (α=0.2, β=0.8, 300 m triangular kernel) is a budget: one more non-redundant dot helps iff its
kernel credit `k > 0.2·DTI` (bar = 0.0556 at 0.2778). H33 multiplied the three strongest measured
effects in the fleet's live-score ladder — highest-credit-density parent surface (h19-5 multi-lineament
corroboration, 0.1922 continuous), kernel-matched ~2.8 px dotted thinning (→0.2600–0.2708), and the B=2
catalogue-flank prune deleting zero-credit mass (→**0.2778**, all user-reported receipts). Beating it —
and the user-reported 0.4413 leaderboard top (≈59% more credit/dot at equal mass) — requires a better
*ranking*, not better thinning. This lane supplies one measured ranking improvement (MPC, below);
full forensic ledger in [`docs/why-h33.md`](docs/why-h33.md).

## This lane (unique — not implemented in GEMSDOE–GEMSDOE77)

**H78-MPC:** monogenic (Riesz-transform) multi-scale *phase congruency* — a contrast-invariant
step-edge signature — on RTP magnetics, isostatic gravity, detrended elevation and depth-to-basement
(σ = 1/2/4 px; PC + amplitudes + mean-phase + orientation coherence + Frangi = 32 features) over the
48-band competition + GeoDAWN/LiDAR/topo stack; leave-one-quadrant-out gradient boosting trained only
on visible catalogue faults; spaced 2.5 px emission of exactly 37,654 dots. Blind faults weak in
gradient *amplitude* (every prior edge lane's signal) still carry a coherent *phase* step.
Mimic: lithologic contacts / flight-line seams. Five ranked hypotheses were preregistered before
Experiment 1: [`docs/research-hypotheses.md`](docs/research-hypotheses.md) ·
[`registry/preregistration_h78_mpc.json`](registry/preregistration_h78_mpc.json).

**IR-78-EMIT-01 (own-the-outcome disclosure):** Pass 1's preregistered allocator emitted contiguous
dot runs (98.9% of dots with a neighbour ≤1.5 px; control median spacing 3.16 px) and scored
HOLDOUT-DTI 0.0471 ≈ random. Pass 2 re-emitted the *frozen* surfaces with the control's spaced
emitter (no retraining): 0.0977. The MPC paired effect is significant under both emitters; both
readings are retained in `evidence/` and the run card.

**Automated gates (no human inspection):** leakage canaries before fitting — max symmetric AUC
0.6105 ≤ 0.90 (80/80 PASS); uniqueness on surface before placement (max |Spearman ρ| 0.1546 ≤ 0.90)
and on final dots (worst mutual 3-px overlap 0.4879 ≤ 0.70 across 74 unique registry rasters);
fail-closed format validator re-reading the written bytes (15/15 checks PASS).

## Reproduce

```bash
pip install -r requirements.txt
python3 scripts/restore_data.py          # sha256-verified data from sibling repos -> .cache/gems_data
python3 scripts/build_features.py        # 80-band stack (48 base + 32 MPC family)
python3 scripts/run_experiments.py       # preregistered E1/E2/E3 + controls (Pass 1)
python3 scripts/pass2_spaced_emission.py # IR-78-EMIT-01 correction on frozen surfaces
python3 scripts/build_production.py --bands all   # full-catalogue LOQO surface (Pass 1 packaging)
python3 scripts/pass2_rebuild_production.py       # spaced production dots + uniqueness + TIF/ZIP
python3 scripts/make_figures.py && python3 scripts/build_run_card.py && python3 scripts/build_site.py
python3 -m pytest tests -q               # 8 tests
```

Shared tools are reused, not forked: `vendor/gems57/` is copied byte-identical from the sibling
template (GEMSDOE73) — `evaluate_holdout.py` (`gems57-pooled-hide-v2`), `metric.py`,
`submission_writer.py`, `validate.py`, `uniqueness.py`. Evaluator hashes are recorded in the run card.
Instrument identity was verified by reproducing the published controls exactly
(h33_analogue_foldfair 0.0939, random 0.0484).

## Standing brief (read at the start of every session on this repo)

**Mission.** Generate a *unique*, high-scoring GeoTIFF submission for the DOE GEMS Prize
(DrivenData #306) and make it *obvious* on the site whether the file is OK to download and OK to
submit. Automate all inspection/validation inside the project — no human-in-the-loop checking.

**Parallel-run protocol.** ① Stay in lane: surface rank-correlation >0.90 or >70% of dots within
3 px of one registry raster (mutual-overlap refinement per GEMSDOE70/73 precedent, all readings
disclosed) = duplicate, stop. Check on the surface before placement AND on final dots.
② Reuse the template's cached stack, `evaluate_holdout.py`, `submission_writer.py`; hide-and-recover
holdout (whole segments + buffer, visible-only features, pixel-exact masking, pooled DTI α0.2 β0.8
300 m triangular). Fix shared tools in the template, never private forks.
③ Label every number HOLDOUT-DTI (evaluator version, withheld count, 95% CI) or ORGANIZER-CONFIRMED
(receipt copy). A projection is never a score.
④ Leakage canary: every feature alone on the holdout first; AUC >0.90 = leakage until proven otherwise.
⑤ One JSON run card: hypothesis, mechanism, mimic process, HOLDOUT-DTI+CI, registry correlation/overlap,
raster sha256, validator output, submission name + ≤140-char note, verdict promote/negative.
Negative results are deliverables. ⑥ Budget: ≤3 experiments / ≤2 h; never auto-spend a weekly slot —
promotion is a human selector step within the portal's weekly cap.

**Benchmarks to beat** (user-reported receipts): fleet best `h33-h33-2-b2` **0.2778** (GEMSDOE32);
competition leaderboard top **0.4413**. Study-of-record for *why*: [`docs/why-h33.md`](docs/why-h33.md).

**Core values.** *Maximize P(Win)* — every decision weighs tradeoffs toward the highest probability of
winning. *Own the Outcome* — own results end-to-end, publish failures measured, improve from signals.

**Work line by line from official verified sources; flag irregularities; no hallucinations.**
Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ·
Rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf ·
Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution ·
USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
INGENIOUS/GDR 1391: https://gdr.openei.org/submissions/1391 · EPSG:32611: https://epsg.io/32611 ·
Phase congruency: https://peterkovesi.com/projects/phasecongruency/index.html ·
Monogenic signal: Felsberg & Sommer, IEEE TSP 2001 https://www.diva-portal.org/smash/get/diva2:241550/FULLTEXT01.pdf

**Known limitations / next session.** ① DrivenData login data cannot be fetched in-sandbox; the
sha256-verified restore path via sibling repos is the workaround (`scripts/restore_data.py`).
② Candidate-vs-control holdout delta is non-significant; the live score is unknown until a selector
spends a slot — record the receipt as ORGANIZER-CONFIRMED when it exists.
③ Next preregistered test: MPC features on top of a visible-network-context LOQO model (sibling
holdout 0.16–0.19 recipe) with per-quadrant mass quotas, same instrument, same gate.
④ Registry uniqueness here covers 74 rasters from 4 sibling checkouts + scored set, not the full
~1,000-raster fleet inventory; widen before any second slot.
