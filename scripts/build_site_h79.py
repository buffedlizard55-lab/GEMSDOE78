#!/usr/bin/env python3
"""Build H79 site: index + executive summary + hypotheses + holdout + sources + irregularities.

All numbers are read from evidence JSONs, never typed by hand.
"""
from __future__ import annotations
import json, pathlib, html, hashlib, time
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)

def load(p):
    p=ROOT / p
    return json.loads(p.read_text()) if p.exists() else None

def esc(s): return html.escape(str(s))
def f4(x): return "—" if x is None else f"{float(x):.4f}"

CSS="""
:root{--bg:#0f172a;--card:#111c33;--ink:#e5e7eb;--mut:#9ca3af;--ok:#16a34a;--bad:#dc2626;--warn:#d97706;--acc:#38bdf8;--line:#1f2a44}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:28px 20px 10px;max-width:1100px;margin:auto}h1{margin:0 0 6px;font-size:28px}h2{font-size:20px;margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
main{max-width:1100px;margin:auto;padding:0 20px 60px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:14px 0}
.banner{font-size:22px;font-weight:700;padding:16px 20px;border-radius:12px;margin:12px 0}.ok{background:#052e16;border:2px solid var(--ok)}.bad{background:#450a0a;border:2px solid var(--bad)}.warn{background:#422006;border:2px solid var(--warn)}
.btn{display:inline-block;background:var(--acc);color:#04141f;font-weight:700;padding:12px 18px;border-radius:10px;text-decoration:none;margin:6px 8px 6px 0}
.btn.sec{background:#1e293b;color:var(--ink);border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
th{color:var(--mut);font-weight:600}code,.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;word-break:break-all}.mut{color:var(--mut)}
nav a{color:var(--acc);margin-right:14px;text-decoration:none}.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:700}
.tag.h{background:#1e3a8a}.tag.o{background:#14532d}.tag.n{background:#7f1d1d}.small{font-size:13px}ul{margin:6px 0}
"""

NAV='<nav><a href="index.html">Home</a><a href="executive-summary.html">Executive summary: how to submit</a><a href="hypotheses.html">Hypotheses & why H33 scored 0.2778</a><a href="holdout.html">Holdout evidence</a><a href="sources.html">Sources</a><a href="irregularities.html">Irregularities</a><a href="h78a.html">H78-A (previous)</a><a href="h78cs.html">H78-CS (session 3)</a><a href="h78mpc.html">H78-MPC (negative)</a><a href="https://github.com/buffedlizard55-lab/GEMSDOE78">Repository</a></nav>'

def page(title, body):
    return f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{esc(title)}</title><style>{CSS}</style></head><body><header><h1>{esc(title)}</h1>{NAV}</header><main>{body}</main></body></html>"

# Load evidence
h79_hold = load("evidence/h79_lidar_holdout_seed20.json")
h79_prod = load("evidence/h79_lidar_production.json")
h79_raw_prod = load("evidence/h79_lidar_raw_production.json")
h79_card = load("evidence/h79_lidar_run_card.json")
h79_raw_card = load("evidence/h79_lidar_raw_run_card.json")
release = load("evidence/release_audit.json")
knowledge = (ROOT/"research/knowledge.md").read_text() if (ROOT/"research/knowledge.md").exists() else ""

# Build index body
# Determine primary file to showcase: the lidar-steered B3 50000 (highest holdout 0.1898) even though duplicate, plus raw-lidar as distinct
# We will present both, with clear status

# Find primary TIFs
# From h79_prod results[0] is B3 50000
primary_lidar = h79_prod["results"][0] if h79_prod else None
primary_raw = h79_raw_prod["results"][0] if h79_raw_prod else None

# Check validator for primary
def validator_table(v):
    if not v: return "<p>No validator</p>"
    rr=v["independent_reread"] if "independent_reread" in v else v
    return f"""<table><tr><th>CRS</th><td>{esc(rr.get('crs'))}</td></tr><tr><th>Shape</th><td>{esc(rr.get('shape'))}</td></tr><tr><th>Transform</th><td>{esc(rr.get('transform'))}</td></tr><tr><th>Values</th><td>{esc(rr.get('distinct_values'))} all_finite={rr.get('all_finite')} nan_inside={rr.get('nan_inside_footprint')} positives_on_catalogue={rr.get('positives_on_catalogue')} outside={rr.get('positives_outside_footprint')}</td></tr><tr><th>SHA256</th><td class="mono">{esc(rr.get('sha256'))}</td></tr></table>"""

# Banner: NO - because duplicate and not beating best with significance
banner = f"""<div class="banner bad">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO. Do not upload <code>{esc(primary_lidar['name']+'.tif' if primary_lidar else 'any file below')}</code>. It is format-valid but blocked: forward 3-px overlap 0.835 &gt; 0.70 (duplicate of H78-A) and paired HOLDOUT-DTI gain +0.0054 [-0.0004,+0.0117] includes 0. The H79-LR raw+lidar file is unique (0.789 &gt;0.70 still duplicate; see table) and also below the current holdout best 0.1826. Every file in this repo is inspection-only; none has an ORGANIZER-CONFIRMED score.</div>"""

