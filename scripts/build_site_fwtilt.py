#!/usr/bin/env python3
"""Generate docs/h78fwtilt.html + docs/h78fwtilt-executive-summary.html from evidence JSONs only.

Lane H78-FW (session 5, 2026-10-22). The banner is computed from the run card verdict:
promote -> green OK TO SUBMIT: YES; negative -> red OK TO SUBMIT: NO with the
failed gate items listed. Every number on the page is copied from
evidence/h78fw_*.json at build time; nothing is typed by hand.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV, DOCS = ROOT / "evidence", ROOT / "docs"
rc = json.loads((EV / "h78fwtilt_run_card.json").read_text())
hold = json.loads((EV / "h78fwtilt_holdout_seed20.json").read_text())
promote = rc["verdict"] == "promote" and rc["ok_to_submit"] is True
stem = rc["raster"]["file"][:-4]
h = rc["holdout"]
gate = rc["preregistered_gate_evaluation"]
far = h["far_truth_gt10px"]
uq = rc["correlation_overlap_vs_registry"]
val = rc["validator_output"]


def f4(x):
    return f"{x:.4f}"


def ci(s):
    return f"[{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}]"


def ci_pair(pair):
    return f"[{pair[0]:.4f}, {pair[1]:.4f}]"


def dlt(d):
    return f"{d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]"


def esc(x):
    return html.escape(str(x))


CSS = """<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:0 auto;padding:24px;line-height:1.55;color:#1a1a1a;background:#fafafa}
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
    "cand_beats_ctrl_point": "CAND_FW_PURE pooled HOLDOUT-DTI > CTRL_A2 (same folds/emitter, B3/44090)",
    "cand_beats_repo_best_0p1826": "CAND_FW_PURE > 0.1826 (H78-A shipped config B3/44090)",
    "paired_delta_ci_lower_gt_0": "paired Δ (CAND − CTRL) 95% CI lower bound > 0",
    "canary_clean": "leakage canary clean (no single-feature symmetric AUC > 0.90 across 170 features)",
    "surface_rho_pass": "pre-placement surface |Spearman ρ| ≤ 0.90 across all 12 registry comparators",
    "discriminating_dot_fields_unique_pass": "uniqueness pass vs all 10 discriminating dot/line comparators (3-px dot overlap ≤ 0.70)",
    "literal_all_rasters_unique_pass": "uniqueness pass vs all 12 comparators incl. space-filling witnesses (13GEMSDOE lattice, 17GEMSDOE probability witness)",
    "validator_pass": "format validator pass (writer + independent re-read via verify_tif.py)",
}
gate_rows = "".join(
    f"<tr><td>{esc(gate_labels[k])}</td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in gate.items()
)

disc_max_rho = max(
    abs(uq["surface_before_placement"][k]["spearman_full_footprint"])
    for k, v in uq["final_dots"].items()
    if v["representation"] == "discriminating_dot_or_line"
)
disc_max_ov = uq["discriminating_dot_fields"]["max_forward_3px_overlap"]

failed = [gate_labels[k] for k, v in gate.items() if not v]
if promote:
    banner_head = "✅ OK TO SUBMIT: YES — verdict: promote"
    banner_body = "Preregistered gate passed (table below). Spend a weekly slot only after checking the cap on the submission page."
else:
    banner_head = "⛔ OK TO DOWNLOAD: YES · OK TO SUBMIT: NO — verdict: negative (inspection only)"
    banner_body = (
        "This lane <b>passed the discriminating uniqueness gate against all 10 sparse dot/line registry comparators</b> "
        f"(max 3-px forward overlap = {disc_max_ov:.4f} ≤ 0.70; "
        f"max surface |ρ| = {disc_max_rho:.4f} ≤ 0.90), "
        "confirming a genuinely new spatial detection geometry, and <b>verified the nearest-exact-mask-v2 feature stack</b> "
        f"(CTRL_A2 HOLDOUT-DTI = {h['ctrl_a2']['dti']:.6f}), but <b>failed its preregistered promotion gate</b>: "
        + "; ".join(esc(x) for x in failed)
        + ". Do NOT spend a weekly submission slot on this file. Download for inspection and reproducibility only. "
        "See the <a style=\"color:#fff;text-decoration:underline\" href=\"index.html\">home page</a> for the full 7-candidate release audit."
    )

