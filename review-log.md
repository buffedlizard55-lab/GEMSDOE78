# Review log — GEMSDOE78 initial repository audit

## Pass 1 — inventory and source verification

- `git ls-files` and the repository root showed one tracked file (`README.md`) and no data, source code, tests, package/config, cached feature stack, evaluator, writer, validator, or TIF.
- GitHub API shows Pages is already configured to serve the `main` branch root at https://buffedlizard55-lab.github.io/GEMSDOE78/ (legacy source). Added root static HTML pages; did not add a competing Actions deployment workflow.
- Read the linked GEMSDOE32 page. It marks the H33-2-B2 artifact as not organizer-scored and describes proxy/Monte Carlo results separately. Consequently, the user-supplied 0.2778 cannot be treated as an organizer score sourced from that page.
- Read the official DrivenData problem page and submission-format section, USGS GeoDAWN record, GBCGE INGENIOUS project page, EPSG:32611 record, and official public leaderboard. Official format requires a single float32 band, values from 0 to 1, matching projected CRS, resolution and bounds, and null/NaN outside bounds. USGS lists the GeoDAWN magnetic/radiometric data release and its DOI.
- Rejected generation of an arbitrary or copied TIFF because no inputs, shared evaluation tools, duplicate-reference raster, or validation capability exist.

## Pass 2 — implementation and scientific-risk review

- Added README operating rules, evidence classifications, source links, ranked untested hypotheses, known blockers and ordered next actions.
- Added a visible static home page and executive-summary/submission page. Both explicitly show a blocked/no-file state; neither advertises a fictitious download.
- Added machine-readable negative run card with null result fields and explicit reasons for unrun checks.
- Reviewed hypothesis claims for overstatement: all are labeled untested; improvement ranks are qualitative and no score is projected. The external radiometric source is identified as official/public, but actual files are not claimed downloaded or checksum-verified.

## Pass 3 — cross-check against user requirements and edge cases

- Confirmed no competition slot was selected/spent, no sibling TIFF was copied, and no performance score is fabricated.
- Confirmed the project explicitly flags missing lane paragraph/registry rasters, so no correlation/overlap assertion is invented.
- Confirmed the result and TIF validator remain negative because the sample grid/footprint/data are absent; JSON uses `null` for unavailable measurements.
- Confirmed the site link to a submission file is intentionally absent and the prominent status says not to submit.
- Pending: authorized competition data placement; shared tools/template availability; a named single-method lane; registry-raster surface/final duplicate checks; leakage canaries; preregistered holdout; resulting byte-level validator; official receipt if an authorized competitor submits.

## Values that are scores

- **ORGANIZER-CONFIRMED**: official public leaderboard snapshot read 2026-10-21 UTC lists rank 1 `xiaofanhu` at 0.4413 and rank 2 `cfld__` at 0.3904. The dynamic leaderboard should be checked again before operational decisions.
- The user-prompt value 0.2778 for the GEMSDOE32 artifact is not confirmed as an organizer score by the linked page, which explicitly says no organizer score exists for its artifact. It is not an experiment result of this checkout.
- No **HOLDOUT-DTI** measurement was performed in this checkout. No DTI value or CI is reported for the hypotheses.
