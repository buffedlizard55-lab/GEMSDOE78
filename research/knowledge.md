# GEMSDOE78 knowledge store — verified facts only

Every entry carries a provenance class: **MEASURED** (computed in this repo from SHA-256-pinned files; script named),
**OFFICIAL** (organizer / agency document; URL given, fetch status stated), **FAMILY** (a statement from a sibling
GEMSDOE repo — a claim, not independently authenticated), **LITERATURE** (peer-reviewed / agency science, URL given).
This sandbox can only reach github.com, so every non-GitHub URL is listed for *manual* review; none was re-fetched here
unless stated. `registry/sources.json` is the machine-readable twin of this file.

## 1 Competition mechanics

| Fact | Class | Evidence / link |
|---|---|---|
| Grid: EPSG:32611, 3730 × 3292 px, 100 m, transform (100, 0, 243350, 0, −100, 4508550) | MEASURED | read from `data/bridge/sample_submission.tif` (`scripts/verify_tif.py`); CRS definition https://epsg.io/32611 |
| Scoring footprint 5,167,373 px; catalogue 60,988 px in 3,199 8-connected components | MEASURED | `evidence/forensics_h33_vs_d28.json` |
| Metric: DTI = TPw / (TPw + α·FPw + β·FNw), α = 0.2, β = 0.8, triangular kernel k(d) = max(1 − d/300 m, 0) | OFFICIAL (transcribed) | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ; implemented and brute-force-tested in `vendor/gems57/metric.py` |
| Known USGS/INGENIOUS fault pixels are masked from scoring; "new fault" = any fault pixel not already in the catalogue | OFFICIAL (staff posts, FAMILY-fetched) | https://community.drivendata.org/t/11516 , https://community.drivendata.org/t/11536 (quoted in GEMSDOE32 knowledge base, fetched there 2026-10-03) |
| Submission: single-layer 100 m GeoTIFF (or zip), values in [0, 1]; previous portal rejection text "Predicted values must be in range [0, 1]" | OFFICIAL + user report | rules PDF https://docs.nlr.gov/docs/fy26osti/96647.pdf ; prompt (PROMPT.md) |
| Weekly submission cap and single final selection across prize rounds | OFFICIAL | rules PDF §3.4–3.6 (cited via GEMSDOE32 `research/official-rules-review-2026-10-03.md`) |
| Organizer reference solution: U-Net with Monte-Carlo cross-validation (Prof. John Lipor) | OFFICIAL | https://github.com/drivendataorg/gems-prize-reference-solution — README fetched 2026-10-21 |
| Leaderboard tops quoted in prompt: 0.4413 (GEMSDOE family claim) / 0.3195 / 0.3262 (2026-10-04) | FAMILY | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (login; not reachable here) |

**Metric consequences (derived, MEASURED by algebra on the official formula):** a dot of credit c changes DTI by
≈ (c − 0.2·DTI·(1−c)) / denominator, so an emitted pixel helps only when its max-credit exceeds ≈ 0.2 × DTI (0.032 at DTI 0.16; 0.056 at 0.28). Max-credit per truth pixel means a second dot within 300 m of the same truth adds cost and no credit → sparse dots ≥ 2.83 px apart dominate dense lines (the D1.5 → D2.8 → H33 chain).

## 2 Why H33-2-B2 scored 0.2778 (FAMILY score, MEASURED structure)

* H19-5 solid: 121,131 line pixels, owner-report 0.1922. D2.8: 44,090 binary dots placed on those lines with NN spacing min 2.83 / median 3.0 px, owner-report 0.2600. H33-2-B2: the exact 37,654-dot subset of D2.8 obtained by deleting every dot ≤ 2 px from the catalogue (6,436 dots), owner-report 0.2778. SHA-256s: H33 c55bafc4…, D2.8 91eae1ca…, H19-5 ec1f9b56… (`evidence/forensics_h33_vs_d28.json`).
* The whole 0.19 → 0.28 climb is emission geometry on one unchanged detector. By the formula above, the 6,436 removed near-flank dots earned mean credit < 0.055 each, i.e. less than 40 % of the average dot — the near flank of mapped faults is poor live truth territory.
* Ceiling reasoning: at 0.2778 with ~37.6k dots the average dot credit is ≈ 0.13; to pass 0.32 the same budget needs ≈ 0.16 per dot, which requires a better *ranking* of candidate pixels (detector), not more thinning — hence lane H78 changes the detector and keeps the emission grammar.

## 3 Geology that motivates lane H78

| Fact | Class | Link |
|---|---|---|
| Great Basin geothermal systems concentrate at fault step-overs, terminations, relay ramps and intersections of sub-parallel normal-fault arrays; strands within an array share regional strike | LITERATURE | Faulds et al., OSTI 1110517 https://www.osti.gov/servlets/purl/1110517 |
| GeoDAWN: USGS airborne magnetic and radiometric survey, NW Great Basin (source of the magnetic/radiometric bands) | OFFICIAL | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and |
| INGENIOUS (GBCGE) and the GDR 1391 data package (fault catalogue, geodetic strain, conductivity, basement depth) | OFFICIAL | https://gbcge.org/current-projects/ingenious/ , https://gdr.openei.org/submissions/1391 |
| Catalogue strike field in the footprint is coherent at the 4 km scale (median coherence 0.56 of the σ = 40 px structure tensor) | MEASURED | `evidence/h78_run_card.json["features"]["coherence_median"]` |
| No free public catalogue supplies new faults: GDR QFaults v2 lies within 300 m of the competition catalogue for 59,064 / 59,065 px; SGMC contacts score 0.05 off-catalogue | FAMILY (GEMSDOE32 §7) | GEMSDOE32 knowledge base |

## 4 What this repo measured (HOLDOUT-DTI, evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives)

* Leakage canary clean: max single-feature AUC 0.586 (threshold 0.90).
* A2 steered vs A1 isotropic vs A0 raw-19, all B2 @ 44,090 dots: 0.1586 / 0.1462 / 0.1376; paired Δ A2−A1 +0.0124 [+0.0032, +0.0223]; A2−A0 +0.0210 [+0.0107, +0.0326].
* Flank radius: B3 @ 44,090 = 0.1826 [0.1628, 0.2004], Δ vs B2 +0.0240 [+0.0196, +0.0281]. Candidate dots 2–3 px from visible faults earn mean credit 0.014 (break-even 0.032).
* Far-truth stratum (> 10 px from any visible fault, 5,150 positives): A2 0.066 vs A1 +0.0147 [+0.006, +0.024], vs A0 +0.0283 [+0.017, +0.040]; on par with D2.8.
* Distance-to-catalogue profile of the shipped primary: median 6.0 px, 43 % ≤ 5 px (H33: 19.6 px, 15 %). Open risk IR-78-09.

## 5 Standing rules for every session
Read PROMPT.md and README.md first. Label every number. Never write a projection as a score. Check uniqueness before placement and on final dots. Fix shared tools in the template, never fork. Three experiments or two hours, then stop and write the run card.