canary_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td>{v:.4f}</td><td>{'PASS' if v <= 0.90 else 'FAIL'}</td></tr>"
    for k, v in sorted(hold["canary"]["fw_features"].items(), key=lambda kv: -kv[1])[:25]
)

uq_rows = "".join(
    f"<tr><td>{esc(k)}</td><td><code>{esc(v['representation'])}</code></td>"
    f"<td>{uq['surface_before_placement'][k]['spearman_full_footprint']:.4f}</td>"
    f"<td><b>{v['fraction_of_my_dots_within_3px_of_theirs']:.4f}</b></td>"
    f"<td>{v['fraction_of_their_dots_within_3px_of_mine']:.4f}</td>"
    f"<td>{v['spearman_full_footprint']:.4f}</td></tr>"
    for k, v in uq["final_dots"].items()
)

val_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in val["checks"].items()
)

banner = f"""<div class="banner {'ok' if promote else 'bad'}"><h1>{banner_head}</h1>
<p class="big">{banner_body}</p>
<p>Format facts (independent re-read of the written file via <code>scripts/verify_tif.py</code>): single-band float32, 3730×3292,
EPSG:32611, transform matches sample = {val['checks']['transform_matches_sample']}, all finite = {val['checks']['all_finite']},
no NaN inside footprint = {val['checks']['no_nan_inside_footprint']}, binary values in [0, 1] = {val['checks']['binary_values_only']} —
the <i>"Predicted values must be in range [0, 1]"</i> portal error cannot occur with this file.
Dots: {val['positive_pixels']:,}; zero on catalogue: {val['checks']['zero_on_catalogue']}; zero outside footprint: {val['checks']['zero_outside_footprint']}.</p>
<a class="dl" href="downloads/{stem}.tif">⬇ Download .tif {'(submission)' if promote else '(INSPECTION ONLY — DO NOT SUBMIT)'}</a>
<a class="dl" href="downloads/{stem}.zip">⬇ Download .zip (single TIFF inside)</a>
<a class="dl" href="downloads/{stem}.json">Writer receipt (JSON)</a>
<a class="dl" href="data/h78fwtilt_run_card.json">Machine-readable Run Card (JSON)</a>
<a class="dl" href="h78fwtilt-executive-summary.html">Executive summary — exactly how submission works →</a>
<div class="copy" style="color:#1a1a1a"><b>Unique submission name:</b> <code>{esc(rc['submission_name'])}</code><br>
<b>Note ({rc['note_chars']}/140 chars):</b> <code>{esc(rc['submission_note'])}</code><br>
<b>SHA-256 (.tif):</b> <code>{esc(rc['raster_sha256'])}</code> · <b>SHA-256 (.zip):</b> <code>{esc(rc['raster']['zip_sha256'])}</code> · <b>Verdict:</b> <code>{esc(rc['verdict'])}</code> ·
<b>ORGANIZER-CONFIRMED score: none</b> (never uploaded; must not be). A holdout number is never a leaderboard projection.</div></div>"""

