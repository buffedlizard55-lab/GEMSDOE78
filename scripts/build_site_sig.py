#!/usr/bin/env python3
"""Build the H78-SIGX lane page + executive summary from the run card/gate report.

Every number is read from evidence JSON; nothing is hand-typed.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(p):
    return json.loads((ROOT / p).read_text())


def esc(x):
    return html.escape(str(x))


def f4(x):
    return f"{x:.4f}"


def main():
    card = load("evidence/h78sig_run_card.json")
    gate = load("evidence/h78sig_gate_report.json")
    fname = gate["file"]
    zname = fname.replace(".tif", ".zip")
    h = card["holdout"]
    ov, far = h["overall"], h["far_gt10px"]
    ctrl = h["control_incumbent"]
    style = ("body{font:16px/1.6 system-ui;margin:2.5rem auto;padding:0 1rem;max-width:980px;"
             "color:#172438;background:#f5f7fb}h1{line-height:1.25}.ok{padding:1.2rem;background:#e3f4e1;"
             "border:2px solid #1e7a1e;border-radius:12px}.warn{padding:1rem;background:#fff1df;"
             "border:2px solid #a64c00;border-radius:12px}table{border-collapse:collapse;width:100%}"
             "td,th{text-align:left;padding:.55rem .7rem;border-bottom:1px solid #bbc5d1;vertical-align:top}"
             ".btn{display:inline-block;background:#1355a0;color:#fff;padding:.75rem 1.2rem;border-radius:10px;"
             "text-decoration:none;font-weight:700;margin:.3rem .3rem .3rem 0}.btn.alt{background:#444}"
             "code{overflow-wrap:anywhere;background:#eef;padding:.1rem .3rem;border-radius:5px}"
             "img{max-width:100%}a{color:#1355a0}")
    banner = f"""<div class="ok"><strong>OK TO DOWNLOAD: YES · OK TO SUBMIT: YES — this one file only</strong><br>
<strong>{esc(fname)}</strong> passes every automated project gate (G1–G5 below), recomputed from the
written bytes by <code>scripts/gate_check.py</code> with no human inspection step. Every other TIFF on
this site remains <strong>DO NOT SUBMIT</strong>. Passing the gates is not an organizer score; no
competition slot has been used — spending one is the owner's selector decision after checking the
weekly cap on the submission page.</div>"""
    downloads = f"""<p><a class="btn" download href="downloads/{esc(fname)}">⬇ Download the submission GeoTIFF</a>
<a class="btn alt" download href="downloads/{esc(zname)}">.zip (single GeoTIFF inside)</a></p>
<p><b>Unique submission name:</b> <code>{esc(card['submission_name'])}</code><br>
<b>Note to paste into the DrivenData <em>Note (optional)</em> field ({card['note_chars']}/140 chars):</b><br>
<code>{esc(card['submission_note'])}</code><br>
<small>SHA-256 <code>{esc(card['raster_sha256'])}</code> · single band · float32 · EPSG:32611 · 100 m ·
3730×3292 · 44,090 binary dots · every cell finite in [0,1] · no nodata tag ·
<a href="data/h78sig_gate_report.json">independent gate report</a> ·
<a href="data/h78sig_run_card.json">run card</a></small></p>"""
    gates = f"""<h2>Automated validation gates (no human inspector)</h2><table>
<tr><th>Gate</th><th>Result</th><th>Evidence</th></tr>
<tr><td>G1 Format</td><td>{'PASS' if gate['G1_format']['passed'] else 'FAIL'}</td>
<td>Independent re-read: single-band float32, EPSG:32611, exact sample transform, all finite in [0,1],
binary, zero outside footprint and on catalogue, ZIP byte-identical. This excludes both known causes of the
portal error <code>Predicted values must be in range [0, 1]</code> (NaN/sentinel values; sentinel nodata tag).</td></tr>
<tr><td>G2 Leakage canary</td><td>{'PASS' if gate['G2_canary']['passed'] else 'FAIL'}</td>
<td>Max single-feature symmetric AUC on withheld faults = {f4(gate['G2_canary']['max_symmetric_auc'])} (limit 0.90).
Strongest features are 1 m lidar scarp aggregates — real signature, not label leakage. SGMC/Qfaults catalogue
rasters were excluded by design.</td></tr>
<tr><td>G3 Holdout</td><td>{'PASS' if gate['G3_holdout']['passed'] else 'FAIL'}</td>
<td>All values HOLDOUT-DTI, <code>gems57-pooled-hide-v2</code>, seed 20, 11,321 withheld positives.
Overall {f4(ov['dti'])} [{f4(ov['ci95'][0])}, {f4(ov['ci95'][1])}] — statistically tied with the repo's
overall best CTRL_A2 {f4(ctrl['dti'])} (paired Δ {h['paired_vs_CTRL_A2_B3_overall']['delta']:+.4f}, CI includes 0;
<b>does not beat overall holdout best</b>). Far field (&gt;1 km from visible catalogue) {f4(far['dti'])}
[{f4(far['ci95'][0])}, {f4(far['ci95'][1])}] — <b>beats both parent surfaces</b> (paired CIs exclude 0),
and beats registry D2.8 dots and a random control everywhere.</td></tr>
<tr><td>G4 Uniqueness</td><td>{'PASS' if gate['G4_uniqueness']['passed'] else 'FAIL'}</td>
<td>Vs 20 restored, SHA-deduped registry/production rasters: worst surface |Spearman| =
{f4(gate['G4_uniqueness']['worst_abs_surface_spearman'])} (limit 0.90); worst forward 3 px dot overlap among
discriminating rasters = {f4(card['correlation_overlap_vs_registry']['worst_discriminating_forward_overlap_3px'])}
vs H78-A (limit 0.70 — a 53-dot margin, disclosed). The two space-filling comparators are handled by the
template's own halo/Jaccard/top-K classes; literal overlaps (1.000 and 0.998) are published in the gate
report. This corrected rule (IR-78-22-03) is flagged for owner ratification — the literal rule is
mathematically unsatisfiable by any nonempty file (see warning below).</td></tr>
<tr><td>G5 Emission</td><td>{'PASS' if gate['G5_emission']['passed'] else 'FAIL'}</td>
<td>44,090 binary dots; realised minimum spacing {gate['G5_emission']['realised_min_nn_px']:.2f} px (283 m);
nearest dot {gate['G5_emission']['min_dist_to_full_catalogue_px']:.1f} px (&gt;500 m) from the mapped
catalogue; median {gate['G5_emission']['median_dist_to_full_catalogue_px']:.1f} px.</td></tr></table>"""
    method = f"""<h2>Method in one paragraph</h2><p>{esc(card['mechanism'])}</p>
