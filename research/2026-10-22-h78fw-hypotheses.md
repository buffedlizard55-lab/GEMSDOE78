# 2026-10-22 session — H78-FW candidate register BEFORE evaluation

Scope: owner-mirrored, SHA-256-pinned 19-band competition stack
(`4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`),
bridge catalogue + sample grid, pinned registry rasters (D2.8, H33, H19-5 solid,
17GEMSDOE saturation witness). Owner mirrors are integrity-pinned, NOT
organizer-authenticated. Target is **missing fault traces**, not direct
geothermal-vent observations. All expected-gain statements below are qualitative
judgments, not numeric projections and not scores. No ORGANIZER-CONFIRMED score
exists for any file in this repo.

The current prompt supplies no identifiable assigned single-method paragraph
(preflight blocker, `evidence/protocol_preflight.json`). This session therefore
defines **one new single lane H78-FW** (hypothesis #1 below) and stays inside
it: no blending with H78-A/CS/SPY/MPC/tooth/crosslayer features, learners, or
rasters. If a registry gate fires, the result is logged as a duplicate with
verdict `negative` and a `DO-NOT-SUBMIT` inspection artifact only. Zero weekly
slots will be used. The literal forward-overlap gate is binding: dense
continuous rasters are NOT silently exempted (see `vendor/gems57/uniqueness.py`
`binding_duplicate_decision`, rule `literal-all-rasters`). Both the literal
(all-rasters) and the informative (dot-fields-only) readings are reported.

## Why H33 appears first in the family ledger (measured, not scored)

- RASTER-GEOMETRY-DIAGNOSTIC (reproduced this session,
  `evidence/h33_geometry_review_2026-10-22.json`): D2.8 = 44,090 dots; H33 =
  37,654 dots; H33 equals D2.8 minus exactly the 6,436 dots within 2 px
  (200 m at 100 m grid) of the catalogue. All removed dots are 1–2 px from the
  catalogue. H19-5 solid = 121,131 line pixels; all D2.8 dots sit on it.
- The pinned GEMSDOE32 owner page (commit
  `f62038b54dcb7767d4d997f80b033cdc3d42bef9`, fetched via codeload tarball this
  session) labels H33-2-B2 `projected 0.2747; UNSCORED` on a `0.2708 base`. It
  is not a submission-page receipt. The user-supplied `0.2778`, `0.3195`, and
  `0.4413` figures are unreconciled user/owner reports, not ORGANIZER-CONFIRMED
  (IR-78FW-01). No causal organizer-score improvement is established.
- Plausible metric mechanism (inference from the official DTI form
  TPw/(TPw+0.2·FPw+0.8·FNw), 300 m triangular kernel, catalogue masked): pruning
  near-catalogue dots removes FP mass that rarely earns kernel credit because
  hidden faults in the test set appear mostly >200 m from mapped traces, while
  keeping recall on far faults. Sparse binary emission also avoids paying
  repeatedly for thick bands (a second dot inside another's kernel earns nothing
  under max-credit but still pays 0.2). Direction of any metric change is not
  guaranteed without hidden truth; removing dots can also remove recall.
- Family pattern (owner reports, not receipts): every file ≥0.23 in the ledger
  is an out-of-fold learner trained on the catalogue and emitted as sparse
  dots; every physics-first field without catalogue learning scored 0.00–0.16.
  Inference: hidden test faults come from the same mapping process as the
  catalogue, so P(fault|features) learned from the catalogue — with catalogue
  *location* excluded — is the Bayes-relevant field. Beating H33 requires a
  field whose top ~35–45k dots carry more kernel credit on unmapped faults, not
  further pruning of the same H19-5 field (near break-even 0.2·DTI per dot).

## Five untested hypotheses (ranked by expected gain per cost)

| Rank / cost / confidence | ID — layers and physical signature | Why an unmapped fault, not just a mapped one | Named non-fault mimic | Difference from checked-in THIS repo |
|---|---|---|---|---|
| 1 / low-medium / low; TEST | **H78-FW broad flank warp + central potential-field step** — `det_elev` detrended by 3 km Gaussian background; wide-scale (σ=8 px ≈800 m) Hessian curvature magnitude as warp score; central discontinuity = geometric mean of robustly normalized `rtp` + `iso_grav_anom` gradient magnitudes at σ=3 px (300 m); composite = √(warp·discontinuity), catalogue-blind, unsupervised | A buried normal-fault tip produces distributed monoclinal warping hundreds of metres wide with no narrow surface rupture for 1:250k compilations; narrow σ≤300 m filters (H78-A/MPC/crosslayer) miss the wide signal while the central basement step persists in magnetics/gravity | Differential sediment compaction across a basin margin (also broad warp + density step); secondarily buried lava-flow edges | No checked-in lane uses wide-scale (800 m) detrended curvature: H78-A uses σ=1.5/3 px steered/iso derivatives as supervised learner inputs; MPC uses phase at 1/2/4 px; crosslayer uses σ=3 px unsigned gradient alignment with no detrending or wide scale; CS integrates narrow responses along strike; tooth uses catalogue spacing. FW is unsupervised and catalogue-blind end to end |
| 2 / medium / low; DEFERRED | **H78-TP throw-polarity coherence** — `det_elev` + `depth_to_base_surf`: signed across-strike step from oriented first derivatives in a data-driven (structure-tensor, catalogue-blind) frame; along-strike sign persistence over ±1 km windows; score = step magnitude × polarity coherence | Consistent downthrown-side polarity along strike distinguishes a real fault scarp from isolated noise even when amplitude is below a mapper's threshold; polarity is invisible to unsigned magnitudes | Monoclinal drape over a buried lava-flow or sill edge (also polarity-consistent) | All checked-in derivative features are unsigned magnitudes/curvatures (|gn|, Hnn as learner inputs, phase congruency, unsigned alignment). No lane tests signed throw persistence |
| 3 / medium / low; DEFERRED | **H78-TB magnetic texture break** — `rtp`, `tmi`, `tmi_hg`: transverse discontinuity of analytic-signal texture energy (local Gabor/pseudogravity gradient energy) rather than gradient-ridge magnitude; requires a lateral change in magnetic character across the candidate line | Intrabasement faults offset magnetic sources and change texture wavelength without a surface scarp or a sharp RTP ridge; surface-mapped catalogues miss them | Lithologic contacts within basement; aeromagnetic flight-line levelling seams (linear, texture-breaking, non-geological) | H78-A uses RTP gradient/Hessian magnitudes as supervised inputs; MPC uses RTP phase; crosslayer uses RTP gradient magnitude+direction. None measures transverse texture-energy change |
| 4 / medium / very low; DEFERRED | **H78-CD conductivity clay-cap edge** — `cond_surf` + `det_elev`: signed flank contrast (median difference of 300 m side boxes across a data-driven lineament) conditioned on a relief residual; requires paired one-sided conductivity step | Fault-controlled permeability creates clay alteration on one side of an unmapped trace with no scarp; topography-only mappers miss it | Playa/evaporitic clay boundaries; soil-moisture/irrigation edges | No checked-in lane uses `cond_surf` flank asymmetry; H78-A uses cond_surf only as pointwise supervised inputs |
| 5 / high / very low; DEFERRED | **H78-SO stepover linking fault** — `det_elev` + `rtp`: ridge-termination endpoint detection, mechanical stepover pairing (separation <2 km, overlap >0), emission in the stepover gap | Relay ramps/stepovers host small linking faults below mapping resolution but predicted by normal-fault mechanics (cf. Faulds step-over settings) | En-échelon dune crests; distributary channel avulsions | No checked-in lane builds an endpoint/stepover graph; CS integrates along strike but does not pair endpoints or emit in gaps |

Ranking is judgment on plausible incremental HOLDOUT-DTI per implementation cost,
not projected scores. All five use only the existing 19-band stack; none depends
on new external data. External-dependent ideas (e.g. H78-G 2020 Mw 6.5 Monte
Cristo rupture from USGS ScienceBase) remain NOT VIABLE in this sandbox: USGS /
DrivenData / NLR / GDR hosts are outside the network allowlist
(github.com, codeload.github.com, api.github.com, pypi only), verified by the
failed fetch policy in prior reviews and unchanged here. No new external-data
availability is claimed.

## Frozen protocol — H78-FW (#1 only)

- Inputs: SHA-pinned stack via `src/gems78/data.py` (`build_stack`,
  `nearest-exact-mask-v2`, log1p on `depth_to_base_surf` already applied in
  cache). Bands: `det_elev` (index 11), `rtp` (1), `iso_grav_anom` (12).
- Surface (catalogue-blind, no labels): (a) detrend: `elev_res = det_elev −
  gaussian(det_elev, σ=30 px)`; (b) warp: Hessian of `elev_res` at σ=8 px,
  `warp_raw = max(|λ1|,|λ2|)` (rotation-invariant wide curvature); robust
  normalize by within-footprint 90th percentile, cap [0,1]; (c) central:
  Gaussian gradient magnitudes of `rtp`, `iso_grav_anom` at σ=3 px, each
  robust-p90 normalized, capped; `central = √(rtp_n·grav_n)`; (d) composite
  `score = √(warp_n·central)`, zeros outside footprint, finite, in [0,1].
  Four canary features: `warp_n`, `rtp_n`, `grav_n`, `composite`.
- Holdout: `vendor/gems57/holdout.py:buffered_component_draw(seed=20,
  hide_frac=0.20, buffer_px=3)` — whole 8-connected components, label-blind
  eroded quadrants, visible-only context (here: no catalogue input at all),
  pixel-exact `masked_known` mask. Evaluator: unmodified
  `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`), pooled DTI
  α=0.2/β=0.8, 300 m triangular kernel, 1000-draw paired 20 km block CI
  (seed 520810). Withheld positives expected 11,321 (asserted).
