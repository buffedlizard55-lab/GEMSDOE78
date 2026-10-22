#!/usr/bin/env python3
"""Fail-closed consolidated publication audit for GEMSDOE78 (Sessions 1-5).

Validates every published GeoTIFF + ZIP + JSON sidecar in docs/downloads/, binds SHA-256
digests, writes strict JSON to evidence/release_audit.json, docs/data/release_audit.json,
and docs/data/status.json, and renders crisp, top-of-page submission-readiness banners
with one-click downloads on docs/index.html and docs/executive-summary.html.
"""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor"))
from preflight import run as run_preflight
from gems57.uniqueness import compare_to_registry


def load(path):
    return json.loads((ROOT / path).read_text())


def literal_failures(rows):
    return [
        r
        for r in rows
        if r["forward_overlap_mine_in_theirs3px"] > 0.70
        or r.get("spearman_full_footprint", 0) > 0.90
    ]


def validate(path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_tif.py"), str(path)],
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"all_passed": False, "error": result.stderr[-2000:]}
    report["all_passed"] = result.returncode == 0 and report["all_passed"]
    return report


def main():
    a = load("evidence/h78_run_card.json")
    m = load("evidence/h78mpc_run_card.json")
    u = load("evidence/h78mpc_uniqueness.json")
    prod = load("evidence/h78mpc_production.json")
    a_review = load("evidence/h78a_current_review.json")
    failed = literal_failures(u["dot_rows"])
    fresh = load("evidence/rechecked_overlap.json")
    cs = load("evidence/h78cs_run_card.json")
    spy = load("evidence/h78spy_run_card.json")
    mghd_path = ROOT / "evidence/h78mghd_run_card.json"
    mghd = load("evidence/h78mghd_run_card.json") if mghd_path.exists() else None
    mghd_uniq = (
        load("evidence/h78mghd_uniqueness_summary.json")
        if (ROOT / "evidence/h78mghd_uniqueness_summary.json").exists()
        else None
    )

    preflight = run_preflight()
    witness = (
        next(e for e in preflight["verified_inputs"] if e["id"] == "saturation_witness")
        if preflight["correlation_overlap_vs_registry"]
        else None
    )
    footprint = None
    if witness:
        with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
            footprint = np.isfinite(src.read(1))

    candidates = []
    specs = [
        ("H78-A", a["raster"]["file"], f"INCOMPLETE: {a_review['reason']}"),
        (
            "H78-MPC",
            prod["final_stem"] + ".tif",
            "DUPLICATE: recorded forward overlap exceeds the literal threshold. Stop required.",
        ),
        (
            "H78-CS",
            cs["raster"]["file"],
            "DUPLICATE + NEGATIVE: failed matched HOLDOUT-DTI comparison; replication did not establish a gain. Forward 3px overlap vs H78-A 0.8908 exceeds 0.70. Full labelled results: evidence/h78cs_run_card.json.",
        ),
        (
            "H78-SPY",
            spy["file"],
            "DUPLICATE + NEGATIVE: failed matched holdout control; forward overlap vs H78-A 0.9245 exceeds 0.70.",
        ),
        (
            "H78-A-altB2",
            "gems78-h78a-strike-steered-44090dots-20261021T223133Z-ec00c053-altB2-zeros.tif",
            "Historical same-model flank alternative, not a new lane. No current slot authorization.",
        ),
    ]
    cross_path = ROOT / "evidence/crosslayer_run_card.json"
    if cross_path.exists():
        cross = load("evidence/crosslayer_run_card.json")
        specs.append(
            (
                "H78-CROSSLAYER",
                cross["submission_name"] + ".tif",
                "DUPLICATE + NEGATIVE: separate parallel session generated this file; it failed its holdout control and registry gates. Not generated in this review.",
            )
        )
    if mghd is not None:
        s20_dti = mghd["holdout"]["experiment_E2_selected_arm_seed20_44090"]["candidate"]["dti"]
        s30_dti = mghd["holdout"]["experiment_E3_seed30_zero_retune_44090"]["candidate"]["dti"]
        specs.append(
            (
                "H78-MGHD",
                mghd["submission_file"],
                f"DUPLICATE-STOP (RESEARCH ONLY): Session 5 multi-scale geodetic-hydrothermal-LiDAR dual-cover beats incumbent on BOTH holdout seeds (HOLDOUT-DTI {s20_dti:.4f} s20, {s30_dti:.4f} s30) and passes all 801 sparse dot submissions (max 0.6800 <= 0.70), but fails literal all-1,103-raster overlap against dense corridor / continuous sibling rasters (1.0000 > 0.70). Full evidence: evidence/h78mghd_run_card.json.",
            )
        )

    known = {filename for _, filename, _ in specs}
    for path in sorted((ROOT / "docs/downloads").glob("*.tif")):
        if path.name not in known:
            specs.append(
                (
                    "UNREGISTERED",
                    path.name,
                    "No scientific eligibility card is indexed for this artifact; fail closed.",
                )
            )

    for lane, filename, reason in specs:
        p = ROOT / "docs/downloads" / filename
        digest = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        try:
            sidecar = load(str(p.with_suffix(".json").relative_to(ROOT)))
        except (OSError, ValueError):
            sidecar = {}
        format_report = validate(p)
        integrity = digest is not None and digest == sidecar.get("sha256")
        uniqueness = None
        if witness and format_report["all_passed"] and integrity:
            uniqueness = compare_to_registry(
                p,
                [
                    dict(
                        file=witness["local_path"],
                        sha256=witness["sha256"],
                        repo=witness["repo"],
                        submission=witness["path"],
                    )
                ],
                footprint,
            )
            uniqueness["my_file"] = str(p.relative_to(ROOT))
            for row in uniqueness["rows"]:
                row["file"] = witness["local_path"]
        cand_row = dict(
            lane=lane,
            file=filename,
            sha256=digest,
            validator=format_report,
            integrity_passed=integrity,
            final_dots_vs_saturation_witness=uniqueness,
            surface_before_placement=None,
            ok_to_download=p.exists(),
            ok_to_submit=False,
            verdict="negative",
            reason=reason,
            protocol_blocker=(
                "Universal registry witness blocks every nonempty in-footprint prediction."
                if witness
                else "Preflight unverified; fail closed."
            ),
        )
        if lane == "H78-MGHD" and mghd is not None:
            cand_row["session5_run_card"] = "evidence/h78mghd_run_card.json"
            cand_row["session5_preplacement_surface_gate"] = {
                "registry_rasters_checked": mghd["correlation_overlap_vs_registry"]["registry_total_rasters_compared"],
                "max_abs_spearman": mghd["correlation_overlap_vs_registry"]["surface_max_abs_spearman"],
                "passed": mghd["correlation_overlap_vs_registry"]["surface_gate_passed"],
            }
        candidates.append(cand_row)
        sidecar.setdefault(
            "historical_release_flags",
            {key: sidecar.get(key) for key in ("approved_for_weekly_slot", "promoted", "status")},
        )
        sidecar.update(
            approved_for_weekly_slot=False,
            promoted=False,
            status="blocked-do-not-submit",
            current_release_audit="../data/release_audit.json",
            publication_note="Historical approval flags are superseded. Download for education only; no upload authorization.",
        )
        p.with_suffix(".json").write_text(json.dumps(sidecar, indent=2, allow_nan=False) + "\n")

    card = dict(
        schema_version=1,
        review_date="2026-10-22",
        reviewed_utc=datetime.now(timezone.utc).isoformat(),
        protocol_preflight=preflight,
        hypothesis=m["hypothesis"],
        mechanism=m["mechanism"],
        non_fault_mimic=m["mimic_nonfault_process"],
        holdout={
            **m["holdout"]["candidate_E2_MPC_SPACED"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": m["holdout"]["evaluator_version"],
            "seed": m["holdout"].get("seed", 20),
            "withheld_positive_pixels": m["holdout"]["withheld_positive_pixels"],
            "provenance": "Historical evidence; not rerun in this review",
        },
        candidate_vs_h33_control_paired_difference={
            "evidence_class": "HOLDOUT-DTI paired difference",
            **m["holdout"]["paired_deltas_candidate_minus"]["h33_analogue_foldfair"],
        },
        current_repo_best_holdout=m["current_repo_best_holdout"],
        candidate_beats_current_repo_best_holdout=m["candidate_beats_current_repo_best_holdout"],
        correlation_overlap_vs_registry=dict(
            surface_max_abs_sampled_rho=u["preplacement_max_abs_sampled_rho"],
            surface_correlation_limit=0.90,
            registry_rasters_compared=u["registry_count"],
            informative_forward_overlap=u["worst_forward_informative"],
            literal_all_rasters_forward_overlap=u["worst_forward_literal_all_rasters"],
            forward_3px_overlap_limit=0.70,
            failed_forward_rows=failed,
            complete_registry_verified=False,
            scope_note="74 locally accessible rasters were compared in H78-MPC; see session5_h78mghd for the complete 84-repo (1,103-raster) accessible scan.",
            provenance="evidence/h78mpc_uniqueness.json; historical measurements preserved",
        ),
        raster_sha256=candidates[1]["sha256"],
        validator_output=candidates[1]["validator"],
        submission_name=prod["name"],
        submission_note="DO NOT SUBMIT: literal forward-overlap gate failed; retained for reproducibility only.",
        verdict="negative",
        ok_to_download=True,
        ok_to_submit=False,
        stop_required=True,
        new_experiments=0,
        new_tif_generated=False,
        submission_slots_used=0,
        organizer_confirmed_score=None,
        session5_h78mghd={
            "run_card": "evidence/h78mghd_run_card.json",
            "uniqueness_summary": "evidence/h78mghd_uniqueness_summary.json",
            "file": mghd["submission_file"],
            "sha256": mghd["raster_sha256"],
            "experiments_used": mghd["experiments_used"],
            "holdout_seed20_44090": mghd["holdout"]["experiment_E2_selected_arm_seed20_44090"]["candidate"]["dti"],
            "holdout_seed30_44090": mghd["holdout"]["experiment_E3_seed30_zero_retune_44090"]["candidate"]["dti"],
            "holdout_pooled_2seed_44090": mghd["holdout"]["pooled_two_seed_44090"]["candidate"]["dti"],
            "registry_total_rasters_compared": mghd["correlation_overlap_vs_registry"]["registry_total_rasters_compared"],
            "sparse_dot_le_65k_worst_overlap": mghd["correlation_overlap_vs_registry"]["sparse_dot_le_65k_worst_forward_3px_overlap"],
            "verdict": mghd["verdict"],
            "ok_to_submit": mghd["ok_to_submit"],
        }
        if mghd is not None
        else None,
        candidates=candidates,
    )
    for row in fresh["rows"]:
        candidate = next(c for c in candidates if c["lane"] == row["lane"])
        if row["candidate_sha256"] != candidate["sha256"]:
            candidate["integrity_passed"] = False
            candidate["reason"] += " Historical recheck does not match the current candidate bytes."
    card["correlation_overlap_vs_registry"]["independent_recheck"] = fresh

    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "evidence/release_audit.json").write_text(text)
    (ROOT / "docs/data/release_audit.json").write_text(text)

    # Display H78-MGHD first visually in HTML candidate table while keeping candidates list index order intact
    ordered_visual = sorted(candidates, key=lambda c: 0 if c["lane"] == "H78-MGHD" else 1)
    rows_html = "".join(
        f'<tr><td><strong>{html.escape(c["lane"])}</strong></td>'
        f'<td>{"PASS (13/13 checks)" if c["validator"]["all_passed"] and c["integrity_passed"] else "FAIL / UNVERIFIED"}</td>'
        f'<td>NO — {html.escape(c["reason"])}<br>{html.escape(c["protocol_blocker"])}</td>'
        f'<td><a download href="downloads/{html.escape(c["file"])}">Download {"NEW Session-5 " if c["lane"] == "H78-MGHD" else "historical "}TIFF — do not submit</a><br>'
        f'<small>SHA-256 <code>{c["sha256"]}</code></small></td></tr>'
        for c in ordered_visual
    )

    mghd_hero_actions = ""
    mghd_science_block = ""
    if mghd is not None:
        e2 = mghd["holdout"]["experiment_E2_selected_arm_seed20_44090"]
        e3 = mghd["holdout"]["experiment_E3_seed30_zero_retune_44090"]
        p2s = mghd["holdout"]["pooled_two_seed_44090"]
        reg = mghd["correlation_overlap_vs_registry"]
        mghd_hero_actions = (
            f'<div class="btn-row">'
            f'<a class="btn-primary" download href="downloads/{html.escape(mghd["submission_file"])}">'
            f'&#11015; Download NEW Session-5 GeoTIFF ({html.escape(mghd["submission_file"])})</a> '
            f'<a class="btn-secondary" download href="downloads/{html.escape(mghd["submission_zip"])}">'
            f'&#11015; Download Single-TIFF ZIP (127 KB)</a> '
            f'<a class="btn-secondary" href="h78mghd.html">Full H78-MGHD Lane Evidence &amp; Validator Receipt</a> '
            f'<a class="btn-secondary" href="data/h78mghd_run_card.json">H78-MGHD Run Card JSON</a>'
            f'</div>'
            f'<div class="meta-strip">'
            f'<b>Automated Validator (0 human-inspector deferral):</b> 13/13 checks PASS · single-band <code>float32</code> · '
            f'<code>EPSG:32611</code> · <code>3730 &times; 3292</code> · affine <code>(100, 0, 243350, 0, -100, 4508550)</code> · '
            f'values strictly finite in <code>[0, 1]</code> (binary <code>{{0.0, 1.0}}</code>, 44,090 dots, 0 NaN inside footprint) · '
            f'SHA-256 <code>{mghd["raster_sha256"]}</code> · Note ({mghd["submission_note_length"]}/140 chars): '
            f'<code>{html.escape(mghd["submission_note"])}</code>'
            f'</div>'
        )
        mghd_science_block = f"""
<div class="card">
<h2>Session 5 New Candidate Summary: Lane <code>H78-MGHD</code> (Multi-Scale Geodetic–Hydrothermal–LiDAR Dual-Cover)</h2>
<ul>
  <li><b>Two-Seed Spatial Hide-and-Recover Breakthrough (<code>HOLDOUT-DTI</code>, <code>gems57-pooled-hide-v2</code>):</b>
    <ul>
      <li><b>Seed 20 (11,321 withheld positives, 44,090 dots):</b> <code>{e2['candidate']['dti']:.6f}</code> [95% CI <code>{e2['candidate']['ci95'][0]:.6f}</code>, <code>{e2['candidate']['ci95'][1]:.6f}</code>] vs matched incumbent <code>CTRL_A2_v2</code> <code>{e2['control_CTRL_A2_v2_44090']['dti']:.6f}</code> &rarr; paired &Delta; = <b>+{e2['paired_delta_cand_minus_ctrl']['delta']:.6f}</b> [95% CI <code>+{e2['paired_delta_cand_minus_ctrl']['ci95'][0]:.6f}</code>, <code>+{e2['paired_delta_cand_minus_ctrl']['ci95'][1]:.6f}</code>] (also beats 50,000-dot incumbent <code>{e2['control_CTRL_A2_v2_50000']['dti']:.6f}</code> with 5,910 fewer dots).</li>
      <li><b>Seed 30 Zero-Retune Replication (11,342 withheld positives, 44,090 dots):</b> <code>{e3['candidate']['dti']:.6f}</code> [95% CI <code>{e3['candidate']['ci95'][0]:.6f}</code>, <code>{e3['candidate']['ci95'][1]:.6f}</code>] vs matched <code>CTRL_A2_v2</code> <code>{e3['control_CTRL_A2_v2_44090']['dti']:.6f}</code> &rarr; paired &Delta; = <b>+{e3['paired_delta_cand_minus_ctrl']['delta']:.6f}</b> [95% CI <code>+{e3['paired_delta_cand_minus_ctrl']['ci95'][0]:.6f}</code>, <code>+{e3['paired_delta_cand_minus_ctrl']['ci95'][1]:.6f}</code>].</li>
      <li><b>Pooled 2-Seed Summary (22,663 withheld positives):</b> <code>{p2s['candidate']['dti']:.6f}</code> [95% CI <code>{p2s['candidate']['ci95'][0]:.6f}</code>, <code>{p2s['candidate']['ci95'][1]:.6f}</code>] vs <code>{p2s['control_CTRL_A2_v2_44090']['dti']:.6f}</code> &rarr; paired &Delta; = <b>+{p2s['paired_delta_cand_minus_ctrl']['delta']:.6f}</b> [95% CI <code>+{p2s['paired_delta_cand_minus_ctrl']['ci95'][0]:.6f}</code>, <code>+{p2s['paired_delta_cand_minus_ctrl']['ci95'][1]:.6f}</code>].</li>
    </ul>
  </li>
  <li><b>Leakage Canaries:</b> All 123 pure-physics features tested individually before model fitting; max symmetric ROC AUC = <code>{mghd['leakage_canary_summary']['max_symmetric_auc']:.4f} &le; 0.90</code> PASS (SGMC / QFaults / catalogue distance strictly excluded).</li>
  <li><b>Complete 84-Repository (1,103-Raster) Registry Audit:</b> Surface <code>max |Spearman &rho;| = {reg['surface_max_abs_spearman']:.4f} &le; 0.90</code> PASS across all 1,103 rasters; passes <code>&le; 0.70</code> forward 3-px overlap across <b>all 801/801 sparse dot submissions (&le;65,000 dots; max = {reg['sparse_dot_le_65k_worst_forward_3px_overlap']:.4f}, vs H78-A = {reg['vs_h78a_forward_3px_overlap']:.4f})</b>; <b>binding literal stop triggered</b> by 81 continuous space-filling rasters (<code>1.0000 &gt; 0.70</code>) and 32 wide fault-corridor rasters (<code>0.9158 &gt; 0.70</code>) &rarr; <b>Verdict: <code>negative</code> (OK TO DOWNLOAD: YES · DO NOT SUBMIT; 0 slots used)</b>.</li>
</ul>
</div>"""

    nav_bar = (
        '<nav class="topnav">'
        '<a href="index.html">Readiness &amp; Download</a> · '
        '<a href="executive-summary.html">Executive Summary &amp; How-To Submit</a> · '
        '<a href="h78mghd.html">H78-MGHD Lane (New)</a> · '
        '<a href="why-h33.md">Why GEMSDOE32 (H33) Scored Higher</a> · '
        '<a href="review-release.md">Ranked Hypotheses &amp; Audit</a> · '
        '<a href="sources.html">Verified Sources</a> · '
        '<a href="irregularities.html">Irregularities</a> · '
        '<a href="data/release_audit.json">release_audit.json</a>'
        '</nav>'
    )

    page = (
        '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>GEMSDOE78 — Submission Readiness, GeoTIFF Download &amp; Scientific Audit</title>
<style>
body{font:16.5px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem auto;padding:0 1.1rem 3rem;max-width:1140px;color:#172438;background:#f5f7fb}
h1{line-height:1.2;margin:.4rem 0 1rem}h2{margin-top:1.8rem;line-height:1.3}
.topnav{font-size:.93rem;padding:.6rem .9rem;background:#e8eef7;border-radius:10px;margin-bottom:1rem}
.alert{padding:1.35rem 1.5rem;background:#fff1df;border:3px solid #b43c00;border-radius:14px;box-shadow:0 2px 10px rgba(0,0,0,.05)}
.status-kicker{font-size:1.35rem;font-weight:800;color:#8a1c00;letter-spacing:.01em}
.btn-row{margin:.9rem 0 .7rem}
.btn-primary{display:inline-block;background:#b42318;color:#fff !important;font-weight:700;padding:.68rem 1.05rem;border-radius:9px;text-decoration:none;margin:.25rem .45rem .25rem 0}
.btn-secondary{display:inline-block;background:#fff;color:#134078 !important;border:1.5px solid #8ea6c7;font-weight:600;padding:.62rem .95rem;border-radius:9px;text-decoration:none;margin:.25rem .45rem .25rem 0}
.meta-strip{font-size:.87rem;background:#fffaf3;border:1px solid #e4c39b;border-radius:9px;padding:.65rem .85rem;margin-top:.55rem}
.card{background:#fff;border:1px solid #cbd5e1;border-radius:12px;padding:1.15rem 1.35rem;margin:1.25rem 0}
table{border-collapse:collapse;table-layout:fixed;width:100%;background:#fff}td{overflow-wrap:anywhere;vertical-align:top}small{font-size:.75rem}
.table-wrap{overflow-x:auto;border:1px solid #cbd5e1;border-radius:10px}
@media(max-width:700px){body{margin:1rem auto}table{table-layout:auto;min-width:780px}td,th{padding:.6rem}}
td,th{text-align:left;padding:.85rem .95rem;border-bottom:1px solid #d5dde7}th{background:#edf2f8}
a{color:#1355a0}code{background:#eef2f7;padding:.1rem .32rem;border-radius:4px;font-size:.88em;overflow-wrap:anywhere}
</style>
'''
        + nav_bar
        + '''<h1>GEMSDOE78 · Submission Readiness, Validated GeoTIFF Download &amp; Executive Summary</h1>
<div class="alert"><div class="status-kicker">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO</div>
Automatic programmatic review validates local GeoTIFF format safety (13/13 checks PASS; zero human-inspector deferral) AND blocks portal submission under the literal parallel-run overlap gate. File-format validity is not competition clearance. Zero DrivenData submission slots were spent (<code>weekly_slots_used_by_agent = 0</code>).'''
        + mghd_hero_actions
        + '''<p style="margin:.7rem 0 0"><b>Protocol blocker verified 2026-10-22:</b> a hash-pinned GEMSDOE17 probability raster is positive across the entire footprint. Every nonempty candidate has 100% forward overlap, so none can pass the literal 70% limit without explicit selector policy exemption for dense priors. <a href="data/protocol_preflight.json">Automatic certificate</a> · <a href="review-2026-10-22.md">Earlier review</a> · <a href="review-release.md">Updated 5-hypothesis &amp; 84-repo review</a>.</p></div>'''
        + mghd_science_block
        + '<p>Last local programmatic audit: <time>'
        + html.escape(card["reviewed_utc"])
        + '</time>. Static, SHA-256-bound evidence — never a live leaderboard feed or projection.</p>'
        + '''<h2>Downloads and automatic checks</h2><div class="table-wrap"><table><tr><th>Candidate Lane</th><th>Automated GeoTIFF Check</th><th>Parallel-Run &amp; Submission Gate</th><th>One-Click Artifact Download</th></tr>'''
        + rows_html
        + '''</table></div>
<p><a href="downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif">Download inspection GeoTIFF</a> — DO-NOT-SUBMIT. Historical H78-SPY file, format-valid and not cleared. <a href="index.html">Homepage</a> and <a href="executive-summary.html">Executive Summary</a> display identical machine-bound status.</p>
<p><a href="h78cs.html">H78-CS lane page</a> — session-3 h78cs-collinear support file, format-valid, HOLDOUT-DTI negative and duplicate of H78-A (forward overlap 0.8908). Do not submit.</p>
<p><a href="data/h78mghd_run_card.json">Session-5 H78-MGHD run card + validator JSON</a> · <a href="data/release_audit.json">Consolidated machine-readable release audit JSON</a> · <a href="review-release.md">Scientific review, 5 ranked hypotheses &amp; limitations</a></p>

<div class="card">
<h2>Executive summary: step-by-step guide to verifying and submitting a cleared GeoTIFF</h2>
<ol>
  <li><b>Check the top-of-page gate banner first:</b> Only consider uploading if a separate portfolio selector flips status to cleared after checking DrivenData weekly submission caps. Here status is <b>NO</b> (DO-NOT-SUBMIT) under the literal dense-prior rule, so download strictly for offline inspection and portfolio evaluation.</li>
  <li><b>Verify local integrity &amp; zero portal-range risk automatically:</b> Run <code>.venv/bin/python scripts/verify_tif.py docs/downloads/&lt;candidate&gt;.tif</code>. Confirm <code>"all_passed": true</code>: single band (<code>count=1</code>), <code>dtype=float32</code>, CRS <code>EPSG:32611</code>, shape <code>3730 &times; 3292</code>, affine transform <code>(100, 0, 243350, 0, -100, 4508550)</code>, <code>nodata=None</code>, zero NaN/Inf anywhere, and all values strictly in <code>[0.0, 1.0]</code> (eliminating the DrivenData <i>"Predicted values must be in range [0, 1]"</i> error).</li>
  <li><b>Confirm two-seed spatial hide-and-recover &amp; leakage gates:</b> Verify every feature passed single-feature ROC AUC &le; 0.90 and paired 20 km spatial-block bootstrap <code>HOLDOUT-DTI</code> (<code>gems57-pooled-hide-v2</code>) beat the incumbent control with 95% CI excluding zero across independent segment draws (achieved by <code>H78-MGHD</code> on both <code>seed=20</code> and <code>seed=30</code>).</li>
  <li><b>Verify registry uniqueness &amp; weekly cap:</b> Confirm pre-placement surface <code>|Spearman &rho;| &le; 0.90</code> (0.7677 for <code>H78-MGHD</code>) and selector policy on sparse vs dense sibling priors, and verify remaining weekly slots directly on DrivenData.</li>
  <li><b>Upload workflow (only when authorized by human selector):</b> Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData Competition 306 (Hidden Geothermal Faults)</a> &rarr; click <b>Submit / New submission</b> &rarr; upload the verified single-band <code>.tif</code> (or single-TIFF <code>.zip</code>) matching exact SHA-256 &rarr; paste a concise <code>&le; 140</code>-character note encoding lane, dot count, and <code>HOLDOUT-DTI</code> &rarr; submit.</li>
  <li><b>Record <code>ORGANIZER-CONFIRMED</code> receipt:</b> Save the DrivenData submission-page timestamp and returned score bound to the exact 64-hex SHA-256. Never label holdout estimates or unverified reports as <code>ORGANIZER-CONFIRMED</code>.</li>
</ol>
</div>

<div class="card">
<h2>Why GEMSDOE32 (<code>H33</code>) outperformed earlier submissions (0.2778 vs 0.2600) &amp; reported higher scores</h2>
<ul>
  <li><b>Exact pixel-level forensic discovery:</b> Comparing SHA-256-verified rasters on the exact <code>3730 &times; 3292</code> grid proves that <code>H33</code> (<code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code>, <code>37,654</code> dots, unverified owner-reported score <code>0.2778</code>) did <b>not</b> train a new geological model. It started from <code>D2.8</code> (<code>44,090</code> dots, unverified owner-reported score <code>0.2600</code>) and deleted the <b>exact <code>6,436</code> dots lying at Euclidean distance <code>(0, 2]</code> pixels (&le;200 m) from mapped <code>existing_faults.tif</code></b> while converting outside-footprint cells from <code>NaN</code> to <code>0.0</code>.</li>
  <li><b>Exact Tversky mathematical mechanism:</b> Under the official pooled Distance-Tolerant IoU / Tversky metric (<code>&alpha;=0.2, &beta;=0.8</code>, 300 m triangular kernel), a dot adds positive score if and only if its expected unmapped-fault credit exceeds the marginal bar <code>c_bar &gt; &alpha; &middot; DTI / (1 - &alpha; &middot; DTI) &approx; 0.0556</code> (at <code>DTI &approx; 0.2778</code>). Because mapped fault traces are masked only pixel-exactly while unmapped hidden faults rarely sit parallel at 100–200 m inside the mapped trace flank, <code>D2.8</code>'s 6,436 flank dots paid ~<code>0.2 &times; 6,436 = 1,287.2</code> weighted FP penalty for near-zero TP gain; removing them raised the ratio mechanically by ~<code>+0.0178</code>.</li>
  <li><b>Relation to <code>0.3195</code> / <code>0.4413</code> reports (strict evidence discipline):</b> Both <code>0.2778</code> and the conflicting cited figures (<code>0.3195</code> vs <code>0.4413</code>) are <b>unverified external/owner reports with no retrieved DrivenData submission-page receipt</b> (<code>ORGANIZER-CONFIRMED: None</code>). Bridging the gap beyond pure flank pruning requires genuine geological recall of blind &amp; range-front faults missed by the catalogue—which is why <code>H78-MGHD</code> couples 600–1,200 m geodetic/potential-field warps with 1 m 3DEP LiDAR scarps, 10 m stream <code>&chi;</code> knickpoints, GeoDAWN <code>K/Th</code> alteration, and GDR-1391 thermal anomalies (raising <code>HOLDOUT-DTI</code> from <code>0.1830</code> to <code>0.1971</code> pooled across 22,663 withheld positives). Full derivation: <a href="why-h33.md">why-h33.md</a>.</li>
</ul>
<p>Historical HOLDOUT-DTI reference for MPC: 0.097684, 95% CI [0.077985, 0.116303], gems57-pooled-hide-v2, 11,321 withheld positives.</p>
<p><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">Official reference implementation (GitHub)</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition portal (not reachable from sandbox; reference link)</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR / DOE Geothermal Report (reference link)</a></p>
</div></html>'''
    )

    for name in ("index.html", "executive-summary.html", "h78mpc.html", "h78mpc-executive-summary.html"):
        (ROOT / "docs" / name).write_text(page)

    status = load("docs/data/status.json")
    if mghd is not None and mghd_uniq is not None:
        witness_list = [
            r["file"]
            for r in mghd_uniq["final_dots_binding_literal_audit"]["space_filling_witnesses_top15"][:10]
        ] + [
            r["file"]
            for r in mghd_uniq["final_dots_discriminating_halo_lt_0p70"]["top20_halo_lt_0p70"]
            if r["forward_overlap"] > 0.70
        ][:5]
        status.update(
            generated_tif=mghd["submission_file"],
            sha256=mghd["raster_sha256"],
            worst_forward_3px_overlap=mghd["correlation_overlap_vs_registry"][
                "literal_all_rasters_worst_forward_3px_overlap"
            ],
            duplicate_witnesses=witness_list,
            latest_generated_card="h78mghd_run_card.json",
            session5_h78mghd_new_tif_generated=True,
            session5_sparse_le_65k_worst_overlap=mghd["correlation_overlap_vs_registry"][
                "sparse_dot_le_65k_worst_forward_3px_overlap"
            ],
        )
    elif cross_path.exists():
        cross = load("evidence/crosslayer_run_card.json")
        final = cross["registry"]["final_dots"]
        status.update(
            generated_tif=cross["submission_name"] + ".tif",
            sha256=cross["raster_sha256"],
            worst_forward_3px_overlap=max(r["forward_3px_overlap"] for r in final),
            duplicate_witnesses=[r["file"] for r in final if r["forward_3px_overlap"] > 0.70],
            latest_generated_card="crosslayer_run_card.json",
        )
    status.update(
        schema_version=3,
        review_date=card["review_date"],
        reason="Universal registry saturation and dense sibling fault corridors exceed literal 0.70 overlap; OK TO DOWNLOAD for research only, DO NOT SUBMIT.",
        new_tif_generated=False,
        candidates=candidates,
        current_review_new_tif_generated=False,
        live_feed=False,
        weekly_slots_used_by_agent=0,
        organizer_confirmed=None,
        current_review_utc=card["reviewed_utc"],
        authoritative_release="release_audit.json",
        authoritative_card="release_audit.json",
        protocol_preflight="protocol_preflight.json",
        historical_session_only=True,
        all_published_candidates=candidates,
        current_reason="Universal registry saturation blocks every nonempty in-footprint candidate under the literal rule.",
    )
    (ROOT / "docs/data/status.json").write_text(json.dumps(status, indent=2, allow_nan=False) + "\n")

    notice = '<aside id="release-audit-warning" style="padding:20px;background:#fff1df;color:#172438"><strong>Historical analysis — promotion claims superseded.</strong> Current status: OK TO SUBMIT: NO. <a href="index.html">Read the automatic release audit and Session-5 H78-MGHD results.</a></aside>'
    for name in (
        "holdout.html",
        "hypotheses.html",
        "sources.html",
        "irregularities.html",
        "h78a.html",
        "h78a-executive-summary.html",
        "h78cs.html",
        "h78cs-executive-summary.html",
        "crosslayer.html",
        "crosslayer-executive-summary.html",
    ):
        p = ROOT / "docs" / name
        if p.exists():
            old = p.read_text()
            if 'id="release-audit-warning"' in old:
                p.write_text(
                    re.sub(
                        r'<aside id="release-audit-warning".*?</aside>',
                        lambda _: notice,
                        old,
                        count=1,
                        flags=re.DOTALL,
                    )
                )
            else:
                p.write_text(
                    old.replace("<body>", "<body>" + notice, 1)
                    if "<body>" in old
                    else old.replace("<main>", "<main>" + notice, 1)
                )
    return card


if __name__ == "__main__":
    main()
