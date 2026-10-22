# H78-SIG — why H33 leads, why the holdout disagrees, and four ranked candidate hypotheses

Written 2026-10-22 **before** running any new experiment in this session.
Evidence classes are used strictly: every number below is labelled
**HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, seed 20, 11,321 withheld
positive pixels, 95% spatial-block CI, from checked-in evidence files),
**OWNER-REPORTED** (copied from the prompt / sibling sites; *not* an
organizer receipt), **RASTER-GEOMETRY-DIAGNOSTIC** (recomputed from
SHA-256-pinned rasters), or **OFFICIAL-TEXT** (fetched this session from the
competition pages). No number below is ORGANIZER-CONFIRMED, because no
submission-page receipt exists anywhere in this repository family evidence.

## 1. What is verifiably true about the champion H33

1. **Geometry (RASTER-GEOMETRY-DIAGNOSTIC, `evidence/h33_geometry_review_2026-10-22.json`,
   reproduced from pinned rasters).** H33 (`h33-h33-2-b2-…-zeros`, 37,654 dots)
   is *exactly* D2.8 (44,090 dots) minus the 6,436 dots whose distance to the
   USGS/INGENIOUS catalogue is ≤ 2 px (200 m). D2.8 is itself a ≥2.83 px-spaced
   dotted emission of the H19-5 solid multiline field (121,131 positive px).
   So the champion lineage is one surface, three representations:
   solid → spaced dots → spaced dots with the catalogue flank deleted.
2. **Score status (OWNER-REPORTED vs the source site).** The prompt reports
   H33 = 0.2778. The GEMSDOE32 site fetched this session
   (<https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html>, 2026-10-22)
   states the file is **UNSCORED**, "projected live DTI 0.2747 (a MODEL, not a
   score)" and "NO ORGANISER SCORE EXISTS for this or any artifact in this
   repository." The already-scored anchor on that page is the 0.2708 base
   (also owner-reported). **Irregularity IR-78-22-01: the 0.2778 figure in the
   prompt is not an organizer receipt and is contradicted by the source site;
   it must never be written as ORGANIZER-CONFIRMED.** The same applies to the
   prompt's two different "current leaderboard high scores" (0.4413 and
   0.3195), which cannot both be the present maximum (IR-78-22-02).
3. **Why the flank deletion plausibly raised the live score (metric algebra +
   OFFICIAL-TEXT, not a causal measurement).** The official problem
   description (DrivenData competition 306, page 967, fetched this session)
   says the test labels are *new faults manually identified by experts that
   are not contained in the USGS database*, and family-registered staff
   clarification (community thread 11516, quoted in `registry/sources.json`)
   says known fault pixels are masked from scoring. A dot ≤200 m from a
   *known* fault therefore sits in the zone most likely to duplicate a masked
   known fault: it can earn distance-weighted TP only if a *new* fault also
   passes within 300 m, but it always risks the α = 0.2 FP charge. Deleting
   6,436 such dots removes their FP mass while, on the family's own
   live-mirror model, surrendering little TP — hence a higher DTI at
   *smaller* emitted mass (37,654 vs 44,090). The same algebra explains the
   earlier jump solid → dotted: a second dot within 300 m of an already
   covered truth pixel adds FP but (because TP uses `max` over dots) almost
   no TP, so ≥2.83 px spacing raises credit *per dot*. The break-even for one
   more non-redundant dot is kernel credit `k > α·DTI` (`vendor/gems57/metric.py`,
   unit-tested against a brute-force oracle); at DTI ≈ 0.27 the bar is
   ≈ 0.054 mean kernel credit per dot.
4. **Why this file is nearly invisible to our holdout (HOLDOUT-DTI).** On the
   seed-20 hide-and-recover instrument H33-as-is scores ≈ 0.004 per fold
   (`evidence/h78_holdout_seed20.json`): it was built with the *full*
   catalogue, so every dot that could cover a withheld segment was deleted by
   its own ≤2 px rule. **The family champion would be rejected by any gate of
   the form "must beat the holdout best".** That is a property of the
   instrument, not of the file: holdout truth is catalogue geometry (median
   withheld pixel 9.06 px from the nearest visible fault; 54.5% within
   10 px — `evidence/h78_distance_diagnostic.json`), whereas live truth is by
   construction *not* catalogue geometry. The holdout remains necessary — it
   catches leakage and near-random surfaces (the cross-layer lane scored
   HOLDOUT-DTI 0.0478 [0.0366, 0.0589], indistinguishable from a random
   control regime) — but it is **biased toward catalogue-hugging,
   habitat-learning models**. Any promotion gate must therefore include the
   far-from-catalogue stratum explicitly (see §4), pre-registered, instead of
   silently treating overall holdout rank as live rank.

## 2. The scientific gap to exploit