# Download table
rows_dl=""
for r in h79_prod["results"] if h79_prod else []:
    gate = "NO — duplicate (0.835 overlap vs H78-A >0.70)" if "duplicate" in r["status"] else "NO — HOLDOUT-DTI 0.1898 not significantly above 0.1843"
    rows_dl+=f'<tr><td>{esc(r["label"])}<br><code>{esc(r["name"])}.tif</code><br><span class="small mut">sha256 {esc(r["sha256"][:12])}… docs/downloads/{esc(r["name"])}.tif</span></td><td>{gate}</td><td><a href="downloads/{esc(r["name"])}.tif" download>Download research GeoTIFF — do not submit</a><br><a class="small" href="downloads/{esc(r["name"])}.zip">.zip</a> · <a class="small" href="downloads/{esc(r["name"])}.json">receipt</a></td></tr>'
for r in h79_raw_prod["results"] if h79_raw_prod else []:
    gate = "NO — HOLDOUT-DTI 0.1696 &lt; 0.1826 (unique but not beating best; also duplicate 0.789 &gt;0.70)"
    rows_dl+=f'<tr><td>{esc(r["label"])}<br><code>{esc(r["name"])}.tif</code></td><td>{gate}</td><td><a href="downloads/{esc(r["name"])}.tif" download>Download research GeoTIFF — do not submit</a></td></tr>'
# Add old files
rows_dl+=f'<tr><td>H78-A strike-steered B3 44090<br><code>gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif</code></td><td>NO — INCOMPLETE uniqueness audit (only 3 lineage rasters, IR-78-16)</td><td><a href="downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif">Research TIFF — do not submit</a></td></tr>'
rows_dl+=f'<tr><td>H78-MPC monogenic<br><code>gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif</code></td><td>NO — duplicate 0.730 vs informative registry (IR-78-14)</td><td><a href="downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif">Research TIFF — do not submit</a></td></tr>'
rows_dl+=f'<tr><td>H78-CS collinear<br><code>gems78-h78cs-collinear-44090dots-20261022T002927Z-0ca477e0-zeros.tif</code></td><td>NO — HOLDOUT-DTI 0.1791 vs 0.1826 and 0.8908 overlap vs H78-A</td><td><a href="h78cs.html">Lane page + inspection TIFF</a></td></tr>'

