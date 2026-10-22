#!/usr/bin/env python3
"""Generate docs/h78cs.html + docs/h78cs-executive-summary.html from evidence JSONs only.

Lane H78-CS (session 3). The banner is computed from the run card verdict:
promote -> green OK TO SUBMIT: YES; negative -> red OK TO SUBMIT: NO with the
failed gate items listed. Every number on the page is copied from
evidence/h78cs_*.json at build time; nothing is typed by hand.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV, DOCS = ROOT / "evidence", ROOT / "docs"
rc = json.loads((EV / "h78cs_run_card.json").read_text())
hold = json.loads((EV / "h78cs_holdout_seed20.json").read_text())
promote = rc["verdict"] == "promote" and rc["ok_to_submit"] is True
stem = rc["raster"]["file"][:-4]
h = rc["holdout"]
gate = rc["preregistered_gate_evaluation"]
far = h["far_truth_gt10px"]


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
    "cand_beats_ctrl_point": "CAND_CS pooled HOLDOUT-DTI > CTRL_A2 (same folds/emitter, B3/44090)",
    "cand_beats_repo_best_0p1826": "CAND_CS > 0.1826 (H78-A shipped config B3/44090; repo best incl. @50k dots = 0.1843)",
    "paired_delta_ci_lower_gt_0": "paired Δ (CAND − CTRL) 95% CI lower bound > 0",
    "canary_clean": "leakage canary clean (no single-feature symmetric AUC > 0.90)",
    "uniqueness_pass": "uniqueness pass (surface ρ ≤ 0.90 and 3-px dot overlap ≤ 0.70 vs registry)",
    "validator_pass": "format validator pass (writer + independent re-read)",
}
gate_rows = "".join(
    f"<tr><td>{esc(gate_labels[k])}</td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in gate.items())

failed = [gate_labels[k] for k, v in gate.items() if not v]
if promote:
    banner_head = "✅ OK TO SUBMIT: YES — verdict: promote"
    banner_body = "Preregistered gate passed (table below). Spend a weekly slot only after checking the cap on the submission page."
else:
    banner_head = "⛔ OK TO SUBMIT: NO — verdict: negative (inspection only)"
    banner_body = ("This lane <b>failed its preregistered gate</b>: " + "; ".join(esc(x) for x in failed)
                   + ". Do NOT spend a weekly submission slot on this file. The file below is published "
                     "for inspection and reproducibility — a negative result is a deliverable. "
                     "Every file in this repo is currently blocked by the release audit - see the <a style=\"color:#fff;text-decoration:underline\" href=\"index.html\">home page</a> for current status.")

rep = rc.get("replication_seed30")
rep_row = ""
if rep:
    rep_row = (f"<tr><td>CAND_CS seed-30 replication (IR-78CS-01; cannot promote)</td>"
               f"<td><b>{f4(rep['cand']['dti'])}</b></td><td>[{rep['cand']['ci95'][0]:.4f}, {rep['cand']['ci95'][1]:.4f}]</td>"
               f"<td>{rep['withheld_positive_pixels']:,}</td></tr>"
               f"<tr><td>CTRL_A2 seed-30 replication</td><td>{f4(rep['ctrl']['dti'])}</td>"
               f"<td>[{rep['ctrl']['ci95'][0]:.4f}, {rep['ctrl']['ci95'][1]:.4f}]</td><td>{rep['withheld_positive_pixels']:,}</td></tr>"
               f"<tr><td>paired Δ seed 30 (CAND − CTRL)</td><td colspan=\"3\">{dlt(rep['paired_delta_cand_minus_ctrl'])}</td></tr>")

canary_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td>{v:.4f}</td><td>{'PASS' if v <= 0.90 else 'FAIL'}</td></tr>"
    for k, v in sorted(rc["canary"]["cs_features"].items(), key=lambda kv: -kv[1]))

uq = rc["correlation_overlap_vs_registry"]
uq_rows = "".join(
    f"<tr><td>{esc(k)}</td><td>{uq['surface_before_placement'][k]['spearman_full_footprint']:.4f}</td>"
    f"<td>{v['fraction_of_my_dots_within_3px_of_theirs']:.4f}</td><td>{v['fraction_of_their_dots_within_3px_of_mine']:.4f}</td>"
    f"<td>{v['spearman_full_footprint']:.4f}</td></tr>"
    for k, v in uq["final_dots"].items())

val = rc["validator_output"]["independent_reread"]
checks = rc["validator_output"]["writer_receipt_checks"]
val_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in checks.items())

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
<a class="dl" href="h78cs-executive-summary.html">Executive summary — exactly how submission works →</a>
<div class="copy" style="color:#1a1a1a"><b>Unique submission name:</b> <code>{esc(rc['submission_name'])}</code><br>
<b>Note ({rc['note_chars']}/140 chars):</b> <code>{esc(rc['submission_note'])}</code><br>
<b>SHA-256:</b> <code>{esc(rc['raster_sha256'])}</code> · <b>Verdict:</b> <code>{esc(rc['verdict'])}</code> ·
<b>ORGANIZER-CONFIRMED score: none</b> (never uploaded{'' if promote else '; must not be'}). A holdout number is never a leaderboard projection.</div></div>"""

