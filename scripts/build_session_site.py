#!/usr/bin/env python3
"""Homepage and executive summary for the 2026-10-21 tooth/spy session.

Numbers are read from evidence JSON. This overwrites docs/index.html and
docs/executive-summary.html so a green 'OK TO SUBMIT: YES' banner cannot sit
above a file this session marked negative.
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
    spy = load("evidence/h78spy_run_card.json")
    tooth = load("evidence/h78tooth_negative.json")
    hold = load("evidence/h78spy_holdout.json")
    file = spy["file"]
    sha = spy["raster_sha256"]
    dti = hold["pooled_summary"]["scores"]["spy|nms0_B3|44090"]["dti"]
    ci = hold["pooled_summary"]["scores"]["spy|nms0_B3|44090"]["ci95"]
    delta = hold["pooled_summary"]["paired_differences"]["A2_control|nms0_B3|44090"]
    ctrl = hold["control_B3_44090"]
    ov = spy["correlation_overlap_vs_registry"]["worst_forward_3px"]
    rho = spy["correlation_overlap_vs_registry"]["surface_max_abs_rho"]
    prof = spy["distance_to_catalogue_px"]
    status = {
        "session": "2026-10-21 tooth then spy",
        "generated_tif": file,
        "ok_to_download_for_inspection": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "reason": "HOLDOUT-DTI did not beat 0.1826, and 92.45% of dots lie within 3 px of H78-A (duplicate lane).",
        "holdout_dti": dti,
        "holdout_ci95": ci,
        "control_dti": ctrl,
        "paired_delta": delta["delta"],
        "paired_delta_ci95": delta["ci95"],
        "evaluator": "gems57-pooled-hide-v2",
        "withheld_positive_pixels": 11321,
        "organizer_confirmed": None,
        "weekly_slots_used_by_agent": 0,
        "sha256": sha,
        "duplicate_of": "H78-A",
        "forward_3px_overlap_h78a": spy["correlation_overlap_vs_registry"]["final_dots"]["H78-A"]["forward_3px"],
        "validator_independent_all_passed": True,
    }
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / "data" / "status.json").write_text(json.dumps(status, indent=2))
    (DOCS / "downloads" / "run_card_h78spy.json").write_text(json.dumps(spy, indent=2))

    home = f"""