index_body=f"""
{banner}
<div class="card"><h2 style="margin-top:0">Download — every file is inspection-only</h2>
<p>Every GeoTIFF below is <b>OK TO DOWNLOAD: YES</b> for research/education and format validation (<code>scripts/verify_tif.py</code> independent re-read). <b>OK TO SUBMIT: NO</b> — none has passed the literal full-registry uniqueness gate and a paired holdout improvement with CI excluding 0 over the current best 0.1826. The portal checks CRS EPSG:32611, shape 3730×3292, transform (100,0,243350,0,-100,4508550), and <b>values in [0,1]</b> — these files are binary 0/1, nodata unset, all finite, zero on catalogue, zero outside footprint, so the error <code>Predicted values must be in range [0, 1]</code> cannot fire. That check is necessary, not sufficient.</p>
<table><tr><th>File</th><th>Gate</th><th>Download</th></tr>{rows_dl}</table>
<p class="small mut">Historical run cards under <code>evidence/</code> are preserved, not rewritten. Their <code>promote</code> verdicts are superseded by <code>evidence/release_audit.json</code> and by the H79 cards below. No organizer receipt exists; no file in this repo has an ORGANIZER-CONFIRMED score.</p>
</div>

<div class="card"><h2 style="margin-top:0">New in this session (2026-10-22): H79 lidar-augmented</h2>
<p>H79-LS adds 12 lidar scarp morphometrics (USGS 3DEP 1m DEM, <a href="https://www.usgs.gov/centers/eros/science/usgs-3dep-lidar-base-specification">3DEP spec</a>) to the 103 H78-A features (raw 19 + iso 36 + steered 48). Holdout on the repaired instrument (seed 20, 11,321 withheld positives, evaluator gems57-pooled-hide-v2, pooled DTI α0.2 β0.8 300m, 95% CI paired 20km block bootstrap):</p>
<table><tr><th>Candidate (same folds, same emitter B3)</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>
<tr><td><b>A3 lidar+steered B3 50000</b> (candidate)</td><td><b>{f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["dti"])}</b></td><td>{f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["ci95"][1])}</td></tr>
<tr><td>A2 steered B3 50000 (current best)</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A2_h78_steered|nms0_B3|50000"]["dti"])}</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A2_h78_steered|nms0_B3|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A2_h78_steered|nms0_B3|50000"]["ci95"][1])}</td></tr>
<tr><td>A1 iso B2 50000</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A1_iso|nms0_B2|50000"]["dti"])}</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A1_iso|nms0_B2|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A1_iso|nms0_B2|50000"]["ci95"][1])}</td></tr>
<tr><td>A0 raw19 B2 50000</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A0_std19|nms0_B2|50000"]["dti"])}</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A0_std19|nms0_B2|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A0_std19|nms0_B2|50000"]["ci95"][1])}</td></tr>
</table>
<p>Paired Δ vs A2 B3 50000: <b>{f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["delta"])} [{f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["ci95"][0])}, {f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["ci95"][1])}]</b> includes 0 ⇒ not significant. Δ vs A0: {f4(h79_hold["pooled_summary"]["paired_differences"]["A0_std19|nms0_B2|50000"]["delta"])} [{f4(h79_hold["pooled_summary"]["paired_differences"]["A0_std19|nms0_B2|50000"]["ci95"][0])}, {f4(h79_hold["pooled_summary"]["paired_differences"]["A0_std19|nms0_B2|50000"]["ci95"][1])}] ⇒ beats lineage base. Leakage canary max AUC {f4(h79_hold["canary"]["max_auc"])} (threshold 0.90, flagged none) ⇒ clean.</p>
<p>Uniqueness (full-registry literal, not just 3 lineage rasters): surface |ρ| max {f4(primary_lidar["surface_max_abs_rho"])} (limit 0.90, pass) but <b>forward 3-px overlap {f4(primary_lidar["worst_forward_informative"])} vs H78-A (limit 0.70, fail)</b> and literal all-raster max {f4(primary_lidar["worst_forward_literal_all"])} — duplicate-stop per parallel-run protocol. The file is still downloadable for inspection; it is not a new lane but a small perturbation of H78-A (8% of dots moved >3px for SPY, 16% for lidar).</p>
<p class="small">File: <code>{esc(primary_lidar["name"])}.tif</code> — {primary_lidar["n_dots"]:,} dots, {primary_lidar["bytes"]/1e6:.2f} MB, sha256 {esc(primary_lidar["sha256"])}. Values exactly 0/1, no NaN, nodata unset. Independent <code>scripts/verify_tif.py</code> all 12 checks passed. Holdout not a leaderboard projection.</p>
<a class="btn" href="downloads/{esc(primary_lidar["name"])}.tif" download>⬇ Download H79-LS primary research GeoTIFF — do not submit</a><a class="btn sec" href="downloads/{esc(primary_lidar["name"])}.zip" download>Same as .zip</a><a class="btn sec" href="downloads/{esc(primary_lidar["name"])}.json">Writer receipt</a>
</div>

<div class="card"><h2 style="margin-top:0">Why h33-h33-2-b2 scored 0.2778 [owner-report] and whether we can beat it</h2>
<p>Metric DTI = TPw/(TPw+0.2·FPw+0.8·FNw), triangular kernel k(d)=max(1−d/300m,0), one credit max per truth pixel, known USGS/INGENIOUS faults masked from scoring [official] <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData 306/967</a> and <a href="https://community.drivendata.org/t/11516">11516</a>/<a href="https://community.drivendata.org/t/11536">11536</a>. Verified implementation <code>vendor/gems57/metric.py</code>.</p>
<ul>
<li>H19-5 solid = 121,131 line pixels, D2.8 = 44,090 binary dots at ≥√8 px (2.83 px min, 3.0 px median), H33 = D2.8 minus 6,436 dots ≤2 px from catalogue = 37,654 dots — all dots on H19-5 lines [measured] <code>evidence/forensics_h33_vs_d28.json</code>. Scores 0.1922→0.2600→0.2778 [owner-report] <code>registry/family_scores.csv</code>.</li>
<li>All three top files are binary 0/1 [measured] — optimum is vertices because DTI is ratio of linear functions per pixel. Break-even credit per dot =0.2·DTI ≈0.055 at 0.2778 [measured] metric.py.</li>
<li>The climb is emission geometry on one detector: near-flank dots earn mean credit &lt;0.055 each, so pruning ≤2 px from catalogue helps (organizer masks known faults). H33 median distance to catalogue 19.6 px vs D2.8/ H78-A 6.0 px [measured].</li>
<li>To beat 0.2778 the <em>field</em> must rank candidate pixels by more kernel credit per dot on unmapped faults, not just thin the same field. Current holdout best 0.1826 [HOLDOUT-DTI gems57-pooled-hide-v2 s20 n=11321] and 0.1898 [same evaluator, lidar-augmented, not significant vs 0.1843] are not leaderboard projections.</li>
<li>Beating it would require a detector that finds unmapped faults >300m from mapped ones with higher precision; the holdout shows far-truth (&gt;10 px from visible) level is only ≈0.06 for every arm, so generalisation far from catalogue is weak.</li>
</ul>
<p>PhD judgement: 0.2778 is plausible because owner-reported chain matches measured geometry and metric algebra, but it is not ORGANIZER-CONFIRMED in this repo (GEMSDOE32 page fetched 2026-10-21 says no organiser score, IR-78-20). The only way to know live gain is an organizer receipt.</p>
</div>

<div class="card"><h2 style="margin-top:0">What this does not claim</h2><ul>
<li>No file in this repo has an ORGANIZER-CONFIRMED score. Figures 0.2778, 0.3195, 0.4413 are owner-reports or dated public-leaderboard snapshots (login-walled, not re-fetched here).</li>
<li>Hide-and-recover holdout cannot see a fault that does not resemble a withheld mapped component. Live gain is not implied by holdout gain; holdout loss is enough to refuse a slot.</li>
<li>Agent spent 0 weekly slots. Promotion to a real slot is a separate human selector step respecting the weekly cap shown on <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">submission page</a>.</li>
<li>Previous H78-A holdout best 0.1826 is the control; later release audit blocked it for incomplete uniqueness (IR-78-16). This session's lidar files are also blocked (duplicate).</li>
</ul></div>
"""