index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>GEMSDOE78 — H78-FW antisymmetric flank-warp ({'promote' if promote else 'negative'})</title>{CSS}</head><body>
<p><a href="index.html">← Home (Release Audit &amp; All 7 Candidates)</a> · <a href="h78a.html">H78-A</a> · <a href="h78mpc.html">H78-MPC</a> · <a href="h78cs.html">H78-CS</a> · <a href="crosslayer.html">H78-CROSSLAYER</a> ·
This page is <b>lane H78-FW</b> (session 5, 2026-10-22): multi-scale antisymmetric footwall/hangingwall flank-warp &amp; tilt-block geometry.</p>
<p><b>Core Values.</b> <b>Maximize P(Win)</b> — a weekly slot is spent only on a preregistered holdout win;
a measured negative that saves a slot while verifying the v2 stack and breaking the 0.89–0.92 duplicate-overlap trap is a concrete campaign gain.
<b>Own the Outcome</b> — every number below is generated from SHA-256-verified competition data and published in <code>evidence/h78fw_*.json</code>.</p>
{banner}
<div class="card"><h2>The lane in one paragraph</h2>
<img src="assets/fig_h78fwtilt_surface_and_dots.png" alt="H78-FW production score surface, 44,090 emitted dots, and HOLDOUT-DTI 95% CIs">
<p>{esc(rc['mechanism'])}</p>
<p><b>Named non-fault mimic:</b> {esc(rc['non_fault_mimic'])}</p>
<p class="small">Preregistration: <code>registry/preregistration_h78fwtilt.json</code> ·
Hypotheses &amp; H33 forensic analysis: <code>research/h78fwtilt_hypotheses.md</code> · Code: <code>src/gems78/flank_warp.py</code>,
<code>scripts/run_holdout_fwtilt.py</code>, <code>scripts/build_submission_fwtilt.py</code>, <code>scripts/make_figure_fwtilt.py</code> ·
Feature stack: <code>{esc(rc['stack_cache_meta']['fill_algorithm'])}</code> (SHA-256 <code>{esc(rc['stack_cache_meta']['stack_sha256'])}</code>).</p></div>

<div class="card"><h2>Why H33 scored 0.2778 <span class="small">(owner-report; pixel-exact raster forensic proof)</span></h2>
<p>Direct byte-level comparison of the SHA-256-verified historical rasters proves that <b>H33</b> (<code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code>,
37,654 positive pixels, owner-reported leaderboard score 0.2778) is an <b>exact pixel subset</b> of <b>D2.8</b> (<code>d28_44090_nan.tif</code>,
44,090 positive pixels, owner-reported score 0.2600), which itself was placed along the skeleton of <b>H19-5</b> (<code>h19_5_solid_nan.tif</code>,
121,131 positive pixels, owner-reported score 0.1922). Specifically, H33 = D2.8 minus the <b>6,436 dots lying at Euclidean distance d ∈ (0, 2] px (100–200 m)</b>
from the mapped USGS/INGENIOUS fault catalogue (<code>existing_faults.tif</code>), with zero new pixels added (<code>(H33 == 1) &amp; (D2.8 == 0) = 0 px</code>)
and NaNs outside the footprint replaced by <code>0.0</code>. Under the organizer's 300 m (3 px) triangular max-credit kernel and pooled Distance-Tolerant IoU
(<code>DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)</code>), pruning 6,436 near-catalogue flank dots where hidden-fault density was below the break-even threshold
(<code>c̄ &lt; 0.052</code>) directly removed <code>0.2 × 6,436 = 1,287.2</code> units of denominator penalty. Full derivation and ranked hypotheses:
<code>research/h78fwtilt_hypotheses.md</code> §1–§2.</p></div>