<div class="banner no">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO. Do not upload <code>{esc(file)}</code>. It failed the holdout gate and it is a duplicate of the earlier H78-A raster. The older H78-A and H78-MPC files are blocked too.</div>
<div class="card">
<h2 style="margin-top:0">Every downloadable file is blocked</h2>
<table>
<tr><th>File</th><th>Gate</th><th></th></tr>
<tr><td>H78-SPY, this session</td><td>NO — holdout 0.1808 vs control 0.1826, and 92.45% of dots within 3 px of H78-A</td><td><a href="downloads/{esc(file)}">Download inspection GeoTIFF</a></td></tr>
<tr><td>H78-A, previous session</td><td>NO — INCOMPLETE uniqueness check: only three lineage rasters (release audit, IR-78-16). Not a measured duplicate, and not cleared.</td><td><a href="downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif">Research TIFF — do not submit</a></td></tr>
<tr><td>H78-CS, session 3 (merged later)</td><td>NO - HOLDOUT-DTI 0.1791 vs control 0.1826 (seed 20; seed-30 delta +0.0004, CI includes 0), and 89.08% of dots within 3 px of H78-A (duplicate)</td><td><a href="h78cs.html">Lane page + inspection TIFF - do not submit</a></td></tr>
<tr><td>H78-MPC, previous session</td><td>NO — forward 3 px overlap 0.730 against a non-spacefilling registry raster (IR-78-14). Stop.</td><td><a href="downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif">Research TIFF — do not submit</a></td></tr>
</table>
<p>Historical audit: <a href="data/release_audit.json">release_audit.json</a> · <a href="review-release.md">review</a>. This session's card: <a href="downloads/run_card_h78spy.json">run_card_h78spy.json</a>.</p>
</div>
<div class="card">
<h2 style="margin-top:0">Download — inspection only</h2>
<p>The file is format-valid. That is not permission to submit it. The filename contains <b>DO-NOT-SUBMIT</b>.</p>
<a class="btn bad" href="downloads/{esc(file)}" download>Download inspection GeoTIFF — do not submit</a>
<a class="btn sec" href="downloads/{esc(file.replace('.tif', '.zip'))}" download>Same file as .zip</a>
<a class="btn sec" href="downloads/{esc(file.replace('.tif', '.json'))}">Writer receipt</a>
<a class="btn sec" href="downloads/run_card_h78spy.json">Run card</a>
<a class="btn sec" href="data/status.json">Machine-readable status</a>
<table>
<tr><th>Submission name</th><td class="mono">{esc(spy['submission_name'])}</td></tr>
<tr><th>Note (93 characters — do not paste this into a live slot)</th><td class="mono">{esc(spy['submission_note'])}</td></tr>
<tr><th>sha256</th><td class="mono">{esc(sha)}</td></tr>
<tr><th>Format</th><td>single-band float32, 3730×3292, EPSG:32611, transform (100, 0, 243350, 0, −100, 4508550), nodata unset, all finite, values exactly 0 or 1, 44,090 positives, 0 on the catalogue, 0 outside the footprint. Independent re-read: <code>scripts/verify_tif.py</code> all checks passed.</td></tr>
<tr><th>HOLDOUT-DTI</th><td><b>{dti:.4f}</b> [{ci[0]:.4f}, {ci[1]:.4f}] — evaluator gems57-pooled-hide-v2, seed 20, 11,321 withheld positives. Control (same folds, same emitter) <b>{ctrl:.4f}</b>. Paired delta {delta['delta']:+.4f} [{delta['ci95'][0]:+.4f}, {delta['ci95'][1]:+.4f}].</td></tr>
<tr><th>ORGANIZER-CONFIRMED</th><td>none. This file has not been uploaded. A holdout number is not a leaderboard projection.</td></tr>
<tr><th>Uniqueness</th><td>Surface |Spearman| max {rho:.4f} (limit 0.90, pass). Forward 3 px overlap vs H78-A <b>{ov:.4f}</b> (limit 0.70, <b>fail — duplicate</b>). Stopped.</td></tr>
</table>
<img src="assets/fig_h78spy_holdout.png" alt="Holdout DTI bars: spy below the 0.1826 gate" style="width:100%;border-radius:8px;margin-top:12px">
</div>
<div class="card">
<h2 style="margin-top:0">Why h33-h33-2-b2 is the family's best owner-reported file, and whether we can beat 0.2778</h2>
<p><span class="tag n">owner-report</span> The prompt lists 0.2778 for <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code>. That number is <b>not</b> ORGANIZER-CONFIRMED in this repository. The GEMSDOE32 page, re-fetched this session, says no organiser score exists for that file and its own note says projected 0.2747, unscored (IR-78-20). What was re-measured here, from the SHA-256-pinned raster <code>c55bafc4…</code>, is the structure:</p>
<ul>
<li>H19-5 is 121,131 line pixels. D2.8 is 44,090 binary dots, all of them on those lines. H33 is the 37,654-dot subset of D2.8.</li>
<li>The 6,436 removed dots all lie 1.0–2.0 px from the catalogue. H33's own dots have nearest-neighbour spacing minimum 2.83 px, median 3.0 px, and median distance to the catalogue 19.6 px. Zero dots sit on the catalogue. Every value is 0 or 1, every cell finite, nodata unset.</li>
<li>Along the owner-reported chain 0.1922 → 0.2600 → 0.2778 the detector did not change. The metric charges 0.2 per emitted pixel and gives each truth pixel at most one kernel credit (300 m triangle). Dots inside another dot's kernel, and dots within 200 m of a mapped fault that the organiser masks out of scoring, are cost without credit.</li>
</ul>
<p>Beating 0.2778, if that owner-report is real, requires a <i>field</i> whose top ~35–45k dots carry more kernel credit on unmapped faults than H19-5's do. Thinning the same field further will not do it. This session tested two unrun hypotheses aimed at that field. Neither beat the holdout best already in this repo (0.1826), so neither is a slot.</p>
<table>
<tr><th>Hypothesis</th><th>Result <span class="tag h">HOLDOUT-DTI</span></th><th>Verdict</th></tr>
<tr><td>H78-TOOTH. Across-strike missing tooth: a gap kernel that peaks where distance to the visible catalogue equals the local array spacing.</td><td>Mechanism falsified. Withheld faults sit at median 0.39 spacings, not 1. gap1 mean 0.118 on truth vs 0.191 on background (AUC 0.514). The location-proxy features collapsed the learner onto the 48,340 training positives. No raster written.</td><td>negative</td></tr>
<tr><td>H78-SPY. Drop unlabeled cells scoring above the 15th percentile of labeled positives (19,100 of 450,000; cap not hit), refit once, same emitter.</td><td>0.1808 [0.1623, 0.1985] vs control 0.1826. Paired CI includes 0 and the point estimate is lower. Deployment overlap with H78-A is 0.9245.</td><td>negative, duplicate, stop</td></tr>
</table>
<p class="mut">Named non-fault mimics, stated before the fits: regularly spaced drainages and dune ridges (tooth); lithologic contacts and range-front-parallel drainages (spy). Literature for the spacing claim, not re-fetched in full because those hosts are outside this sandbox: Ackermann, Schlische and Withjack 2001, JSG 23:1803, DOI 10.1016/S0191-8141(01)00028-1; Soliva and Benedicto 2006, DOI 10.1029/2004JB003507. Great Basin structural settings: Faulds et al., <a href="https://www.osti.gov/servlets/purl/1110517">OSTI 1110517</a>.</p>
</div>
<div class="card">
<h2 style="margin-top:0">What this does not claim</h2>
<ul>
<li>No file in this repository has an ORGANIZER-CONFIRMED score. Prompt figures 0.2778, 0.3195 and 0.4413 were not copied from a DrivenData receipt this session. The public leaderboard is login-walled from here.</li>
<li>The catalogue hide-and-recover holdout cannot see a fault that does not resemble a withheld mapped component. A live gain is not implied by a holdout gain, and a holdout loss is not a live score either. It is enough to refuse a slot.</li>
<li>The agent spent 0 weekly slots. Promotion is a human selector decision. The selector should not spend one on the file above.</li>
<li>An earlier session's H78-A file (HOLDOUT-DTI 0.1826) is the control this session failed to beat. A later release audit blocked it for an incomplete uniqueness check (IR-78-16). It is preserved at <a href="h78a.html">h78a.html</a> and is not a new clearance.</li>
</ul>
</div>
<div class="card">
<h2 style="margin-top:0">Next work, not started</h2>
<ul>
<li>Do not retune tooth sigma or the spy percentile. Both failure modes are identified.</li>
<li>A detector that is not a small perturbation of H78-A. Spy moved only 8% of dots more than 3 px away. The organizer reference is a U-Net (Monte Carlo CV); this sandbox is CPU-only and did not train one.</li>
<li>A second holdout seed before any further emission change. Only seed 20 has been run.</li>
<li>External rupture catalogues (2020 Monte Cristo Range) are not reachable from this sandbox (usgs.gov is not an allowed host). Do not treat that idea as viable here until the USGS ScienceBase release is actually fetched.</li>
</ul>
<p>Read <a href="https://github.com/buffedlizard55-lab/GEMSDOE78/blob/main/PROMPT.md">PROMPT.md</a> at the start of every session. Status feed: <a href="data/status.json">docs/data/status.json</a>.</p>
</div>
"""
    (DOCS / "index.html").write_text(page("GEMSDOE78 — do not submit this session's file", home))

    steps = f"""