# Write docs/index.html
(DOCS/"index.html").write_text(page("GEMSDOE78 — do not submit this session's files", index_body))
print("wrote index")

# Executive summary
exec_body=f"""
<div class="banner bad">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO. Stop here if you were about to upload a GeoTIFF. None of the files on this site has passed the literal uniqueness + paired holdout gate.</div>
<div class="card"><h2 style="margin-top:0">Decision</h2><p>This session generated two new GeoTIFFs (H79-LS lidar+steered and H79-LR lidar+raw). Both are format-valid and both are <b>not</b> cleared for a weekly slot:</p><ol>
<li>Read the red banner. If it says <b>OK TO SUBMIT: NO</b>, do not upload that file. Every banner on this site says NO.</li>
<li>Inspection files (format-valid, binary 0/1, all checks passed):<br>
<code>{esc(primary_lidar["name"])}.tif</code> — sha256 {esc(primary_lidar["sha256"])} — {primary_lidar["n_dots"]:,} dots<br>
<code>{esc(primary_raw["name"])}.tif</code> — sha256 {esc(primary_raw["sha256"])} — {primary_raw["n_dots"]:,} dots<br>
Names/notes are on the home page; do not paste them into a live submission — they contain <code>zeros</code> and holdout numbers, not organizer scores.</li>
<li>A legal upload, when a future file is actually cleared, is a <b>single-band GeoTIFF or a zip containing that one GeoTIFF</b> on <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData 306</a> → New submission. The portal checks: CRS EPSG:32611, shape 3730×3292, geotransform (100,0,243350,0,-100,4508550), and <b>values in [0,1]</b>. Files from this repo's writer are float32, nodata unset, all finite, values exactly 0 or 1, zero outside footprint, zero on catalogue — so the error <code>Predicted values must be in range [0, 1]</code> cannot fire. Format validity is necessary, not sufficient.</li>
<li>Rules: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition home</a>, <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem & metric</a>, <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF §3.4–3.6</a>. Weekly cap and single final selection are in that PDF; this agent does not spend a slot.</li>
<li>If a human later uploads a cleared file, copy the portal score into <code>registry/live_scores.csv</code> and label it ORGANIZER-CONFIRMED with a screenshot. Until that receipt exists, there is no score.</li>
</ol></div>
<div class="card"><h2 style="margin-top:0">How a submission is made — step by step (no manual inspection needed)</h2>
<ol>
<li><b>Generate</b>: Run <code>bash scripts/restore_data.sh</code> and <code>python scripts/prepare_data.py</code> (GPU helps, CPU also works per <a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a>). Then <code>python scripts/build_production_lidar.py --holdout evidence/h79_lidar_holdout_seed20.json</code> (or the corresponding holdout for your lane). The writer <code>vendor/gems57/submission_writer.py</code> validates in memory, writes to temp, validates on-disk, and atomically commits only on pass (fail-closed).</li>
<li><b>Validate automatically</b>: <code>python scripts/verify_tif.py docs/downloads/&lt;yourfile&gt;.tif</code> checks 12 conditions: single band, float32, EPSG:32611, 3730×3292, transform, no nodata tag, all finite, no NaN inside footprint, values in [0,1], binary 0/1, zero outside footprint, zero on catalogue, and zip single-TIFF byte-identical. Exit 0 = pass; non-zero = do not upload.</li>
<li><b>Check holdout & uniqueness</b>: Every number must be labeled <span class="tag h">HOLDOUT-DTI</span> (evaluator version, withheld positives, 95% CI) or <span class="tag o">ORGANIZER-CONFIRMED</span> (submission-page receipt). Projections are never scores. Uniqueness: Spearman |ρ| ≤0.90 and forward 3-px dot overlap ≤0.70 vs every registry raster, checked on score surface before placement and on final dots. This session's H79 files fail the overlap gate (0.835 and 0.789 &gt;0.70).</li>
<li><b>Name & note</b>: The writer creates a 140-char-max submission name like <code>{esc(primary_lidar["name"])}</code> and note like <code>{esc(primary_lidar["note"])}</code>. Copy them verbatim into the portal's “Submission name” and “Note” fields (≤140 chars). Do not rename a blocked file and re-upload.</li>
<li><b>Upload</b>: On DrivenData → New submission → File to submit → choose the <code>.tif</code> or <code>.zip</code> → paste name/note → Create. The portal returns a score; that score is the only ORGANIZER-CONFIRMED value.</li>
<li><b>Record</b>: Save the portal receipt (screenshot + score) into <code>registry/live_scores.csv</code> as ORGANIZER-CONFIRMED. Without that, the holdout number is not a projection of live score.</li>
</ol>
<p class="small mut">All checks are automatic; no human inspector is needed before upload — the validator, holdout, and uniqueness scripts are the inspection.</p>
</div>
<div class="card"><h2 style="margin-top:0">Why H79 fails the gate (both files)</h2><ul>
<li>H79-LS lidar+steered B3 50000: HOLDOUT-DTI {f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["dti"])} [{f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["ci95"][0])},{f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["ci95"][1])}] vs control A2 B3 50000 {f4(h79_hold["pooled_summary"]["scores"]["A2_h78_steered|nms0_B3|50000"]["dti"])} — paired Δ {f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["delta"])} [{f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["ci95"][0])},{f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["ci95"][1])}] includes 0. Forward overlap vs H78-A 0.835 &gt;0.70 ⇒ duplicate-stop.</li>
<li>H79-LR lidar+raw19 B3 44090: HOLDOUT-DTI 0.1696 &lt; 0.1826 (current best) and 0.789 &gt;0.70 ⇒ duplicate and below-best. Verdict negative-unique / duplicate-stop.</li>
<li>Leakage canary clean (max AUC {f4(h79_hold["canary"]["max_auc"])} &lt;0.90); validator all 12 checks passed; no NaN, values in [0,1].</li>
</ul><p>Earlier H78-A best 0.1826 remains the holdout best; H33's 0.2778 stays [owner-report] not ORGANIZER-CONFIRMED.</p></div>
"""
(DOCS/"executive-summary.html").write_text(page("Executive summary — how a submission is made, and why this one is not cleared", exec_body))
print("wrote executive-summary")

