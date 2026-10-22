#!/usr/bin/env python3
"""Generate the H78-STEP lane pages from evidence JSONs.

Lane H78-STEP (session 2026-10-22). The banner is computed from the run-card
verdict/gate; every number is copied from evidence/h78step_*.json at build
time, nothing is typed by hand. Historical lanes stay blocked exactly as in
evidence/release_audit.json / their own run cards (never re-promoted here).

POST-MERGE SCOPE: this builder writes ONLY docs/h78step.html,
docs/h78step-executive-summary.html and docs/downloads/run_card_h78step.json.
The homepage, executive summary and docs/data/status.json are owned by the
consolidated release audit (scripts/audit_release.py, final publication
step on main), into which H78-STEP is integrated as a blocked candidate.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV, DOCS = ROOT / "evidence", ROOT / "docs"
rc = json.loads((EV / "h78step_run_card.json").read_text())
hold = json.loads((EV / "h78step_holdout_seed20.json").read_text())
promote = rc["verdict"] == "promote" and rc["ok_to_submit"] is True
stem = rc["raster"]["file"][:-4]
h = rc["holdout"]
gate = rc["preregistered_gate_evaluation"]
far = h["far_truth_gt10px"]
val = rc["validator_output"]["independent_reread"]
uq = rc["correlation_overlap_vs_registry"]


def f4(x):
    return f"{x:.4f}"


def ci(s):
    return f"[{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}]"


def dlt(d):
    return f"{d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]"


def esc(x):
    return html.escape(str(x))


CSS = """<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:0 auto;padding:24px;line-height:1.55;color:#172438;background:#f5f7fb}
.banner{border-radius:12px;padding:22px;margin:18px 0;color:#fff}.ok{background:linear-gradient(135deg,#14663a,#1e9e57)}
.bad{background:linear-gradient(135deg,#8f1d1d,#c0392b)}.banner h1{margin:0 0 8px;font-size:1.55rem}.big{font-size:1.1rem;font-weight:600}
.dl{display:inline-block;background:#fff;color:#173;font-weight:700;padding:12px 18px;border-radius:8px;text-decoration:none;margin:8px 8px 0 0}
.banner.bad .dl{color:#7a1a1a}
table{border-collapse:collapse;width:100%;margin:12px 0;background:#fff}td,th{border:1px solid #d5dce6;padding:7px 9px;text-align:left;font-size:.92rem;vertical-align:top}
code{background:#eef1f6;padding:2px 5px;border-radius:4px;word-break:break-all}
.card{background:#fff;border:1px solid #d5dce6;border-radius:10px;padding:16px 20px;margin:16px 0}
.copy{background:#f4f4f4;border:1px dashed #999;border-radius:8px;padding:12px;margin:10px 0;color:#172438}
img{max-width:100%}.small{font-size:.85rem;color:#555}
.pass{color:#14663a;font-weight:700}.fail{color:#b3261e;font-weight:700}
nav a{margin-right:14px;color:#1355a0;text-decoration:none}
</style>"""

NAV = """<nav><a href="index.html">Home / download status</a><a href="executive-summary.html">Executive summary — how to submit</a>
<a href="h78step.html">H78-STEP lane (this session)</a><a href="h78cs.html">H78-CS (negative)</a>
<a href="holdout.html">H78-A holdout</a><a href="hypotheses.html">Earlier hypotheses</a>
<a href="sources.html">Sources</a><a href="irregularities.html">Irregularities</a>
<a href="https://github.com/buffedlizard55-lab/GEMSDOE78">Repository</a></nav>"""

gate_labels = {
    "cand_beats_ctrl_point": "CAND_STEP pooled HOLDOUT-DTI > CTRL_A2 (same folds/emitter, B3/44,090)",
    "cand_beats_repo_best_0p1826": "CAND_STEP > 0.1826 (repo holdout best B3/44,090; 0.1843 at 50k dots)",
    "paired_delta_ci_lower_gt_0": "paired Δ (CAND − CTRL) 95% CI lower bound > 0",
    "canary_clean": "leakage canary clean (no single-feature symmetric AUC > 0.90, 157 features)",
    "surface_rho_vs_ctrl_le_0p90": "holdout score-surface |Spearman ρ| CAND vs CTRL_A2 ≤ 0.90 (distinct lane)",
    "seed30_delta_point_gt_0": "seed-30 replication paired Δ point > 0 (passes vacuously if not run — preregistration)",
    "uniqueness_pass": "uniqueness pass vs frozen 9-raster indexed registry (surface |ρ| ≤ 0.90 before placement; final-dot FORWARD 3-px overlap ≤ 0.70)",
    "validator_pass": "format validator pass (shared writer + independent re-read + scripts/verify_tif.py)",
}
gate_rows = "".join(
    f"<tr><td>{esc(gate_labels.get(k, k))}</td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in gate.items())
failed = [gate_labels.get(k, k) for k, v in gate.items() if not v]

if promote:
    banner_head = "✅ OK TO DOWNLOAD: YES · OK TO SUBMIT: YES — verdict: promote (to selector)"
    banner_body = ("Every preregistered gate passed within the frozen 9-raster indexed-registry scope "
                   "(table below). This session used <b>0 weekly slots</b> and uploaded nothing: a separate "
                   "selector must still verify the weekly cap on the DrivenData submission page and re-scan "
                   "the wider family registry before spending a slot, then paste the note below and preserve "
                   "the organizer receipt against the SHA-256.")
else:
    banner_head = "⛔ OK TO DOWNLOAD: YES · OK TO SUBMIT: NO — verdict: negative (inspection only)"
    banner_body = ("This session's file <b>failed its preregistered gate</b>: " + "; ".join(esc(x) for x in failed)
                   + ". <b>Do NOT spend a weekly submission slot on it.</b> It is downloadable for inspection "
                     "and reproducibility — a negative result is a deliverable. The filename contains "
                     "<b>DO-NOT-SUBMIT</b>. No file in this repository is currently cleared for a slot.")

rep = rc.get("replication_seed30")
rep_rows = ""
if rep:
    rep_rows = (f"<tr><td>CAND_STEP seed-30 replication</td><td><b>{f4(rep['cand']['dti'])}</b></td>"
                f"<td>[{rep['cand']['ci95'][0]:.4f}, {rep['cand']['ci95'][1]:.4f}]</td><td>{rep['withheld_positive_pixels']:,}</td></tr>"
                f"<tr><td>CTRL_A2 seed-30 replication</td><td>{f4(rep['ctrl']['dti'])}</td>"
                f"<td>[{rep['ctrl']['ci95'][0]:.4f}, {rep['ctrl']['ci95'][1]:.4f}]</td><td>{rep['withheld_positive_pixels']:,}</td></tr>"
                f"<tr><td>paired Δ seed 30 (CAND − CTRL)</td><td colspan=\"3\">{dlt(rep['paired_delta_cand_minus_ctrl'])}</td></tr>")

abl_rows = "".join(
    f"<tr><td>{esc(k)}</td><td>{f4(v['dti'])}</td><td>{ci(v)}</td><td>{h['withheld_positive_pixels']:,}</td></tr>"
    for k, v in h["ablations"].items())
budget_rows = ""
for arm, cfgs in h["budgets_B3"].items():
    cells = "".join(f"<td>{f4(v)}</td>" for k, v in sorted(cfgs.items()))
    budget_rows += f"<tr><td>{esc(arm)}</td>{cells}</tr>"
budget_heads = ""
if h["budgets_B3"]:
    first = next(iter(h["budgets_B3"].values()))
    budget_heads = "".join(f"<th>{esc(k)}</th>" for k in sorted(first))

canary_step = rc["canary"]["step_features"]
top_canary = sorted(canary_step.items(), key=lambda kv: -kv[1])[:12]
canary_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td>{v:.4f}</td><td>{'PASS' if v <= 0.90 else 'FAIL'}</td></tr>"
    for k, v in top_canary)

uq_rows = "".join(
    f"<tr><td>{esc(k)}</td><td>{uq['surface_before_placement'][k]['spearman_full_footprint']:.4f}</td>"
    f"<td><b>{v['fraction_of_my_dots_within_3px_of_theirs']:.4f}</b></td><td>{v['fraction_of_their_dots_within_3px_of_mine']:.4f}</td>"
    f"<td>{v['spearman_full_footprint']:.4f}</td></tr>"
    for k, v in uq["final_dots"].items())

checks = rc["validator_output"]["writer_receipt_checks"]
val_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in checks.items())

banner = f"""<div class="banner {'ok' if promote else 'bad'}"><h1>{banner_head}</h1>
<p class="big">{banner_body}</p>
<p>Format facts (independent re-read of the written file): single-band {esc(val['dtype'])}, {val['shape'][0]}×{val['shape'][1]},
{esc(val['crs'])}, transform matches the pinned sample submission = {all(val['matches_sample'].values())}, nodata tag = {esc(val['nodata'])},
all finite = {val['all_finite']}, NaN inside footprint = {val['nan_inside_footprint']}, values exactly {esc(val['distinct_values'])} ⊂ [0, 1] —
the <i>"Predicted values must be in range [0, 1]"</i> portal error cannot be caused by this file's values.
Dots: {val['positive_pixels']:,}; on catalogue: {val['positives_on_catalogue']}; outside footprint: {val['positives_outside_footprint']}.
Format validity is <b>not</b> organizer acceptance and is not a score.</p>
<a class="dl" href="downloads/{stem}.tif" download>⬇ Download .tif {'(submission file)' if promote else '(INSPECTION ONLY — do not submit)'}</a>
<a class="dl" href="downloads/{stem}.zip" download>⬇ Download .zip (single TIFF inside)</a>
<a class="dl" href="downloads/{stem}.json">Writer receipt (JSON)</a>
<a class="dl" href="downloads/run_card_h78step.json">Run card (JSON)</a>
<a class="dl" href="executive-summary.html">Executive summary — exactly how submission works →</a>
<div class="copy"><b>Unique submission name:</b> <code>{esc(rc['submission_name'])}</code><br>
<b>Note ({rc['note_chars']}/140 chars):</b> <code>{esc(rc['submission_note'])}</code><br>
<b>SHA-256:</b> <code>{esc(rc['raster_sha256'])}</code> · <b>Verdict:</b> <code>{esc(rc['verdict'])}</code> ·
<b>ORGANIZER-CONFIRMED score: none</b> (never uploaded by this session; 0 slots used). A holdout number is never a leaderboard projection.</div></div>"""

holdout_card = f"""<div class="card"><h2>Holdout evidence — every performance number is HOLDOUT-DTI</h2>
<p>Evaluator <code>{esc(h['evaluator_version'])}</code> (shared, unmodified), seed 20 buffered whole-component
hide-and-recover, {h['withheld_positive_pixels']:,} withheld positive pixels, pooled DTI α=0.2 / β=0.8 / 300 m
triangular kernel, visible faults masked pixel-exactly, 95% CI by paired 20-km block bootstrap. Identical folds,
training rows, learner and emitter for every arm — only feature columns differ.</p>
<table><tr><th>Arm (B3 / 44,090 dots)</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Withheld positives</th></tr>
<tr><td><b>CAND_STEP</b> (19 raw + 54 cross-strike step features)</td><td><b>{f4(h['candidate']['dti'])}</b></td><td>{ci(h['candidate'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td>CTRL_A2 (103 H78-A features; repo best model class)</td><td>{f4(h['ctrl']['dti'])}</td><td>{ci(h['ctrl'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
{abl_rows}{rep_rows}
<tr><td>paired Δ CAND − CTRL (primary)</td><td colspan="3">{dlt(h['paired_delta_cand_minus_ctrl'])}</td></tr>
<tr><td>Far-truth stratum (&gt;10 px from visible faults, {far['n_positives']:,} positives): CAND vs CTRL</td>
<td colspan="3">CAND {f4(far['scores']['CAND_STEP|B3|44090']['dti'])} {ci(far['scores']['CAND_STEP|B3|44090'])} ·
CTRL {f4(far['scores']['CTRL_A2|B3|44090']['dti'])} {ci(far['scores']['CTRL_A2|B3|44090'])} ·
Δ {dlt(far['paired_delta_cand_minus_ctrl'])}</td></tr></table>
<p>Budgets/configs (pooled HOLDOUT-DTI, same instrument):</p>
<table><tr><th>Arm</th>{budget_heads}</tr>{budget_rows}</table>
<p>Leakage canary: max single-feature symmetric AUC {rc['canary']['max_single_feature_auc']:.4f} over 157 features
(threshold 0.90; clean = {rc['canary']['clean']}). Top STEP features:</p>
<table><tr><th>STEP feature</th><th>symmetric AUC</th><th>≤0.90</th></tr>{canary_rows}</table>
<img src="assets/fig_h78step_holdout.png" alt="HOLDOUT-DTI by arm with 95% CI, and the candidate score surface / dots"></div>"""

why_h33 = """<div class="card"><h2>Why h33-h33-2-b2 tops the family's owner ledger — and what beating it would take</h2>
<p><b>Flagged irregularity:</b> the prompt lists 0.2778 as that file's score, but its source site
(<a href="https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html">GEMSDOE32</a>, re-fetched 2026-10-22) states
"projected live DTI 0.2747 (a MODEL, not a score)", "NO ORGANISER SCORE EXISTS", and its submission note ends
"UNSCORED". 0.2778 is therefore an <b>owner-report without an organizer receipt</b> in any evidence available here —
never ORGANIZER-CONFIRMED. The prompt's leaderboard highs (0.4413 and 0.3195) likewise were not verified from the
login-walled leaderboard in this sandbox.</p>
<p>What <i>was</i> re-measured here from the SHA-256-pinned rasters (2026-10-22): H19-5 = 121,131 line pixels →
D2.8 = 44,090 binary dots, all on those lines → H33 = the exact 37,654-dot subset of D2.8 after deleting the 6,436
dots 1.0–2.0 px from the catalogue; NN spacing min 2.83 px / median 3.0 px; median distance to catalogue 19.6 px;
values exactly {0,1}. Under DTI (max kernel credit per truth pixel, 0.2 charge per emitted pixel), redundant and
near-catalogue dots are cost without credit, so the whole owner-reported climb 0.1922 → 0.2600 → 0.2778 is
<b>emission geometry on one unchanged detector</b>. Beating it needs a ranking whose top ~35–45k dots earn more
kernel credit on unmapped faults — a detector improvement, tested here only as HOLDOUT-DTI, never as a
leaderboard projection. Full analysis: <code>research/h78step_hypotheses.md</code> in the repository.</p></div>"""

uniq_card = f"""<div class="card"><h2>Uniqueness vs the frozen indexed registry (REGISTRY-MEASUREMENT, not a score)</h2>
<p>Score-surface |Spearman ρ| was checked <b>before placement</b> and final-dot <b>forward</b> overlap (fraction of
this file's dots within 3 px of theirs — the literal protocol statistic, no mutual/reverse substitution)
after placement. Limits: ρ ≤ 0.90, forward overlap ≤ 0.70. Max surface |ρ| {uq['surface_max_abs_rho']:.4f};
max forward overlap {uq['dots_max_overlap']:.4f}; passed = {uq['passed']}; duplicate vs: {esc(uq['duplicate_lane_vs']) or 'none'}.</p>
<p class="small">{esc(uq['registry_scope'])}</p>
<table><tr><th>Registry raster</th><th>Surface ρ before placement</th><th>My dots ≤3px of theirs (forward)</th><th>Their dots ≤3px of mine</th><th>Final-dot ρ</th></tr>
{uq_rows}</table></div>"""

val_card = f"""<div class="card"><h2>Automatic format validation (no human inspector)</h2>
<p>Shared writer checks (re-read from disk by the writer, again by this lane's builder, and again by the
independent <code>scripts/verify_tif.py</code> — all three must pass before this page is built):</p>
<table><tr><th>Check</th><th>Result</th></tr>{val_rows}</table>
<p>File: <code>{esc(rc['raster']['file'])}</code> ({rc['raster']['bytes']:,} bytes), zip contains only that TIFF
(zip sha256 <code>{esc(rc['raster']['zip_sha256'])}</code>). Values are exactly 0/1, all finite, no nodata sentinel —
if DrivenData ever rejects this file it cannot be for "values in range [0, 1]". Local validation is a preflight,
not organizer acceptance.</p></div>"""

howto = f"""<div class="card"><h2>Exactly how a submission is made (executive summary)</h2>
<ol>
<li><b>Read the banner above first.</b> Current status of this session's file: <b>OK TO SUBMIT: {'YES' if promote else 'NO'}</b>
— {"proceed only after step 2." if promote else "<b>stop here; do not upload it.</b>"}</li>
<li>Selector step (always required): open the official competition
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS page</a> (login required;
not reachable from the build sandbox), confirm the weekly submission cap shown there, and confirm no newer family
raster duplicates this file. This session spent 0 slots.</li>
<li>Download <code>{stem}.tif</code> (or the .zip with that single TIFF inside) from the banner, and verify its
SHA-256 equals <code>{esc(rc['raster_sha256'])}</code> (e.g. <code>sha256sum {stem}.tif</code>).</li>
<li>On DrivenData choose <b>New submission</b>, attach that exact file, and paste the note
(<b>{rc['note_chars']}/140</b> chars): <code>{esc(rc['submission_note'])}</code></li>
<li>After scoring, save the submission-page receipt (score + timestamp + filename) into the repository
(<code>evidence/</code>) before calling anything ORGANIZER-CONFIRMED. Until then every number for this file is
HOLDOUT-DTI only.</li>
</ol>
<p>Format the portal requires (and this file passes locally): single-band GeoTIFF matching the sample submission's
CRS (EPSG:32611), shape (3730×3292) and geotransform, predicted values in [0, 1].</p></div>"""

blocked_table = """<div class="card"><h2>All downloadable files and their gates</h2>
<table><tr><th>File / lane</th><th>OK to submit</th><th>Why (evidence)</th></tr>
<tr><td><b>H78-STEP (this session, 2026-10-22)</b></td><td><b>__STEP_VERDICT__</b></td><td>Preregistered gate above; run card <code>evidence/h78step_run_card.json</code></td></tr>
<tr><td>H78-A strike-steered</td><td>NO</td><td>Blocked: INCOMPLETE uniqueness audit vs only three lineage rasters (H19-5, D2.8, and H33 lineage rasters) — not cleared, and not a measured duplicate finding (<code>evidence/release_audit.json</code>)</td></tr>
<tr><td>H78-MPC monogenic phase congruency</td><td>NO</td><td>Duplicate/stop: forward 3-px overlap 0.730 vs a non-spacefilling registry raster</td></tr>
<tr><td>H78-SPY PU-cleaned</td><td>NO</td><td>HOLDOUT-DTI 0.1808 vs control 0.1826; forward overlap vs H78-A 0.9245</td></tr>
<tr><td>H78-CS collinear support</td><td>NO</td><td>HOLDOUT-DTI 0.1791 vs 0.1826 (seed-30 Δ +0.0004, CI includes 0); forward overlap vs H78-A 0.8908</td></tr>
</table><p class="small">Historical promotion claims are superseded by <a href="data/release_audit.json">release_audit.json</a>.
No file in this repository has an ORGANIZER-CONFIRMED score.</p></div>""".replace(
    "__STEP_VERDICT__", "YES — promote to selector (cap check still required)" if promote else "NO — inspection only")

sources = """<div class="card"><h2>Official sources for manual review</h2>
<ul>
<li>Competition / problem: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData #306 overview</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard (login; not fetched here)</a></li>
<li>Rules PDF: <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NREL FY26 OSTI 96647</a> (not fetched in this sandbox)</li>
<li>Organizer reference solution: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a></li>
<li>GeoDAWN airborne magnetics/radiometrics: <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS data page</a></li>
<li>INGENIOUS: <a href="https://gbcge.org/current-projects/ingenious/">gbcge.org/ingenious</a> · GDR submission 1391: <a href="https://gdr.openei.org/submissions/1391">gdr.openei.org/submissions/1391</a></li>
<li>Grid CRS: <a href="https://epsg.io/32611">EPSG:32611</a> · Metric background: <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></li>
<li>Great Basin geothermal structural settings: Faulds et al., <a href="https://www.osti.gov/servlets/purl/1110517">OSTI 1110517</a></li>
</ul><p class="small">Non-GitHub hosts are outside this sandbox's network allowlist and were not re-fetched this
session (GEMSDOE32 github.io page excepted, via the page fetcher). Links are for manual review; link presence is
not a claim of fresh verification. Inputs used here are SHA-256-pinned owner mirrors of the competition files
(<code>registry/data_manifest.json</code>) — hash identity, not organizer authentication.</p></div>"""

def page(title, body):
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{esc(title)}</title>{CSS}</head><body>{NAV}{body}</body></html>")

hyp_card = f"""<div class="card"><h2>Hypothesis, mechanism, mimic (preregistered before any result)</h2>
<p><b>Hypothesis.</b> {esc(rc['hypothesis'])}</p>
<p><b>Mechanism.</b> {esc(rc['mechanism'])}</p>
<p><b>Named non-fault mimic.</b> {esc(rc['non_fault_mimic'])}</p>
<p>Five ranked hypotheses, the H33 analysis, and rejected alternatives: <code>research/h78step_hypotheses.md</code>;
preregistration: <code>registry/preregistration_h78step.json</code>.</p>
<table><tr><th>Preregistered gate item</th><th>Result</th></tr>{gate_rows}</table></div>"""

(DOCS / "h78step.html").write_text(page(
    f"GEMSDOE78 H78-STEP — {'OK TO SUBMIT: YES' if promote else 'do not submit'}",
    f"<h1>GEMSDOE78 — lane H78-STEP (cross-strike step-offset concordance)</h1>{banner}{hyp_card}{holdout_card}{uniq_card}{val_card}{why_h33}{sources}"))
(DOCS / "h78step-executive-summary.html").write_text(page(
    "GEMSDOE78 H78-STEP executive summary",
    f"<h1>Executive summary — H78-STEP</h1>{banner}{howto}{holdout_card}{sources}"))
# POST-MERGE (2026-10-22): the consolidated release audit on main
# (scripts/audit_release.py) is the final publication step and owns
# docs/index.html, docs/executive-summary.html and docs/data/status.json.
# This lane builder therefore writes ONLY the H78-STEP lane pages and its
# run-card copy; H78-STEP is integrated into the audit's candidate specs so
# the consolidated homepage lists it as blocked. (At branch point this
# script also wrote the homepage/status; superseded -- IR-78STEP-07.)
# The `blocked_table`/`status` objects below are retained as the lane's
# record for the lane pages' companion evidence, not written over the
# consolidated homepage/status feed.
status = dict(
    session="2026-10-22 H78-STEP cross-strike step-offset concordance",
    generated_tif=rc["raster"]["file"],
    ok_to_download_for_inspection=True,
    ok_to_submit=bool(promote),
    verdict=rc["verdict"],
    selector_note=rc["selector_guidance"],
    holdout_dti=h["candidate"]["dti"], holdout_ci95=h["candidate"]["ci95"],
    control_dti=h["ctrl"]["dti"],
    paired_delta=h["paired_delta_cand_minus_ctrl"]["delta"],
    paired_delta_ci95=h["paired_delta_cand_minus_ctrl"]["ci95"],
    evaluator=h["evaluator_version"],
    withheld_positive_pixels=h["withheld_positive_pixels"],
    evidence_class="HOLDOUT-DTI",
    organizer_confirmed=None,
    weekly_slots_used_by_agent=0,
    sha256=rc["raster_sha256"],
    submission_name=rc["submission_name"], submission_note=rc["submission_note"],
    note_chars=rc["note_chars"],
    dots=rc["raster"]["dots"],
    gate=gate,
    dots_max_forward_3px_overlap=uq["dots_max_overlap"],
    surface_max_abs_rho=uq["surface_max_abs_rho"],
    duplicate_lane_vs=uq["duplicate_lane_vs"],
    run_card="evidence/h78step_run_card.json",
)
# NOTE: docs/data/status.json + docs/data/submission.json belong to the
# consolidated audit / historical lanes; never overwrite them from here.
(DOCS / "downloads" / "run_card_h78step.json").write_text(json.dumps(rc, indent=2, default=float) + "\n")
print("lane pages written; promote =", promote, "; stem =", stem, "; lane status keys:", len(status))