- Canary: symmetric AUC (max(AUC,1−AUC)) per feature on withheld positives vs
  active background (300k negatives, seed 20); >0.90 stops before emission.
- Emission: existing `src/gems78/emit.py:greedy_dots(min_dist=2.8,
  pool=1,500,000)` + `flank_mask(visible,3.0)` (B3); exactly 44,090 dots
  (D2.8 geometry) for holdout; production allowed =
  footprint & ~flank(full catalogue,3.0). One candidate, one budget, one seed;
  no sweep, no tuning, no seed shopping.
- Comparators on identical folds/terms: registry D2.8 (44,090) and H33 (37,654)
  dots (built with full-catalogue knowledge; H33 structurally capped on
  withheld segments — reported for context, not as beatable controls), plus the
  stored same-draw H78-A best (B3/50,000: HOLDOUT-DTI 0.1843 [0.1658,0.2015];
  B3/44,090: 0.1826 [0.1628,0.2004]) descriptively. No paired cross-lane claim
  without shared terms; paired CI only within this run's own terms.
- Uniqueness: BEFORE placement, exact full-footprint tied-rank Spearman of the
  composite surface vs each available hash-pinned registry raster (D2.8, H33,
  H19-5 solid, 17GEMSDOE saturation witness, all shipped `docs/downloads/*.tif`
  present at run time); |ρ|>0.90 aborts before emission/file creation. AFTER
  placement, forward 3-px dot overlap + full-footprint ρ on final dots; breach
  (>0.70 forward or >0.90 ρ, literal all-rasters rule, dense rasters binding)
  = duplicate, verdict `negative`, `DO-NOT-SUBMIT` inspection artifact only.
  Informative (dot-fields-only) reading reported alongside; it never overrides
  the literal gate.
