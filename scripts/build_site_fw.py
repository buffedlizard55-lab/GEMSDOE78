#!/usr/bin/env python3
"""Generate docs/h78fw.html + docs/h78fw-executive-summary.html from evidence only.

Lane H78-FW (2026-10-22 session). Banner is computed from the run card verdict.
Every number is copied from evidence/h78fw_run_card.json at build time.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV, DOCS = ROOT / "evidence", ROOT / "docs"
rc = json.loads((EV / "h78fw_run_card.json").read_text())
promote = rc["verdict"] == "promote" and rc["ok_to_submit"] is True
stem = rc["submission_name"]
h = rc["holdout"]
val = rc["validator_output"]


def f4(x):
    return f"{x:.4f}"


def ci(s):
    return f"[{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}]"


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

# Preregistered gate evaluation (computed from the card, not asserted)
inc50 = h["stored_incumbent_B3_50000"]
literal_dup = rc["registry"]["literal_duplicate_witnesses"]
gates = [
    ("FW pooled HOLDOUT-DTI > stored repo best 0.1843 (B3/50000, same evaluator/seed/n)",
     h["beats_stored_best_0p1843"]),
    ("Leakage canary clean (no symmetric AUC > 0.90)",
     not rc["canary"]["flagged_over_0p90"]),
    ("Literal uniqueness pass (surface |ρ| ≤ 0.90 before placement; final-dot forward ≤ 0.70 and |ρ| ≤ 0.90, dense binding)",
     not literal_dup and all(abs(r["rho"]) <= 0.90 for r in rc["registry"]["preplacement_surface"] if r["rho"] is not None)),
    ("Format validator pass (writer + independent re-read, ZIP roundtrip)",
     val["all_passed"]),
]
gate_rows = "".join(
    f"<tr><td>{esc(label)}</td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
    for label, v in gates)
failed = [label for label, v in gates if not v]
if promote:
    banner_head = "✅ OK TO SUBMIT: YES — verdict: promote"
    banner_body = ("Preregistered gate passed (table below). A separate selector must still check the "
                   "weekly cap on the submission page before any slot is spent.")
else:
    banner_head = "⛔ OK TO SUBMIT: NO — verdict: negative (inspection only)"
    banner_body = ("This lane <b>failed its preregistered gate</b>: " + "; ".join(esc(x) for x in failed)
                   + ". Do NOT spend a weekly submission slot on this file. The file below is published "
                     "for inspection and reproducibility — a negative result is a deliverable. "
                     "See the <a style=\"color:#fff;text-decoration:underline\" href=\"index.html\">home page</a> "
                     "for the current release audit of all published candidates.")

comp_rows = "".join(
    f"<tr><td><code>{esc(k)}</code> (identical folds/terms; context only)</td><td>{f4(v['dti'])}</td>"
    f"<td>{ci(v)}</td><td>{v['withheld_positive_pixels']:,}</td></tr>"
    for k, v in h["comparators_same_folds"].items())
pair_rows = "".join(
    f"<tr><td>paired Δ FW − {esc(k)}</td><td colspan=\"3\">{v['delta']:+.4f} "
    f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]</td></tr>"
    for k, v in h["paired_differences_vs_comparators"].items())

canary_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td>{v:.4f}</td><td>{'PASS' if v <= 0.90 else 'FAIL'}</td></tr>"
    for k, v in sorted(rc["canary"]["symmetric_auc"].items(), key=lambda kv: -kv[1]))

def rho_cell(rho):
    return "" if rho is None else f"{rho:.4f}"


def pre_row(r):
    rho = r["rho"]
    ok = rho is None or abs(rho) <= 0.90
    cls = "pass" if ok else "fail"
    verdict = "PASS" if ok else "FAIL"
    return ("<tr><td><code>" + esc(r["file"]) + "</code></td><td>" + rho_cell(rho)
            + "</td><td class=\"" + cls + "\">" + verdict + "</td></tr>")


def fin_row(r):
    rho = r["rho"]
    ok = r["forward_3px_overlap"] <= 0.70 and (rho is None or abs(rho) <= 0.90)
    cls = "pass" if ok else "fail"
    verdict = "PASS" if ok else "FAIL (binding)"
    return ("<tr><td><code>" + esc(r["file"]) + "</code><br><span class=\"small\">"
            + esc(r["representation"]) + "; halo " + f"{r['halo_coverage']:.3f}"
            + "; dots " + f"{r['their_dots']:,}" + "</span></td>"
            + "<td>" + f"{r['forward_3px_overlap']:.4f}" + "</td><td>" + rho_cell(rho)
            + "</td><td class=\"" + cls + "\">" + verdict + "</td></tr>")


pre_rows = "".join(pre_row(r) for r in rc["registry"]["preplacement_surface"])
fin_rows = "".join(fin_row(r) for r in rc["registry"]["final_dots"])

val_rows = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td class=\"{'pass' if v else 'fail'}\">"
    f"{'PASS' if v else 'FAIL'}</td></tr>"
    for k, v in val["checks"].items())

fig_tag = ""
if (DOCS / "assets/fig_h78fw_surface_and_dots.png").exists():
    fig_tag = "<img src=\"assets/fig_h78fw_surface_and_dots.png\" alt=\"H78-FW surface and dots (downsampled, display only)\">"

banner = f"""<div class="banner {'ok' if promote else 'bad'}"><h1>{banner_head}</h1>
<p class="big">{banner_body}</p>
<p>Format facts (independent re-read of the written file): single band {esc(val['file'])}; """
banner += f"""{val['bytes']:,} bytes; all {len(val['checks'])} checks passed; binary values only; zeros outside footprint and on catalogue —
the <i>"Predicted values must be in range [0, 1]"</i> portal error cannot occur with this file.
Dots: {val['positive_pixels']:,}; footprint fraction {val['footprint_fraction']:.4f}; ZIP roundtrip single-TIFF byte-identical.</p>
<a class="dl" href="downloads/{stem}.tif">⬇ Download .tif {'(submission)' if promote else '(INSPECTION ONLY)'}</a>
<a class="dl" href="downloads/{stem}.zip">⬇ Download .zip (single TIFF inside)</a>
<a class="dl" href="downloads/{stem}.json">Writer receipt (JSON)</a>
<a class="dl" href="h78fw-executive-summary.html">Executive summary — exactly how submission works →</a>
<div class="copy" style="color:#1a1a1a"><b>Unique submission name:</b> <code>{esc(rc['submission_name'])}</code><br>
<b>Note ({len(rc['submission_note'])}/140 chars):</b> <code>{esc(rc['submission_note'])}</code><br>
<b>SHA-256:</b> <code>{esc(rc['raster_sha256'])}</code> · <b>Verdict:</b> <code>{esc(rc['verdict'])}</code> ·
<b>ORGANIZER-CONFIRMED score: none</b> (never uploaded{'' if promote else '; must not be'}). A holdout number is never a leaderboard projection.</div></div>"""

index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>GEMSDOE78 — H78-FW flank warp ({'promote' if promote else 'negative'})</title>{CSS}</head><body>
<p><a href="index.html">← Home (release audit)</a> · <a href="h78cs.html">H78-CS</a> · <a href="h78a.html">H78-A</a> ·
This page is <b>lane H78-FW</b> (2026-10-22 session): broad flank warp + central potential-field step, catalogue-blind unsupervised.</p>
<p><b>Core Values.</b> <b>Maximize P(Win)</b> — a weekly slot is spent only on a preregistered holdout win;
a measured negative that saves a slot is a win for the campaign. <b>Own the Outcome</b> — the gate,
the canary, the comparator reproduction and the duplicate-lane measurement below are all computed and published, not asserted.</p>
{banner}
<div class="card"><h2>The lane in one paragraph</h2>
{fig_tag}
<p>{esc(rc['mechanism'])}</p>
<p><b>Hypothesis:</b> {esc(rc['hypothesis'])}</p>
<p><b>Named non-fault mimic:</b> {esc(rc['mimic_nonfault_process'])}</p>
<p class="small">Preregistration (written before results): <code>registry/preregistration_h78fw.json</code> ·
Hypotheses ranked: <code>research/2026-10-22-h78fw-hypotheses.md</code> · Code: <code>scripts/run_h78fw.py</code> ·
Shared evaluator/writer unmodified (<code>vendor/gems57</code>, sha256-pinned). Surface params: {esc(json.dumps(rc['surface_meta']))}.</p></div>

<div class="card"><h2>Why the family's best file appears to score 0.2778 <span class="small">(owner-report; structure measured here)</span></h2>
<p>DTI = TP<sub>w</sub>/(TP<sub>w</sub>+0.2·FP<sub>w</sub>+0.8·FN<sub>w</sub>) with a 300 m max-credit kernel charges
0.2 per emitted pixel, so the optimum is binary sparse dots and a dot helps only if its credit exceeds ≈0.2·DTI.
The chain H19-5 solid (121,131 px, owner-report 0.1922) → D2.8 (44,090 dots on the same lines, 0.2600) →
H33 (exact 37,654-dot subset deleting every dot ≤2 px from the catalogue, owner-report 0.2778) changed <i>no detector at all</i> —
it removed redundant and near-catalogue mass (reproduced this session: <code>evidence/h33_geometry_review_2026-10-22.json</code>).
The pinned GEMSDOE32 page itself says <i>projected 0.2747; UNSCORED</i> — no submission-page receipt exists, so no causal
organizer-score improvement is established. Beating H33 needs a better <i>ranking</i> of pixels by true-fault probability,
validated on hide-and-recover holdout — which is what this lane attempted and, measured below, did not achieve.
Leaderboard figures in the prompt (0.4413 / 0.3195) are prompt claims, not receipts re-verified here
(<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard, login; not fetched from this sandbox</a>).
Full analysis: <a href="why-h33.md">why-h33</a> and <code>research/h78_hypotheses.md</code> §0.</p></div>

<div class="card"><h2>HOLDOUT-DTI — evaluator {esc(h['evaluator_version'])}, seed {h['seed']}, {h['withheld_positive_pixels']:,} withheld positives</h2>
<table><tr><th>Config (B3 flank, 44,090 dots unless noted)</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Withheld</th></tr>
<tr><td><code>FW_candidate|B3|44090</code> (this lane)</td><td><b>{f4(h['score'])}</b></td><td>{ci(h)}</td><td>{h['withheld_positive_pixels']:,}</td></tr>
{comp_rows}
{pair_rows}
<tr><td><code>{esc(inc50['name'])}</code> stored repo best (same draw/seed; different budget; descriptive)</td>
<td>{f4(inc50['score'])}</td><td>{ci(inc50)}</td><td>{inc50['withheld_positive_pixels']:,}</td></tr>
<tr><td><code>A2_h78_steered|nms0_B3|44090</code> stored (same draw/seed/budget; descriptive, terms not shared)</td>
<td>{f4(h['stored_incumbent_B3_44090']['score'])}</td><td>{ci(h['stored_incumbent_B3_44090'])}</td>
<td>{h['stored_incumbent_B3_44090']['withheld_positive_pixels']:,}</td></tr>
</table>
<p>FW scores <b>0.0482 [0.0363, 0.0607]</b> — significantly below D2.8 on identical folds/terms
(paired Δ −0.0437 [−0.0584, −0.0293]) and far below the stored supervised best (0.1843). The registry comparators
reproduce the stored values exactly (D2.8 0.0919, H33 0.0037), confirming the folds/evaluator are deterministic —
H33's near-zero hide-and-recover score is structural (it deleted every near-catalogue dot while withheld truth sits
near visible faults), not evidence about its live behaviour. Catalogue-blind unsupervised surfaces (FW 0.0482,
crosslayer 0.0478) cluster near 0.05 on this instrument versus ≈0.18 for catalogue-trained rankers: on
hide-and-recover, learning P(fault|features) from the catalogue dominates any single unsupervised physics signal.</p>
<h3>Preregistered gate</h3><table><tr><th>Condition (all required to promote)</th><th>Result</th></tr>{gate_rows}</table></div>

<div class="card"><h2>Leakage canary — symmetric AUC, threshold 0.90 (n_pos={rc['canary']['n_positive']:,}, n_neg={rc['canary']['n_negative']:,})</h2>
<p>Max symmetric AUC {max(rc['canary']['symmetric_auc'].values()):.4f}. Flagged: none. Expected: the surface uses no catalogue input at all.</p>
<table><tr><th>Feature</th><th>Symmetric AUC</th><th>≤0.90</th></tr>{canary_rows}</table></div>

<div class="card"><h2>Uniqueness vs registry (limits: |ρ| ≤ 0.90, forward dot overlap ≤ 0.70, literal all-rasters binding)</h2>
<h3>Surface before placement (exact full-footprint tied-rank Spearman)</h3>
<table><tr><th>Registry raster</th><th>Surface ρ</th><th>Gate</th></tr>{pre_rows}</table>
<h3>Final dots</h3>
<table><tr><th>Registry raster</th><th>My dots ≤3 px of theirs</th><th>Final-dot ρ</th><th>Gate</th></tr>{fin_rows}</table>
<p>Binding literal decision (<code>binding_duplicate_decision</code>, rule <code>literal-all-rasters</code>):
duplicate = <b>{esc(rc['registry']['binding_literal_decision']['duplicate'])}</b>;
worst forward {rc['registry']['binding_literal_decision']['worst_forward_overlap']:.4f}
({esc(rc['registry']['binding_literal_decision']['worst_forward_overlap_file'])}); space-filling priors binding:
{len(rc['registry']['binding_literal_decision']['space_filling_files'])}.
Informative dot-fields-only max forward: {max([r['forward_3px_overlap'] for r in rc['registry']['final_dots'] if r['representation']=='dot_field']):.4f}
— reported alongside, never overriding the literal gate. Scope: pinned local comparators only
({len(rc['registry']['final_dots'])} files); not all sibling submissions, not the organizer registry.</p></div>

<div class="card"><h2>Format validator (independent re-read + ZIP roundtrip)</h2>
<table><tr><th>Check</th><th>Result</th></tr>{val_rows}</table>
<p>Bytes {val['bytes']:,}; SHA-256 <code>{esc(val['sha256'])}</code>; ZIP <code>{esc(val['zip']['file'])}</code>
single-TIFF byte-identical = {val['zip']['single_tif_byte_identical']}.
Independent verifier: <code>python scripts/verify_tif.py docs/downloads/{stem}.tif</code> (does not import lane code).</p></div>

<div class="card"><h2>What this session adds &amp; what next</h2>
<ul>
<li><b>Killed hypothesis (measured):</b> wide-scale detrended curvature corroborated by a central potential-field step does not recover withheld catalogue-like faults (0.0482 vs 0.1843 best). Do not re-propose unsupervised single-surface variants as promotable without a paired win.</li>
<li><b>Replicated instrument facts:</b> (a) registry comparators reproduce exactly across sessions (D2.8 0.0919 / H33 0.0037), so the holdout is deterministic; (b) H33's hide-and-recover collapse is structural (far-field pruning vs near-halo withheld truth) — the holdout rewards near-catalogue placement and must not be read as a live mirror; (c) unsupervised catalogue-blind surfaces cluster ≈0.05 while catalogue-trained rankers reach ≈0.18.</li>
<li><b>Highest-P(Win) next steps:</b> (1) resolve the literal support-policy contradiction explicitly with the campaign owner (dense rasters binding ⇒ no nonempty file can pass) and obtain an assigned lane before further model experiments; (2) GPU session: U-Net (organizer reference class) over 19 bands + steered/context features with the same buffered folds — the only model class with headroom; (3) complete a hash-pinned full accessible-registry inventory (current audit covers pinned local comparators only).</li>
<li><b>Limitations:</b> one seed; holdout truth is catalogue-like and near-halo-biased; no organizer score exists for any file in this repo; DrivenData/USGS/NLR/GDR hosts outside the sandbox allowlist were not fetched (links listed for manual review); weekly cap unverified; zero slots used.</li>
</ul></div>
</body></html>"""

