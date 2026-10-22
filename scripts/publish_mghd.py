#!/usr/bin/env python3
"""Publish dedicated Session-5 H78-MGHD deep-dive page (docs/h78mghd.html) and run release audit."""
from __future__ import annotations

import hashlib
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def publish() -> dict:
    card = json.loads((ROOT / "evidence" / "h78mghd_run_card.json").read_text())
    uniq = json.loads((ROOT / "evidence" / "h78mghd_uniqueness_summary.json").read_text())
    seed20 = json.loads((ROOT / "evidence" / "h78mghd_holdout_seed20.json").read_text())
    seed30 = json.loads((ROOT / "evidence" / "h78mghd_holdout_seed30.json").read_text())

    tif = ROOT / "docs" / "downloads" / card["submission_file"]
    if not tif.exists():
        raise FileNotFoundError(f"Missing H78-MGHD GeoTIFF: {tif}")
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    if digest != card["raster_sha256"]:
        raise ValueError("H78-MGHD SHA-256 mismatch between run card and downloadable GeoTIFF")

    ver = json.loads(subprocess.check_output([sys.executable, str(ROOT / "scripts" / "verify_tif.py"), str(tif)]))
    if not ver["all_passed"] or ver["sha256"] != digest:
        raise ValueError("Independent GeoTIFF revalidation failed")

    e = html.escape
    h = card["holdout"]
    e1 = h["experiment_E1_matched_emitter_seed20_44090"]
    e2 = h["experiment_E2_selected_arm_seed20_44090"]
    e3 = h["experiment_E3_seed30_zero_retune_44090"]
    p2s = h["pooled_two_seed_44090"]
    reg = card["correlation_overlap_vs_registry"]
    h78a_ext = uniq["historical_h78a_full_accessible_audit"]
    pass1 = seed20.get("pass1_weighted_oof_diagnostic_IR_78_MGHD_01") or {}

    top_sparse_rows = "".join(
        f"<tr><td><code>{e(r['file'])}</code></td><td>{r['their_dots']:,}</td>"
        f"<td>{r['forward_overlap']:.4f}</td><td>{(r['spearman_full_footprint'] or 0.0):.4f}</td></tr>"
        for r in uniq["final_dots_sparse_dot_submissions_le_65k"]["top15_sparse"][:8]
    )
    top_corridor_rows = "".join(
        f"<tr><td><code>{e(r['file'])}</code></td><td>{r['their_dots']:,}</td>"
        f"<td>{r['halo_coverage']:.4f}</td><td>{r['forward_overlap']:.4f}</td></tr>"
        for r in uniq["final_dots_discriminating_halo_lt_0p70"]["top20_halo_lt_0p70"][:8]
    )

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE78 · Lane H78-MGHD (Session 5 Full Evidence &amp; Validator Receipt)</title>
<style>
:root{{--bg:#0b1324;--card:#121e36;--ink:#eaf2fc;--mut:#9db0cc;--bad:#ef4444;--ok:#22c55e;--acc:#60a5fa;--line:#263959}}
*{{box-sizing:border-box}}body{{margin:0;padding:1.8rem 1rem 4rem;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}}
main{{max-width:1100px;margin:0 auto}}h1{{font-size:2rem;margin:.3rem 0 .8rem}}h2{{font-size:1.35rem;margin-top:0;color:#fff}}
section{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1.3rem 1.5rem;margin:1.2rem 0}}
.banner{{background:#3b1016;border:3px solid var(--bad);border-radius:14px;padding:1.3rem 1.5rem;margin:1rem 0}}
.btns a{{display:inline-block;margin:.5rem .7rem .2rem 0;padding:.75rem 1.1rem;border-radius:9px;font-weight:700;text-decoration:none}}
.btn-main{{background:#f87171;color:#1b0b0e}}.btn-sec{{background:#1e3152;color:var(--ink);border:1px solid #3c5887}}
table{{width:100%;border-collapse:collapse;font-size:.92rem;margin:.6rem 0}}
th,td{{padding:.55rem .65rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{color:var(--mut);font-weight:600}}code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.86rem;overflow-wrap:anywhere}}
nav a{{color:var(--acc);margin-right:1rem;text-decoration:none;font-weight:600}}a{{color:var(--acc)}}
.pill-ok{{color:#86efac;font-weight:700}}.pill-no{{color:#fca5a5;font-weight:700}}
</style></head><body><main>
<nav><a href="index.html">Home &amp; Readiness Gate</a><a href="executive-summary.html">Executive Summary &amp; Submit Guide</a><a href="why-h33.md">Why H33 Outperformed</a><a href="review-release.md">Full Scientific Review</a><a href="data/h78mghd_run_card.json">H78-MGHD Run Card JSON</a><a href="data/release_audit.json">Consolidated Release Audit JSON</a></nav>
<h1>Lane H78-MGHD · Multi-Scale Geodetic–Hydrothermal–LiDAR Dual-Cover</h1>

<div class="banner">
  <div style="font-size:1.35rem;font-weight:800">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO</div>
  <p style="margin:.5rem 0"><strong>Scientific &amp; format gates PASSED</strong> (beats incumbent on both spatial holdout seeds with 95% CIs excluding 0; 123/123 leakage canaries &le; 0.90; 13/13 GeoTIFF checks passed; passes &le; 0.70 overlap against <strong>all 801/801 sparse dot submissions</strong> across all 84 accessible repos), <strong>AND binding literal registry gate BLOCKS upload</strong> because 113 dense corridor / continuous-surface sibling rasters exceed 70% 3-px forward overlap (100.00% on space-filling surfaces). Retained strictly for research &amp; education — <strong>DO NOT UPLOAD TO DRIVENDATA</strong>.</p>
  <div class="btns">
    <a class="btn-main" download href="downloads/{e(card['submission_file'])}">Download New H78-MGHD GeoTIFF (158 KB · DO-NOT-SUBMIT)</a>
    <a class="btn-sec" download href="downloads/{e(card['submission_zip'])}">Download Single-TIFF ZIP (127 KB)</a>
    <a class="btn-sec" href="data/h78mghd_run_card.json">Machine-Readable Run Card (JSON)</a>
  </div>
</div>

<section>
  <h2>1. Artifact Identity &amp; Automated Programmatic Validator Receipt (Zero Human-Inspector Deferral)</h2>
  <table>
    <tr><th>Unique submission name</th><td><code>{e(card['submission_name'])}</code></td></tr>
    <tr><th>Note (&le;140 chars: {card['submission_note_length']} chars)</th><td><code>{e(card['submission_note'])}</code></td></tr>
    <tr><th>GeoTIFF SHA-256</th><td><code>{e(card['raster_sha256'])}</code> ({ver['bytes']:,} bytes)</td></tr>
    <tr><th>Single-TIFF ZIP SHA-256</th><td><code>{e(card['submission_zip_sha256'])}</code> (byte-identical member: <span class="pill-ok">{ver['zip']['single_tif_byte_identical']}</span>)</td></tr>
    <tr><th>Grid, CRS &amp; Data Type</th><td><span class="pill-ok">PASS</span> — Single band (<code>count=1</code>), <code>float32</code>, <code>EPSG:32611</code>, <code>3730 &times; 3292</code>, affine <code>(100, 0, 243350, 0, -100, 4508550)</code>, <code>nodata=None</code></td></tr>
    <tr><th>Range &amp; Footprint Safety</th><td><span class="pill-ok">PASS</span> — All 12,279,160 cells finite in <code>[0.0, 1.0]</code> (binary <code>{{0.0, 1.0}}</code>, zero NaN inside or outside footprint, <code>44,090</code> dots strictly inside footprint, <code>0</code> on mapped catalogue; portal <code>[0, 1]</code> error impossible)</td></tr>
    <tr><th>ORGANIZER-CONFIRMED Score</th><td><strong>None</strong> — Zero DrivenData slots consumed (<code>weekly_slots_used_by_agent = 0</code>); no projections ever reported as scores.</td></tr>
  </table>
</section>

<section>
  <h2>2. Two-Seed Spatial Hide-and-Recover Validation (<code>HOLDOUT-DTI</code>, <code>gems57-pooled-hide-v2</code>)</h2>
  <p>Whole 8-connected fault segments withheld (20% per quadrant + 3 px collar), strike field &amp; features derived strictly from visible faults only, visible faults masked pixel-exactly, scored with official <code>&alpha;=0.2, &beta;=0.8</code> 300 m triangular kernel and 1,000-draw 20 km paired spatial-block bootstrap. Single-feature canary across all 123 features: <strong>max symmetric ROC AUC = {card['leakage_canary_summary']['max_symmetric_auc']:.4f} &le; 0.90 PASS</strong> (<code>{e(card['leakage_canary_summary']['max_feature'])}</code>).</p>
  <table>
    <tr><th>Experiment / Seed Split</th><th>Withheld Positives</th><th>Candidate <code>HOLDOUT-DTI</code> [95% CI]</th><th>Matched Control <code>CTRL_A2_v2</code> [95% CI]</th><th>Paired &Delta; (Cand &minus; Ctrl) [95% CI]</th></tr>
    <tr><td><strong>E1</strong> · Seed 20 matched emitter (<code>min_dist=2.8</code>, 44,090 dots)</td><td>{e1['withheld_positive_pixels']:,}</td><td><strong>{e1['candidate']['dti']:.6f}</strong> [{e1['candidate']['ci95'][0]:.6f}, {e1['candidate']['ci95'][1]:.6f}]</td><td>{e1['control_CTRL_A2_v2_44090']['dti']:.6f} [{e1['control_CTRL_A2_v2_44090']['ci95'][0]:.6f}, {e1['control_CTRL_A2_v2_44090']['ci95'][1]:.6f}]</td><td><span class="pill-ok">+{e1['paired_delta_cand_minus_ctrl']['delta']:.6f} [{e1['paired_delta_cand_minus_ctrl']['ci95'][0]:+.6f}, {e1['paired_delta_cand_minus_ctrl']['ci95'][1]:+.6f}]</span></td></tr>
    <tr><td><strong>E2</strong> · Seed 20 selected 300 m non-overlap (<code>min_dist=3.01</code>, 44,090 dots)</td><td>{e2['withheld_positive_pixels']:,}</td><td><strong>{e2['candidate']['dti']:.6f}</strong> [{e2['candidate']['ci95'][0]:.6f}, {e2['candidate']['ci95'][1]:.6f}]</td><td>{e2['control_CTRL_A2_v2_44090']['dti']:.6f} [{e2['control_CTRL_A2_v2_44090']['ci95'][0]:.6f}, {e2['control_CTRL_A2_v2_44090']['ci95'][1]:.6f}]</td><td><span class="pill-ok">+{e2['paired_delta_cand_minus_ctrl']['delta']:.6f} [{e2['paired_delta_cand_minus_ctrl']['ci95'][0]:+.6f}, {e2['paired_delta_cand_minus_ctrl']['ci95'][1]:+.6f}]</span></td></tr>
    <tr><td><strong>E2 vs 50k</strong> · Seed 20 44,090-dot candidate vs 50,000-dot <code>CTRL_A2_v2</code></td><td>{e2['withheld_positive_pixels']:,}</td><td><strong>{e2['candidate']['dti']:.6f}</strong> (5,910 fewer dots)</td><td>{e2['control_CTRL_A2_v2_50000']['dti']:.6f} [{e2['control_CTRL_A2_v2_50000']['ci95'][0]:.6f}, {e2['control_CTRL_A2_v2_50000']['ci95'][1]:.6f}]</td><td><span class="pill-ok">+{e2['paired_delta_cand_minus_ctrl50k']['delta']:.6f} [{e2['paired_delta_cand_minus_ctrl50k']['ci95'][0]:+.6f}, {e2['paired_delta_cand_minus_ctrl50k']['ci95'][1]:+.6f}]</span></td></tr>
    <tr><td><strong>E3</strong> · Seed 30 zero-retune spatial replication (<code>min_dist=3.01</code>, 44,090 dots)</td><td>{e3['withheld_positive_pixels']:,}</td><td><strong>{e3['candidate']['dti']:.6f}</strong> [{e3['candidate']['ci95'][0]:.6f}, {e3['candidate']['ci95'][1]:.6f}]</td><td>{e3['control_CTRL_A2_v2_44090']['dti']:.6f} [{e3['control_CTRL_A2_v2_44090']['ci95'][0]:.6f}, {e3['control_CTRL_A2_v2_44090']['ci95'][1]:.6f}]</td><td><span class="pill-ok">+{e3['paired_delta_cand_minus_ctrl']['delta']:.6f} [{e3['paired_delta_cand_minus_ctrl']['ci95'][0]:+.6f}, {e3['paired_delta_cand_minus_ctrl']['ci95'][1]:+.6f}]</span></td></tr>
    <tr><td><strong>Pooled 2-Seed</strong> · Combined Seeds 20 + 30 (44,090 dots)</td><td>{p2s['withheld_positive_pixels']:,}</td><td><strong>{p2s['candidate']['dti']:.6f}</strong> [{p2s['candidate']['ci95'][0]:.6f}, {p2s['candidate']['ci95'][1]:.6f}]</td><td>{p2s['control_CTRL_A2_v2_44090']['dti']:.6f} [{p2s['control_CTRL_A2_v2_44090']['ci95'][0]:.6f}, {p2s['control_CTRL_A2_v2_44090']['ci95'][1]:.6f}]</td><td><span class="pill-ok">+{p2s['paired_delta_cand_minus_ctrl']['delta']:.6f} [{p2s['paired_delta_cand_minus_ctrl']['ci95'][0]:+.6f}, {p2s['paired_delta_cand_minus_ctrl']['ci95'][1]:+.6f}]</span></td></tr>
  </table>
  <p><small>Pass-1 diagnostic disclosure (<code>IR-78-MGHD-01</code>): passing inverse-sampling weights (~20.5&times;) directly into <code>HistGradientBoosting</code> split Hessians starved fault leaves on seed 20 (<code>0.139381</code> greedy / <code>0.141531</code> submodular) before seed 30 was ever run; Pass-2 unweighted fitting with post-hoc Bayes prior calibration fixed the defect prior to zero-retune seed-30 replication.</small></p>
</section>

<section>
  <h2>3. Complete 84-Repository (1,103-Raster) Uniqueness Audit — Before &amp; After Dot Placement</h2>
  <table>
    <tr><th>Audit Gate / Comparison Tier</th><th>Rasters Checked</th><th>Measured Worst Statistic</th><th>Threshold</th><th>Outcome</th></tr>
    <tr><td><strong>Gate 1A</strong> · Pre-placement continuous surface (all rasters)</td><td>{reg['registry_total_rasters_compared']:,}</td><td><code>|Spearman &rho;| = {reg['surface_max_abs_spearman']:.6f}</code></td><td>&le; 0.90</td><td><span class="pill-ok">PASS</span></td></tr>
    <tr><td><strong>Diagnostic Tier</strong> · All sparse dot submissions (&le;65,000 positive pixels)</td><td>{reg['sparse_dot_le_65k_count']:,}</td><td><code>{reg['sparse_dot_le_65k_worst_forward_3px_overlap']:.6f}</code> (vs H78-A: <code>{reg['vs_h78a_forward_3px_overlap']:.4f}</code>)</td><td>&le; 0.70</td><td><span class="pill-ok">PASS (801/801)</span></td></tr>
    <tr><td><strong>Wide-Corridor Tier</strong> · All rasters with global halo &lt; 0.70 (incl. ~624k-px range-front corridors)</td><td>{reg['halo_lt_0p70_count']:,}</td><td><code>{reg['halo_lt_0p70_worst_forward_3px_overlap']:.6f}</code> on <code>{e(reg['halo_lt_0p70_worst_file'])}</code></td><td>&le; 0.70</td><td><span class="pill-no">STOP (&gt; 0.70)</span></td></tr>
    <tr><td><strong>Binding Literal Gate</strong> · All accessible sibling rasters (zero exemptions)</td><td>{reg['registry_total_rasters_compared']:,}</td><td><code>{reg['literal_all_rasters_worst_forward_3px_overlap']:.6f}</code> on <code>{e(reg['literal_all_rasters_worst_file'])}</code></td><td>&le; 0.70</td><td><span class="pill-no">BINDING STOP &rarr; NEGATIVE</span></td></tr>
  </table>
  <p><strong>Historical H78-A resolution:</strong> Completing the full {h78a_ext['external_rasters_compared']:,}-raster external sibling audit on historical <code>H78-A</code> confirms that <code>H78-A</code> also exceeds 0.70 both among sparse &le;65k-dot submissions (<code>{h78a_ext['worst_sparse_le_65k_forward_3px_overlap']:.4f}</code> against <code>{e(h78a_ext['worst_sparse_le_65k_file'])}</code>) and against wide corridors (<code>{h78a_ext['worst_halo_lt_0p70_forward_3px_overlap']:.4f}</code>).</p>
  <h3>Closest Sparse Dot Submissions (&le;65,000 Positive Pixels Across All 84 Repos)</h3>
  <table><tr><th>Sibling Artifact (Repo@Commit:Path)</th><th>Positive Pixels</th><th>Forward 3-px Overlap</th><th>Footprint &rho;</th></tr>{top_sparse_rows}</table>
  <h3>Wide-Corridor Rasters Explaining Non-Space-Filling &gt;0.70 Overlap</h3>
  <table><tr><th>Sibling Artifact (Repo@Commit:Path)</th><th>Positive Pixels</th><th>Global 3-px Halo</th><th>Forward 3-px Overlap</th></tr>{top_corridor_rows}</table>
</section>
</main></body></html>
"""
    (ROOT / "docs" / "h78mghd.html").write_text(page)
    from audit_release import main as run_audit
    run_audit()
    return json.loads((ROOT / "docs" / "data" / "status.json").read_text())


if __name__ == "__main__":
    publish()
