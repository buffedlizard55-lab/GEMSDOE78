#!/usr/bin/env python3
"""Render docs/ (GitHub Pages) from the evidence JSON files. No number on the
site is typed by hand: everything is read from evidence/*.json and registry/*.json."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(rel):
    p = ROOT / rel
    return json.loads(p.read_text()) if p.exists() else None


def esc(x):
    return html.escape(str(x))


def f4(x):
    return "—" if x is None else f"{float(x):.4f}"


CSS = """
:root{--bg:#0f172a;--card:#111c33;--ink:#e5e7eb;--mut:#9ca3af;--ok:#16a34a;--bad:#dc2626;--warn:#d97706;--acc:#38bdf8;--line:#1f2a44}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:28px 20px 10px;max-width:1100px;margin:auto}h1{margin:0 0 6px;font-size:28px}h2{font-size:20px;margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
main{max-width:1100px;margin:auto;padding:0 20px 60px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:14px 0}
.banner{font-size:22px;font-weight:700;padding:16px 20px;border-radius:12px;margin:12px 0}.ok{background:#052e16;border:2px solid var(--ok)}.bad{background:#450a0a;border:2px solid var(--bad)}
.btn{display:inline-block;background:var(--acc);color:#04141f;font-weight:700;padding:12px 18px;border-radius:10px;text-decoration:none;margin:6px 8px 6px 0}
.btn.sec{background:#1e293b;color:var(--ink);border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
th{color:var(--mut);font-weight:600}code,.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;word-break:break-all}.mut{color:var(--mut)}
nav a{color:var(--acc);margin-right:14px;text-decoration:none}.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:700}
.tag.h{background:#1e3a8a}.tag.o{background:#14532d}.tag.n{background:#7f1d1d}.small{font-size:13px}ul{margin:6px 0}
"""

NAV = """<nav><a href="index.html">Home</a><a href="executive-summary.html">Executive summary: how to submit</a>
<a href="hypotheses.html">Hypotheses & why H33 scored 0.2778</a><a href="holdout.html">Holdout evidence</a>
<a href="sources.html">Sources</a><a href="irregularities.html">Irregularities</a>
<a href="h78mpc.html">H78-MPC lane (2nd candidate)</a>
<a href="https://github.com/buffedlizard55-lab/GEMSDOE78">Repository</a></nav>"""


def page(title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><header><h1>{esc(title)}</h1>{NAV}</header><main>{body}</main></body></html>"""


def banner(card):
    if card is None:
        return '<div class="banner bad">NO SUBMISSION FILE HAS BEEN BUILT YET — nothing to download.</div>'
    if card["ok_to_submit"]:
        return (f'<div class="banner ok">OK TO SUBMIT: YES — <code>{esc(card["raster"]["file"])}</code> passed the preregistered '
                f'holdout gate, the leakage canary, the uniqueness audit and the format validator. Verdict: {esc(card["verdict"])}.</div>')
    return (f'<div class="banner bad">OK TO SUBMIT: NO — <code>{esc(card["raster"]["file"])}</code> is published for inspection only '
            f'(verdict: {esc(card["verdict"])}). Do not spend a weekly slot on it.</div>')


def index(card, hold, forensic):
    dl = ""
    if card:
        r = card["raster"]
        dl = f"""
<div class="card"><h2 style="margin-top:0">Download</h2>
<a class="btn" href="downloads/{esc(r['file'])}" download>⬇ Download submission GeoTIFF ({r['dots']:,} dots, {r['bytes']/1e6:.2f} MB)</a>
<a class="btn sec" href="downloads/{esc(r['zip'])}" download>⬇ Same file as .zip</a>
<a class="btn sec" href="downloads/{esc(Path(r['file']).with_suffix('.json').name)}">Writer receipt (JSON)</a>
<p class="small mono">sha256 {esc(r['sha256'])}</p>
<table><tr><th>Submission name (paste into the portal)</th><td class="mono">{esc(card['submission_name'])}</td></tr>
<tr><th>Note (≤140 chars, paste into the portal)</th><td class="mono">{esc(card['submission_note'])} <span class="mut">({card['note_chars']} chars)</span></td></tr>
<tr><th>Format</th><td>single band float32, {esc(card['validator']['independent_reread']['shape'])}, {esc(card['validator']['independent_reread']['crs'])}, transform {esc(card['validator']['independent_reread']['transform'])}, all finite, values {esc(card['validator']['independent_reread']['distinct_values'])}, NaN inside footprint = {card['validator']['independent_reread']['nan_inside_footprint']}, positives on catalogue = {card['validator']['independent_reread']['positives_on_catalogue']}</td></tr>
</table></div>"""
    h = ""
    if card:
        ho = card["holdout"]
        rows = "".join(f"<tr><td class='mono'>{esc(k)}</td><td>{f4(v['dti'])}</td><td>{f4(v['ci95'][0])} – {f4(v['ci95'][1])}</td></tr>" for k, v in ho["controls"].items())
        pd = "".join(f"<tr><td class='mono'>{esc(k)}</td><td>{v['delta']:+.4f}</td><td>{v['ci95'][0]:+.4f} – {v['ci95'][1]:+.4f}</td></tr>" for k, v in ho["paired_differences"].items())
        h = f"""
<div class="card"><h2 style="margin-top:0">What the numbers mean <span class="tag h">HOLDOUT-DTI</span> <span class="tag o">ORGANIZER-CONFIRMED</span> <span class="tag n">owner-report</span></h2>
<p><b>Candidate</b> <code>{esc(ho['candidate'])}</code>: <b>{f4(ho['dti'])}</b> HOLDOUT-DTI (evaluator {esc(ho['evaluator_version'])}, {ho['withheld_positive_pixels']:,} withheld positives, 95 % CI {f4(ho['ci95'][0])} – {f4(ho['ci95'][1])}; seed {ho['seed']}, hide {ho['hide_frac']}, buffer {ho['buffer_px']} px).
<b>ORGANIZER-CONFIRMED score for this file: none</b> (it has not been uploaded). A holdout number is never a leaderboard projection.</p>
<table><tr><th>Control / comparator (same folds)</th><th>HOLDOUT-DTI</th><th>95 % CI</th></tr>{rows}</table>
<p class="small mut">Registry comparators D2.8 and H33 were built with knowledge of the full catalogue (and H33 removed every dot within 2 px of it), so their holdout numbers are structurally handicapped and are shown only for completeness.</p>
<table><tr><th>Paired difference, candidate − control</th><th>Δ</th><th>95 % CI (paired 20 km blocks)</th></tr>{pd}</table>
<p>Beats the lineage base model class (A0, 19 raw bands) with CI &gt; 0: <b>{ho['beats_A0_std19_ci']}</b>. Beats the rotation-invariant control (A1), i.e. the steering hypothesis itself: <b>{ho['beats_A1_iso_ci']}</b>.
Leakage canary: max single-feature AUC {f4(card['canary']['max_single_feature_auc'])} (threshold 0.90), flagged: {esc(card['canary']['flagged'] or 'none')}.
Uniqueness: max |ρ| vs registry {f4(card['uniqueness']['surface_max_abs_rho'])} (limit 0.90); max fraction of dots within 3 px of a registry dot set {f4(card['uniqueness']['dots_max_overlap'])} (limit 0.70) → <b>{'pass' if card['uniqueness']['passed'] else 'FAIL'}</b>.</p></div>"""
    risk = ""
    dd = load("evidence/h78_distance_diagnostic.json"); dc = load("evidence/h78_dot_distance_to_catalogue.json")
    if card and dd and dc:
        far = dd["strata"]["far_gt10px"]; cr = dd["candidate_dot_self_credit_by_distance_to_visible"]
        alts = "".join(f"<li><code>{esc(a['raster']['file'])}</code> — {esc(a['verdict'])}; HOLDOUT-DTI {f4(a['holdout']['dti'])} [{f4(a['holdout']['ci95'][0])}, {f4(a['holdout']['ci95'][1])}]; <a href='downloads/{esc(a['raster']['file'])}'>tif</a> · <a href='downloads/{esc(a['raster']['zip'])}'>zip</a> (inspection only, <b>not</b> OK-to-submit)</li>" for a in card.get("alternatives", {}).values())
        risk = f"""<div class="card" style="border-left:6px solid #b45309"><h2 style="margin-top:0">Known risk before you upload (IR-78-09) <span class="tag h">HOLDOUT-DTI</span></h2>
<img src="assets/fig1_h78_surface_and_dots.png" alt="score surface and dots" style="width:100%;border-radius:8px;margin-bottom:10px">
<p>The shipped dots sit closer to the mapped catalogue than the family's best live file: primary median distance <b>{dc['H78 alt (B3)']['p50']:.1f} px</b>, {dc['H78 alt (B3)']['frac_le_5px']*100:.0f} % within 5 px, {dc['H78 alt (B3)']['frac_gt_30px']*100:.0f} % beyond 30 px — versus H33 median {dc['H33']['p50']:.1f} px, {dc['H33']['frac_le_5px']*100:.0f} % within 5 px, {dc['H33']['frac_gt_30px']*100:.0f} % beyond 30 px. The holdout's withheld truth lies median {dd['withheld_truth_distance_to_visible_px']['p50']:.1f} px from a visible fault ({dd['withheld_truth_frac_within_10px_of_visible']*100:.0f} % within 10 px), so it rewards near-catalogue placement more than the live truth may.</p>
<p><b>Mitigating evidence.</b> Restricting the withheld truth to pixels &gt; 10 px from any visible fault ({far['n_truth']:,} positives) the candidate still beats both controls: Δ vs A1 {far['paired_vs_candidate']['A1_iso|B2|44090'][0]:+.4f} [{far['paired_vs_candidate']['A1_iso|B2|44090'][1][0]:+.4f}, {far['paired_vs_candidate']['A1_iso|B2|44090'][1][1]:+.4f}], Δ vs A0 {far['paired_vs_candidate']['A0_std19|B2|44090'][0]:+.4f} [{far['paired_vs_candidate']['A0_std19|B2|44090'][1][0]:+.4f}, {far['paired_vs_candidate']['A0_std19|B2|44090'][1][1]:+.4f}] (B2 variants; paired 20 km blocks), and is on par with D2.8 there. Mean kernel credit per candidate dot by distance to the visible catalogue: 2–3 px {cr['2-3px']['mean_kernel_credit']:.3f} ({cr['2-3px']['n']:,} dots), 3–5 px {cr['3-5px']['mean_kernel_credit']:.3f}, 5–10 px {cr['5-10px']['mean_kernel_credit']:.3f}, 10–20 px {cr['10-20px']['mean_kernel_credit']:.3f}, &gt; 20 px {cr['20-1000000000.0px']['mean_kernel_credit']:.3f}; break-even is 0.2 × DTI ≈ {dd['break_even_credit_0.2xDTI']:.3f}. This is why the 3-px flank file is primary (amendment IR-78-01b, declared after results) — every piece of evidence, including the only live step D2.8 → H33, says the near flank is dead weight.</p>
<p><b>Alternative file(s) built from the same model</b> (labelled, for the selector's inspection):</p><ul>{alts}</ul>
<p class="small mut">Full tables: <code>evidence/h78_distance_diagnostic.json</code>, <code>evidence/h78_dot_distance_to_catalogue.json</code>. Declared post-hoc: see <a href="irregularities.html">irregularities</a> IR-78-01b / IR-78-09 / IR-78-10.</p></div>"""
    fo = ""
    if forensic:
        fo = f"""<div class="card"><h2 style="margin-top:0">Why the family's best file scored 0.2778 <span class="tag n">owner-report</span></h2>
<p>Measured here from the SHA-256-pinned rasters: H19-5 solid = {forensic['h19_5_solid']['positive_px']:,} line px; D2.8 = {forensic['d28']['positive_px']:,} binary dots, all on the H19-5 lines, nearest-neighbour spacing min {forensic['d28_nn_spacing_px']['min']:.2f} px / median {forensic['d28_nn_spacing_px']['median']:.1f} px; H33 = exact subset of D2.8 with {forensic['h33']['positive_px']:,} dots, the {forensic['removed_dots']['n']:,} removed dots all 1.0–2.0 px from the catalogue. Owner-reported chain 0.1922 → 0.2600 → 0.2778 with <i>no detector change</i>: the metric charges 0.2 per emitted pixel and gives max-credit per truth pixel, so redundant and near-catalogue mass was pure cost. The full argument, and what it implies for beating 0.2778, is on the <a href="hypotheses.html">hypotheses page</a>.</p></div>"""
    body = banner(card) + dl + h + risk + fo + """
<div class="card"><h2 style="margin-top:0">Read this first (every session)</h2>
<ul><li>The original project prompt is archived verbatim in <a href="https://github.com/buffedlizard55-lab/GEMSDOE78/blob/main/PROMPT.md">PROMPT.md</a> and summarised in the README; it is the specification.</li>
<li>Reproduce: <code>python scripts/run_holdout.py --seed 20</code> → <code>python scripts/build_submission.py</code> → <code>python scripts/build_site.py</code>. Inputs are restored and SHA-256-verified by <code>scripts/restore_data.sh</code>.</li>
<li>Labels: <span class="tag h">HOLDOUT-DTI</span> measured here on withheld catalogue segments; <span class="tag o">ORGANIZER-CONFIRMED</span> copied from a DrivenData receipt (none exist for this repo); <span class="tag n">owner-report</span> a score the family wrote down, not independently authenticated.</li></ul></div>"""
    return page("GEMSDOE78 — Lane H78: strike-steered lineament learning", body)


def exec_summary(card):
    r = card["raster"] if card else None
    steps = f"""
<ol>
<li>Confirm the banner on the <a href="index.html">home page</a> says <b>OK TO SUBMIT: YES</b>. If it says NO, stop — the file is for inspection only.</li>
<li>Download <code>{esc(r['file']) if r else '(no file yet)'}</code> from the home page (or the .zip; both contain the same single-band GeoTIFF).</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the competition's submissions page</a> (login required) → <b>New submission</b> → <b>File to submit</b> → choose the .tif (or .zip).</li>
<li>In <b>Note</b> paste: <code>{esc(card['submission_note']) if card else ''}</code></li>
<li>Submit. The portal checks CRS (EPSG:32611), shape (3730 × 3292), geotransform and that values are in [0, 1]. This file is all-finite (zeros outside the footprint) with values exactly 0 or 1, so the earlier portal error "Predicted values must be in range [0, 1]" (seen on a NaN-outside file) cannot recur for this reason.</li>
<li>Copy the score the portal returns into <code>registry/live_scores.csv</code> as ORGANIZER-CONFIRMED. Until then the file has no score.</li>
</ol>
<p class="mut small">Weekly cap: the rules allow a limited number of platform submissions per week and one final selection across both prize rounds (official rules PDF, §3.4–3.6). Promotion to a slot is a separate selector decision; this page only certifies that the file is format-valid and passed its preregistered holdout gate.</p>"""
    return page("Executive summary — how to make a submission", f'{banner(card)}<div class="card">{steps}</div>')


def hypotheses_page():
    md = (ROOT / "research/h78_hypotheses.md").read_text()
    # minimal markdown: headings, tables, paragraphs
    out, in_tbl = [], False
    for line in md.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            tag = "th" if not in_tbl else "td"
            if not in_tbl:
                out.append("<table>")
                in_tbl = True
            out.append("<tr>" + "".join(f"<{tag}>{md_inline(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_tbl:
            out.append("</table>")
            in_tbl = False
        if line.startswith("# "):
            out.append(f"<h2>{md_inline(line[2:])}</h2>")
        elif line.startswith("## "):
            out.append(f"<h2>{md_inline(line[3:])}</h2>")
        elif line.strip().startswith(("* ", "- ")):
            out.append(f"<li>{md_inline(line.strip()[2:])}</li>")
        elif line.strip()[:2].rstrip(".").isdigit() and ". " in line[:4]:
            out.append(f"<p>{md_inline(line.strip())}</p>")
        elif line.strip():
            out.append(f"<p>{md_inline(line)}</p>")
    if in_tbl:
        out.append("</table>")
    return page("Hypotheses — and why H33 scored 0.2778", '<div class="card">' + "\n".join(out) + "</div>")


def md_inline(s):
    import re
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    return s.replace("\\|", "|")


def holdout_page(hold):
    if not hold:
        return page("Holdout evidence", "<p>No holdout run yet.</p>")
    rows = []
    for arm, res in hold["results"].items():
        if "variants" not in res:
            continue
        for vname, v in res["variants"].items():
            for n, r in v["budgets"].items():
                rows.append((arm, vname, int(n), r["pooled_dti"], r["dots_on_visible_catalogue"]))
    rows.sort(key=lambda t: -t[3])
    tbl = "".join(f"<tr><td class='mono'>{esc(a)}</td><td class='mono'>{esc(v)}</td><td>{n:,}</td><td><b>{d:.4f}</b></td><td>{c}</td></tr>" for a, v, n, d, c in rows)
    can = hold["canary"]
    top = "".join(f"<tr><td class='mono'>{esc(k)}</td><td>{v:.4f}</td></tr>" for k, v in can["top10"])
    recs = "".join(f"<tr><td>{esc(r['fold'])}</td><td>{r['held_components']}</td><td>{r['withheld_positive_pixels']:,}</td><td>{r['eligible_components']}</td></tr>" for r in hold["fold_receipts"])
    body = f"""<div class="card"><h2 style="margin-top:0">Design</h2><p>Evaluator <code>{esc(hold['evaluator_version'])}</code> (unmodified shared template; sha256 of evaluate_holdout.py <code>{esc(hold['evaluator_sha256']['evaluate_holdout.py'])}</code>).
Seed {hold['seed']}, hide fraction {hold['hide_frac']}, feature collar {hold['buffer_px']} px, visible catalogue {hold['visible_px']:,} px, withheld {hold['hidden_px']:,} px ({hold['withheld_positive_pixels_scored']:,} scored inside the label-blind regions).</p>
<table><tr><th>Fold</th><th>Withheld components</th><th>Withheld px</th><th>Eligible components</th></tr>{recs}</table></div>
<div class="card"><h2 style="margin-top:0">Leakage canary (single-feature AUC on withheld truth vs background; flag &gt; 0.90)</h2>
<p>Max AUC {can['max_auc']:.4f}; flagged: {esc(can['flagged_over_0p90'] or 'none')} ({can['n_pos']:,} positives vs {can['n_neg']:,} background cells).</p><table><tr><th>Feature</th><th>AUC</th></tr>{top}</table></div>
<div class="card"><h2 style="margin-top:0">Emission sweep — pooled HOLDOUT-DTI (all arms, same folds, same emitter)</h2>
<table><tr><th>Arm</th><th>Variant (nms, flank px)</th><th>Dots (global budget)</th><th>Pooled HOLDOUT-DTI</th><th>Dots on visible catalogue</th></tr>{tbl}</table></div>
<div class="card"><h2 style="margin-top:0">Pooled summary with CIs</h2><pre class="small">{esc(json.dumps(hold['pooled_summary'], indent=1))}</pre></div>"""
    return page("Holdout evidence (HOLDOUT-DTI)", body)


def sources_page():
    src = load("registry/sources.json") or []
    rows = "".join(f"<tr><td>{esc(s['what'])}</td><td><a href='{esc(s['url'])}'>{esc(s['url'])}</a></td><td>{esc(s['verified'])}</td></tr>" for s in src)
    man = load("registry/data_manifest.json") or {}
    mrows = "".join(f"<tr><td class='mono'>{esc(f['dest'])}</td><td class='mono'>{esc(f['sha256'])}</td><td>{f['bytes']:,}</td><td>{esc(f['provenance'])}</td></tr>" for f in man.get("files", []))
    return page("Sources and data manifest", f"<div class='card'><table><tr><th>What</th><th>Link</th><th>How it was verified</th></tr>{rows}</table></div><div class='card'><h2 style='margin-top:0'>Input files (SHA-256 pinned, verified on restore)</h2><table><tr><th>File</th><th>sha256</th><th>bytes</th><th>Provenance</th></tr>{mrows}</table></div>")


def irregularities_page():
    ir = load("registry/irregularities.json") or []
    rows = "".join(f"<tr><td class='mono'>{esc(i['id'])}</td><td>{esc(i['severity'])}</td><td>{esc(i['what'])}</td><td>{esc(i['action'])}</td></tr>" for i in ir)
    return page("Irregularities flagged for review", f"<div class='card'><table><tr><th>ID</th><th>Severity</th><th>What</th><th>Action / status</th></tr>{rows}</table></div>")


def main():
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("")
    card = load("evidence/h78_run_card.json")
    hold = load("evidence/h78_holdout_seed20.json")
    forensic = load("evidence/forensics_h33_vs_d28.json")
    # H78-A pages are preserved, but they are not the session homepage. A later
    # negative result must not be covered by this function's green banner.
    h78a = index(card, hold, forensic)
    warn = (
        '<div class="banner" style="background:#451a03;border:2px solid #d97706">'
        'Previous session only. The live homepage decision is '
        '<a href="index.html">OK TO SUBMIT: NO</a> for the new file. '
        'The green banner below is the earlier H78-A gate, not a new clearance.</div>'
    )
    h78a = h78a.replace("<main>", "<main>" + warn, 1)
    (DOCS / "h78a.html").write_text(h78a)
    (DOCS / "h78a-executive-summary.html").write_text(exec_summary(card))
    (DOCS / "hypotheses.html").write_text(hypotheses_page())
    (DOCS / "holdout.html").write_text(holdout_page(hold))
    (DOCS / "sources.html").write_text(sources_page())
    (DOCS / "irregularities.html").write_text(irregularities_page())
    (ROOT / "index.html").write_text('<!doctype html><meta http-equiv="refresh" content="0; url=docs/index.html">')
    # Session homepage (tooth/spy negative) overwrites index + executive summary
    # after the H78-A archive pages are written. Do not remove this call.
    import runpy
    runpy.run_path(str(Path(__file__).with_name("build_session_site.py")), run_name="__main__")
    print("site built")


if __name__ == "__main__":
    main()