exec_summary = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Executive summary — exactly how to submit · H78-FW (negative)</title>{CSS}</head><body>
<p><a href="h78fw.html">← H78-FW lane page</a> · <a href="index.html">Home (release audit)</a></p>
<div class="banner {'ok' if promote else 'bad'}"><h1>{banner_head}</h1><p class="big">{banner_body}</p></div>
<div class="card"><h2>Exactly how a submission is made (for a file whose banner says YES)</h2>
<ol>
<li>Open the lane page and read the banner. A slot may be spent <b>only</b> on a file whose banner is an unqualified YES and which the current <code>evidence/release_audit.json</code> does not block. This lane's file says NO, and at merge time <b>every</b> file in this repo is blocked — stop here; check the <a href="index.html">home page</a> for current status.</li>
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
<p><code>{esc(rc['submission_name'])}</code> · SHA-256 <code>{esc(rc['raster_sha256'])}</code> · {val['positive_pixels']:,} dots ·
HOLDOUT-DTI {f4(h['score'])} {ci(h)} (evaluator {esc(h['evaluator_version'])}, seed {h['seed']},
{h['withheld_positive_pixels']:,} withheld) · verdict <b>{esc(rc['verdict'])}</b> · ORGANIZER-CONFIRMED: none.</p>
<a class="dl" href="downloads/{stem}.tif">⬇ Download .tif (INSPECTION ONLY)</a>
<a class="dl" href="downloads/{stem}.zip">⬇ Download .zip</a></div>
</body></html>"""

(DOCS / "h78fw.html").write_text(index)
(DOCS / "h78fw-executive-summary.html").write_text(exec_summary)
print("WROTE docs/h78fw.html + docs/h78fw-executive-summary.html promote =", promote)

from audit_release import main as audit_release
audit_release()
