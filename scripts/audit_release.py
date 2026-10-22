#!/usr/bin/env python3
"""Fail-closed publication audit. Historical measurements are not new experiments.
Run after either historical site builder; no network or competition upload.
"""
import hashlib
from datetime import datetime, timezone
import html
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'vendor'))
from preflight import run as run_preflight
from gems57.uniqueness import compare_to_registry
import numpy as np
import rasterio

def load(path):
    return json.loads((ROOT / path).read_text())

def literal_failures(rows):
    return [r for r in rows if r['forward_overlap_mine_in_theirs3px'] > 0.70
            or r.get('spearman_full_footprint', 0) > 0.90]

def validate(path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify_tif.py'), str(path)],
                            capture_output=True, text=True)
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {'all_passed': False, 'error': result.stderr[-2000:]}
    report['all_passed'] = result.returncode == 0 and report['all_passed']
    return report

def main():
    a = load('evidence/h78_run_card.json')
    m = load('evidence/h78mpc_run_card.json')
    u = load('evidence/h78mpc_uniqueness.json')
    prod = load('evidence/h78mpc_production.json')
    a_review = load('evidence/h78a_current_review.json')
    failed = literal_failures(u['dot_rows'])
    fresh = load('evidence/rechecked_overlap.json')
    cs = load('evidence/h78cs_run_card.json')
    spy = load('evidence/h78spy_run_card.json')
    preflight = run_preflight(restore=not (ROOT / 'data/registry/17GEMSDOE_E-proba-multiscale.tif').exists())
    witness = next(e for e in preflight['verified_inputs'] if e['id'] == 'saturation_witness') if preflight['correlation_overlap_vs_registry'] else None
    footprint = None
    if witness:
        with rasterio.open(ROOT / 'data/bridge/sample_submission.tif') as src:
            footprint = np.isfinite(src.read(1))
    candidates = []
    specs = [
        ('H78-A', a['raster']['file'], f"INCOMPLETE: {a_review['reason']}"),
        ('H78-MPC', prod['final_stem'] + '.tif', 'DUPLICATE: recorded forward overlap exceeds the literal threshold. Stop required.'),
        ('H78-CS', cs['raster']['file'], 'DUPLICATE + NEGATIVE: failed matched HOLDOUT-DTI comparison; replication did not establish a gain. Forward 3px overlap vs H78-A 0.8908 exceeds 0.70. Full labelled results: evidence/h78cs_run_card.json.'),
        ('H78-SPY', spy['file'], 'DUPLICATE + NEGATIVE: failed matched holdout control; forward overlap vs H78-A 0.9245 exceeds 0.70.'),
        ('H78-A-altB2', 'gems78-h78a-strike-steered-44090dots-20261021T223133Z-ec00c053-altB2-zeros.tif', 'Historical same-model flank alternative, not a new lane. No current slot authorization.')]
    cross_path = ROOT / 'evidence/crosslayer_run_card.json'
    if cross_path.exists():
        cross = load('evidence/crosslayer_run_card.json')
        specs.append(('H78-CROSSLAYER', cross['submission_name'] + '.tif', 'DUPLICATE + NEGATIVE: separate parallel session generated this file; it failed its holdout control and registry gates. Not generated in this review.'))
    step_path = ROOT / 'evidence/h78step_run_card.json'
    if step_path.exists():
        step = load('evidence/h78step_run_card.json')
        specs.append(('H78-STEP', step['raster']['file'], 'DUPLICATE + NEGATIVE: parallel session 2026-10-22 (lane H78-STEP) generated this file; HOLDOUT-DTI 0.1730 vs matched control 0.1826 (paired delta -0.0096), score-surface rho vs control 0.9013, forward 3px overlap vs H78-A 0.8167. Full labelled results: evidence/h78step_run_card.json. Not generated in this review.'))
    fw_path = ROOT / 'evidence/h78fw_run_card.json'
    if fw_path.exists():
        fw = load('evidence/h78fw_run_card.json')
        specs.append(('H78-FW', fw['submission_name'] + '.tif', 'DUPLICATE + NEGATIVE: catalogue-blind flank-warp lane failed its holdout control (HOLDOUT-DTI 0.0482 vs repo best 0.1843, same evaluator/seed/n) and the literal forward-overlap gate (1.0 vs the dense saturation witness; informative dot-field max 0.4083). Full labelled results: evidence/h78fw_run_card.json.'))
    flank_path = ROOT / 'evidence/h78stepflank_run_card.json'
    if flank_path.exists():
        flank = load('evidence/h78stepflank_run_card.json')
        specs.append(('H78-STEP-FLANK', flank['raster']['file'], 'DUPLICATE + NEGATIVE: second parallel session 2026-10-22 independently implemented the same step hypothesis (renamed STEP-FLANK at merge); HOLDOUT-DTI 0.1662 vs control 0.1826 (paired -0.0164), forward 3px overlap 0.79 vs H78-A lineage and 0.79 vs H78-STEP. Full labelled results: evidence/h78stepflank_run_card.json.'))
    fwtilt_path = ROOT / 'evidence/h78fwtilt_run_card.json'
    if fwtilt_path.exists():
        fwtilt = load('evidence/h78fwtilt_run_card.json')
        specs.append(('H78-FWTILT', fwtilt['raster']['file'], 'NEGATIVE + LITERAL-BLOCKED: H78-FWTILT (67 antisymmetric flank-warp & tilt-block features) passed all 10 discriminating dot/line comparators (max 3px overlap 0.6542 <= 0.70, max |rho| 0.1188 <= 0.90), verified CTRL_A2 (0.182583) on the nearest-exact-mask-v2 stack, and beat raw-band CTRL_A0 on far-truth (>1 km, 0.0586 vs 0.0482), but trailed CTRL_A2 overall (HOLDOUT-DTI 0.1481 vs 0.1826) and is blocked by the literal space-filling witnesses (13GEMSDOE 0.9967, 17GEMSDOE 1.0000). Full card: evidence/h78fwtilt_run_card.json.'))
    known = {filename for _, filename, _ in specs}
    for path in sorted((ROOT / 'docs/downloads').glob('*.tif')):
        if path.name not in known:
            specs.append(('UNREGISTERED', path.name, 'No scientific eligibility card is indexed for this artifact; fail closed.'))
    prev_by_sha = {}
    if (ROOT / 'evidence/release_audit.json').exists():
        try:
            for pc in load('evidence/release_audit.json').get('candidates', []):
                if pc.get('sha256') and pc.get('final_dots_vs_saturation_witness'):
                    prev_by_sha[pc['sha256']] = pc['final_dots_vs_saturation_witness']
        except (OSError, ValueError, KeyError):
            prev_by_sha = {}
    for lane, filename, reason in specs:
        p = ROOT / 'docs/downloads' / filename
        digest = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        try:
            sidecar = load(str(p.with_suffix('.json').relative_to(ROOT)))
        except (OSError, ValueError):
            sidecar = {}
        format_report = validate(p)
        integrity = digest is not None and digest == sidecar.get('sha256')
        uniqueness = None
        if witness and format_report['all_passed'] and integrity:
            cached_u = prev_by_sha.get(digest)
            if cached_u and cached_u.get('rows') and cached_u['rows'][0].get('sha256') == witness['sha256']:
                uniqueness = json.loads(json.dumps(cached_u))
            else:
                uniqueness = compare_to_registry(p, [dict(file=witness['local_path'], sha256=witness['sha256'],
                    repo=witness['repo'], submission=witness['path'])], footprint)
            # Absolute sandbox paths must not leak into a portable public receipt.
            uniqueness['my_file'] = str(p.relative_to(ROOT))
            for row in uniqueness['rows']:
                row['file'] = witness['local_path']
        candidates.append(dict(lane=lane, file=filename, sha256=digest,
                               validator=format_report, integrity_passed=integrity,
                               final_dots_vs_saturation_witness=uniqueness,
                               surface_before_placement=None,
                               ok_to_download=p.exists(), ok_to_submit=False,
                               verdict='negative', reason=reason,
                               protocol_blocker='Universal registry witness blocks every nonempty in-footprint prediction.' if witness else 'Preflight unverified; fail closed.'))
        sidecar.setdefault('historical_release_flags', {key: sidecar.get(key) for key in
            ('approved_for_weekly_slot', 'promoted', 'status')})
        sidecar.update(approved_for_weekly_slot=False, promoted=False, status='blocked-do-not-submit',
                       current_release_audit='../data/release_audit.json',
                       publication_note='Historical approval flags are superseded. Download for education only; no upload authorization.')
        p.with_suffix('.json').write_text(json.dumps(sidecar, indent=2, allow_nan=False) + '\n')
    card = dict(schema_version=1, review_date='2026-10-22', reviewed_utc=datetime.now(timezone.utc).isoformat(), protocol_preflight=preflight, hypothesis=m['hypothesis'],
                mechanism=m['mechanism'], non_fault_mimic=m['mimic_nonfault_process'],
                holdout={**m['holdout']['candidate_E2_MPC_SPACED'], 'evidence_class':'HOLDOUT-DTI',
                         'evaluator_version':m['holdout']['evaluator_version'],
                         'seed':m['holdout'].get('seed', 20),
                         'withheld_positive_pixels':m['holdout']['withheld_positive_pixels'],
                         'provenance':'Historical evidence; not rerun in this review'},
                candidate_vs_h33_control_paired_difference={
                    'evidence_class':'HOLDOUT-DTI paired difference',
                    **m['holdout']['paired_deltas_candidate_minus']['h33_analogue_foldfair']},
                current_repo_best_holdout=m['current_repo_best_holdout'],
                candidate_beats_current_repo_best_holdout=m['candidate_beats_current_repo_best_holdout'],
                correlation_overlap_vs_registry=dict(surface_max_abs_sampled_rho=u['preplacement_max_abs_sampled_rho'],
                    surface_correlation_limit=0.90,
                    registry_rasters_compared=u['registry_count'],
                    informative_forward_overlap=u['worst_forward_informative'],
                    literal_all_rasters_forward_overlap=u['worst_forward_literal_all_rasters'],
                    forward_3px_overlap_limit=0.70,
                    failed_forward_rows=failed, complete_registry_verified=False,
                    scope_note='74 locally accessible rasters were compared; this is not proof of every sibling/organizer raster being available.',
                    provenance='evidence/h78mpc_uniqueness.json; historical measurements, not freshly recomputed'),
                raster_sha256=candidates[1]['sha256'], validator_output=candidates[1]['validator'],
                submission_name=prod['name'], submission_note='DO NOT SUBMIT: literal forward-overlap gate failed; retained for reproducibility only.',
                verdict='negative', ok_to_download=True, ok_to_submit=False, stop_required=True, new_experiments=0,
                new_tif_generated=False, submission_slots_used=0, organizer_confirmed_score=None,
                candidates=candidates)
    for row in fresh['rows']:
        candidate = next(c for c in candidates if c['lane'] == row['lane'])
        if row['candidate_sha256'] != candidate['sha256']:
            candidate['integrity_passed'] = False
            candidate['reason'] += ' Historical recheck does not match the current candidate bytes.'
    card['correlation_overlap_vs_registry']['independent_recheck'] = fresh
    text = json.dumps(card, indent=2, allow_nan=False) + '\n'
    (ROOT / 'evidence/release_audit.json').write_text(text)
    (ROOT / 'docs/data/release_audit.json').write_text(text)
    rows = ''.join(f'<tr><td>{c["lane"]}</td><td>{"PASS" if c["validator"]["all_passed"] and c["integrity_passed"] else "FAIL / UNVERIFIED"}</td><td>NO — {html.escape(c["reason"])}<br>{html.escape(c["protocol_blocker"])}</td><td><a download href="downloads/{c["file"]}">Download historical TIFF — do not submit</a><br><small>SHA-256 <code>{c["sha256"]}</code></small></td></tr>' for c in candidates)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>GEMS78 — Submission readiness</title>