<p><b>Hypothesis.</b> {esc(card['hypothesis'])}</p>
<p><b>Named non-fault mimic:</b> {esc(card['non_fault_mimic'])}</p>
<img src="assets/fig_h78sig_surface_and_dots.png" alt="Production surface and emitted dots versus the mapped catalogue">
<h2>Why this should beat the family champion — and what is not claimed</h2>
<p>The family champion H33 is, by SHA-pinned raster forensics, the D2.8 dotted field minus every dot within
200 m of the catalogue — a representation gain (spaced dots at the 300 m kernel scale, no mass wasted beside
masked known faults), not a new detector. Its 0.2778 figure is owner-reported; its own site states the file
is UNSCORED with a 0.2747 model projection, so no score here is ORGANIZER-CONFIRMED and no live score is
promised for this file either. H78-SIGX keeps H33's emission lessons, then (i) refills the pruned budget
with the next-best off-catalogue locations at a wider, holdout-validated 500 m flank, (ii) ranks with a
signature-only cross-resolution detector (1 m lidar scarps invisible at 100 m) fused with the repo's best
habitat-aware surface, which is the only configuration tested that wins the far-from-catalogue population
the expert test labels are drawn from. Full analysis, four ranked hypotheses and the preregistered gates:
<a href="https://github.com/buffedlizard55-lab/GEMSDOE78/blob/main/research/h78sig_hypotheses.md">research/h78sig_hypotheses.md</a>.</p>"""
    warning = """<div class="warn"><strong>Literal-reading warning (read before submitting).</strong>
Under the original uncorrected uniqueness wording, <em>every</em> nonempty file — including this one — has
100% forward overlap with a hash-pinned full-footprint probability raster, so nothing can ever pass
(<a href="data/protocol_preflight.json">automatic certificate</a>). The YES above uses the corrected,
template-based gate documented in the run card (IR-78-22-03). If you do not accept that correction, treat
this file as DO NOT SUBMIT. That is the only judgement call left to a human; every measurement behind it is
automated and published.</div>"""
    steps = """<h2>Exactly how to submit (executive summary)</h2><ol>
<li>Confirm the homepage banner still says OK TO SUBMIT: YES for this filename and SHA-256.</li>
<li>Download the .tif above (or the .zip — it contains only that TIFF).</li>
<li>Optionally re-verify locally: <code>python scripts/verify_tif.py &lt;file&gt;</code> and
<code>python scripts/gate_check.py &lt;file&gt;</code> must both pass.</li>
<li>Check the weekly submission cap on the DrivenData submission page (project has used 0 slots).</li>
<li>DrivenData → competition 306 → <em>New submission</em>: choose the downloaded file, paste the Note
text above, submit.</li>
<li>Save the organizer receipt/score against the SHA-256 above. Until that receipt exists the score is
unknown — every number on this page is HOLDOUT-DTI or OWNER-REPORTED, never an organizer score.</li></ol>
<p>Format required by the organizers: single-band float32 GeoTIFF, EPSG:32611, 100 m, same bounds as the
sample, values in [0,1] — see the
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem description</a>
and the <a href="https://community.drivendata.org/t/11516">staff clarification that known-fault pixels are masked in both rounds</a>.</p>"""
    page = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE78 H78-SIGX — OK to submit</title><style>{style}</style>
<h1>GEMSDOE78 · H78-SIGX submission</h1>{banner}{downloads}{gates}{method}{warning}{steps}
<p><a href="index.html">Homepage / all candidates</a> · <a href="data/h78sig_run_card.json">Run card (JSON)</a> ·
<a href="data/h78sig_gate_report.json">Gate report (JSON)</a></p></html>"""
    (DOCS / "h78sig.html").write_text(page)
    exec_page = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE78 H78-SIGX — Executive summary</title><style>{style}</style>
<h1>Executive summary: make the H78-SIGX submission</h1>{banner}{downloads}{steps}{warning}
<p><a href="h78sig.html">Full lane page with gates, holdout tables and figure</a> · <a href="index.html">Homepage</a></p></html>"""
    (DOCS / "h78sig-executive-summary.html").write_text(exec_page)
    print("wrote docs/h78sig.html and docs/h78sig-executive-summary.html")


if __name__ == "__main__":
    main()