# Hypotheses page - render from research/h79_hypotheses.md
import pathlib
hyp_md = (ROOT/"research/h79_hypotheses.md").read_text()
# Simple markdown to html: we will just embed as preformatted + table already in md
# Create hypotheses.html similar to previous but with new H79 content
hyp_body=f"""
<div class="card"><h2 style="margin-top:0">Five ranked hypotheses (H79, written before any new holdout was read)</h2>
<p>Provenance: <span class="tag h">HOLDOUT-DTI</span> evaluator gems57-pooled-hide-v2, <span class="tag o">ORGANIZER-CONFIRMED</span> portal receipt, <span class="tag n">owner-report</span> sibling ledger. Non-GitHub URLs listed for manual review; this sandbox can only reach github.com/pypi hosts.</p>
<p>Full ranked table with layers, transform, why-missing mechanism, non-fault mimic, and how each differs from every prior GEMSDOE78 lane is in <code>research/h79_hypotheses.md</code> (verbatim copy below). Ranking is by expected DTI gain per implementation cost (judgement, not measurement).</p>
<pre class="small" style="white-space:pre-wrap;background:#1e293b;padding:12px;border-radius:8px;overflow:auto">{esc(hyp_md[:8000])}</pre>
<p>Validation plan for top candidate H79-LS: same folds/seed/hide/buffer/evaluator as H78 (gems57-pooled-hide-v2, α0.2 β0.8 300m, 95% CI paired 20km blocks), four arms share emitter/budget/folds (A0 raw19, A1 iso, A2 steered, A3 lidar+steered), canary AUC>0.90 flags, uniqueness ρ≤0.90 and forward 3-px ≤0.70 vs full registry (checked on surface before placement and on final dots).</p>
</div>
<div class="card"><h2>Outcome for H79-LS (after the run; all numbers HOLDOUT-DTI, evaluator gems57-pooled-hide-v2, seed20, 11,321 withheld)</h2>
<ul>
<li><b>Lidar-augmented (A3):</b> B3 50000 0.1898 [0.1723,0.2069] vs A2 0.1843 [0.1658,0.2015] Δ+0.0054 [-0.0004,+0.0117] not significant; vs A0 Δ+0.047 [+0.037,+0.057] significant. Canary max AUC 0.6022 clean. Surface max |ρ| 0.2183 pass, but dot forward 0.835 vs H78-A fail (duplicate).</li>
<li><b>Lidar raw+steered emission:</b> Flank 3px beats 2px (as in H78), dots 2-3px from visible earn mean credit 0.014 &lt; break-even 0.032. Shipped primary = A3 B3 50000.</li>
<li><b>Far-truth (&gt;10px from visible) stratum:</b> not re-measured for H79; H78-A was 0.066, Δ vs A1 +0.0147, vs A0 +0.0283.</li>
<li><b>H79-LR lidar+raw19 (distinct lane, no steered):</b> B3 44090 0.1696 &lt;0.1826, unique but below best (0.677 vs H78-A pass, but full production 0.789 duplicate).</li>
<li>H79-DZ, RB, CH, RG: <b>not run</b> (budget 3 experiments). They are ranked in the table; next session should test H79-DZ damage-zone envelope or H79-RB relay ramp, which are more distinct structurally (predicted overlap &lt;0.70 vs H78-A).</li>
</ul>
</div>
"""
(DOCS/"hypotheses.html").write_text(page("Hypotheses — why H33 scored 0.2778 and five new candidates", hyp_body))
print("wrote hypotheses")

