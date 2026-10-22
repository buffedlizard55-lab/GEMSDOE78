#!/usr/bin/env python3
"""Revalidate newest inspection file and publish a fail-closed, hash-bound landing page.

Static status is NOT a live leaderboard feed; rebuild after each experiment.
"""
from __future__ import annotations
import hashlib
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def publish():
    card = json.loads((ROOT/'evidence/crosslayer_run_card.json').read_text())
    tif = ROOT/'docs/downloads'/(card['submission_name']+'.tif')
    if tif.name != card['validator_output']['file'] or not tif.exists():
        raise ValueError('run card and TIFF identity differ')
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    if digest != card['raster_sha256']:
        raise ValueError('run card SHA256 does not match downloadable file')
    verification = json.loads(subprocess.check_output([sys.executable,
        str(ROOT/'scripts/verify_tif.py'), str(tif)]))
    if not verification['all_passed'] or verification['sha256'] != digest:
        raise ValueError('independent revalidation failed; refuse publication')
    if len(card['submission_note']) > 140 or card['ok_to_submit'] or card['verdict'] != 'negative':
        raise ValueError('publication gate conflict; refuse publication')
    rows = card['registry']['final_dots']
    witnesses = [r for r in rows if r['forward_3px_overlap'] > .70 or
                 (r['rho'] is not None and abs(r['rho']) > .90)]
    if len(witnesses) != len(card['registry']['duplicate_witnesses']):
        raise ValueError('stale registry gate')
    if not witnesses or card['holdout']['score'] >= card['holdout']['control_incumbent']['score']:
        raise ValueError('negative run card no longer matches measured gates')
    consolidated = json.loads((ROOT/'evidence/release_audit.json').read_text()) if (ROOT/'evidence/release_audit.json').exists() else None
    if consolidated is not None:
        inventory = {c['file']:c for c in consolidated['candidates']}
        if tif.name not in inventory or inventory[tif.name]['sha256'] != digest or not all(c['validator']['all_passed'] for c in inventory.values()):
            raise ValueError('consolidated audit missing or invalid for newest TIFF')
    status = dict(schema_version=2, generated_utc=card['generated_utc'],
        review_date='2026-10-22', new_tif_generated=True,
        candidates=consolidated['candidates'] if consolidated else [],
        authoritative_card='crosslayer_run_card.json',
        generated_tif=tif.name, sha256=digest, verdict='negative',
        ok_to_download_for_inspection=True, ok_to_submit=False,
        reason='Holdout below incumbent and literal registry overlap above 70%; stop.',
        holdout_evidence_class='HOLDOUT-DTI', holdout_dti=card['holdout']['score'],
        holdout_ci95=card['holdout']['ci95'], evaluator=card['holdout']['evaluator_version'],
        withheld_positive_pixels=card['holdout']['withheld_positive_pixels'],
        worst_forward_3px_overlap=max(r['forward_3px_overlap'] for r in rows),
        duplicate_witnesses=[r['file'] for r in witnesses],
        validator_independent_all_passed=True, organizer_confirmed=None,
        weekly_slots_used_by_agent=0, live_feed=False,
        source='evidence/crosslayer_run_card.json; static snapshot, not an organizer receipt')
    (ROOT/'docs/data/status.json').write_text(json.dumps(status,indent=2,allow_nan=False)+'\n')
    (ROOT/'docs/data/crosslayer_run_card.json').write_text(json.dumps(card,indent=2,allow_nan=False)+'\n')
    e = html.escape
    h = card['holdout']
    ov = max(rows,key=lambda r:r['forward_3px_overlap'])
    body=f'''<h1>GEMSDOE78 · Submission readiness</h1>
<div class="alert"><strong>OK TO DOWNLOAD: YES · OK TO SUBMIT: NO</strong><br>
New cross-layer TIFF is format-valid, but failed holdout and the literal duplicate-stop rule. Do not upload it to DrivenData. Zero slots spent.</div>
<section><h2>Latest file · inspection only</h2>
<p><a class="button" download href="downloads/{e(tif.name)}">Download the NEW TIFF — DO NOT SUBMIT</a>
<a download href="downloads/{e(tif.stem)}.zip">Download single-TIFF ZIP — DO NOT SUBMIT</a></p>
<table><tr><th>Unique candidate name</th><td><code>{e(card['submission_name'])}</code></td></tr>
<tr><th>Note (do NOT paste into a slot)</th><td><code>{e(card['submission_note'])}</code></td></tr>
<tr><th>SHA-256</th><td><code>{digest}</code></td></tr>
<tr><th>Format</th><td>Verified single-band float32, EPSG:32611, 3730 × 3292, pinned 100 m transform. All cells finite and within [0,1], zero outside footprint and on mapped faults; ZIP round-trip passed.</td></tr>
<tr><th>HOLDOUT-DTI</th><td>{h['score']:.4f} [95% CI {h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}]; evaluator {e(h['evaluator_version'])}, {h['withheld_positive_pixels']:,} withheld positives, seed {h['seed']}. Incumbent HOLDOUT-DTI {h['control_incumbent']['score']:.4f} (same seed, different budget; descriptive comparison).</td></tr>
<tr><th>Registry failure</th><td>{ov['forward_3px_overlap']:.2%} of new dots within 3 px of <code>{e(ov['file'])}</code>, above literal 70% stop threshold. Surface maximum |ρ| {max(abs(r['rho']) for r in card['registry']['preplacement_surface'] if r['rho'] is not None):.4f} (below 0.90). Only {len(rows)} locally pinned comparisons; inventory incomplete.</td></tr>
<tr><th>ORGANIZER-CONFIRMED</th><td>None. No receipt, no inferred leaderboard score.</td></tr></table>
<p><a href="data/crosslayer_run_card.json">New run card + validator</a> · <a href="data/status.json">Machine-readable current status</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE78/blob/main/research/2026-10-22-hypotheses.md">Preregistered scientific hypotheses (repository)</a></p>
</section>
<section><h2>Executive summary: how to submit a FUTURE cleared file</h2>
<ol><li>Look at this page's status first. <strong>NO means stop</strong>; don't upload inspection files. A valid TIFF is not an approved prediction.</li>
<li>The automation must test whole buffered fault segments, each feature's leakage AUC, pooled DTI against the incumbent, and the complete accessible registry both before and after dot emission. Duplicate threshold: rho &gt; 0.90 or forward dot overlap &gt; 70% against ANY registry raster.</li>
<li>On a separately approved candidate, download its linked .tif (or single-TIFF ZIP), and verify its SHA-256 against the automatic card. Use the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">organizer template</a> to confirm grid. This project's validator checks CRS, shape, transform, finite values in [0,1], exact footprint, one band and ZIP identity; it never silently clips out-of-range data.</li>
<li>Only after a separate selector checks the official weekly cap, visit <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition 306</a> → New submission → File to submit → choose the approved TIFF → paste its short note → submit. Keep the submission-page receipt with the exact SHA. This agent has not done that.</li></ol>
</section>
<section><h2>Why H33 drew attention</h2><p>The supplied 0.2778 is an <strong>unverified owner report</strong>, not an ORGANIZER-CONFIRMED score; 0.3195 and 0.4413 conflict as stated current high scores. Local forensic evidence indicates H33 kept 37,654 of D2.8's 44,090 dots and removed 6,436 near the catalogue without changing the detector. Under distance-tolerant Tversky scoring, removing redundant false-positive mass can improve a ratio; this is a plausible mechanism, not proof of a future score. The target is unmapped faults, not directly observed geothermal vents. <a href="review-release.md">Detailed review and caveats</a>.</p></section>
<section><h2>Official sources and limitations</h2><p><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizing team's reference code</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR PDF</a>. Only GitHub is reachable in this sandbox; non-GitHub links are for later manual review, not falsely reported as fetched. The numerical stack is an owner mirror with SHA-256 identity but not authenticated against the login-walled organizer download. There is no live leaderboard/weekly-cap feed. Previous H78-A clearance is INCOMPLETE (only three lineage comparators): <a href="h78a.html">archived A lane</a> · <a href="h78cs.html">Previous CS lane</a> · <a href="data/release_audit.json">Historical release audit</a>.</p></section>'''
    css='''body{font:17px/1.6 system-ui,Arial;margin:0 auto;padding:1.5rem;max-width:1050px;background:#0b1526;color:#eaf2fc}h1{font-size:2rem}section{padding:1.3rem;margin:1.3rem 0;border:1px solid #334b6a;border-radius:12px;background:#15253b}.alert{padding:1.3rem;border:3px solid #f87171;background:#4c171e;border-radius:12px;font-size:1.2rem}a{color:#76caff}a.button{display:inline-block;background:#f87171;color:#1a1620;padding:.8rem;border-radius:8px;font-weight:bold}table{border-collapse:collapse}td,th{text-align:left;vertical-align:top;padding:.6rem;border-bottom:1px solid #39516e}code{overflow-wrap:anywhere}li{margin:.7rem 0}'''
    for title, name in (('Historical cross-layer inspection','crosslayer.html'),('Historical cross-layer guide','crosslayer-executive-summary.html')):
        (ROOT/'docs'/name).write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{css}</style></head><body><nav><a href="index.html">Home</a> · <a href="executive-summary.html">Submission guide</a></nav>{body}</body></html>')
    # Keep this lane page, but never replace the newer common protocol review.
    from audit_release import main as audit_release
    audit_release()
    return status

if __name__ == '__main__':
    publish()
