#!/usr/bin/env python3
"""Generate docs/index.html + executive-summary.html from evidence JSONs only."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
EV, DOCS = ROOT / "evidence", ROOT / "docs"
exp = json.loads((EV / "h78mpc_experiments.json").read_text())
exp2 = json.loads((EV / "h78mpc_experiments_pass2_spaced.json").read_text())
prod = json.loads((EV / "h78mpc_production.json").read_text())
uq = json.loads((EV / "h78mpc_uniqueness.json").read_text())
can = json.loads((EV / "h78mpc_canaries.json").read_text())
rc = json.loads((EV / "h78mpc_run_card.json").read_text())
sc = exp2["summaries"]["E2_MPC_SPACED"]["scores"]
pd_ = exp2["summaries"]["E2_MPC_SPACED"]["paired_differences"]
sc0 = exp["summaries"]["E2_MPC"]["scores"]
stem = prod["final_stem"]
promote = rc["verdict"] == "promote"
def f4(x): return f"{x:.4f}"
def ci(s): return f"[{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}]"
CSS = """<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:960px;margin:0 auto;padding:24px;line-height:1.55;color:#1a1a1a;background:#fafafa}
.banner{border-radius:12px;padding:22px;margin:18px 0;color:#fff}.ok{background:linear-gradient(135deg,#14663a,#1e9e57)}
.bad{background:linear-gradient(135deg,#8f1d1d,#c0392b)}.banner h1{margin:0 0 8px;font-size:1.6rem}.big{font-size:1.12rem;font-weight:600}
.dl{display:inline-block;background:#fff;color:#14663a;font-weight:700;padding:12px 20px;border-radius:8px;text-decoration:none;margin:8px 8px 0 0}
table{border-collapse:collapse;width:100%;margin:12px 0;background:#fff}td,th{border:1px solid #ddd;padding:7px 9px;text-align:left;font-size:.92rem}
code{background:#eee;padding:2px 5px;border-radius:4px;word-break:break-all}
.card{background:#fff;border:1px solid #ddd;border-radius:10px;padding:16px 20px;margin:16px 0}
.copy{background:#f4f4f4;border:1px dashed #999;border-radius:8px;padding:12px;margin:8px 0}
img{max-width:100%}.small{font-size:.85rem;color:#555}.warn{background:#fff8e6;border:1px solid #e0b400;border-radius:8px;padding:10px 14px}
</style>"""
best = rc["current_repo_best_holdout"]
uniq = rc["correlation_overlap_vs_registry"]

if promote:
    banner = f"""<div class="banner ok"><h1>✅ OK TO DOWNLOAD &amp; SUBMIT — verdict: promote-to-selector-only</h1>
<p class="big">✅ OK to download: YES — local format validator PASS: float32, EPSG:32611, 3730×3292, all finite, values [0,1].<br>
✅ OK to submit: YES for the separate selector to consider, not automatic approval. HOLDOUT-DTI {f4(sc['E2_MPC_SPACED']['dti'])} {ci(sc['E2_MPC_SPACED'])}
(evaluator gems57-pooled-hide-v2, 11,321 withheld positives) passes all configured gates. No score for this file is ORGANIZER-CONFIRMED; the agent spent 0 slots.</p>"""
else:
    banner = f"""<div class="banner bad"><h1>⛔ OK TO DOWNLOAD: YES — RESEARCH ONLY · OK TO SUBMIT: NO</h1>
<p class="big">Do not upload this file or spend a competition slot. Local format validation passes (float32, EPSG:32611, 3730×3292,
all finite, values in [0,1]), but the strict duplicate gate fails: <b>{uniq['final_dots_worst_forward_3px_informative']:.3f}</b> of its dots
are within 3 px of a non-spacefilling registry raster (limit 0.700), and the all-raster maximum is <b>{uniq['final_dots_worst_forward_3px_literal_all_rasters']:.3f}</b>.
Its HOLDOUT-DTI {f4(sc['E2_MPC_SPACED']['dti'])} {ci(sc['E2_MPC_SPACED'])} (evaluator gems57-pooled-hide-v2, 11,321 withheld positives)
is below the current repository best HOLDOUT-DTI {f4(best['dti'])} {ci(best)} (same evaluator and withheld-positive count; descriptive, not a paired test).
No replacement raster was generated after the duplicate-stop rule; 0 slots were spent.</p>"""
banner += f"""
<a class="dl" href="downloads/{stem}.tif">⬇ Download research GeoTIFF (do not submit)</a>
<a class="dl" href="downloads/{stem}.zip">⬇ Research .zip (single TIFF inside; do not submit)</a>
<a class="dl" href="downloads/run_card_h78mpc.json">JSON run card</a>
<a class="dl" href="h78mpc-executive-summary.html">Submission process &amp; current stop status →</a>
<div class="copy" style="color:#1a1a1a"><b>Artifact name (do not enter in the portal):</b> <code>{prod['name']}</code><br>
<b>Candidate note (metadata only; do not paste into the portal):</b> <code>{prod['note']}</code><br>
<b>SHA-256:</b> <code>{prod['sha256']}</code></div>
<p class="small" style="color:#eafff2">HOLDOUT-DTI vs fold-fair H33 control: paired difference +{pd_['h33_analogue_foldfair']['delta']:.4f}
{ci(pd_['h33_analogue_foldfair'])} (not statistically significant). MPC vs no-MPC ablation: paired HOLDOUT-DTI difference
+{pd_['E1_BASE_SPACED']['delta']:.4f} [{pd_['E1_BASE_SPACED']['ci95'][0]:.4f}, {pd_['E1_BASE_SPACED']['ci95'][1]:.4f}].
There is no ORGANIZER-CONFIRMED score for this file. A successful local preflight is not organizer acceptance.</p></div>"""

rows = "".join(f"<tr><td>{n}</td><td><b>{f4(sc[n]['dti'])}</b></td><td>{ci(sc[n])}</td></tr>"
    for n in ["E2_MPC_SPACED", "h33_analogue_foldfair", "E1_BASE_SPACED", "random_control", "E3_MPC_ONLY_SPACED"])
rows0 = "".join(f"<tr><td>{n}</td><td>{f4(sc0[n]['dti'])}</td><td>{ci(sc0[n])}</td></tr>"
    for n in ["E2_MPC", "E1_BASE", "E3_MPC_ONLY", "random_control", "h33_analogue_foldfair"])
informative = [r for r in uq["dot_rows"] if r.get("their_3px_halo_fp_fraction", 0) < 0.70]
worst6 = sorted(informative, key=lambda r: -r["mutual"])[:6]
uq_rows = "".join(f"<tr><td><code>{r['name']}</code></td><td>{r['their_dots']:,}</td><td>{r['forward_overlap_mine_in_theirs3px']:.4f}</td><td>{r['reverse_overlap_theirs_in_mine3px']:.4f}</td><td><b>{r['mutual']:.4f}</b></td><td>{r['their_3px_halo_fp_fraction']:.3f}</td></tr>" for r in worst6)
mpc_can = sorted([c for c in can["features"] if c["feature"].startswith(("mpc_", "frangi_"))], key=lambda c: -c["symmetric_auc"])[:10]
mpc_rows = "".join(f"<tr><td><code>{c['feature']}</code></td><td>{c['auc_catalogue']:.3f}</td><td>{c['auc_withheld']:.3f}</td><td>{c['symmetric_auc']:.3f}</td><td>{'PASS' if c['passed'] else 'FAIL'}</td></tr>" for c in mpc_can)

if promote:
    exec_status = f"""<div class="banner ok"><p class="big">OK TO DOWNLOAD: YES · OK TO SUBMIT: YES for selector consideration only. HOLDOUT-DTI {f4(sc['E2_MPC_SPACED']['dti'])} {ci(sc['E2_MPC_SPACED'])}; no ORGANIZER-CONFIRMED score exists. Follow the current weekly cap.</p></div>"""
else:
    exec_status = f"""<div class="banner bad"><p class="big">⛔ OK TO DOWNLOAD: YES — RESEARCH / EDUCATION ONLY · OK TO SUBMIT: NO. Do not upload this file or spend a slot. Literal forward 3-px overlap is {uq['worst_forward_informative']:.3f} (>0.700) against an informative registry raster; the recorded repository-best HOLDOUT-DTI is {f4(best['dti'])} {ci(best)}, above the candidate. No new raster was built after the required duplicate stop.</p></div>"""

index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>GEMSDOE78 — H78-MPC monogenic phase-congruency review (negative / duplicate stop)</title>{CSS}</head><body>
<p><a href="index.html">← Primary lane H78-A (home)</a> · H78-MPC is a separate experiment. Its TIF is downloadable for research/education only; the strict registry-overlap gate fails and it is <b>not OK to submit</b>. See IR-78-14 / IR-78-15 in the registry and the JSON run card.</p><p><b>Core Values.</b> <b>Maximize P(Win)</b> — every weekly slot is an experiment gated by a preregistered holdout, not a lottery ticket.
<b>Own the Outcome</b> — the emission defect found in our own Pass 1 (IR-78-EMIT-01) is measured, published, and corrected below, not hidden.</p>
{banner}
<div class="card"><h2>Why did h33-h33-2-b2 (GEMSDOE32) score 0.2778 — and can we beat it?</h2>
<p><b>Scoring law</b> (organizer-published; re-derived and unit-tested in <code>vendor/gems57/metric.py</code>):
DTI = TP<sub>w</sub>/(TP<sub>w</sub>+0.2·FP<sub>w</sub>+0.8·FN<sub>w</sub>), 300 m triangular kernel. For binary dots,
one more non-redundant dot raises DTI iff its kernel credit <code>k &gt; 0.2·DTI</code> — at 0.2778 the bar is
<b>0.0556 credit/dot</b>. DTI is a budget: credit density at the emitted mass decides everything.</p>
<p><b>H33's ladder</b> (all values are family/owner reports, not authenticated organizer receipts in this repository): continuous parent h19-5
(multi-lineament-corroborated) 0.1922 → dotted d1.5 0.2477 → dotted d2.8 0.2600 → solo re-emit 0.2708 →
<b>+B=2 catalogue-flank prune 0.2778</b> (37,654 dots). Three plausible contributors: parent credit density,
kernel-matched ~2.8 px dotted spacing, and deleting near-catalogue mass (per the cited metric/masking interpretation).
The measured raster relationship and provenance caveats are in <code>docs/why-h33.md</code>.</p>
<p><b>Beating it</b> requires a better ranking of likely hidden faults, not merely a different thinning rule. The 0.4413 figure
is a user-supplied/dated public-leaderboard report, not this project's score and not re-fetched here. In this lane, adding
MPC features improved HOLDOUT-DTI by a paired +{pd_['E1_BASE_SPACED']['delta']:.4f} over an identical 48-band stack without them
(evaluator gems57-pooled-hide-v2, 11,321 withheld positives, 95% CI [{pd_['E1_BASE_SPACED']['ci95'][0]:.4f}, {pd_['E1_BASE_SPACED']['ci95'][1]:.4f}]); that ablation result is a scientific signal, not a submission result.</p></div>

<div class="card"><h2>This lane: H78-MPC — monogenic phase congruency (duplicate-stop result)</h2>
<p><b>Hypothesis.</b> Catalogue-missing blind faults have weak gradient <i>amplitude</i> — what HGM/tilt/worm/Blakely/Steger/radon
lanes (all tried, live ≤0.16 as pure lanes) key on — but retain a coherent local-<i>phase</i> step across scales.
Phase congruency from the Riesz-transform monogenic signal is contrast-invariant, targeting exactly those edges.
<b>Mimic:</b> lithologic contacts and flight-line seams. <b>Method:</b> 32 MPC-family features (σ=1/2/4 on RTP, isostatic gravity,
detrended elevation, depth-to-basement + Frangi) over a 48-band base; leave-one-quadrant-out gradient boosting trained
only on visible catalogue; spaced (2.5 px) emission of exactly 37,654 dots, min catalogue distance 2.83 px, 0 on-catalogue.
Five ranked hypotheses were preregistered before Experiment 1 (<a href="research-hypotheses.md">view the candidate table and ranking</a>;
see also <code>registry/preregistration_h78_mpc.json</code>).</p>
<img src="assets/fig1.png" alt="Measured: OOF surface, final dots vs catalogue, holdout bars"></div>

<div class="card"><h2>Holdout — HOLDOUT-DTI, <code>gems57-pooled-hide-v2</code>, seed 20, 11,321 withheld positives</h2>
<p>Whole fault components hidden with a 3 px feature buffer; every catalogue-based input derived from visible faults only;
visible faults masked pixel-exactly; pooled DTI α=0.2 β=0.8 R=300 m. Instrument identity verified this run: control
<code>h33_analogue_foldfair = {f4(sc['h33_analogue_foldfair']['dti'])}</code> and random <code>{f4(sc['random_control']['dti'])}</code>
match the values published by GEMSDOE73/GEMSDOE77 on the identical instrument.</p>
<table><tr><th>Arm (spaced emission, IR-78-EMIT-01 corrected)</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>{rows}</table>
<p><b>Paired:</b> E2−E1 +{pd_['E1_BASE_SPACED']['delta']:.4f} [{pd_['E1_BASE_SPACED']['ci95'][0]:.4f}, {pd_['E1_BASE_SPACED']['ci95'][1]:.4f}] (significant —
the MPC effect); E2−control +{pd_['h33_analogue_foldfair']['delta']:.4f} [{pd_['h33_analogue_foldfair']['ci95'][0]:.4f}, {pd_['h33_analogue_foldfair']['ci95'][1]:.4f}]
(not significant); E2−random +{pd_['random_control']['delta']:.4f} [{pd_['random_control']['ci95'][0]:.4f}, {pd_['random_control']['ci95'][1]:.4f}].</p>
<div class="warn"><b>IR-78-EMIT-01 (Pass-1 reading, retained):</b> as originally preregistered, the vendor greedy allocator emitted
contiguous runs (98.9% of dots with a neighbour ≤1.5 px vs control median spacing 3.16 px), wasting kernel credit.
Those scores were E2 {f4(sc0['E2_MPC']['dti'])} / E1 {f4(sc0['E1_BASE']['dti'])} / control {f4(sc0['h33_analogue_foldfair']['dti'])}
(<code>evidence/h78mpc_experiments.json</code>). Pass 2 re-emitted the <i>frozen</i> surfaces with the control's spaced emitter — no retraining —
and the MPC paired effect is significant under <i>both</i> emitters. The superseded clustered production file
(sha256 <code>{prod['superseded_clustered']['sha256'][:16]}…</code>) was withdrawn.</div>
<table><tr><th>Arm (Pass-1 clustered emitter — defective)</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>{rows0}</table></div>

<div class="card"><h2>Automated validation — no human inspection in the loop</h2>
<p><b>Leakage canaries (before any fitting):</b> all 80 features alone vs catalogue &amp; withheld truth; max symmetric AUC
<b>{can['max_symmetric_auc']:.4f} ≤ 0.90 — PASS</b>. Top MPC-family rows:</p>
<table><tr><th>Feature</th><th>AUC cat</th><th>AUC withheld</th><th>Symmetric</th><th>Gate</th></tr>{mpc_rows}</table>
<p><b>Strict uniqueness gate (surface before placement AND final dots):</b> the available local inventory contains
{uq['registry_count']} rasters ({uq['informative_count']} had a 3-px halo covering under 70% of the footprint); this is not proof
that every sibling or organizer raster was available. Pre-placement max |Spearman ρ| on a 300k-cell fixed-seed sample is
<b>{uq['preplacement_max_abs_sampled_rho']:.4f} ≤ 0.90</b> (PASS). The binding rule is the literal one-way fraction of our final dots
within 3 px of a registry raster's dots — not mutual overlap. It is <b>{uq['worst_forward_informative']:.4f} > 0.70</b> against
<code>gems70-p5-submodular-multiphysics-hydro-54000-20261020.tif</code>, and <b>{uq['worst_forward_literal_all_rasters']:.4f} > 0.70</b>
against the r13 lattice raster. Therefore the candidate is a <b>duplicate under the specified rule; stop / not OK to submit</b>.
Mutual-overlap values are diagnostic only. Every row is in <code>evidence/h78mpc_uniqueness.json</code>.</p>
<table><tr><th>Registry raster (worst mutual; diagnostic only)</th><th>Their dots</th><th>Fwd 3px</th><th>Rev 3px</th><th>Mutual diagnostic</th><th>Their halo/footprint</th></tr>{uq_rows}</table>
<p><b>Format validator (re-read from disk):</b> all checks PASS — see <a href="downloads/{stem}.json">receipt</a>:
single-band float32, EPSG:32611, 3730×3292, transform = sample submission, 12,279,160/12,279,160 cells finite in [0,1],
0 NaN, nodata=None, values exactly {{0,1}}, 37,654 dots, 0 on catalogue, 0 outside footprint.
Local format/range preflight — not organiser acceptance.</p></div>

<div class="card"><h2>Run card, reproduction, sources</h2>
<p><a href="downloads/run_card_h78mpc.json">Machine-readable run card (JSON)</a> · Evidence in repo:
<code>evidence/h78mpc_experiments.json</code>, <code>evidence/h78mpc_experiments_pass2_spaced.json</code>, <code>evidence/h78mpc_canaries.json</code>,
<code>evidence/h78mpc_uniqueness.json</code>, <code>evidence/h78mpc_duplicate_stop.json</code>. This review ran no new experiment.
The existing production scripts now fail closed before packaging under the recorded duplicate audit; do not rerun model experiments beyond the lane budget.
Replay the status/site only with <code>python3 scripts/build_run_card_mpc.py</code> → <code>python3 scripts/build_site_mpc.py</code>.
Tests: <code>pytest tests -q</code>.</p>
<p class="small">Official sources: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData #306 problem description</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">GEMS Prize rules (NLR FY26OSTI-96647)</a> ·
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">organiser reference solution</a> ·
<a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> ·
<a href="https://gdr.openei.org/submissions/1391">GDR 1391 INGENIOUS</a> · <a href="https://epsg.io/32611">EPSG:32611</a> ·
<a href="https://peterkovesi.com/projects/phasecongruency/index.html">Kovesi, phase congruency</a> ·
<a href="https://www.diva-portal.org/smash/get/diva2:241550/FULLTEXT01.pdf">Felsberg &amp; Sommer 2001, monogenic signal</a>.</p></div>
</body></html>"""

exec_sum = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Executive summary — exactly how to submit · GEMSDOE78</title>{CSS}</head><body>
<h1>Executive summary: exactly how to make the submission</h1>
{exec_status}
<div class="card">
<h2>Current candidate disposition</h2>
<p>This H78-MPC TIFF is <b>downloadable for research/education, but not eligible for submission</b>. Do not select it in DrivenData. Its final-dot forward overlap exceeds the strict 3-px duplicate limit, and its HOLDOUT-DTI does not beat the repository's recorded best. No slot has been spent; no replacement was generated after the mandatory stop.</p>
<h2>Step 1 — Download for inspection only (not for upload)</h2>
<p><a href="downloads/{stem}.tif"><b>{stem}.tif — research artifact; do not submit</b></a> or <a href="downloads/{stem}.zip"><b>{stem}.zip — research artifact; do not submit</b></a>
(the ZIP contains exactly that one TIFF). Integrity check: <code>sha256sum {stem}.tif</code> → <code>{prod['sha256']}</code>.</p>
<h2>Step 2 — When a future candidate is explicitly marked OK TO SUBMIT: YES</h2>
<p>Use <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition 306</a> → sign in → <b>New submission</b>.
Read the current weekly cap on the competition page. Do not upload the H78-MPC research artifact described here.</p>
<h2>Step 3 — File to submit (future eligible candidate only)</h2>
<p>Choose the exact <code>.tif</code> linked from the eligible candidate's page (or its single-TIFF <code>.zip</code> if allowed).
The H78-MPC file itself passes local format checks: single-band float32, EPSG:32611, shape 3730×3292, geotransform
(100, 0, 243350, 0, −100, 4508550), all finite, and values in [0,1]. Local preflight is not organizer acceptance.</p>
<h2>Step 4 — Name and Note (future eligible candidate only)</h2>
<p>Copy the unique name and note only from a page whose automated run card says <code>ok_to_submit: true</code>.
Do not paste the H78-MPC artifact metadata below into the form.</p>
<div class="copy"><b>Research artifact name — not for portal use:</b><br><code>{prod['name']}</code></div>
<div class="copy"><b>Research artifact note — not for portal use:</b><br><code>{prod['note']}</code></div>
<h2>Step 5 — Range error preflight</h2>
<p>The local verifier re-opened this research TIFF: all 12,279,160 cells are finite, min 0.0, max 1.0, 0 NaN, and <code>nodata=None</code>
(<a href="downloads/{stem}.json">validator receipt</a>). Thus the stored bytes do not show an out-of-range/NaN cause for the reported
"Predicted values must be in range [0, 1]" error; this does not guarantee organizer acceptance.</p>
<h2>Step 6 — After a future submission</h2>
<p>Copy the score verbatim from that submission-page receipt, label it <b>ORGANIZER-CONFIRMED</b> with the file name and SHA-256.
Never record a HOLDOUT-DTI or a projection as an organizer score.</p></div>
<p><a href="h78mpc.html">← H78-MPC page</a> · <a href="index.html">Primary lane home</a></p></body></html>"""
(DOCS / "h78mpc.html").write_text(index)
(DOCS / "h78mpc-executive-summary.html").write_text(exec_sum)
print("site written; promote =", promote)