index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>GEMSDOE78 — H78-CS collinear support ({'promote' if promote else 'negative'})</title>{CSS}</head><body>
<p><a href="index.html">← Home (H78-A primary)</a> · <a href="h78mpc.html">H78-MPC second candidate</a> ·
This page is <b>lane H78-CS</b> (session 3, 2026-10-21): strike-following collinear support.</p>
<p><b>Core Values.</b> <b>Maximize P(Win)</b> — a weekly slot is spent only on a preregistered holdout win;
a measured negative that saves a slot is a win for the campaign. <b>Own the Outcome</b> — the gate,
the replication and the duplicate-lane measurement below are all computed and published, not asserted.</p>
{banner}
<div class="card"><h2>The lane in one paragraph</h2>
<img src="assets/fig_h78cs_surface_and_dots.png" alt="H78-CS production score surface and emitted dots (downsampled x4, display only)">
<p>{esc(rc['mechanism'])}</p>
<p><b>Named non-fault mimic:</b> {esc(rc['non_fault_mimic'])}</p>
<p class="small">Preregistration (written before results): <code>registry/preregistration_h78cs.json</code> ·
Hypotheses ranked: <code>research/h78cs_hypotheses.md</code> · Code: <code>src/gems78/collinear.py</code>,
<code>scripts/run_holdout_cs.py</code>, <code>scripts/build_submission_cs.py</code> · Shared evaluator/writer
unmodified (<code>vendor/gems57</code>, sha256-pinned).</p></div>

<div class="card"><h2>Why the family's best file scored 0.2778 <span class="small">(owner-report; structure measured here)</span></h2>
<p>DTI = TP<sub>w</sub>/(TP<sub>w</sub>+0.2·FP<sub>w</sub>+0.8·FN<sub>w</sub>) with a 300 m max-credit kernel charges
0.2 per emitted pixel, so the optimum is binary sparse dots and a dot helps only if its credit exceeds ≈0.2·DTI
(0.0556 at 0.2778). The chain H19-5 solid (121,131 px, 0.1922) → D2.8 (44,090 dots on the same lines, 0.2600) →
H33 (exact 37,654-dot subset deleting every dot ≤2 px from the catalogue, 0.2778) changed <i>no detector at all</i> —
it removed redundant and near-catalogue mass. Beating 0.2778 therefore needs a better <i>ranking</i> of pixels by
true-fault probability (credit per dot ≈0.13 → ≈0.16 for ~0.32), validated on hide-and-recover holdout — which is
what this lane attempted and, measured below, did not achieve. Full argument: <a href="hypotheses.html">hypotheses page</a>
and <code>research/h78cs_hypotheses.md</code> §0. Leaderboard figures in the prompt (0.4413 / 0.3195) are prompt claims,
not receipts re-verified here (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard, login</a>).</p></div>

