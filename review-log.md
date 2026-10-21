# Review log — GEMSDOE78 initial repository audit

## Pass 1 — inventory and source verification

- At the beginning of this work the checked-out branch was based on an initial README-only tree. During the review, `origin/main` advanced via another session's PR #1. We fetched and merged that main update on this branch, preserving its `docs/review-2026-10-21.md` and extending the shared README rather than overwriting the concurrent work.
- The resulting repository has project documentation but no data, model/evaluation code, cached feature stack, evaluator, writer, validator, or TIF.
- GitHub API shows Pages is configured to serve the `main` branch root at https://buffedlizard55-lab.github.io/GEMSDOE78/ (legacy source). Root static HTML pages were added without adding a competing Actions deployment workflow.
- Read the linked GEMSDOE32 page, its H33 artifact audit and method notes. The GEMSDOE32 page says no organizer score exists for H33-2-B2; the inspected GEMSDOE71 page later calls 0.2778 ORGANIZER-CONFIRMED but no DrivenData receipt was exposed in the reviewed sources. Treat the value as **unverified owner-page claim here**, not compliant HOLDOUT-DTI and not independently receipt-confirmed. This is a flagged source conflict.
- Read the official DrivenData problem page and submission-format section, September 2026 DOE/NLR rules, USGS GeoDAWN record, GBCGE INGENIOUS page, GDR 1391 data catalog, EPSG:32611 record, and official public leaderboard. The official format requires a single float32 band, values from 0 to 1, matching projected CRS, resolution and bounds, and null/NaN outside bounds.
- Inspected prior-method descriptions on GEMSDOE32 H33 and GEMSDOE71, 73, 74, and 75. The GEMSDOE71 page already describes GDR 1391 two-metre probes, paleogeothermal deposits and spring/geothermometer data, so our initial radiometric/geothermal ideas would not have been sufficiently novel. They were replaced by provisional Sentinel-1 InSAR, Landsat surface-temperature, and ASTER surface-reflectance hypotheses. All overlap/novelty claims remain provisional because the full fleet registry is absent.
- Checked official Copernicus S1 archive documentation, USGS Landsat Collection 2 surface-temperature availability, and NASA ASTER V004 product status. Public data pathways are listed, but no exact study-footprint scenes were queried or downloaded. NASA's ASTER record warns SWIR detectors stopped functioning in 2009; this limits the ASTER proposal to historical SWIR data.
- The official DrivenData public leaderboard was read on 2026-10-21 UTC: rank 1 `xiaofanhu`, 0.4413, and rank 2 `cfld__`, 0.3904 (**official public-leaderboard snapshot; not a submission-page receipt, therefore not classified ORGANIZER-CONFIRMED under the strict run-card rule**).
- Rejected generation of an arbitrary or copied TIFF because no inputs, shared evaluation tools, duplicate-reference raster, or validation capability exist.

## Pass 2 — implementation and scientific-risk review

- Added README operating rules, evidence classifications, source links, ranked untested hypotheses, known blockers and ordered next actions.
- Added a visible static home page and executive-summary/submission page. Both explicitly show a blocked/no-file state; neither advertises a fictitious download.
- Added machine-readable negative run card with null result fields and explicit reasons for unrun checks.
- Reviewed hypothesis claims for overstatement: all are labeled untested; improvement ranks are qualitative and no score is projected. Copernicus/USGS/NASA catalogs establish source availability pathways, but no study-area scenes were queried, downloaded, or checksum-verified.

## Pass 3 — cross-check against user requirements and edge cases

- Confirmed no competition slot was selected/spent, no sibling TIFF was copied, and no performance score is fabricated.
- Confirmed the project explicitly flags missing lane paragraph/registry rasters, so no correlation/overlap assertion is invented.
- Confirmed the result and TIF validator remain negative because the sample grid/footprint/data are absent; JSON uses `null` for unavailable measurements.
- Confirmed the site link to a submission file is intentionally absent and the prominent status says not to submit.
- GitHub Pages API reports the latest legacy build as `built`, and the executive-summary URL serves the new guide. However, a fetch of the public root still returned the prior README-rendered homepage rather than the new `index.html`; this deployment/routing irregularity is flagged. Added prominent executive-summary and research links near the top of README as a fallback; recheck the live root after the next Pages build.
- Pending: authorized competition data placement; shared tools/template availability; a named single-method lane; registry-raster surface/final duplicate checks; leakage canaries; preregistered holdout; resulting byte-level validator; official receipt if an authorized competitor submits.

## Values that are scores

- **Official leaderboard snapshot (not receipt-backed)**: page read 2026-10-21 UTC listed rank 1 `xiaofanhu` at 0.4413 and rank 2 `cfld__` at 0.3904. These figures are not classified ORGANIZER-CONFIRMED for run-card reporting because no submission-page receipt was copied. Recheck the dynamic leaderboard before operational decisions.
- The requested 0.2778 is an **unverified owner-page claim in this review**: GEMSDOE32 says no organizer score exists for its artifact; GEMSDOE71 later calls it ORGANIZER-CONFIRMED, but no actual DrivenData receipt was present in reviewed sources. It is not a HOLDOUT-DTI result from this checkout.
- No **HOLDOUT-DTI** measurement was performed in this checkout. No DTI value or CI is reported for the hypotheses.
