# Consolidated publication review — 2026-10-22

## Outcome

**OK to download for research. NOT OK to submit any published TIFF.** No new unique TIFF was generated, no model experiment was run, and no competition slot was used. This does not fulfill the requested new-candidate deliverable; it is a negative review with explicit blockers, not an invented success.

The user refers to a single assigned method paragraph but none is identifiable in the supplied prompt. Historical H78-MPC, SPY and CS evidence already triggers the duplicate-stop rule. Renaming, perturbing, or re-emitting these predictions is not scientific novelty. A complete registry clearance and an explicitly assigned distinct method remain prerequisites for a new experiment.

## Pass 1 — implementation and verification

Reviewed README, PROMPT, prior review, evaluator/writer inventory, historical run cards, site builders and verifier. The consolidated audit previously omitted SPY and the alternate H78-A TIFF. It now inventories all five published TIFFs, reopens each with the independent validator, and writes identical candidate records to the release card and status feed. All five currently pass local format checks; all five remain scientifically blocked. This audit covers published files, not the complete external registry.

The reference repository's current main SHA was checked through GitHub API and still resolves to `aebe92f7c8a990f0e3443451b7a825d9afd6336b`:
https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b

## Pass 2 — defects and edge cases

Fixed wrong-shape validation so footprint indexing cannot crash before a structured failure. Missing/unreadable TIFFs and corrupt ZIPs return JSON failure. ZIP acceptance now requires exactly one entry with the TIFF's actual filename and byte-identical contents; a renamed `.bin` is rejected. The no-NaN footprint check now also rejects infinity. Local policy additionally requires binary float32 data; these are conservative project restrictions, not claims about all organizer-allowed probabilities.

Found a rebuild-order bug: historical builders ran the release audit and then overwrote the homepage/status with the old SPY session view. The session builder now ends with the consolidated audit; the CS builder also ends with it. Rebuilding cannot silently reduce the visible inventory to an older session.

## Pass 3 — requirement audit

Automated suite: **40 passed**, including all-published-file coverage, synchronized status, builder replay safety, malformed ZIP and wrong-shape cases. This is software-test evidence, not a performance score. Raster and historical evidence bytes were not regenerated.

Three ranked geological hypotheses, layers, missing-fault mechanisms, mimics and differences are retained in [the prior scientific review](review-release.md#ranked-hypotheses-for-a-future-authorized-h78-a-experiment). They are deferred proposals, not new tests or claims of novelty across all sibling projects. Highest priority remains cross-layer signed profile-offset consistency on magnetics, gravity and basement depth (medium cost, unknown DTI improvement). Relief-conditioned residual scarp ranking is second; persistent conductivity/radiometric/magnetic flank asymmetry is third. No new external source is represented as obtainable or verified in this review.

H33's sparse-emission/flank-pruning explanation remains an inference supported by [local raster forensics](../evidence/forensics_h33_vs_d28.json), not an organizer-confirmed causal result. The supplied leaderboard claims conflict; none is backed here by an organizer receipt. A higher leaderboard score cannot be promised. Missing fault trace prediction is a proxy relevant to geothermal exploration, not direct vent detection.

## Limitations and next work

- Official DrivenData, USGS, GDR and literature hosts are outside this sandbox's network allowlist. Their supplied links are for follow-up, not fresh verification. GitHub mirrors establish byte identity, not official data provenance.
- No DrivenData session or receipt is available; weekly submission cap and live leaderboard are unverified. Do not upload automatically.
- A selector must establish complete indexed-registry coverage, resolve the literal overlap stop condition and assign the distinct lane before training. Compare against the actual current best on identical buffered whole-segment folds, run per-feature canaries and paired CIs, and audit surfaces before placement and final dots afterward.
- The full user message is not archived verbatim. README and PROMPT explicitly distinguish the operational restatement and excerpt; do not claim otherwise.

Authoritative output: [release card](data/release_audit.json). [Executive download/submission guide](executive-summary.html).