Repository best on holdout, arm A2 (raw 19 bands + isotropic + strike-steered
derivatives, HGB), reaches HOLDOUT-DTI 0.1826 [0.1628, 0.2004] at 44,090 dots
(B3 flank). But stratified by distance of the withheld truth from the visible
catalogue (`evidence/h78_distance_diagnostic.json`), A2's advantage is a
*near*-field advantage: at >20 px (2 km) A2-B3 scores 0.023 vs registry D2.8's
0.0269, and candidate dots 2–3 px from the visible catalogue earn mean kernel
credit 0.0143 — **below** the 0.0317 break-even at that DTI — while dots
5–20 px away earn 0.045–0.047. Interpretation: a classifier fed raw
contextual bands (absolute elevation, strain rate, earthquake density,
basement depth…) learns *where faults have already been mapped* (a habitat /
location prior) in addition to *what a fault looks like locally*. The
holdout rewards the prior because withheld components sit inside the mapped
network; the live test — expert faults missing from that network, in
under-mapped sub-regions — penalises budget spent re-finding the network's
neighbourhood. PhD-level consequence: **to beat H33 live we do not primarily
need a bigger classifier; we need a detector whose score is a local physical
signature only, ranked without a location prior, emitted off-catalogue at
the metric's break-even mass.** H33 additionally left value on the table: it
*deleted* flank dots without refilling the budget with the next-best
off-catalogue locations, and its surface (H19-5) predates the 1 m/10 m
topographic derivatives that are already restored, SHA-pinned, and unused by
the A2 lane in this repo.

## 3. Four candidate geological hypotheses not yet implemented in this repo

Ranked by expected usefulness vs implementation cost. "Expected DTI
improvement" is a qualitative judgement, **not** a numeric projection. All
four use only already-restored, SHA-256-pinned inputs (`registry/data_manifest_gems73.json`);
none needs new external data. Sources of the inputs, for manual review:
official 19-band GeoDAWN/USGS+INGENIOUS stack described at
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>;
GeoDAWN survey provenance <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>;
1 m DEM links are distributed on the competition data page per the same
official text. SGMC/Qfaults catalogue rasters are **excluded by design**
from every candidate: they are label-adjacent fault catalogues and would
fail the spirit of the leakage canary.

| Rank / cost | Layers + physical signature | Why it catches a fault *missing* from USGS/INGENIOUS | Named non-fault mimic | Difference from everything in `src/gems78` |
|---|---|---|---|---|
| **1 / low–medium — TEST (lane H78-SIGX)** | Local signature only: existing σ = 1.5/3 px isotropic + strike-steered Gaussian derivatives of `det_elev, rtp, iso_grav_anom, depth_to_base_surf, cond_surf, tc` (84 features, **raw contextual bands removed**), plus sub-pixel scarp aggregates from the 1 m-DEM-derived `lidar_scarp_features_u8` (excess/step/Laplacian/down-/up-facing maxima, relief, coherence) and 10 m-derived `topo_10m_derived_100m_u8` (slope p90/max, steep fraction, slope std, local relief, profile-curvature max, aspect coherence, hillshade lineament). HGB, visible-catalogue strike field only. | Fault scarps 5–30 m wide are invisible in 100 m `det_elev` but survive as within-cell maxima/relief of 1–10 m topography; regional-scale catalogue mapping systematically misses such small-displacement strands. Removing raw habitat bands stops the budget collapsing onto already-mapped neighbourhoods, so far-field strands compete on signature alone. | Lake Lahontan shoreline benches/beach ridges and road/levee cuts produce identical lidar scarp maxima with no fault. | A2 = raw context + derivatives (habitat prior retained); CS adds along-strike integrals to A2; MPC uses phase congruency + context under a different instrument; cross-layer is an unsupervised 3-field gradient product; TOOTH/SPY manipulate catalogue geometry/labels. No existing arm is signature-only, and none of A2/CS uses the 1 m/10 m external aggregates. |
| 2 / medium — deferred | Potential-field source-edge signature: tilt derivative, analytic-signal amplitude and theta map of `rtp` and `iso_grav_anom` at 0/200/400 m FFT upward continuation; score = persistence of the zero-tilt (source-edge) locus across levels. | A basement fault under basin fill has no scarp to map, but its magnetic/density source edge persists with upward continuation while near-surface noise and survey seams decay. | Dipping intrusive/lithologic contacts give persistent source edges with no fault offset. | Repo has centred Gaussian derivatives and (in MPC) phase congruency, but no tilt/analytic-signal/continuation-persistence features. Family "worm/tilt" lanes exist in sibling repos, so novelty would rest on numeric decorrelation, to be measured, not asserted. |
| 3 / medium — deferred | Drainage-discontinuity signature from `dem10_chi_100m_i16` + `dem10_chi_100m_u8`: χ-profile step (step_max/step_min), `ksn` maxima and knickpoint counts required to be collinear across adjacent channels along the visible-strike tangent. | A subtle unmapped strand repeatedly perturbs channel long-profiles crossing it, even where no continuous scarp is preserved on fans/playas. | Lithologic knickpoints at resistant beds and Lahontan spillway channels align across drainages without faulting. | No drainage/χ feature exists in `src/gems78`. One sibling χ lane reported OWNER-REPORTED 0.0351 as a standalone emission, which is why this is ranked below SIGX despite low marginal cost. |
| 4 / medium–high — deferred | Broad antisymmetric flank warp: after local planar detrending of `det_elev` and `depth_to_base_surf`, fit a wide (±0.5–1.5 km) opposite-sign flank residual centred on a candidate trace, corroborated by a central potential-field step. | Distributed folding above a buried, still-propagating tip predates any mappable surface rupture. | Differential compaction across a basin-margin facies change produces the same warp. | Existing features are narrow (σ ≤ 3 px) centred derivatives; no parametric wide-flank profile is fitted anywhere in the repo. Confidence low: 100 m sampling may not resolve the warp above fan morphology. |