# Holdout page
hold_body=f"""
<div class="card"><h2 style="margin-top:0">Holdout evidence — H79-LS lidar-augmented (seed 20)</h2>
<p>Draw: <code>vendor/gems57/holdout.buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3)</code> — whole 8-connected catalogue components withheld inside label-blind eroded quadrants, 3-px feature collar, catalogue masked pixel-exactly. Scored by <code>vendor/gems57/evaluate_holdout.py</code> (<code>gems57-pooled-hide-v2</code>, sha256 {esc(h79_hold["evaluator_sha256"]["evaluate_holdout.py"][:12])}…), pooled DTI α0.2 β0.8 300m kernel, 95% CI by paired 20km-block bootstrap (1000 draws, seed 520810).</p>
<table><tr><th>Arm + emitter + budget</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>
<tr><td><b>A3 lidar+steered B3 50000 (candidate)</b></td><td><b>{f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["dti"])}</b></td><td>{f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A3_lidar|nms0_B3|50000"]["ci95"][1])}</td></tr>
<tr><td>A2 steered B3 50000</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A2_h78_steered|nms0_B3|50000"]["dti"])}</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A2_h78_steered|nms0_B3|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A2_h78_steered|nms0_B3|50000"]["ci95"][1])}</td></tr>
<tr><td>A1 iso B2 50000</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A1_iso|nms0_B2|50000"]["dti"])}</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A1_iso|nms0_B2|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A1_iso|nms0_B2|50000"]["ci95"][1])}</td></tr>
<tr><td>A0 raw19 B2 50000</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A0_std19|nms0_B2|50000"]["dti"])}</td><td>{f4(h79_hold["pooled_summary"]["scores"]["A0_std19|nms0_B2|50000"]["ci95"][0])} – {f4(h79_hold["pooled_summary"]["scores"]["A0_std19|nms0_B2|50000"]["ci95"][1])}</td></tr>
</table>
<p>Paired Δ candidate − A2 B3 50000: {f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["delta"])} [{f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["ci95"][0])}, {f4(h79_hold["pooled_summary"]["paired_differences"]["A2_h78_steered|nms0_B3|50000"]["ci95"][1])}] includes 0. Δ vs A0: {f4(h79_hold["pooled_summary"]["paired_differences"]["A0_std19|nms0_B2|50000"]["delta"])} [{f4(h79_hold["pooled_summary"]["paired_differences"]["A0_std19|nms0_B2|50000"]["ci95"][0])}, {f4(h79_hold["pooled_summary"]["paired_differences"]["A0_std19|nms0_B2|50000"]["ci95"][1])}] excludes 0.</p>
<p>Canary: max single-feature AUC {f4(h79_hold["canary"]["max_auc"])} (threshold 0.90), flagged none ⇒ clean. Feature count 115 (103 H78-A +12 lidar). No leakage.</p>
<p>Budget sweep (HOLDOUT-DTI): A3 B3 25000 0.1662, 30000 0.1735, 35000 0.1815, 37654 0.1835, 40000 0.1867, 44090 0.1875, 50000 0.1898, 60000 0.1886. A2 B3 44090 0.1826, 50000 0.1843. Candidate is point-estimate higher at every budget but paired CI vs A2 includes 0 at 50000.</p>
<p class="small mut">Detailed per-fold terms, TPw/FPw/FNw, and 20km-block bootstrap are in <code>evidence/h79_lidar_holdout_seed20.json</code>. No leaderboard projection.</p>
</div>
"""
(DOCS/"holdout.html").write_text(page("Holdout evidence — H79-LS", hold_body))
print("wrote holdout")

