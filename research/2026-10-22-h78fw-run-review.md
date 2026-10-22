# H78-FW session run review — 2026-10-22 (three passes)

Branch: `arena/a52ff4a8-gemsdoe78`. Scope: one new preregistered lane (H78-FW),
one model experiment, one new inspection TIFF, site + docs + tests. Zero weekly
slots used. No organizer receipt exists for any file in this repo.

## Pass 1 — implementation and verification

1. Re-read README, PROMPT.md, `research/USER_REQUEST_2026-10-22.md` (current
   task text, identical to this session's prompt), `docs/review-2026-10-22.md`,
   and all lane run cards. Confirmed the two standing blockers: (a) no assigned
   single method paragraph; (b) the literal forward-overlap gate is
   unsatisfiable for any nonempty in-footprint candidate (saturation witness
   `ab0a0a62…`, restored and re-verified via `scripts/preflight.py --restore`).
2. Restored the full pinned inputs with `bash scripts/restore_data.sh`. The
   5-part 419 MB training stack initially failed on part-004 (GitHub API rate
   limit 403); recovered that part via zero-rate-limit codeload tarball
   streaming and verified the reassembled SHA-256
   `4371c82e…` exactly (IR-78FW-04). Registry D2.8/H33/H19-5 and externals all
   hash-verified. Built the versioned feature cache
   (`nearest-exact-mask-v2`, 890 MB memmap).
3. Re-verified H33 geometry (`scripts/review_h33.py`): H33 = D2.8 minus exactly
   the 6,436 dots ≤2 px from the catalogue. Re-fetched the organizer reference
   README at pinned `aebe92f…` and the GEMSDOE32 H33 page at pinned `f62038b…`
   via codeload (gh API rate-limited): the owner page says
   `projected 0.2747; UNSCORED`. The prompt's 0.2778 / 0.3195 / 0.4413 figures
   remain unreconciled user/owner reports, not ORGANIZER-CONFIRMED (IR-78FW-01).
4. Wrote five ranked hypotheses BEFORE any implementation
   (`research/2026-10-22-h78fw-hypotheses.md`) plus a preregistration
   (`registry/preregistration_h78fw.json`) with frozen surface/emission/holdout/
   uniqueness/decision rules and vendor SHA pins. Defined one new lane (H78-FW)
   and stayed inside it; no blending with prior lanes.
5. Implemented `scripts/run_h78fw.py` reusing the template's cached stack,
   `holdout.buffered_component_draw`, `evaluate_holdout` (unmodified,
   `gems57-pooled-hide-v2`), `emit.greedy_dots`, `submission_writer`, and
   `uniqueness` helpers — no private metric, emitter, or writer fork
   (`git diff vendor/` empty at end).
6. Ran experiment 1 (single candidate, single budget 44,090, single seed 20):
   - Surface ρ max 0.2256 (passes 0.90) → proceeded to emission.
   - Canary max symmetric AUC 0.5585 (clean) → proceeded.
   - HOLDOUT-DTI 0.0482 [0.0363, 0.0607], n=11,321; D2.8 0.0919 / H33 0.0037 on
     identical folds/terms (exact reproduction of stored values); paired FW−D2.8
     Δ −0.0437 [−0.0584, −0.0293]. Below the 0.1843 best → holdout gate fails.
   - Final dots: forward 1.0 vs the dense witness (literal duplicate, binding)
     and ≤0.4083 vs dot fields (informative passes) → literal gate fails.
   - Wrote `gems78-h78fw-flankwarp-44090dots-20261022T013114Z-21656430-DO-NOT-SUBMIT`
     (`a18160d5…`) via the shared writer; independent `verify_tif.py` 13/13
     pass + ZIP roundtrip. Verdict `negative`, `ok_to_submit: false`.
   - Lane stopped per prereg (Exp 2–3 only if Exp 1 promotes). Experiments
     charged: 1 of 3. Model-experiment wall time ≈ 3 min (well under 2 h).
7. Built `docs/h78fw.html` + `docs/h78fw-executive-summary.html` from the run
   card only (banner computed from verdict), a display figure
   (`docs/assets/fig_h78fw_surface_and_dots.png`), extended `audit_release.py`
   with the FW candidate row, and rebuilt the release audit: 7/7 TIFFs
   format-pass, 7/7 blocked with explicit reasons. Fixed two bugs found during
   the build (missing 44k incumbent key lookup; f-string nesting in the site
   builder) and one policy error (FW pages must not carry the
   historical-analysis banner). Set 644 permissions on published files.
8. Updated README (seven TIFFs, FW row), `docs/why-h33.md` (full
   evidence-vs-inference analysis), `registry/irregularities.json`
   (IR-78FW-01…04), `research/knowledge.md` (§7), and added
   `tests/test_fw_release.py`.

## Pass 2 — defect, edge-case, and assumption review

- Re-checked every number on the FW pages against `evidence/h78fw_run_card.json`
  (holdout, CI, canary, overlaps, ρ, sha, bytes, note length 67/140, name
  length 72/140). All copied at build time; none hand-typed.
- Edge cases exercised: gh API 403 fallback path; missing registry files fail
  closed in `compare_*` (all 10 comparators present here); empty-dot and NaN
  handling inherited from shared helpers (untouched); `_sha` pin mismatch
  raises (no silent use of wrong bytes); writer refuses overwrite and
  non-[0,1]/non-finite/off-footprint/on-catalogue mass (verified by the passing
  receipt + independent re-read).
- Assumptions challenged: (a) H33's 0.0037 hide-and-recover score does NOT
  imply H33 is weak live — documented as structural (far-field pruning vs
  near-halo withheld truth); (b) FW's informative uniqueness (0.4083) does NOT
  clear the literal gate — dense witness binding, verdict stays negative;
  (c) format-valid does NOT imply organizer acceptance — stated on every page;
  (d) the 10-comparator audit is NOT a complete sibling inventory — stated in
  the card scope; (e) no leaderboard projection is made anywhere (grep-verified
  no `0.27`/`0.31`/`0.44` appears as a FW expectation).
- `git diff vendor/` empty (shared template untouched); `.venv/`, `data/raw`,
  `data/processed`, `data/registry` untracked or ignored as appropriate (large
  inputs/cache kept out of Git per repo conventions — verify `.gitignore`
  covers them before push).
- Ran the full suite: `python -m pytest -q tests` (expect all pass, count
  recorded in the PR), `scripts/preflight.py` (expect exit 2 BLOCKED with
  structured JSON), `scripts/audit_release.py` (rebuilt without errors).

## Pass 3 — requirement audit vs the original request

- Unique TIF generated from the pinned stack (new lane, new bytes
  `a18160d5…`): YES. Copied/renamed prior submission: NO.
- Obvious download/submit status (banner + release audit + sidecars): YES —
  OK TO DOWNLOAD: YES, OK TO SUBMIT: NO on the home page, FW pages, and
  machine-readable `docs/data/status.json` / `release_audit.json`.
- Easy one-click TIF download + executive submission guide: YES
  (`docs/h78fw.html`, `docs/h78fw-executive-summary.html`, home dashboard).
- Values in [0,1], no NaN, CRS/shape/transform match (portal `[0,1]` error
  impossible): YES — 13/13 validator checks + ZIP roundtrip.
- Unique name + ≤140-char note: YES (name 72, note 67 chars).
- Lane discipline + surface-before-placement AND final-dot registry checks with
  0.90/0.70 literal gates: YES; duplicate logged, verdict negative, stopped.
- Reused cached stack / holdout / writer; whole-segment buffered hide-and-
  recover; visible-only features (here: none); exact visible mask; pooled DTI
  α0.2/β0.8/300 m: YES.
- Every number labelled HOLDOUT-DTI (version, n, CI) or ORGANIZER-CONFIRMED
  (none): YES; projections never written as scores.
- Per-feature canary before trusting results: YES (max 0.5585, clean).
- JSON run card with hypothesis/mechanism/mimic/holdout+CI/overlap/sha/
  validator/name+note/verdict: YES (`evidence/h78fw_run_card.json`).
- Budget ≤3 experiments / ≤2 h; no slot picking (selector separate, cap
  unverified): YES (1 experiment, ≈3 min, 0 slots).
- 3–5 new ranked hypotheses with layers/transform/missing-not-mapped mechanism/
  differences; top validated on the blocked holdout before any slot; external-
  data viability checked (none required; USGS/GDR outside allowlist flagged):
  YES.
- H33 0.2778 explained at PhD level with measured geometry + metric theory +
  honest limits: YES (`docs/why-h33.md`, lane pages, hypotheses §0).
- Line-by-line verification from official/pinned sources with links; no manual
  input; irregularities flagged; no hallucinations: YES — fetched sources via
  codeload with pins; unfetchable hosts explicitly listed, never asserted.
- Prompt in README, re-read every session: YES (embedded + session links).
- Three passes + PR + merge + next-work/limitations: this file is the record;
  PR created and merged after the suite passes; limitations below.

## Limitations and next work

1. Literal policy contradiction unresolved: dense rasters binding ⇒ no nonempty
   file can pass. Needs an explicit owner decision (representation policy +
   assigned lane) before further model experiments — not a silent exemption.
2. Holdout is near-halo-biased (withheld truth median 9 px from visible faults);
   far-field live strength (H33-style) scores ~0 here. A distance-stratified or
   far-truth-weighted instrument is needed before live claims.
3. Only model class with headroom toward 0.32+ is the organizer's U-Net class
   (GPU); CPU per-pixel HGB is near its ceiling (0.1843). FW + crosslayer
   replicate the ≈0.05 unsupervised ceiling on this instrument.
4. Registry inventory covers pinned local comparators only (10 files); a
   hash-pinned full accessible inventory is still needed for any future
   promotion consideration.
5. No DrivenData/USGS/NLR/GDR access from this sandbox (allowlist); weekly cap
   unverified; zero slots used. Any future upload needs a login-bearing machine
   and a receipt bound to the file SHA-256 in `registry/live_scores.csv`.
