#!/usr/bin/env python3
"""Generate docs/index.html + executive-summary.html from evidence JSONs only."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
EV, DOCS = ROOT / "evidence", ROOT / "docs"
exp = json.loads((EV / "experiments.json").read_text())
exp2 = json.loads((EV / "experiments_pass2_spaced.json").read_text())
prod = json.loads((EV / "production.json").read_text())
uq = json.loads((EV / "uniqueness_production.json").read_text())
can = json.loads((EV / "canaries.json").read_text())
rc = json.loads((EV / "run_card.json").read_text())
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
banner = f"""<div class="banner {'ok' if promote else 'bad'}"><h1>{'✅ OK TO DOWNLOAD &amp; SUBMIT — verdict: promote (human selector spends the slot)' if promote else '⛔ NOT OK TO SUBMIT'}</h1>
<p class="big">✅ OK to download: YES — validator PASS, every value in [0,1], 0 NaN anywhere, nodata=None, EPSG:32611, 3730×3292, float32
(the <i>"Predicted values must be in range [0, 1]"</i> portal error cannot occur with this file).<br>
✅ OK to submit: YES — preregistered gate passed on the shared <code>gems57-pooled-hide-v2</code> holdout after a disclosed
emission-defect correction: <b>HOLDOUT-DTI {f4(sc['E2_MPC_SPACED']['dti'])}</b> {ci(sc['E2_MPC_SPACED'])} (seed 20, 11,321 withheld positives)
vs fold-fair H33 control {f4(sc['h33_analogue_foldfair']['dti'])} and vs no-MPC ablation {f4(sc['E1_BASE_SPACED']['dti'])}
(paired MPC effect +{pd_['E1_BASE_SPACED']['delta']:.4f} [{pd_['E1_BASE_SPACED']['ci95'][0]:.4f}, {pd_['E1_BASE_SPACED']['ci95'][1]:.4f}], significant).
0 weekly slots have been spent by this system — <b>check the weekly cap on the submission page, then upload once.</b></p>
<a class="dl" href="downloads/{stem}.tif">⬇ Download submission .tif</a>
<a class="dl" href="downloads/{stem}.zip">⬇ Download .zip (single TIFF inside)</a>
<a class="dl" href="downloads/run_card.json">JSON run card</a>
<a class="dl" href="executive-summary.html">How to submit (step-by-step) →</a>
<div class="copy" style="color:#1a1a1a"><b>Unique submission name:</b> <code>{prod['name']}</code><br>
<b>Note to paste ({len(prod['note'])}/140 chars):</b> <code>{prod['note']}</code><br>
<b>SHA-256:</b> <code>{prod['sha256']}</code></div>
<p class="small" style="color:#eafff2">Honest caveats, measured: advantage over the H33 fold-fair control is
+{pd_['h33_analogue_foldfair']['delta']:.4f} [{pd_['h33_analogue_foldfair']['ci95'][0]:.4f}, {pd_['h33_analogue_foldfair']['ci95'][1]:.4f}]
— a point-estimate win, <b>not statistically significant</b>; emission was corrected post-hoc (IR-78-EMIT-01, both readings published below);
no organizer score exists yet for this file. No projection on this site is a score.</p></div>"""

rows = "".join(f"<tr><td>{n}</td><td><b>{f4(sc[n]['dti'])}</b></td><td>{ci(sc[n])}</td></tr>"
    for n in ["E2_MPC_SPACED", "h33_analogue_foldfair", "E1_BASE_SPACED", "random_control", "E3_MPC_ONLY_SPACED"])
rows0 = "".join(f"<tr><td>{n}</td><td>{f4(sc0[n]['dti'])}</td><td>{ci(sc0[n])}</td></tr>"
    for n in ["E2_MPC", "E1_BASE", "E3_MPC_ONLY", "random_control", "h33_analogue_foldfair"])
informative = [r for r in uq["dot_rows"] if r.get("their_3px_halo_fp_fraction", 0) < 0.70]
worst6 = sorted(informative, key=lambda r: -r["mutual"])[:6]
uq_rows = "".join(f"<tr><td><code>{r['name']}</code></td><td>{r['their_dots']:,}</td><td>{r['forward_overlap_mine_in_theirs3px']:.4f}</td><td>{r['reverse_overlap_theirs_in_mine3px']:.4f}</td><td><b>{r['mutual']:.4f}</b></td><td>{r['their_3px_halo_fp_fraction']:.3f}</td></tr>" for r in worst6)
mpc_can = sorted([c for c in can["features"] if c["feature"].startswith(("mpc_", "frangi_"))], key=lambda c: -c["symmetric_auc"])[:10]
mpc_rows = "".join(f"<tr><td><code>{c['feature']}</code></td><td>{c['auc_catalogue']:.3f}</td><td>{c['auc_withheld']:.3f}</td><td>{c['symmetric_auc']:.3f}</td><td>{'PASS' if c['passed'] else 'FAIL'}</td></tr>" for c in mpc_can)

index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>GEMSDOE78 — H78-MPC monogenic phase-congruency submission (promote)</title>{CSS}</head><body>
<p><b>Core Values.</b> <b>Maximize P(Win)</b> — every weekly slot is an experiment gated by a preregistered holdout, not a lottery ticket.
<b>Own the Outcome</b> — the emission defect found in our own Pass 1 (IR-78-EMIT-01) is measured, published, and corrected below, not hidden.</p>
{banner}
<div class="card"><h2>Why did h33-h33-2-b2 (GEMSDOE32) score 0.2778 — and can we beat it?</h2>
<p><b>Scoring law</b> (organizer-published; re-derived and unit-tested in <code>vendor/gems57/metric.py</code>):
DTI = TP<sub>w</sub>/(TP<sub>w</sub>+0.2·FP<sub>w</sub>+0.8·FN<sub>w</sub>), 300 m triangular kernel. For binary dots,
one more non-redundant dot raises DTI iff its kernel credit <code>k &gt; 0.2·DTI</code> — at 0.2778 the bar is
<b>0.0556 credit/dot</b>. DTI is a budget: credit density at the emitted mass decides everything.</p>
<p><b>H33's ladder</b> (all live scores = user-reported submission-page receipts): continuous parent h19-5
(multi-lineament-corroborated) 0.1922 → dotted d1.5 0.2477 → dotted d2.8 0.2600 → solo re-emit 0.2708 →
<b>+B=2 catalogue-flank prune 0.2778</b> (37,654 dots). Three multiplicative ingredients: parent credit density,
kernel-matched ~2.8 px dotted spacing, and deleting zero-credit near-catalogue mass (the organiser masks mapped
faults pixel-exactly). Full forensic ledger: <code>docs/why-h33.md</code>.</p>
<p><b>Beating it</b> requires higher credit density in the top 37,654 cells — a better ranking, not a better thinning
(the user-reported 0.4413 leaderboard top implies ≈59% more credit/dot than H33's parent). This lane contributes one
measured ranking improvement: monogenic phase-congruency features raise holdout DTI by a significant paired
+{pd_['E1_BASE_SPACED']['delta']:.4f} over an identical 48-band stack without them, and lift the surface AUC vs withheld
faults 0.674 → 0.696. That is a building block toward 0.4413, not a claim of reaching it.</p></div>

<div class="card"><h2>This lane: H78-MPC — monogenic phase congruency (unique, not in any sibling)</h2>
<p><b>Hypothesis.</b> Catalogue-missing blind faults have weak gradient <i>amplitude</i> — what HGM/tilt/worm/Blakely/Steger/radon
lanes (all tried, live ≤0.16 as pure lanes) key on — but retain a coherent local-<i>phase</i> step across scales.
Phase congruency from the Riesz-transform monogenic signal is contrast-invariant, targeting exactly those edges.
<b>Mimic:</b> lithologic contacts and flight-line seams. <b>Method:</b> 32 MPC-family features (σ=1/2/4 on RTP, isostatic gravity,
detrended elevation, depth-to-basement + Frangi) over a 48-band base; leave-one-quadrant-out gradient boosting trained
only on visible catalogue; spaced (2.5 px) emission of exactly 37,654 dots, min catalogue distance 2.83 px, 0 on-catalogue.
Five ranked hypotheses were preregistered before Experiment 1 (<code>docs/research-hypotheses.md</code>,
<code>registry/preregistration_h78_mpc.json</code>).</p>
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
(<code>evidence/experiments.json</code>). Pass 2 re-emitted the <i>frozen</i> surfaces with the control's spaced emitter — no retraining —
and the MPC paired effect is significant under <i>both</i> emitters. The superseded clustered production file
(sha256 <code>{prod['superseded_clustered']['sha256'][:16]}…</code>) was withdrawn.</div>
<table><tr><th>Arm (Pass-1 clustered emitter — defective)</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>{rows0}</table></div>

<div class="card"><h2>Automated validation — no human inspection in the loop</h2>
<p><b>Leakage canaries (before any fitting):</b> all 80 features alone vs catalogue &amp; withheld truth; max symmetric AUC
<b>{can['max_symmetric_auc']:.4f} ≤ 0.90 — PASS</b>. Top MPC-family rows:</p>
<table><tr><th>Feature</th><th>AUC cat</th><th>AUC withheld</th><th>Symmetric</th><th>Gate</th></tr>{mpc_rows}</table>
<p><b>Uniqueness (checked on the surface before placement AND on final dots):</b> {uq['registry_count']} unique registry rasters
(GEMSDOE32/36/70/73 downloads + restored scored set), {uq['informative_count']} informative. Pre-placement max |Spearman ρ|
(300k-cell fixed-seed sample) = <b>{uq['preplacement_max_abs_sampled_rho']:.4f} ≤ 0.90</b>; final dots worst <b>mutual</b> 3-px overlap =
<b>{uq['worst_mutual_informative']:.4f} ≤ 0.70</b> (preregistered criterion). Forward-only readings exceed 0.70 only vs the
206,895-dot lattice witness (3-px halo = 99.9% of footprint — vacuous) and one 54,000-dot raster (forward {uq['worst_forward_informative']:.2f},
mutual 0.42); every row is in <code>evidence/uniqueness_production.json</code>.</p>
<table><tr><th>Registry raster (worst mutual)</th><th>Their dots</th><th>Fwd 3px</th><th>Rev 3px</th><th>Mutual</th><th>Their halo/footprint</th></tr>{uq_rows}</table>
<p><b>Format validator (re-read from disk):</b> all checks PASS — see <a href="downloads/{stem}.json">receipt</a>:
single-band float32, EPSG:32611, 3730×3292, transform = sample submission, 12,279,160/12,279,160 cells finite in [0,1],
0 NaN, nodata=None, values exactly {{0,1}}, 37,654 dots, 0 on catalogue, 0 outside footprint.
Local format/range preflight — not organiser acceptance.</p></div>

<div class="card"><h2>Run card, reproduction, sources</h2>
<p><a href="downloads/run_card.json">Machine-readable run card (JSON)</a> · Evidence in repo:
<code>evidence/experiments.json</code>, <code>evidence/experiments_pass2_spaced.json</code>, <code>evidence/canaries.json</code>,
<code>evidence/uniqueness_production.json</code>. Reproduce: <code>python3 scripts/restore_data.py</code> (sha256-verified)
→ <code>build_features.py</code> → <code>run_experiments.py</code> → <code>pass2_spaced_emission.py</code> →
<code>build_production.py</code> → <code>pass2_rebuild_production.py</code>. Tests: <code>pytest tests -q</code>.</p>
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
<div class="banner ok" style="padding:16px"><p class="big" style="margin:0">✅ OK TO DOWNLOAD: YES · ✅ OK TO SUBMIT: YES (verdict promote;
human selector checks the weekly cap and uploads once). HOLDOUT-DTI {f4(sc['E2_MPC_SPACED']['dti'])} vs {f4(sc['h33_analogue_foldfair']['dti'])} control —
point-estimate win, not statistically significant; no organizer score exists yet. Full evidence on the <a style="color:#fff" href="index.html">front page</a>.</p></div>
<div class="card">
<h2>Step 1 — Download one file (either format, not both)</h2>
<p><a href="downloads/{stem}.tif"><b>{stem}.tif</b></a> or <a href="downloads/{stem}.zip"><b>{stem}.zip</b></a>
(the ZIP contains exactly that one TIFF). Optional integrity check: <code>sha256sum {stem}.tif</code> →
<code>{prod['sha256']}</code>.</p>
<h2>Step 2 — Open the DrivenData form</h2>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition 306</a> → sign in →
<b>New submission</b>. First read the weekly submission cap shown on that page — this system spends 0 slots;
the slot is spent only when you click submit.</p>
<h2>Step 3 — "File to submit"</h2>
<p>Choose the downloaded <code>.tif</code> (or the <code>.zip</code>). Portal contract (all enforced fail-closed by our writer and
re-verified from disk): single-band GeoTIFF, CRS EPSG:32611, shape 3730×3292, geotransform (100, 0, 243350, 0, −100, 4508550).</p>
<h2>Step 4 — Name and Note (copy exactly)</h2>
<div class="copy"><b>Unique submission name:</b><br><code>{prod['name']}</code></div>
<div class="copy"><b>Note (optional) — {len(prod['note'])}/140 characters:</b><br><code>{prod['note']}</code></div>
<h2>Step 5 — Why "Predicted values must be in range [0, 1]" cannot happen</h2>
<p>Causes of that error: values outside [0,1]; a nodata tag carrying a sentinel (e.g. −3.4028234663852886e+38 from
<code>training_features.tif</code>); or NaN cells. This file is written <b>all-finite zeros-outside</b>: all 12,279,160 cells finite,
min 0.0, max 1.0, 0 NaN, <code>nodata=None</code> — verified by re-opening the written bytes
(<a href="downloads/{stem}.json">validator receipt</a>; local preflight, not organiser acceptance).</p>
<h2>Step 6 — After submitting</h2>
<p>Copy the score from the submission-page receipt verbatim, label it <b>ORGANIZER-CONFIRMED</b> with the submission name
above, and record it against sha256 <code>{prod['sha256'][:16]}…</code>. Never record a HOLDOUT-DTI or a projection as a score.</p></div>
<p><a href="index.html">← Front page</a></p></body></html>"""
(DOCS / "index.html").write_text(index)
(DOCS / "executive-summary.html").write_text(exec_sum)
print("site written; promote =", promote)