<style>body{font:17px/1.6 system-ui;margin:3rem auto;padding:0 1rem;max-width:1100px;color:#172438;background:#f5f7fb}h1{line-height:1.2}.alert{padding:1.3rem;background:#fff1df;border:2px solid #a64c00;border-radius:12px}table{border-collapse:collapse;table-layout:fixed;width:100%}td{overflow-wrap:anywhere;vertical-align:top}small{font-size:.7rem} .table-wrap{overflow-x:auto} @media(max-width:700px){body{margin:1rem auto}table{table-layout:auto;min-width:780px}td,th{padding:.6rem}}td,th{text-align:left;padding:1rem;border-bottom:1px solid #bbc5d1}a{color:#1355a0}code{overflow-wrap:anywhere}</style>
<h1>GEMS78 · Submission readiness</h1><div class="alert"><strong>OK TO DOWNLOAD: YES · OK TO SUBMIT: NO</strong><br>Automatic review blocks every published candidate, including historical inspection files. File-format validity is not scientific eligibility or organizer acceptance. No competition slot was used.<p><b>Protocol blocker verified 2026-10-22:</b> a hash-pinned GEMSDOE17 probability raster is positive across the entire footprint. Every nonempty candidate has 100% forward overlap, so none can pass the literal 70% limit. <a href="data/protocol_preflight.json">Automatic certificate</a> · <a href="review-2026-10-22.md">Current review and ranked hypotheses</a>.</p></div>
<h2>Downloads and automatic checks</h2><div class="table-wrap"><table><tr><th>Candidate</th><th>Local format</th><th>Submission gate</th><th>File</th></tr>''' + rows + '''</table></div>
<p><a href="downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif">Download inspection GeoTIFF</a> — DO-NOT-SUBMIT. Later H78-SPY file, format-valid and not cleared. <a href="index.html">Homepage</a> states the same gate.</p>
<p><a href="h78cs.html">H78-CS lane page</a> - session-3 collinear-support file, format-valid, HOLDOUT-DTI negative on two seeds and a duplicate of H78-A (forward overlap 0.8908). Do not submit.</p>
<p><a href="h78step.html">H78-STEP lane page</a> - parallel-session 2026-10-22 cross-strike step-offset file, format-valid, HOLDOUT-DTI 0.1730 vs control 0.1826 and a duplicate of the H78-A dot set (forward overlap 0.8167). Do not submit.</p>
<p><a href="h78fw.html">H78-FW lane page</a> - 2026-10-22 catalogue-blind flank-warp file, format-valid, HOLDOUT-DTI 0.0482 negative vs the 0.1843 repo best and a literal duplicate of the dense saturation witness (forward overlap 1.0). Do not submit.</p>
<p><a href="h78stepflank.html">H78-STEP-FLANK lane page</a> - second parallel session independently replicated the step-hypothesis negative (HOLDOUT-DTI 0.1662 vs control 0.1826; dots duplicate H78-A lineage and H78-STEP at 0.79). Do not submit.</p>
<p><a href="h78fwtilt.html"><b>H78-FWTILT lane page (2026-10-22)</b></a> · <a href="h78fwtilt-executive-summary.html">H78-FWTILT executive summary</a> · <a href="downloads/gems78-h78fw-flank-warp-44090dots-20261022T020704Z-c7df4b42-DO-NOT-SUBMIT.tif">Download H78-FWTILT inspection GeoTIFF</a> · <a href="data/h78fwtilt_run_card.json">H78-FWTILT run card JSON</a> — 67-feature antisymmetric footwall/hangingwall flank-warp &amp; tilt-block flexure. Passed all 10 discriminating dot/line comparators (max 3-px forward overlap 0.6542 ≤ 0.70, max |ρ| 0.1188 ≤ 0.90), verified CTRL_A2 (HOLDOUT-DTI 0.182583) on the nearest-exact-mask-v2 stack, and beat raw-band CTRL_A0 on far-truth (&gt;1 km, 0.0586 vs 0.0482), but trailed CTRL_A2 overall (0.1481 vs 0.1826) and is blocked by the literal space-filling witnesses (13GEMSDOE 0.9967, 17GEMSDOE 1.0000). Do not submit.</p>
<p><a href="data/release_audit.json">Machine-readable run card and validator output</a> · <a href="review-release.md">Scientific review, hypotheses and next steps</a></p>
<h2>Executive summary: how a future submission proceeds</h2><ol><li>Generate a genuinely new candidate in the assigned lane. Never rename an old prediction as new.</li><li>Run buffered whole-segment hide-and-recover validation, per-feature canaries and a matched current-best control.</li><li>Check the complete indexed registry before placement and on final dots. Stop for rank correlation above 0.90 or forward overlap above 70%; no mutual-overlap substitution.</li><li>Reopen the TIFF and verify one band, finite values in [0,1], footprint, CRS, shape and transform against the pinned template.</li><li>Only a separate selector may authorize upload after the gates pass and the submission-page weekly cap is checked. The cap is currently unverified.</li><li>Then download the approved TIFF, upload at DrivenData New submission, paste its short note, and preserve the organizer receipt bound to its SHA-256.</li></ol>
<h2>Why H33 might have performed better</h2><p>The repository's raster forensics support a sparse-emission and catalogue-flank-pruning explanation, not proof of a superior geothermal detector. Near-catalogue pixels are not automatically zero-credit; only exact masked catalogue pixels are excluded. Historical owner-reported leaderboard results do not establish causality or predict a new score.</p>
<p>The supplied leaderboard figures conflict and no submission-page receipt was retrieved. No score here is ORGANIZER-CONFIRMED. The task predicts missing fault traces, not direct observations of geothermal vents.</p>
<p>Historical HOLDOUT-DTI for MPC: 0.097684, 95% CI [0.077985, 0.116303], gems57-pooled-hide-v2, 11,321 withheld positives. Not rerun this review; not a leaderboard projection.</p>
<p><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">Official reference implementation</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition (not fetched in this environment)</a></p></html>'''
    page = page.replace('<h2>Downloads and automatic checks</h2>', '<p>Last local audit: <time>' + html.escape(card['reviewed_utc']) + '</time>. Static, dated evidence — not a live leaderboard feed.</p><h2>Downloads and automatic checks</h2>')
    for name in ('index.html','executive-summary.html','h78mpc.html','h78mpc-executive-summary.html'):
        (ROOT / 'docs' / name).write_text(page)
    status = load('docs/data/status.json')
    if cross_path.exists():
        cross = load('evidence/crosslayer_run_card.json')
        final = cross['registry']['final_dots']
        status.update(generated_tif=cross['submission_name'] + '.tif', sha256=cross['raster_sha256'],
                      worst_forward_3px_overlap=max(r['forward_3px_overlap'] for r in final),
                      duplicate_witnesses=[r['file'] for r in final if r['forward_3px_overlap'] > .70],
                      latest_generated_card='crosslayer_run_card.json')
    status.update(schema_version=3, review_date=card['review_date'],
                  reason='Universal registry saturation blocks every nonempty in-footprint candidate under the literal rule.',
                  new_tif_generated=False,
                  candidates=candidates, current_review_new_tif_generated=False, live_feed=False,
                  weekly_slots_used_by_agent=0, organizer_confirmed=None,
                  current_review_utc=card['reviewed_utc'], authoritative_release='release_audit.json', authoritative_card='release_audit.json',
                  protocol_preflight='protocol_preflight.json',
                  historical_session_only=True, all_published_candidates=candidates,
                  current_reason='Universal registry saturation blocks every nonempty in-footprint candidate under the literal rule.')
    (ROOT / 'docs/data/status.json').write_text(json.dumps(status, indent=2, allow_nan=False) + '\n')
    notice = '<aside id="release-audit-warning" style="padding:20px;background:#fff1df;color:#172438"><strong>Historical analysis — promotion claims superseded.</strong> Current status: OK TO SUBMIT: NO. <a href="index.html">Read the automatic release audit and current protocol saturation certificate.</a></aside>'
    for name in ('holdout.html', 'hypotheses.html', 'sources.html', 'irregularities.html', 'h78a.html', 'h78a-executive-summary.html', 'h78cs.html', 'h78cs-executive-summary.html', 'crosslayer.html', 'crosslayer-executive-summary.html', 'h78step.html', 'h78step-executive-summary.html', 'h78stepflank.html', 'h78stepflank-executive-summary.html'):
        # NOTE: h78fw.html + h78fw-executive-summary.html are session pages whose own
        # verdict banner is authoritative; they must NOT receive the historical-analysis notice.
        # A future consolidated review may add them once this session is historical.
        p = ROOT / 'docs' / name
        if p.exists():
            old = p.read_text()
            if 'id="release-audit-warning"' in old:
                p.write_text(re.sub(r'<aside id="release-audit-warning".*?</aside>', lambda _: notice, old, count=1, flags=re.DOTALL))
            else:
                p.write_text(old.replace('<body>', '<body>' + notice, 1) if '<body>' in old else old.replace('<main>', '<main>' + notice, 1))
    return card

if __name__ == '__main__':
    main()