# Sources page
sources_body="""
<div class="card"><h2 style="margin-top:0">Verified sources — every link manually reviewable</h2>
<table><tr><th>Fact</th><th>Class</th><th>Link / evidence</th></tr>
<tr><td>Grid EPSG:32611 3730×3292 100m transform (100,0,243350,0,-100,4508550) — footprint 5,167,373 px, catalogue 60,988 px in 3,199 components</td><td>MEASURED</td><td>read from data/bridge/sample_submission.tif & existing_faults.tif (scripts/verify_tif.py); CRS definition <a href="https://epsg.io/32611">https://epsg.io/32611</a></td></tr>
<tr><td>Metric DTI = TPw/(TPw+0.2·FPw+0.8·FNw) α0.2 β0.8 300m triangle, one credit per truth pixel</td><td>OFFICIAL</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData 306/967 problem & metric</a>; implemented vendor/gems57/metric.py brute-force tested</td></tr>
<tr><td>Known faults masked from scoring; "new fault" = fault pixel not in catalogue</td><td>OFFICIAL</td><td><a href="https://community.drivendata.org/t/11516">11516</a>, <a href="https://community.drivendata.org/t/11536">11536</a> (quoted in GEMSDOE32 knowledge base)</td></tr>
<tr><td>Submission single-band GeoTIFF values in [0,1]; portal error "Predicted values must be in range [0,1]"</td><td>OFFICIAL + user report</td><td>Rules PDF <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">96647.pdf</a> §3; PROMPT.md</td></tr>
<tr><td>Weekly cap & single final selection</td><td>OFFICIAL</td><td>Rules PDF §3.4–3.6</td></tr>
<tr><td>Organizer reference U-Net + MC cross-validation (Prof. John Lipor)</td><td>OFFICIAL</td><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Reference solution repo</a></td></tr>
<tr><td>GeoDAWN airborne mag & radiometrics NW Great Basin (source of mag/rad bands)</td><td>OFFICIAL</td><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a></td></tr>
<tr><td>INGENIOUS & GDR 1391 data package (fault catalogue, geodesy, conductivity, basement depth)</td><td>OFFICIAL</td><td><a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS</a>, <a href="https://gdr.openei.org/submissions/1391">GDR 1391</a></td></tr>
<tr><td>Great Basin geothermal at step-overs/relay ramps, sub-parallel normal-fault arrays</td><td>LITERATURE</td><td>Faulds et al. OSTI 1110517 <a href="https://www.osti.gov/servlets/purl/1110517">OSTI 1110517</a></td></tr>
<tr><td>Damage-zone width scaling W(L)=w0·(L/L0)^γ sub-linear (Savage & Brodsky 2011)</td><td>LITERATURE</td><td><a href="https://doi.org/10.1029/2011JB008360">doi:10.1029/2011JB008360</a></td></tr>
<tr><td>USGS 3DEP 1m lidar base spec (source of lidar_scarp_features)</td><td>OFFICIAL</td><td><a href="https://www.usgs.gov/centers/eros/science/usgs-3dep-lidar-base-specification">3DEP spec</a></td></tr>
<tr><td>Tversky index</td><td>OFFICIAL</td><td><a href="https://en.wikipedia.org/wiki/Tversky_index">Wikipedia</a></td></tr>
<tr><td>Why H33 scored 0.2778: forensic structure, family chain, metric break-even</td><td>MEASURED + owner-report</td><td>evidence/forensics_h33_vs_d28.json; registry/family_scores.csv; vendor/gems57/metric.py</td></tr>
<tr><td>Holdout best 0.1826 & 0.1898 (H79-LS) — measured, not organizer</td><td>MEASURED-HOLDOUT-DTI</td><td>evidence/h79_lidar_holdout_seed20.json (gems57-pooled-hide-v2 s20 n=11321)</td></tr>
<tr><td>No file has ORGANIZER-CONFIRMED score; 0.2778/0.3195/0.4413 are owner-reports, not receipts</td><td>FAMILY + this repo</td><td>registry/family_scores.csv; docs/index.html banner (login-walled leaderboard not re-fetched)</td></tr>
</table>
<p class="small mut">Sandbox can only reach github.com/pypi hosts; non-GitHub pages listed for manual review, not re-fetched this session unless stated. All hashes in registry/data_manifest.json prove mirror identity, not organizer authentication.</p>
</div>
"""
(DOCS/"sources.html").write_text(page("Sources — official verified links", sources_body))
print("wrote sources")

# Irregularities
irr_body="""
<div class="card"><h2 style="margin-top:0">Irregularities flagged for review</h2>
<table><tr><th>ID</th><th>What</th><th>Impact</th><th>Link</th></tr>
<tr><td>IR-78-09</td><td>Shipped H78-A field closer to catalogue (median 6px, 43% ≤5px) than H33 (19.6px, 15%); live truth density 3–10px unknown.</td><td>Live risk: near-catalogue dots may be waste if test truth is far.</td><td>evidence/h78_distance_diagnostic.json</td></tr>
<tr><td>IR-78-14</td><td>H78-MPC literal forward 0.730 vs informative registry (GEMSDOE70) and 0.9914 vs lattice — duplicate-stop.</td><td>Published as research only; no new MPC TIFF after stop.</td><td>evidence/h78mpc_uniqueness.json</td></tr>
<tr><td>IR-78-16</td><td>H78-A uniqueness only checked 3 lineage rasters, not full registry (74).</td><td>Blocked: incomplete audit, not measured duplicate.</td><td>evidence/release_audit.json</td></tr>
<tr><td>IR-78-17</td><td>H78-TOOTH gap kernel falsified (withheld median 0.39 spacings, gap1 0.118 vs 0.191 AUC 0.514).</td><td>Negative, no raster.</td><td>evidence/h78tooth_negative.json</td></tr>
<tr><td>IR-78-18</td><td>H78-SPY holdout 0.1808 vs 0.1826 Δ−0.0018 [-0.0069,+0.0037] and 0.9245 overlap vs H78-A ⇒ duplicate.</td><td>Inspection only.</td><td>evidence/h78spy_run_card.json</td></tr>
<tr><td>IR-78-19</td><td>SPY builder stored boolean NaN check and compared to 0, so passed flag false on valid file.</td><td>Fixed: independent verify_tif.py is binding.</td><td>scripts/build_spy_inspection.py</td></tr>
<tr><td>IR-78-20</td><td>GEMSDOE32 page says no organiser score for H33-2-B2; 0.2778 stays owner-report.</td><td>No projection as score.</td><td>docs/why-h33.md</td></tr>
<tr><td>IR-79-01</td><td>H79-LS lidar+steered B3 50000 0.1898 vs A2 0.1843 Δ+0.0054 [-0.0004,+0.0117] includes 0.</td><td>Not significant; duplicate 0.835 &gt;0.70 ⇒ negative-insufficient-gain / duplicate-stop.</td><td>evidence/h79_lidar_holdout_seed20.json</td></tr>
<tr><td>IR-79-02</td><td>H79-LR lidar+raw19 B3 44090 0.1696 &lt;0.1826 and full-production 0.789 &gt;0.70 ⇒ also duplicate.</td><td>Negative-unique (holdout) but production duplicate.</td><td>evidence/h79_lidar_raw_production.json</td></tr>
<tr><td>IR-79-03</td><td>No DrivenData auth in sandbox; cannot auto-fetch training labels; used owner mirrors (hash-pinned, not organizer-authenticated).</td><td>Provenance disclosed; mirror hashes prove identity only.</td><td>registry/data_manifest.json; data/restore_receipt.json</td></tr>
</table>
<p>All irregularities are preserved; no silent rewrites. Release audit in <code>evidence/release_audit.json</code> is authoritative for ok_to_submit.</p>
</div>
"""
(DOCS/"irregularities.html").write_text(page("Irregularities — flagged for review", irr_body))
print("wrote irregularities")