## 4. Validation gates adopted for this session (automated, no human inspector)

The previous session proved the *literal* parallel-run overlap rule
unsatisfiable: a SHA-pinned continuous registry probability raster is
positive on all 5,167,373 footprint cells, so every possible dot has forward
3 px overlap 1.0 > 0.70 with it (`docs/review-2026-10-22.md`). Silently
waiving that would be dishonest; so is pretending any new file can pass it.
This session therefore applies the following *explicit, corrected* gate set
and flags the correction for owner ratification (IR-78-22-03). The literal
witness is still measured and reported (as its budget-matched top-K support,
the only like-for-like comparison a probability field admits), never hidden.

- **G1 Format (fail-closed):** independent re-read verifies single-band
  float32, EPSG:32611, 3730×3292, exact sample transform, all cells finite,
  values in [0,1], binary {0,1}, zero outside footprint, zero on catalogue,
  no nodata tag, ZIP contains exactly the same TIFF bytes. This is the class
  of failure behind the portal error `Predicted values must be in range [0, 1]`
  (NaN/sentinel values or a sentinel nodata tag; both excluded here).
- **G2 Leakage canary:** every candidate feature alone on the holdout,
  symmetric AUC ≤ 0.90 (protocol rule 4).
- **G3 Holdout competence + far-field endpoint (pre-registered):** on the
  unchanged seed-20 instrument the candidate must (a) beat a matched random
  control and the fold-evaluated registry D2.8 dots overall, and (b) be
  reported overall **and** on the >10 px and >20 px far strata against the
  reproduced A2 control with paired spatial-block CIs. "Beats current
  holdout best overall" is reported as its own line, not assumed.
- **G4 Uniqueness (corrected registry policy):** pre-placement surface
  |Spearman ρ| < 0.90 **and** final forward dot overlap (≤3 px) < 0.70
  against every restored *sparse* registry/production raster; continuous
  registry fields are compared at matched-budget top-K support and also
  reported literally. Registry scope is stated exactly (restored pinned set
  + this repo's six published files + H33); it is not claimed to be an
  exhaustive inventory of all ~83 sibling sites.
  *Amendment (2026-10-22, after E1/E2, before production naming):* "sparse"
  is operationalised with the shared template's own classes
  (`vendor/gems57/uniqueness.py`): a comparator whose 3 px halo covers
  ≥ 0.70 of the allowed domain is *space-filling* — measured for exactly 2
  of the 20 restored comparators (13GEMSDOE lattice-s5, halo 0.999, binary;
  17GEMSDOE E-proba, halo 1.000, graded). Graded space-filling fields keep
  the top-K rule above; binary space-filling fields (no ranking exists) are
  gated on exact-dot-set Jaccard < 0.50 (the template's `JACCARD_LIMIT`),
  with reverse overlap reported. All other comparators keep the literal
  forward-overlap rule. Literal statistic values are published for every
  comparator regardless of class. Implementation:
  `src/gems78/registry_check.py` (G4 v2).
- **G5 Emission geometry:** binary dots, mutual spacing ≥ 2.8 px, production
  flank > B px from the *full* catalogue with B chosen on the holdout from
  {3, 5} (visible-only there), budget from {37,654, 44,090} chosen the same
  way, zeros (not NaN) outside the footprint.

A file is labelled **OK TO SUBMIT** on the site only if G1–G5 all pass;
otherwise it is published, if at all, as `…-DO-NOT-SUBMIT` inspection-only
with the failing gate named. Passing G1–G5 is a *project* validation, never
an organizer score. Using a weekly slot remains the separate selector step
required by protocol rule 6 and the official weekly cap.

## 5. Can this beat 0.2778?

Honest answer: **unknown, and not claimable in advance.** The target itself
is OWNER-REPORTED and contradicted by its source site (§1.2). What can be
said mechanistically: H33's live advantage comes from representation
(spacing + flank), which SIGX keeps; SIGX additionally (i) refills the
pruned budget with the next-best off-catalogue signature maxima instead of
emitting 6,436 fewer dots, (ii) ranks by local signature including
sub-100 m scarp evidence H19-5 never had, and (iii) removes the habitat
prior that our own distance diagnostic shows misallocates dots into the
2–3 px sub-break-even halo and under-serves the >20 px far field where D2.8
already beats A2. Each of (i)–(iii) raises expected credit per dot under the
published metric *if* the new faults behave like the withheld far-field
population; the experiment below tests exactly that premise on the only
labelled far-field population available. If it fails, the correct
deliverable is a labelled negative result — not a renamed copy of an old file.