- Packaging: unmodified `vendor/gems57/submission_writer.py` (zeros mode:
  all-finite binary in [0,1], zeros outside footprint and on catalogue) +
  independent `scripts/verify_tif.py` (12 checks incl. EPSG:32611, 3730×3292,
  sample transform, ZIP single-TIFF roundtrip). Name ≤140 chars,
  `gems78-h78fw-<dots>dots-<UTC>-<sha8>-zeros` or `...-DO-NOT-SUBMIT` if gated;
  note ≤140 chars with HOLDOUT-DTI label and `not a projection` / `NOT OK TO
  SUBMIT` as applicable. Run card JSON per protocol §5.
- Budget: this FW run is experiment 1 of ≤3; ≤2 h for model experiments. No
  second seed unless the preregistered promote gate passes (it requires beating
  the matched best with paired CI lower bound >0, clean canary, literal
  uniqueness pass, and full validator pass — otherwise negative). Zero weekly
  slots used; slot selection is a separate step with a freshly verified cap
  (currently unverified; DrivenData outside allowlist).

## Official / pinned sources checked this session (manual-review links)

- Organizer reference code (reachable: github): 
  <https://github.com/drivendataorg/gems-prize-reference-solution> — README at
  pinned `aebe92f7c8a990f0e3443451b7a825d9afd6336b` re-fetched via codeload
  2026-10-22 (CPU+GPU supported; data obtained separately). Notebook Tversky
  0.2/0.8 = training loss, not proof of the 300 m scoring kernel.
- Family H33 raster + page (reachable: github):
  <https://github.com/buffedlizard55-lab/GEMSDOE32/blob/f62038b54dcb7767d4d997f80b033cdc3d42bef9/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif>
  (`c55bafc4…`), page `docs/index.html` same ref (`projected 0.2747; UNSCORED`).
- Competition / leaderboard / rules / GeoDAWN / GDR (NOT fetched: hosts outside
  sandbox allowlist): <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>,
  <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>,
  <https://docs.nlr.gov/docs/fy26osti/96647.pdf>,
  <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>,
  <https://gdr.openei.org/submissions/1391>. No live score, cap, rule, or
  external-data availability is asserted from these here.