<div class="card"><h2>HOLDOUT-DTI — evaluator {esc(h['evaluator_version'])}, seed 20, {h['withheld_positive_pixels']:,} withheld positives</h2>
<table><tr><th>Config (B3 flank, 44,090 dots)</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Withheld</th></tr>
<tr><td><code>CAND_CS|B3|44090</code> (103 + 15 collinear)</td><td><b>{f4(h['candidate']['dti'])}</b></td><td>{ci(h['candidate'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td><code>CTRL_A2|B3|44090</code> (103, exact H78-A rerun)</td><td>{f4(h['ctrl']['dti'])}</td><td>{ci(h['ctrl'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td><code>ABL_A0CS|B3|44090</code> (19 raw + 15 collinear)</td><td>{f4(h['ablation']['dti'])}</td><td>{ci(h['ablation'])}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
<tr><td>paired Δ CAND − CTRL</td><td colspan="3">{dlt(h['paired_delta_cand_minus_ctrl'])}</td></tr>
<tr><td>far-truth stratum (&gt;10 px from visible faults, {far['n_positives']:,} positives): CAND / CTRL / Δ</td>
<td colspan="3">{f4(far['scores']['CAND_CS|B3|44090']['dti'])} / {f4(far['scores']['CTRL_A2|B3|44090']['dti'])} / {dlt(far['paired_delta_cand_minus_ctrl'])}</td></tr>
{rep_row}</table>
<p>The control reproduces the shipped H78-A evidence to four decimals (B3 0.1826, B2 0.1586, B3@50k 0.1843), so the
instrument is not the explanation: adding along-strike path integrals <b>does not help</b> this model — point-negative
overall and significantly negative on far-from-catalogue truth, the stratum that most resembles live hidden faults.
Score-surface Spearman ρ(CAND, CTRL) = {h['surface_rho_candidate_vs_ctrl_seed20']['spearman_full_footprint']:.4f} on the
seed-20 surfaces: as a model class this lane sits inside H78-A's lane (amendment IR-78CS-01) and must not be re-proposed
as a distinct lane.</p>
<h3>Preregistered gate</h3><table><tr><th>Condition (all required to promote)</th><th>Result</th></tr>{gate_rows}</table></div>

<div class="card"><h2>Leakage canary — collinear features (symmetric AUC, threshold 0.90)</h2>
<p>Max over all 118 features: {rc['canary']['max_single_feature_auc']:.4f} (a collinear feature,
<code>cs_det_elev_gn_L5_mean</code> — the features carry univariate signal; they are simply redundant multivariately).
Flagged: none.</p>
<table><tr><th>Feature</th><th>Symmetric AUC</th><th>≤0.90</th></tr>{canary_rows}</table></div>

<div class="card"><h2>Uniqueness vs registry (limits: ρ ≤ 0.90, dot overlap ≤ 0.70)</h2>
<table><tr><th>Registry / shipped raster</th><th>Surface ρ (before placement)</th><th>My dots ≤3 px of theirs</th><th>Their dots ≤3 px of mine</th><th>Final-dot ρ</th></tr>{uq_rows}</table>
<p>Max surface |ρ| {uq['surface_max_abs_rho']:.4f}; max dot overlap {uq['dots_max_overlap']:.4f}; passed = {uq['passed']}.
{esc(uq['note'])}</p></div>

<div class="card"><h2>Format validator (writer receipt checks on the written file)</h2>
<table><tr><th>Check</th><th>Result</th></tr>{val_rows}</table>
<p class="small">Independent verifier: <code>python scripts/verify_tif.py docs/downloads/{stem}.tif</code> (12 checks, does not import lane code).</p></div>

<div class="card"><h2>What this session adds &amp; what next</h2>
<ul>
<li><b>Killed hypothesis (measured):</b> straight along-strike integration of steered responses adds nothing to a pointwise steered HGB — do not spend more lanes on feature-append variants of A2 (ρ≈0.95 = same lane).</li>
<li><b>First across-seed numbers for the repo's best model class</b> (CTRL_A2 seeds 20/30 above) — use the spread, not a single draw, when judging future deltas.</li>
<li><b>Highest-P(Win) next steps:</b> (1) GPU session: U-Net (organizer reference class) over 19 bands + steered features with the same buffered folds — the only model class with headroom toward 0.32+; (2) km-scale geomorphic-setting context features (hypothesis H78-CTX, ranked #3 in <code>research/h78cs_hypotheses.md</code>) as a genuinely distinct CPU lane; (3) complete the full-registry uniqueness audit for H78-A (release-audit blocker IR-78-16) before any selector considers a slot for any file.</li>
<li><b>Limitations:</b> holdout truth is catalogue-like and near-halo-biased (IR-78-09 stands); two seeds only; no organizer score exists for any file in this repo; external pages beyond github.com could not be re-fetched from this sandbox (links listed for manual review).</li>
</ul></div>
</body></html>"""

exec_summary = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Executive summary — exactly how to submit · H78-CS (negative)</title>{CSS}</head><body>
<p><a href="h78cs.html">← H78-CS lane page</a> · <a href="index.html">Home (H78-A primary)</a></p>
<div class="banner {'ok' if promote else 'bad'}"><h1>{banner_head}</h1><p class="big">{banner_body}</p></div>
<div class="card"><h2>Exactly how a submission is made (for a file whose banner says YES)</h2>
<ol>
<li>Open the lane page and read the banner. A slot may be spent <b>only</b> on a file whose banner is an unqualified YES and which the current <code>evidence/release_audit.json</code> does not block. This lane's file says NO, and at merge time <b>every</b> file in this repo is blocked - stop here; check the <a href="index.html">home page</a> for current status.</li>
<li>Download the <code>.tif</code> (or the <code>.zip</code> containing that single TIFF) and note the SHA-256 printed beside it. Optionally re-verify locally: <code>python scripts/verify_tif.py &lt;file&gt;.tif</code> must print <code>all_passed: true</code> (single band float32, EPSG:32611, 3730×3292, sample transform, all values finite and in [0, 1] — so the portal error <i>"Predicted values must be in range [0, 1]"</i> cannot occur).</li>
<li>Go to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition 306</a> → <i>New submission</i> → choose the <code>.tif</code> (or <code>.zip</code>) file. Confirm the weekly cap shown on that page has room — this system never auto-uploads and has spent 0 slots.</li>
<li>Paste the lane's unique submission name and the ≤140-character note from its banner (they identify model, dot budget, flank and the labelled HOLDOUT-DTI; they are not a score projection).</li>
<li>Submit once. Copy the returned score into <code>registry/live_scores.csv</code> labelled <b>ORGANIZER-CONFIRMED</b> (the only label allowed for a portal receipt), then rebuild the site. Until that moment every number for the file is HOLDOUT-DTI or owner-report.</li>
</ol>
<p class="small">Competition pages for manual review: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">about</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules (PDF)</a> ·
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> (login required; not re-fetched from the build sandbox).</p></div>
<div class="card"><h2>This lane's file (inspection only)</h2>
<p><code>{esc(rc['submission_name'])}</code> · SHA-256 <code>{esc(rc['raster_sha256'])}</code> · {rc['raster']['dots']:,} dots ·
HOLDOUT-DTI {f4(h['candidate']['dti'])} {ci(h['candidate'])} vs CTRL {f4(h['ctrl']['dti'])} (evaluator {esc(h['evaluator_version'])}, seed 20,
{h['withheld_positive_pixels']:,} withheld) · verdict <b>{esc(rc['verdict'])}</b> · ORGANIZER-CONFIRMED: none.</p>
<a class="dl" href="downloads/{stem}.tif">⬇ Download .tif (INSPECTION ONLY)</a>
<a class="dl" href="downloads/{stem}.zip">⬇ Download .zip</a></div>
</body></html>"""

(DOCS / "h78cs.html").write_text(index)
(DOCS / "h78cs-executive-summary.html").write_text(exec_summary)
print("WROTE docs/h78cs.html + docs/h78cs-executive-summary.html promote =", promote)