<div class="banner no">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO. Stop on this page if you were about to upload the new GeoTIFF.</div>
<div class="card">
<h2 style="margin-top:0">Decision</h2>
<p>This session generated one new GeoTIFF. It is format-valid and it is <b>not</b> cleared for a weekly slot.</p>
<ol>
<li>Read the red banner. If it says <b>OK TO SUBMIT: NO</b>, do not upload that file. The current banner says NO.</li>
<li>The inspection file, if you need to look at the bytes, is <a href="downloads/{esc(file)}">{esc(file)}</a>. sha256 <code>{esc(sha)}</code>. Name and note are on the home page. Do not paste them into a live submission.</li>
<li>A legal upload, when a future file is actually cleared, is a single-band GeoTIFF or a zip containing that one GeoTIFF. DrivenData competition 306, New submission. The portal checks CRS EPSG:32611, shape 3730×3292, the sample geotransform, and values in [0, 1]. Files from this repo's writer are all-finite, nodata unset, values exactly 0 or 1, which is the fix for the portal error "Predicted values must be in range [0, 1]". Format validity is necessary and not sufficient.</li>
<li>Rules: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition home</a>, <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem and metric</a>, <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a>. Weekly cap and single final selection are in that PDF; this agent does not spend a slot.</li>
<li>If a human later uploads a cleared file, copy the portal score into <code>registry/live_scores.csv</code> and label it ORGANIZER-CONFIRMED. Until that receipt exists, there is no score.</li>
</ol>
</div>
<div class="card">
<h2 style="margin-top:0">Why the new file fails the gate</h2>
<ul>
<li><span class="tag h">HOLDOUT-DTI</span> {dti:.4f} does not beat the reproduced control {ctrl:.4f} or the published holdout best 0.1826. The paired 95% interval on the difference includes zero.</li>
<li>92.45% of its dots fall within 3 px of H78-A. The parallel-run rule stops a lane at 70%. It is not a new submission.</li>
<li>H78-TOOTH, the other experiment, produced no raster: the model collapsed onto the mapped catalogue.</li>
</ul>
<p>Earlier H78-A file, not regenerated this session: see <a href="h78a.html">the archived H78-A page</a>. Submitting it would not be a test of this session's hypotheses. Its own page records a catalogue-halo risk (median 6 px from mapped faults versus 19.6 px for H33).</p>
</div>
"""
    (DOCS / "executive-summary.html").write_text(
        page("Executive summary — how a submission is made, and why this one is not cleared", steps)
    )
    from audit_release import main as audit_release
    audit_release()
    print("session site written; current consolidated gate applied", file)


if __name__ == "__main__":
    main()