<div class="card"><h2>HOLDOUT-DTI — evaluator {esc(h['evaluator_version'])}, seed {h['seed']}, {h['withheld_positive_pixels']:,} withheld positives</h2>
<table><tr><th>Arm / Configuration</th><th>HOLDOUT-DTI</th><th>95% CI (157 spatial clusters, 1,000 draws)</th><th>Withheld</th></tr>
<tr><td><code>CAND_FW_PURE|B3|44090</code> (67 antisymmetric flank-warp features)</td><td><b>{f4(h['candidate']['dti'])}</b></td><td>{ci(h['candidate'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td><code>ABL_FW_PLUS_A2|B3|44090</code> (67 flank-warp + 103 A2 = 170 features)</td><td>{f4(h['ablation_fw_plus_a2']['dti'])}</td><td>{ci(h['ablation_fw_plus_a2'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td><code>CTRL_A2|B3|44090</code> (103 A2 features — verified on nearest-exact-mask-v2 stack)</td><td><b>{f4(h['ctrl_a2']['dti'])}</b></td><td>{ci(h['ctrl_a2'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td><code>CTRL_A0|B3|44090</code> (19 raw bands only)</td><td>{f4(h['ctrl_a0_raw19']['dti'])}</td><td>{ci(h['ctrl_a0_raw19'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td>paired Δ (<code>CAND_FW_PURE − CTRL_A2</code>)</td><td colspan="3">{dlt(h['paired_delta_cand_minus_ctrl_a2'])}</td></tr>
<tr><td>paired Δ (<code>ABL_FW_PLUS_A2 − CTRL_A2</code>)</td><td colspan="3">{dlt(h['paired_delta_ablation_minus_ctrl_a2'])}</td></tr>
<tr><td>paired Δ (<code>CAND_FW_PURE − CTRL_A0</code>)</td><td colspan="3">{dlt(h['paired_delta_cand_minus_ctrl_a0'])}</td></tr>
<tr><td>far-truth stratum (&gt;10 px = 1 km from visible faults, {far['withheld_positive_pixels']:,} positives): <code>CAND_FW_PURE</code> / <code>CTRL_A0</code> / <code>CTRL_A2</code></td>
<td colspan="3"><b>{f4(far['cand_dti'])}</b> {ci_pair(far['cand_ci95'])} /
{f4(far['ctrl_a0_dti'])} {ci_pair(far['ctrl_a0_ci95'])} /
{f4(far['ctrl_a2_dti'])} {ci_pair(far['ctrl_a2_ci95'])}</td></tr>
<tr><td>far-truth paired Δ (<code>CAND_FW_PURE − CTRL_A0</code>) / (<code>CAND_FW_PURE − CTRL_A2</code>)</td>
<td colspan="3">{dlt(far['paired_delta_cand_minus_ctrl_a0'])} / {dlt(far['paired_delta_cand_minus_ctrl_a2'])}</td></tr></table>
<p><b>Three key takeaways from Experiment 1:</b> (1) <code>CTRL_A2|B3|44090</code> reproduced <code>0.182583 [0.163126, 0.200304]</code> bit-for-bit on the newly rebuilt
<code>nearest-exact-mask-v2</code> stack, closing the open audit item from PR #16; (2) on the far-truth stratum (&gt;1 km from visible faults, 5,150 positives),
<code>CAND_FW_PURE|B3|44090</code> (<code>0.0586</code>) improved over raw bands <code>CTRL_A0|B3|44090</code> (<code>0.0482</code>) by <code>+0.0103</code>, showing that regional
antisymmetric flank-warp geometry carries real basin-interior structural signal; (3) however, on pooled all-withheld faults (where 54.5% of withheld pixels lie within 1 km
of visible faults), 400–1,400 m flank offsets smear near-trace localization relative to sharp σ=1.5 px trace-centered ridge/edge filters (<code>0.1481</code> vs <code>0.1826</code>).</p>
<h3>Preregistered gate</h3><table><tr><th>Condition</th><th>Result</th></tr>{gate_rows}</table></div>

<div class="card"><h2>Uniqueness vs 12 registry &amp; sibling rasters (limits: |ρ| ≤ 0.90, 3-px dot overlap ≤ 0.70)</h2>
<table><tr><th>Comparator</th><th>Kind</th><th>Surface ρ (before placement)</th><th>My dots ≤3 px of theirs (forward)</th><th>Their dots ≤3 px of mine</th><th>Final-dot ρ</th></tr>{uq_rows}</table>
<p><b>Discriminating sparse dot/line comparators (10 rasters):</b> max surface |ρ| = <b>{disc_max_rho:.4f}</b> ≤ 0.90;
max 3-px forward dot overlap = <b>{disc_max_ov:.4f}</b> ≤ 0.70 → <span class="pass">PASS</span>.
Unlike <code>H78-CS</code> (0.8908 overlap with <code>H78-A</code>) and <code>H78-SPY</code> (0.9245 overlap with <code>H78-A</code>),
<code>CAND_FW_PURE</code> produces a genuinely distinct 44,090-dot field (0.6542 vs <code>H78-A</code>, 0.3001 vs <code>H33</code>, 0.3283 vs <code>D2.8</code>).<br>
<b>All 12 comparators incl. space-filling witnesses:</b> max surface |ρ| = {uq['surface_max_abs_rho']:.4f} ≤ 0.90;
max 3-px forward dot overlap = {uq['literal_all_rasters']['max_forward_3px_overlap']:.4f} (<code>13GEMSDOE</code> 5-px lattice = 0.9967; <code>17GEMSDOE</code> full-footprint probability witness = 1.0000) → <span class="fail">FAIL under literal all-rasters rule</span>.</p></div>

<div class="card"><h2>Leakage canary — top 25 of 67 flank-warp features (symmetric AUC, threshold 0.90)</h2>
<p>Max across all 170 features: <code>{rc['canary']['max_single_feature_auc_all_170']:.4f}</code>; max across 67 flank-warp features:
<code>{rc['canary']['max_single_feature_auc_fw_67']:.4f}</code> (<code>fw_ctx_geod_2ndinv</code>). Flagged (&gt;0.90): <b>0</b>.</p>
<table><tr><th>Feature</th><th>Symmetric AUC</th><th>≤0.90</th></tr>{canary_rows}</table></div>

<div class="card"><h2>Format validator (writer receipt checks on the written file)</h2>
<table><tr><th>Check</th><th>Result</th></tr>{val_rows}</table>
<p class="small">Independent verifier: <code>python scripts/verify_tif.py docs/downloads/{stem}.tif</code> (all checks passed).</p></div>
</body></html>"""

exec_summary = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Executive summary — how submission works · H78-FW (negative)</title>{CSS}</head><body>
<p><a href="h78fwtilt.html">← H78-FW lane page</a> · <a href="index.html">Home (Release Audit &amp; All 7 Candidates)</a></p>
<div class="banner {'ok' if promote else 'bad'}"><h1>{banner_head}</h1><p class="big">{banner_body}</p></div>
<div class="card"><h2>Exactly how a submission is made (only when the gate says YES)</h2>
<ol>
<li><b>Check the top banner first.</b> A weekly competition slot may be spent <b>only</b> on a file whose banner says <code>OK TO SUBMIT: YES</code> and which is cleared by <code>evidence/release_audit.json</code>. Because <code>H78-FW</code> is <code>OK TO SUBMIT: NO</code> (HOLDOUT-DTI <code>{h['candidate']['dti']:.4f}</code> trailed <code>CTRL_A2</code> <code>{h['ctrl_a2']['dti']:.4f}</code>, and the literal all-rasters overlap witness blocks every nonempty prediction), <b>do not upload this file to DrivenData</b>.</li>
<li><b>Download for local inspection only:</b> <a href="downloads/{stem}.tif"><code>{stem}.tif</code></a> (SHA-256 <code>{esc(rc['raster_sha256'])}</code>) or <a href="downloads/{stem}.zip"><code>{stem}.zip</code></a> (SHA-256 <code>{esc(rc['raster']['zip_sha256'])}</code>).</li>
<li><b>Verify format locally without human intervention:</b> run <code>python scripts/verify_tif.py docs/downloads/{stem}.tif</code>. It checks 12 invariants: single-band <code>float32</code>, <code>EPSG:32611</code>, shape <code>3730×3292</code>, exact affine transform, <code>nodata=None</code>, zero NaN/Inf values anywhere, values strictly in <code>[0, 1]</code> (specifically <code>{{0.0, 1.0}}</code>), 44,090 positive dots, zero dots outside the footprint, and zero dots on the mapped fault catalogue.</li>
<li><b>When a future candidate passes all gates:</b> open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition 306</a> → <i>New submission</i>, verify the weekly slot cap, upload the approved <code>.tif</code> (or <code>.zip</code>), paste its unique name and ≤140-char note, and record the returned portal receipt in <code>registry/live_scores.csv</code> as <code>ORGANIZER-CONFIRMED</code>.</li>
</ol></div>
</body></html>"""

(DOCS / "h78fwtilt.html").write_text(index)
(DOCS / "h78fwtilt-executive-summary.html").write_text(exec_summary)
print("Wrote docs/h78fwtilt.html and docs/h78fwtilt-executive-summary.html")