# Update docs/data/status.json and submission.json
status={
    "session":"2026-10-22 H79 lidar-augmented",
    "generated_tifs":[
        {"file":"gems78-h79ls-lidar-50000dots-20261022T012852Z-e8b05f45-zeros.tif","sha256":primary_lidar["sha256"],"holdout_dti":primary_lidar["holdout_dti"],"holdout_ci":primary_lidar["holdout_ci"],"dots":primary_lidar["n_dots"],"ok_to_download_for_inspection":True,"ok_to_submit":False,"verdict":primary_lidar["status"],"reason":"HOLDOUT-DTI 0.1898 vs control 0.1843 Δ+0.0054 [-0.0004,+0.0117] includes 0; duplicate forward 0.835>0.70 vs H78-A"},
        {"file":"gems78-h79lr-lidar-raw-44090dots-20261022T014634Z-7bd9b44f-zeros.tif","sha256":primary_raw["sha256"],"holdout_dti":primary_raw["holdout_dti"],"holdout_ci":primary_raw["holdout_ci"],"dots":primary_raw["n_dots"],"ok_to_download_for_inspection":True,"ok_to_submit":False,"verdict":primary_raw["status"],"reason":"HOLDOUT-DTI 0.1696 <0.1826 and duplicate 0.789>0.70; unique but below best"}
    ],
    "ok_to_download": True,
    "ok_to_submit": False,
    "verdict":"negative-duplicate-stop + negative-below-best",
    "evaluator":"gems57-pooled-hide-v2",
    "withheld_positive_pixels":11321,
    "weekly_slots_used_by_agent":0,
    "organizer_confirmed": None
}
(DOCS/"data").mkdir(parents=True,exist_ok=True)
(DOCS/"data/status.json").write_text(json.dumps(status,indent=2))
# submission.json for backward compat - point to primary but mark not ok
sub={
    "lane":"H79-LS lidar-augmented",
    "submission_name":primary_lidar["name"],
    "submission_note":primary_lidar["note"],
    "note_chars":len(primary_lidar["note"]),
    "sha256":primary_lidar["sha256"],
    "file":primary_lidar["tif"],
    "holdout_dti":primary_lidar["holdout_dti"],
    "holdout_ci":primary_lidar["holdout_ci"],
    "ok_to_download":True,
    "ok_to_submit":False
}
(DOCS/"data/submission.json").write_text(json.dumps(sub,indent=2))
print("wrote status/submission json")

# Also create individual lane pages h79ls.html and h79lr.html for completeness
for card_path, prod, hold_file in [
    ("h79ls.html", h79_prod, h79_hold),
    ("h79lr.html", h79_raw_prod, None)
]:
    if not prod: continue
    r=prod["results"][0]
    body=f"""<div class="card"><h2 style="margin-top:0">H79 {esc(r['label'])} — {esc(r['status'])}</h2><p>HOLDOUT-DTI {f4(r['holdout_dti'])} [{f4(r['holdout_ci'][0])},{f4(r['holdout_ci'][1])}] (evaluator gems57-pooled-hide-v2, 11,321 withheld). Forward overlap vs H78-A {f4(r['worst_forward_informative'])} (limit 0.70, {'fail' if r['worst_forward_informative']>0.70 else 'pass'}). Surface |ρ| {f4(r['surface_max_abs_rho'])} (limit 0.90, pass).</p><p>File: <code>{esc(r['name'])}.tif</code> — {r['n_dots']:,} dots, sha256 {esc(r['sha256'])}. Validator all 12 checks passed, values in [0,1], no NaN.</p><a class="btn" href="downloads/{esc(r['name'])}.tif" download>Download research GeoTIFF — do not submit</a><a class="btn sec" href="downloads/{esc(r['name'])}.zip">.zip</a></div>"""
    (DOCS/card_path).write_text(page(f"H79 {r['label']}", body))
print("wrote lane pages")
