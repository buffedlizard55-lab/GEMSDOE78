# Current checkout review — 2026-10-22 UTC

## Scope and outcome

Read `PROMPT.md`, `research/USER_REQUEST_2026-10-22.md`, `README.md`, and the existing three-pass review before acting. This session did not generate a new TIFF or start another model experiment: the required lane remains unassigned and the stored protocol certificate proves the literal duplicate/uniqueness gate is impossible for any nonempty in-footprint prediction because one pinned positive-support raster covers every allowed cell. This is a protocol stop, not a scientific result or organizer score. Existing downloads remain explicitly marked **DO NOT SUBMIT**.

## Reproducibility check

At checkout, the Python environment was absent. An initial test attempt therefore could not start (`numpy` missing). Created an ignored local `.venv` from the exact `requirements-lock.txt` pins and ran the shared preflight restore. The preflight exited with its expected negative-stop status `2` while emitting the full certificate; it restored the small hash-pinned files required for offline audit. Rebuilt the common release audit, then ran:

- `.venv/bin/python -m pytest -q tests` — **53 passed**, 9 `PendingDeprecationWarning`s from rasterio/Affine multiplication; no failures.
- `.venv/bin/python scripts/audit_release.py` — exited 0 and refreshed the independent audit/status pages.
- `git diff --check` — clean.

No model experiment or competition slot was used. No portal upload, organizer receipt, current leaderboard lookup, or score claim is made. The refreshed generated JSON and site timestamps are included to keep published status aligned to this verification; the verifier continues to mark all candidates ineligible for submission.

## Limitations and next steps

1. The assigned single-method lane is still absent from the request text; do not invent one.
2. The literal forward-overlap constraint conflicts with the full-support prior: every nonempty allowed prediction exceeds the 70% limit. The policy owner must explicitly revise the support interpretation or threshold before any new lane is attempted. Do not silently exempt full-support rasters.
3. No complete sibling-site registry inventory or live DrivenData leaderboard/weekly-cap feed is available here; the site is a dated static feed, not a current organizer feed.
4. To continue scientific work, make a distinct preregistered hypothesis only after resolving items 1–2, then run the prescribed blinded holdout/canaries and compare with the matched best control. A slot selector must separately verify the official weekly cap and post-submission receipt.

Official/manual-review links and source-access limitations remain documented in `docs/review-2026-10-22.md` and `evidence/source_review_2026-10-22.json`.
