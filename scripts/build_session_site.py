#!/usr/bin/env python3
"""Homepage and executive summary for the 2026-10-22 H78-STEP session.

Numbers are read from evidence JSON (h78step run card; h78spy card for the
historical row). This overwrites docs/index.html and docs/executive-summary.html
so the newest session's file leads the site with its computed gate banner:
OK TO SUBMIT: NO (verdict negative). Historical lane pages are linked, never
rewritten. Runs at the end of build_site.py / build_site_mpc.py after the
release audit, keeping the homepage, executive summary and status feed
consistent after any rebuild.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(rel):
    return json.loads((ROOT / rel).read_text())


def esc(x):
    return html.escape(str(x))


CSS = """
:root{--bg:#0f172a;--card:#111c33;--ink:#e5e7eb;--mut:#9ca3af;--ok:#16a34a;--bad:#dc2626;--warn:#d97706;--acc:#38bdf8;--line:#1f2a44}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:28px 20px 8px;max-width:980px;margin:auto}h1{margin:0 0 6px;font-size:28px}h2{font-size:20px;margin:22px 0 8px}
main{max-width:980px;margin:auto;padding:0 20px 64px}
.banner{font-size:22px;font-weight:800;padding:18px 20px;border-radius:12px;margin:14px 0;line-height:1.35}
.no{background:#450a0a;border:3px solid var(--bad)}
.yes{background:#052e16;border:2px solid var(--ok)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:14px 0}
.btn{display:inline-block;font-weight:800;padding:12px 16px;border-radius:10px;text-decoration:none;margin:6px 8px 6px 0}
.btn.bad{background:var(--bad);color:#fff}
.btn.sec{background:#1e293b;color:var(--ink);border:1px solid var(--line)}
nav a{color:var(--acc);margin-right:14px;text-decoration:none}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--mut)}code,.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;word-break:break-all}
.mut{color:var(--mut)}.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:700}
.tag.h{background:#1e3a8a}.tag.n{background:#7f1d1d}.tag.o{background:#14532d}
"""

NAV = """<nav>
<a href="index.html">Home</a>
<a href="executive-summary.html">How to submit</a>
<a href="h78step.html">H78-STEP lane (this session, negative)</a>
<a href="hypotheses.html">Earlier hypotheses</a>
<a href="holdout.html">H78-A holdout</a>
<a href="sources.html">Sources</a>
<a href="irregularities.html">Irregularities</a>
<a href="h78a.html">Previous H78-A page</a>
<a href="h78cs.html">H78-CS lane (negative, session 3)</a>
<a href="https://github.com/buffedlizard55-lab/GEMSDOE78">Repository</a>
</nav>"""


def page(title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<header><h1>{esc(title)}</h1>{NAV}</header><main>{body}</main></body></html>"""


def main():
    rc = load("evidence/h78step_run_card.json")
    h = rc["holdout"]
    file = rc["raster"]["file"]
    sha = rc["raster_sha256"]
    dti, ci = h["candidate"]["dti"], h["candidate"]["ci95"]
    ctrl = h["control"]["dti"]
    delta = h["paired_delta_cand_minus_ctrl"]
    uq = rc["correlation_overlap_vs_registry"]
    ov_max = uq["dots_max_forward_overlap"]
    ov_a = uq["forward_overlap_vs_h78a_primary"]
    rho_surf = uq["surface_max_abs_rho"]
    status = {
        "session": "2026-10-22 H78-STEP paired flank step",
        "generated_tif": file,
        "ok_to_download_for_inspection": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "reason": rc["ok_to_submit_reason"],
        "holdout_dti": dti,
        "holdout_ci95": ci,
        "control_dti": ctrl,
        "paired_delta": delta["delta"],
        "paired_delta_ci95": delta["ci95"],
        "evaluator": h["evaluator_version"],
        "withheld_positive_pixels": h["withheld_positive_pixels"],
        "organizer_confirmed": None,
        "weekly_slots_used_by_agent": 0,
        "sha256": sha,
        "duplicate_of": "H78-A lineage dot sets (literal forward-overlap rule)",
        "forward_3px_overlap_h78a": ov_a,
        "forward_3px_overlap_max": ov_max,
        "validator_independent_all_passed": bool(rc["validator_output"]["verify_tif"]["all_passed"]),
    }
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / "data" / "status.json").write_text(json.dumps(status, indent=2) + "\n")

    home = f"""
<div class="banner no">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO. Do not upload <code>{esc(file)}</code>. It failed its preregistered holdout gate and its dots duplicate this repo's earlier H78-A-lineage rasters. Every older file below is blocked too. No human inspection is needed anywhere: all validation below is automatic.</div>
<div class="card">
<h2 style="margin-top:0">Download the newest generated TIF — inspection only</h2>
<p>One new, unique-bytes GeoTIFF was generated this session (lane <b>H78-STEP</b>). It is format-valid. That is not permission to submit it. The filename contains <b>DO-NOT-SUBMIT</b> and its note begins "NOT OK TO SUBMIT".</p>
<a class="btn bad" href="downloads/{esc(file)}" download>Download inspection GeoTIFF — do not submit</a>
<a class="btn sec" href="downloads/{esc(file.replace('.tif', '.zip'))}" download>Same file as .zip (single TIFF)</a>
<a class="btn sec" href="downloads/{esc(file.replace('.tif', '.json'))}">Writer receipt</a>
<a class="btn sec" href="h78step.html">Full lane page + run card numbers</a>
<a class="btn sec" href="data/status.json">Machine-readable status</a>
<table>
<tr><th>Unique submission name</th><td class="mono">{esc(rc['submission_name'])}</td></tr>
<tr><th>Note ({rc['note_chars']} of 140 chars — never paste into a live slot)</th><td class="mono">{esc(rc['submission_note'])}</td></tr>
<tr><th>SHA-256</th><td class="mono">{esc(sha)}</td></tr>
<tr><th>Format (automatic re-read)</th><td>single-band float32, 3730×3292, EPSG:32611, transform (100, 0, 243350, 0, −100, 4508550), nodata unset, all finite, no NaN inside footprint, values exactly 0 or 1 (⊂ [0, 1] — the portal error "Predicted values must be in range [0, 1]" cannot occur), 44,090 positives, 0 on catalogue, 0 outside footprint. <code>scripts/verify_tif.py</code> 12/12 passed.</td></tr>
<tr><th><span class="tag h">HOLDOUT-DTI</span></th><td><b>{dti:.4f}</b> [{ci[0]:.4f}, {ci[1]:.4f}] — evaluator {esc(h['evaluator_version'])}, seed 20, {h['withheld_positive_pixels']:,} withheld positives, α 0.2 / β 0.8 / 300 m kernel. Control H78-A rerun (same folds, rows, emitter): <b>{ctrl:.4f}</b>. Paired delta {delta['delta']:+.4f} [{delta['ci95'][0]:+.4f}, {delta['ci95'][1]:+.4f}] — significantly worse.</td></tr>
<tr><th>ORGANIZER-CONFIRMED</th><td>none. Never uploaded; agent used 0 weekly slots. A holdout number is not a leaderboard projection.</td></tr>
<tr><th>Uniqueness (9 comparators)</th><td>Surface |ρ| max {rho_surf:.4f} before placement (limit 0.90, pass). Forward 3-px dot overlap max <b>{ov_max:.4f}</b> vs shipped H78-CS, {ov_a:.4f} vs H78-A primary (limit 0.70, <b>fail — duplicate dots</b>); vs H19-5 / D2.8 / H33 / GEMS70-P5: 0.33–0.44. Registry scope is this repo's restored set, not the organizer's complete registry (<code>complete_registry_verified=false</code>).</td></tr>
</table>
<img src="assets/fig_h78step_surface_and_dots.png" alt="H78-STEP score surface and dots" style="width:100%;border-radius:8px;margin-top:12px">
</div>
<div class="card">
<h2 style="margin-top:0">Every downloadable file is blocked</h2>
<table>
<tr><th>File / lane</th><th>Gate</th><th></th></tr>
<tr><td>H78-STEP, this session (2026-10-22)</td><td>NO — HOLDOUT-DTI {dti:.4f} vs control {ctrl:.4f} (paired delta {delta['delta']:+.4f}), and {ov_a*100:.1f}% of dots within 3 px of H78-A</td><td><a href="h78step.html">Lane page + inspection TIFF</a></td></tr>
<tr><td>H78-CS, session 3</td><td>NO — HOLDOUT-DTI 0.1791 vs control 0.1826 (two seeds), forward overlap 0.8908 vs H78-A</td><td><a href="h78cs.html">Lane page</a></td></tr>
<tr><td>H78-SPY, 2026-10-21 session</td><td>NO — HOLDOUT-DTI 0.1808 vs control 0.1826, forward overlap 0.9245 vs H78-A</td><td><a href="downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif">Inspection TIFF — do not submit</a></td></tr>
<tr><td>H78-A, earlier session</td><td>NO — INCOMPLETE uniqueness audit (release audit; historical check covered only three lineage rasters). Not cleared and not a measured duplicate; this repo's holdout best (0.1826 @44,090; 0.1843 @50,000) but never uploaded</td><td><a href="h78a.html">Archived page</a></td></tr>
<tr><td>H78-MPC, earlier session</td><td>NO — forward overlap 0.730 vs a registry raster. Stop.</td><td><a href="downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif">Research TIFF — do not submit</a></td></tr>
</table>
<p>Release audit: <a href="data/release_audit.json">release_audit.json</a> · <a href="review-release.md">review</a>. This session's run card: repo file <code>evidence/h78step_run_card.json</code>.</p>
</div>
<div class="card">
<h2 style="margin-top:0">Why h33-h33-2-b2 is the family's best owner-reported file (0.2778), and whether we can beat it</h2>
<p><span class="tag n">owner-report</span> 0.2778 (and the prompt's conflicting 0.3195 / 0.4413 leaderboard figures) is not ORGANIZER-CONFIRMED in this repository; the leaderboard is login-gated and was not fetched. What is measured here, from SHA-256-pinned rasters (<code>evidence/forensics_h33_vs_d28.json</code>):</p>
<ul>
<li>H19-5 solid = 121,131 line pixels → D2.8 = 44,090 binary dots <i>on those same lines</i> (NN spacing min √8 px) → H33 = the exact 37,654-dot subset deleting all 6,436 dots within ≤2 px of the catalogue. Owner-reported scores: 0.1922 → 0.2600 → 0.2778. <b>The detector never changed</b> — each step removed prediction mass the metric charges 0.2 per pixel for, where it could not earn kernel credit (300 m triangular kernel, max credit per truth pixel; catalogue pixels masked out of scoring).</li>
<li>Under DTI = TPw/(TPw + 0.2·FPw + 0.8·FNw) the optimum at fixed geometry is binary, and a dot must earn &gt; 0.2·DTI ≈ 0.056 mean kernel credit to be worth adding. Thinning that field further is exhausted (mean dot credit ≈ 0.13 at 0.2778; reaching ~0.32 needs ~25% more credit per dot).</li>
<li>So beating 0.2778 needs a better <i>ranking</i> of pixels by true-fault probability, validated without leakage. That is what this repo's lanes keep testing — and the last four (feature appends, PU refit, missing-tooth, paired-flank step) all failed against the strike-steered control or duplicated its dots. This session's flank-step field detects steps well (its top feature beats every pointwise feature alone, AUC 0.6027) but localises lines too coarsely for the 3-px credit kernel.</li>
</ul>
<p>Honest answer: <b>not with this file, and not by perturbing H78-A.</b> The strongest untried direction in the repo's records is a learned segmentation model (the organizer reference is U-Net class) trained on GPU and preregistered as its own lane.</p>
</div>
<div class="card">
<h2 style="margin-top:0">What this does not claim</h2>
<ul>
<li>No ORGANIZER-CONFIRMED score exists for any file here. Slot selection is a separate selector step; the weekly cap could not be verified from this sandbox.</li>
<li>The hide-and-recover holdout measures recovery of catalogue-style faults (withheld median ~9 px from visible faults). Live hidden faults appear farther away (H33 dots median 19.6 px). Holdout evidence can refuse a slot; it cannot promise a live score.</li>
<li>IR-78STEP-01: band 6's own GeoTIFF description is a magnetic tilt/curvature derivative, not the radiometric total count its code label claims — earlier documents' band-6 interpretation is unsupported. Flagged, not silently renamed.</li>
<li>3 experiments were charged (holdout, declared cannot-promote diagnostic, production build). Shared evaluator/writer used unmodified; no private forks.</li>
</ul>
<p>Read <a href="https://github.com/buffedlizard55-lab/GEMSDOE78/blob/main/PROMPT.md">PROMPT.md</a> and the README at the start of every session. Status feed: <a href="data/status.json">docs/data/status.json</a>.</p>
</div>
"""
    (DOCS / "index.html").write_text(page("GEMSDOE78 — do not submit this session's file (H78-STEP)", home))

    steps = f"""
<div class="banner no">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO. Stop on this page if you were about to upload the new GeoTIFF.</div>
<div class="card">
<h2 style="margin-top:0">Executive summary — exactly how a submission is made</h2>
<ol>
<li>Read the red banner on <a href="index.html">the home page</a>. If it says <b>OK TO SUBMIT: NO</b>, do not upload that file. It currently says NO for every file in this repo.</li>
<li>Download only from the banner buttons (this session's inspection file: <a href="downloads/{esc(file)}">{esc(file)}</a>, sha256 <code>{esc(sha)}</code>; unique name and ≤140-char note are in the banner card). Never rename an old file and call it new.</li>
<li>When a future file's banner says YES: check the weekly cap on the DrivenData submission page first (login-gated; the agent cannot see it and never uploads). Slot choice is a separate selector decision.</li>
<li>DrivenData competition 306 → <i>New submission</i> → choose the single-band GeoTIFF (or a .zip containing only that TIFF) → paste the note from the banner → submit. The portal checks CRS EPSG:32611, shape 3730×3292, the sample geotransform, and values in [0, 1]. This repo's writer emits all-finite float32 values exactly 0/1 with nodata unset and refuses to write otherwise, and the written file is re-read and re-validated automatically (<code>scripts/verify_tif.py</code>) — no human inspector is in the loop, and the "Predicted values must be in range [0, 1]" error cannot occur.</li>
<li>Save the organizer's score receipt next to the file's SHA-256 and record it as ORGANIZER-CONFIRMED. Until that receipt exists, there is no live score — there are only HOLDOUT-DTI numbers and owner reports.</li>
</ol>
<p>Rules and sources for manual review: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition home</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem + metric</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">official reference solution</a>. Non-GitHub hosts were unreachable from this session's sandbox; nothing on this page depends on having fetched them.</p>
</div>
<div class="card">
<h2 style="margin-top:0">Why this session's file fails the gate</h2>
<ul>
<li><span class="tag h">HOLDOUT-DTI</span> {dti:.4f} [{ci[0]:.4f}, {ci[1]:.4f}] vs control {ctrl:.4f}; paired delta {delta['delta']:+.4f} with 95% CI entirely below zero. The hypothesis (paired cross-strike flank steps replace pointwise derivatives) is falsified on this instrument.</li>
<li>{ov_max*100:.1f}% of its dots fall within 3 px of a shipped H78-A-lineage raster. The parallel-run rule stops at 70%: these dots are not a distinct submission even before the holdout loss.</li>
<li>Format is valid (12/12 automatic checks). Format validity is necessary, never sufficient.</li>
</ul>
<p>Full detail: <a href="h78step.html">H78-STEP lane page</a>. Earlier lanes: <a href="h78a.html">H78-A</a> · <a href="h78cs.html">H78-CS</a> · release audit on the <a href="index.html">home page</a>.</p>
</div>
"""
    (DOCS / "executive-summary.html").write_text(
        page("Executive summary — how a submission is made, and why this one is not cleared", steps))
    print("session site written", file)


if __name__ == "__main__":
    main()
