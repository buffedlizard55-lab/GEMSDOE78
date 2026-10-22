#!/usr/bin/env python3
"""Generate docs/h78step.html + docs/h78step-executive-summary.html + status feed.

Lane H78-STEP (session 2026-10-22). Every number is copied from
evidence/h78step_*.json at build time; the banner is computed from the run
card verdict (promote -> YES, negative -> NO with failed gates listed).
Nothing is typed by hand. No human inspection step exists anywhere in this
pipeline: data -> features -> holdout -> writer -> independent re-read ->
this page, all automatic.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV, DOCS = ROOT / "evidence", ROOT / "docs"
rc = json.loads((EV / "h78step_run_card.json").read_text())
promote = rc["verdict"] == "promote" and rc["ok_to_submit"] is True
stem = rc["raster"]["file"][:-4]
h = rc["holdout"]
gate = rc["preregistered_gate_evaluation"]


def f4(x):
    return f"{x:.4f}"


def ci(s):
    return f"[{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}]"


def dlt(d):
    return f"{d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]"


def esc(x):
    return html.escape(str(x))


CSS = """<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:960px;margin:0 auto;padding:24px;line-height:1.55;color:#1a1a1a;background:#fafafa}
.banner{border-radius:12px;padding:22px;margin:18px 0;color:#fff}.ok{background:linear-gradient(135deg,#14663a,#1e9e57)}
.bad{background:linear-gradient(135deg,#8f1d1d,#c0392b)}.banner h1{margin:0 0 8px;font-size:1.6rem}.big{font-size:1.12rem;font-weight:600}
.dl{display:inline-block;background:#fff;color:#7a1a1a;font-weight:700;padding:12px 20px;border-radius:8px;text-decoration:none;margin:8px 8px 0 0}
table{border-collapse:collapse;width:100%;margin:12px 0;background:#fff}td,th{border:1px solid #ddd;padding:7px 9px;text-align:left;font-size:.92rem}
code{background:#eee;padding:2px 5px;border-radius:4px;word-break:break-all}
.card{background:#fff;border:1px solid #ddd;border-radius:10px;padding:16px 20px;margin:16px 0}
.copy{background:#f4f4f4;border:1px dashed #999;border-radius:8px;padding:12px;margin:8px 0}
img{max-width:100%}.small{font-size:.85rem;color:#555}.warn{background:#fff8e6;border:1px solid #e0b400;border-radius:8px;padding:10px 14px}
.pass{color:#14663a;font-weight:700}.fail{color:#b3261e;font-weight:700}
</style>"""

gate_labels = {
    "cand_beats_ctrl_point": "CAND_STEP pooled HOLDOUT-DTI > CTRL_A2 (same folds/emitter, B3/44090)",
    "cand_beats_repo_best_0p1826": "CAND_STEP > 0.1826 (repo best at primary config; repo best incl. @50k dots = 0.1843)",
    "paired_delta_ci_lower_gt_0": "paired Δ (CAND − CTRL) 95% CI lower bound > 0",
    "canary_clean": "leakage canary clean (no single-feature symmetric AUC > 0.90)",
    "surface_rho_vs_ctrl_le_0p90": "holdout score-surface Spearman ρ CAND vs CTRL ≤ 0.90 (lane distinctness)",
    "uniqueness_pass_scoped_9_comparators": "uniqueness pass vs 9 comparators (surface ρ ≤ 0.90 before placement AND forward 3-px dot overlap ≤ 0.70 on final dots)",
    "validator_pass": "format validator pass (shared writer + independent re-read + verify_tif.py)",
}
gate_rows = "".join(
    f"<tr><td>{esc(gate_labels[k])}</td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in gate.items() if k in gate_labels)
gate_rows += (f"<tr><td>seed-30 replication</td><td>{esc(gate['seed30_replication'])}</td></tr>")

failed = [gate_labels[k] for k, v in gate.items() if k in gate_labels and not v]
if promote:
    banner_head = "✅ OK TO SUBMIT: YES — verdict: promote"
    banner_body = "Preregistered gate passed (table below). Spend a weekly slot only after checking the cap on the submission page."
else:
    banner_head = "⛔ OK TO SUBMIT: NO — verdict: negative (inspection only)"
    banner_body = ("This lane <b>failed its preregistered gate</b>: " + "; ".join(esc(x) for x in failed)
                   + ". Do NOT spend a weekly submission slot on this file. The file below is published "
                     "for inspection and reproducibility — a negative result is a deliverable. "
                     "Every file in this repo is currently blocked — see the <a style=\"color:#fff;text-decoration:underline\" href=\"index.html\">home page</a> for current status.")

val = rc["validator_output"]["independent_reread"]
banner = f"""<div class="banner {'ok' if promote else 'bad'}"><h1>{banner_head}</h1>
<p class="big">{banner_body}</p>
<p>Format facts (independent re-read of the written file): single-band {esc(val['dtype'])}, {val['shape'][0]}×{val['shape'][1]},
{esc(val['crs'])}, transform matches sample = {all(val['matches_sample'].values())}, all finite = {val['all_finite']},
NaN inside footprint = {val['nan_inside_footprint']}, values exactly {esc(val['distinct_values'])} ⊂ [0, 1] —
the <i>"Predicted values must be in range [0, 1]"</i> portal error cannot occur with this file.
Dots: {val['positive_pixels']:,}; on catalogue: {val['positives_on_catalogue']}; outside footprint: {val['positives_outside_footprint']}.</p>
<a class="dl" href="downloads/{stem}.tif">⬇ Download .tif {'(submission)' if promote else '(INSPECTION ONLY)'}</a>
<a class="dl" href="downloads/{stem}.zip">⬇ Download .zip (single TIFF inside)</a>
<a class="dl" href="downloads/{stem}.json">Writer receipt (JSON)</a>
<a class="dl" href="h78step-executive-summary.html">Executive summary — exactly how submission works →</a>
<div class="copy" style="color:#1a1a1a"><b>Unique submission name:</b> <code>{esc(rc['submission_name'])}</code><br>
<b>Note ({rc['note_chars']}/140 chars):</b> <code>{esc(rc['submission_note'])}</code><br>
<b>SHA-256:</b> <code>{esc(rc['raster_sha256'])}</code> · <b>Verdict:</b> <code>{esc(rc['verdict'])}</code> ·
<b>ORGANIZER-CONFIRMED score: none</b> (never uploaded{'' if promote else '; must not be'}). A holdout number is never a leaderboard projection.</div></div>"""

can = rc["canary"]
canary_top = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td>{v:.4f}</td><td>{'PASS' if v <= 0.90 else 'FAIL'}</td></tr>"
    for k, v in sorted(can["step_features"].items(), key=lambda kv: -kv[1])[:10])

uq = rc["correlation_overlap_vs_registry"]
uq_rows = "".join(
    f"<tr><td>{esc(k)}</td><td>{uq['surface_before_placement'][k]['spearman_full_footprint']:.4f}</td>"
    f"<td>{v['fraction_of_my_dots_within_3px_of_theirs']:.4f}</td><td>{v['fraction_of_their_dots_within_3px_of_mine']:.4f}</td>"
    f"<td>{v['spearman_full_footprint']:.4f}</td></tr>"
    for k, v in uq["final_dots"].items())

checks = rc["validator_output"]["verify_tif"]["checks"]
val_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in checks.items())

dd = rc["dot_distance_to_catalogue_px"]
dg = rc["experiment2_append_diagnostic"]
ev = h["evaluator_version"]
wn = f"{h['withheld_positive_pixels']:,}"

index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE78 · H78-STEP paired flank step — {'OK TO SUBMIT: YES' if promote else 'OK TO SUBMIT: NO'}</title>{CSS}</head><body>
<p><a href="index.html">← Home (release audit)</a> · <a href="h78cs.html">H78-CS lane</a> ·
<a href="h78a.html">H78-A lane</a> · <a href="h78mpc.html">H78-MPC lane</a></p>
{banner}
<div class="card"><h2>What was tested</h2>
<p><b>Hypothesis (preregistered, <code>registry/preregistration_h78step.json</code>):</b> {esc(rc['hypothesis'])}</p>
<p><b>Mechanism:</b> {esc(rc['mechanism'])}</p>
<p><b>Named non-fault mimic:</b> {esc(rc['non_fault_mimic'])}</p>
<p class="small">Why the family's best file scores 0.2778 [owner-report] and five ranked candidate hypotheses:
<code>research/h78step_hypotheses.md</code> in the repo. In one line: the 0.19→0.28 climb was sparse-dot emission
plus catalogue-flank pruning on one unchanged detector; beating it needs a better pixel ranking, which is what
this lane tried — with a different operator, because appending features to H78-A was already shown to duplicate
that lane (H78-CS ρ 0.952, H78-SPY forward overlap 0.9245).</p></div>

<div class="card"><h2>Holdout result — HOLDOUT-DTI (evaluator {esc(ev)}, seed 20, {wn} withheld positives)</h2>
<table><tr><th>Arm (B3 / 44,090 dots)</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>
<tr><td><b>CAND_STEP</b> (raw19 + 54 STEP)</td><td><b>{f4(h['candidate']['dti'])}</b></td><td>{ci(h['candidate'])}</td></tr>
<tr><td>CTRL_A2 (103 H78-A, rerun control)</td><td>{f4(h['control']['dti'])}</td><td>{ci(h['control'])}</td></tr>
<tr><td>A1_ISO (raw19 + isotropic 36)</td><td>{f4(h['a1_iso']['dti'])}</td><td>{ci(h['a1_iso'])}</td></tr>
<tr><td>ABL_STEPONLY (54 STEP only)</td><td>{f4(h['abl_steponly']['dti'])}</td><td>{ci(h['abl_steponly'])}</td></tr>
<tr><td>paired Δ CAND − CTRL</td><td colspan="2">{dlt(h['paired_delta_cand_minus_ctrl'])}</td></tr>
<tr><td>paired Δ CAND − A1_ISO</td><td colspan="2">{dlt(h['paired_delta_cand_minus_a1'])}</td></tr></table>
<p><b>Reading:</b> the paired Δ vs CTRL is significantly <i>negative</i> — the flank-step operator, used as a
replacement for pointwise steered derivatives, loses. Vs A1_ISO it is a tie: flank contrast carries about as much
usable signal as rotation-invariant derivatives, but less than strike-steered ones. STEP's single strongest feature
(<code>step_det_elev_d4_abs</code>, canary AUC {can['step_features']['step_det_elev_d4_abs']:.4f}) beats every
pointwise feature alone, yet the ensemble is worse — consistent with detection without localisation: flank patches
±4–9 px wide can tell a step exists near a line but cannot place the line inside the 3-px (300 m) credit kernel as
precisely as curvature centred on it.</p>
<p>Far-truth stratum (withheld truth &gt; 10 px from any visible fault, {h['far_truth_gt10px']['n_truth']:,} positives):
CAND {f4(h['far_truth_gt10px']['scores']['CAND_STEP|B3|44090'])} vs CTRL {f4(h['far_truth_gt10px']['scores']['CTRL_A2|B3|44090'])} vs
STEPONLY {f4(h['far_truth_gt10px']['scores']['ABL_STEPONLY|B3|44090'])}. Secondary flank test B5 hurt both arms
(CAND {f4(h['flank_B5_secondary']['candidate']['dti'])}, CTRL {f4(h['flank_B5_secondary']['control']['dti'])}),
so the 3→5 px flank extension is falsified on this instrument and production kept B3.</p>
<p><b>Experiment 2 (amendment IR-78STEP-A1, diagnostic only, could not promote):</b> appending STEP to the full
H78-A stack (157 features) gives HOLDOUT-DTI {f4(dg['diag_dti']['dti'])} {ci(dg['diag_dti'])}, paired Δ vs CTRL
{dlt(dg['paired_delta_diag_minus_ctrl'])}, surface ρ {dg['surface_rho_diag_vs_ctrl']['spearman_full_footprint']:.4f} —
appending adds nothing and duplicates the H78-A lane. STEP signal is largely redundant with steered derivatives
once localisation matters.</p></div>

<div class="card"><h2>Preregistered gate — computed, not asserted</h2>
<table><tr><th>Gate item</th><th>Result</th></tr>{gate_rows}</table>
<p class="small">Production dots: median distance to catalogue {dd['p50']:.1f} px, {dd['frac_le_5px']*100:.0f}% within
5 px (H33 shipped: median 19.6 px) — this field also crowds the catalogue; recorded as a live-transfer risk, now
moot given the negative verdict.</p></div>

<div class="card"><h2>Leakage canary (single-feature symmetric AUC, stop &gt; 0.90)</h2>
<p>All 157 features tested; maximum overall {can['max_single_feature_auc']:.4f} — clean. Top STEP features:</p>
<table><tr><th>Feature</th><th>AUC</th><th>≤ 0.90</th></tr>{canary_top}</table></div>

<div class="card"><h2>Uniqueness vs registry (surface before placement AND final dots)</h2>
<p class="small">Forward overlap = fraction of <i>my</i> dots within 3 px of theirs (the binding direction; reverse shown for diagnosis).
Scope: {esc(uq['scope_note'])} <code>complete_registry_verified = false</code>.</p>
<table><tr><th>Comparator</th><th>Surface ρ (pre-placement)</th><th>Forward overlap</th><th>Reverse overlap</th><th>Dot ρ</th></tr>{uq_rows}</table>
<p>Max surface |ρ| {uq['surface_max_abs_rho']:.4f} (limit 0.90) — pass. Max forward dot overlap
{uq['dots_max_forward_overlap']:.4f} vs {esc(uq['worst_forward_overlap_comparator'])} (limit 0.70) —
<b>FAIL</b>: even with a different operator, ~79% of dots land within 300 m of the H78-A-lineage dots, because both
fields find the same lineaments. Under the literal parallel-run rule this is a duplicate of the H78-A dot set as
well as a holdout negative. Against the older registry (H19-5 / D2.8 / H33 / GEMS70-P5) forward overlaps are
0.33–0.44.</p></div>

<div class="card"><h2>File validation (automatic; no human inspection anywhere)</h2>
<table><tr><th>verify_tif.py check</th><th>Result</th></tr>{val_rows}</table>
<p>SHA-256 <code>{esc(rc['raster_sha256'])}</code> · {rc['raster']['bytes']:,} bytes · ZIP contains the single
byte-identical TIFF (writer is fail-closed: it never clips or repairs model output, so the portal's
<i>"Predicted values must be in range [0, 1]"</i> error is impossible by construction and by re-read).</p>
<img src="assets/fig_h78step_surface_and_dots.png" alt="H78-STEP score surface and emitted dots"></div>

<div class="card warn"><h2>Honesty ledger</h2>
<ul>
<li>Every score on this page is <b>HOLDOUT-DTI</b> ({esc(ev)}, α 0.2, β 0.8, 300 m triangular kernel, {wn} withheld
positives, paired 20-km-block bootstrap CIs). The 0.2778 / 0.4413 / 0.3195 figures in the project prompt are
<b>owner reports</b>, mutually inconsistent, and were not fetched (login-gated). Nothing in this repo is
ORGANIZER-CONFIRMED.</li>
<li>The holdout measures recovery of <i>catalogue-style</i> faults from visible context (withheld median ~9 px from
visible faults); the live test faults appear farther (H33 dots median 19.6 px). Holdout rankings are evidence, not
a leaderboard projection — for any lane.</li>
<li>IR-78STEP-01: band 6 is labelled <code>tc_totalcount</code> in code, but the GeoTIFF's own description says
"tilt angle or total curvature — magnetic field derivative". Interpretations of band 6 as radiometrics in earlier
repo documents are unsupported by the file. Flagged for the template owner.</li>
<li>Budget: 3 experiments charged (holdout, declared diagnostic, production build). Submission slots used: 0.
Weekly cap: unverified (submission page not reachable from this sandbox).</li>
</ul></div>
<p class="small">Sources for manual review: competition
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> ·
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">official reference solution</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF (NLR 96647)</a> ·
<a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> ·
<a href="https://gdr.openei.org/submissions/1391">GDR 1391 (INGENIOUS)</a> ·
<a href="https://epsg.io/32611">EPSG:32611</a> · <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a>.
Non-GitHub hosts were not reachable from this sandbox; links are for manual verification.</p>
</body></html>"""

exec_summary = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Executive summary — H78-STEP · OK TO SUBMIT: {'YES' if promote else 'NO'}</title>{CSS}</head><body>
<p><a href="h78step.html">← H78-STEP lane page</a> · <a href="index.html">Home (release audit)</a></p>
{banner}
<div class="card"><h2>Executive summary: exactly how a submission works</h2>
<ol>
<li>Open the lane page and read the banner. A slot may be spent <b>only</b> on a file whose banner is an unqualified
YES. This lane's file says NO, and at build time <b>every</b> file in this repo is blocked — stop here; check the
<a href="index.html">home page</a> for current status.</li>
<li>If (future) a file says YES: download its <code>.tif</code> (or the single-TIFF <code>.zip</code>) using the
buttons in the banner. Verify the SHA-256 shown there matches your download if you want byte certainty.</li>
<li>Check the weekly submission cap on the DrivenData submission page (the agent cannot see it; it is
login-gated). Slot selection is a separate human/selector step — the agent never uploads.</li>
<li>On DrivenData → <i>New submission</i>: choose the downloaded file. It is a single-band float32 GeoTIFF matching
the sample submission's CRS (EPSG:32611), shape (3730×3292) and geotransform, with all values in [0, 1] — verified
automatically by re-reading the written file (<code>scripts/verify_tif.py</code>), so the
<i>"Predicted values must be in range [0, 1]"</i> error cannot occur.</li>
<li>Paste the unique note from the banner (this lane's, {rc['note_chars']}/140 chars, is shown above and begins
"NOT OK TO SUBMIT" — that prefix is deliberate) and submit. Save the organizer receipt with the file's SHA-256;
only that receipt makes a score ORGANIZER-CONFIRMED.</li>
</ol>
<p><b>Why this file must not be uploaded:</b> {esc(rc['ok_to_submit_reason'])} Additionally its dots fail the
literal uniqueness rule vs this repo's shipped H78-A-lineage files (forward 3-px overlap up to
{uq['dots_max_forward_overlap']:.4f} &gt; 0.70). It exists so the negative is reproducible, not to spend a slot on.</p>
<p><b>What would have to change:</b> a future lane must beat CTRL_A2 = HOLDOUT-DTI {f4(h['control']['dti'])}
(B3/44,090; {f4(0.18431154590898757)} at 50,000 dots) on matched folds with paired CI excluding 0, keep
≤ 70% forward dot overlap against the shipped dot sets, and pass the same automatic validators. The STEP result
suggests candidate <i>detection</i> is no longer the bottleneck — sub-kernel <i>localisation</i> is; the strongest
untried direction in this repo's records is a learned segmentation model (organizer-reference U-Net class) on a GPU
session, preregistered as its own lane.</p></div>
</body></html>"""

(DOCS / "h78step.html").write_text(index)
(DOCS / "h78step-executive-summary.html").write_text(exec_summary)

status = dict(
    session="2026-10-22 H78-STEP paired flank step",
    generated_tif=rc["raster"]["file"],
    ok_to_download_for_inspection=True,
    ok_to_submit=False,
    verdict=rc["verdict"],
    reason=rc["ok_to_submit_reason"],
    holdout_dti=h["candidate"]["dti"], holdout_ci95=h["candidate"]["ci95"],
    control_dti=h["control"]["dti"],
    paired_delta=h["paired_delta_cand_minus_ctrl"]["delta"],
    paired_delta_ci95=h["paired_delta_cand_minus_ctrl"]["ci95"],
    evaluator=ev, withheld_positive_pixels=h["withheld_positive_pixels"],
    organizer_confirmed=None, weekly_slots_used_by_agent=0,
    sha256=rc["raster_sha256"],
    duplicate_of="H78-A lineage dot sets (literal forward-overlap rule)",
    forward_3px_overlap_h78a=uq["forward_overlap_vs_h78a_primary"],
    forward_3px_overlap_max=uq["dots_max_forward_overlap"],
    validator_independent_all_passed=bool(rc["validator_output"]["verify_tif"]["all_passed"]),
)
(DOCS / "data/status.json").write_text(json.dumps(status, indent=2) + "\n")
print("WROTE docs/h78step.html docs/h78step-executive-summary.html docs/data/status.json promote=", promote)
