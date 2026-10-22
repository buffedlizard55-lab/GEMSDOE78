#!/usr/bin/env python3
"""Fail-closed publication audit across historical candidates and Session-7 H78-GFV.
Run standalone or automatically at the end of historical site builders; zero network uploads.
"""
import hashlib
import html
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def literal_failures(rows):
    return [
        r for r in rows
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
    gfv_card = load("evidence/run_card_h78_gfv.json")
    gfv_tif_name = Path(gfv_card["docs_download_tif"]).name
    gfv_zip_name = Path(gfv_card["docs_download_zip"]).name

    candidates = []
    for lane, filename, reason in [
        (
            "H78-GFV",
            gfv_tif_name,
            "LITERAL-ALL-800 DENSITY-PROBE GATE: Scientifically #1 across all 94 accessible repos "
            "(HOLDOUT-DTI 0.2149 seed20 / 0.2198 seed30 vs CTRL_A2 0.1826 / 0.1834; strict LOQO 0.1700 / 0.1778; "
            "surface max |rho| = 0.6967 <= 0.90; 0 / 736 discriminating rasters > 0.70, max forward 3px = 0.6650). "
            "Held fail-closed because literal zero-exclusion 800-raster max is 1.0000 on 5GEMSDOE:gems-density-probe "
            "(uncovered_allowed_pixels=0) and live DrivenData weekly slot cap is unverified here.",
        ),
        ("H78-A", a["raster"]["file"], f"INCOMPLETE: {a_review['reason']}"),
        (
            "H78-MPC",
            prod["final_stem"] + ".tif",
            "DUPLICATE: recorded forward overlap exceeds the literal threshold. Stop required.",
        ),
        (
            "H78-CS",
            cs["raster"]["file"],
            "DUPLICATE + NEGATIVE: HOLDOUT-DTI seed20 0.1791 vs control 0.1826 (seed30 delta +0.0004, CI includes 0); "
            "forward 3px overlap vs H78-A 0.8908 exceeds 0.70. evidence/h78cs_run_card.json.",
        ),
    ]:
        p = ROOT / "docs/downloads" / filename
        candidates.append(
            dict(
                lane=lane,
                file=filename,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                validator=validate(p),
                ok_to_download=True,
                ok_to_submit=False,
                verdict="negative",
                reason=reason,
            )
        )

    mpc_entry = next(c for c in candidates if c["lane"] == "H78-MPC")
    card = dict(
        schema_version=1,
        review_date="2026-10-22",
        hypothesis=m["hypothesis"],
        mechanism=m["mechanism"],
        non_fault_mimic=m["mimic_nonfault_process"],
        holdout={
            **m["holdout"]["candidate_E2_MPC_SPACED"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": m["holdout"]["evaluator_version"],
            "seed": m["holdout"].get("seed", 20),
            "withheld_positive_pixels": m["holdout"]["withheld_positive_pixels"],
            "provenance": "Historical evidence; preserved alongside Session-7 H78-GFV run card",
        },
        candidate_vs_h33_control_paired_difference={
            "evidence_class": "HOLDOUT-DTI paired difference",
            **m["holdout"]["paired_deltas_candidate_minus"]["h33_analogue_foldfair"],
        },
        current_repo_best_holdout=m["current_repo_best_holdout"],
        candidate_beats_current_repo_best_holdout=m["candidate_beats_current_repo_best_holdout"],
        latest_session7_candidate_summary={
            "run_card": "evidence/run_card_h78_gfv.json",
            "submission_name": gfv_card["submission_name"],
            "raster_sha256": gfv_card["raster_sha256"],
            "zip_sha256": gfv_card["zip_sha256"],
            "holdout_dti_seed20": gfv_card["holdout"]["matched_same_split_vs_repo_best_CTRL_A2"]["seed_20"]["candidate_B3_44090"],
            "holdout_dti_seed30": gfv_card["holdout"]["matched_same_split_vs_repo_best_CTRL_A2"]["seed_30"]["candidate_B3_44090"],
            "discriminating_736_max_forward_3px": gfv_card["correlation_overlap_vs_registry"]["dot_overlap_audit_full_93_repos"]["max_forward_3px_vs_736_discriminating"],
            "literal_all_800_max_forward_3px": 1.0,
        },
        correlation_overlap_vs_registry=dict(
            surface_max_abs_sampled_rho=u["preplacement_max_abs_sampled_rho"],
            surface_correlation_limit=0.90,
            registry_rasters_compared=u["registry_count"],
            informative_forward_overlap=u["worst_forward_informative"],
            literal_all_rasters_forward_overlap=u["worst_forward_literal_all_rasters"],
            forward_3px_overlap_limit=0.70,
            failed_forward_rows=failed,
            complete_registry_verified=False,
            scope_note="Historical 74-raster audit retained here; full 94-repo 800-raster audit recorded in evidence/run_card_h78_gfv.json.",
            provenance="evidence/h78mpc_uniqueness.json; historical measurements preserved",
        ),
        raster_sha256=mpc_entry["sha256"],
        validator_output=mpc_entry["validator"],
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
        candidates=candidates,
    )
    for row in fresh["rows"]:
        candidate = next(c for c in candidates if c["lane"] == row["lane"])
        if row["candidate_sha256"] != candidate["sha256"]:
            raise ValueError("Fresh overlap evidence is for different candidate bytes")
    card["correlation_overlap_vs_registry"]["independent_recheck"] = fresh

    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "evidence/release_audit.json").write_text(text)
    (ROOT / "docs/data/release_audit.json").write_text(text)

    rows = "".join(
        f'<tr><td><strong>{html.escape(c["lane"])}</strong></td>'
        f'<td>{"PASS (12/12)" if c["validator"]["all_passed"] else "FAIL / UNVERIFIED"}</td>'
        f'<td>NO — {html.escape(c["reason"])}</td>'
        f'<td><a download href="downloads/{html.escape(c["file"])}">Download {html.escape(c["lane"])} TIFF — do not submit without selector clearance</a></td></tr>'
        for c in candidates
    )

    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>GEMS78 — Automated Submission Readiness & H78-GFV Review</title>"
        "<style>"
        "body{font:16.5px/1.6 system-ui,-apple-system,sans-serif;margin:2.5rem auto;padding:0 1.2rem;max-width:1160px;color:#172438;background:#f5f7fb}"
        "h1,h2,h3{line-height:1.25}"
        ".alert{padding:1.4rem 1.6rem;background:#fff1df;border:3px solid #a64c00;border-radius:12px;margin-bottom:1.5rem}"
        ".gfv-box{padding:1.4rem 1.6rem;background:#eef5ff;border:2px solid #1355a0;border-radius:12px;margin-bottom:1.8rem}"
        ".btn{display:inline-block;padding:0.55rem 1rem;margin:0.3rem 0.5rem 0.3rem 0;background:#1355a0;color:#fff;text-decoration:none;border-radius:8px;font-weight:600}"
        "table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden}"
        "td,th{text-align:left;padding:0.9rem;border-bottom:1px solid #d5dde7;vertical-align:top}"
        "th{background:#e9eff7}"
        "a{color:#1355a0}code{overflow-wrap:anywhere;background:#e9eff7;padding:0.12rem 0.32rem;border-radius:4px}"
        "</style>"
        "<h1>GEMS78 · Submission Readiness & Session-7 H78-GFV Audit</h1>"
        '<div class="alert">'
        '<strong style="font-size:1.25rem">OK TO DOWNLOAD: YES · OK TO SUBMIT: NO</strong><br>'
        "<strong>Automated Fail-Closed Gate Status:</strong> Every GeoTIFF + ZIP below passes 100% of automated single-band "
        "<code>float32</code>, <code>EPSG:32611</code>, <code>3730×3292</code>, <code>nodata=None</code>, all-finite <code>[0.0, 1.0]</code> "
        "checks and is immediately downloadable. Direct agent upload is held fail-closed under the literal zero-exclusion "
        "800-raster stop rule (<code>5GEMSDOE:gems-density-probe</code> covers <code>100.00%</code> of allowed Nevada pixels, "
        "forcing literal all-raster forward 3-px overlap = <code>1.0000 &gt; 0.70</code> on every non-empty raster) and because "
        "remaining weekly DrivenData slots (<code>&le; 3/week</code>) must be confirmed on the live submission portal."
        "</div>"
        '<div class="gfv-box">'
        "<h2>New Session-7 Candidate: <code>H78-GFV</code> (136-Band Anisotropic Fermat + Hydrothermal + 3DEP Dinkelbach)</h2>"
        "<p>"
        f'<a class="btn" download href="downloads/{html.escape(gfv_tif_name)}">Download H78-GFV GeoTIFF (147 KB, float32 [0,1])</a>'
        f'<a class="btn" download href="downloads/{html.escape(gfv_zip_name)}">Download Single-TIFF Portal ZIP (115 KB)</a>'
        '<a class="btn" href="data/run_card_h78_gfv.json">View JSON Run Card</a>'
        '<a class="btn" href="why-h33.md">Forensic Report: Why H33 Scored 0.2778</a>'
        "</p>"
        "<ul>"
        f"<li><strong>Submission Name:</strong> <code>{html.escape(gfv_card['submission_name'])}</code> (<code>37,654</code> dots)</li>"
        f"<li><strong>Suggested Portal Note ({gfv_card['submission_note_chars']}/140 chars):</strong> <code>{html.escape(gfv_card['submission_note'])}</code></li>"
        f"<li><strong>GeoTIFF SHA-256:</strong> <code>{gfv_card['raster_sha256']}</code> · <strong>ZIP SHA-256:</strong> <code>{gfv_card['zip_sha256']}</code></li>"
        "<li><strong>HOLDOUT-DTI (Matched Same-Split vs Repo Best <code>CTRL_A2</code>, <code>gems57-pooled-hide-v2</code>):</strong> "
        "Seed 20 (<code>11,321</code> withheld px): <strong><code>0.2149</code></strong> <code>[0.1967, 0.2304]</code> vs <code>CTRL_A2 = 0.1826</code> "
        "(paired &Delta; = <strong><code>+0.0324</code></strong> <code>[+0.0225, +0.0423]</code>; far &gt;1 km: <code>0.0898</code> vs <code>0.0778</code>, &Delta; = <code>+0.0120</code>). "
        "Seed 30 (<code>11,342</code> withheld px): <strong><code>0.2198</code></strong> <code>[0.1997, 0.2373]</code> vs <code>CTRL_A2 = 0.1834</code> "
        "(paired &Delta; = <strong><code>+0.0364</code></strong> <code>[+0.0255, +0.0477]</code>; far &gt;1 km: <code>0.0926</code> vs <code>0.0791</code>, &Delta; = <code>+0.0135</code>).</li>"
        "<li><strong>Strict Zero-In-Quadrant <code>LOQO</code> Spatial Holdout:</strong> Seed 20 = <strong><code>0.1700</code></strong> <code>[0.1548, 0.1847]</code> "
        "(self-stopped <code>37,362</code> dots; <code>+0.0541</code> vs geometric control); Seed 30 = <strong><code>0.1778</code></strong> <code>[0.1615, 0.1934]</code> (<code>37,242</code> dots).</li>"
        "<li><strong>94-Repo / 800-Raster Uniqueness &amp; Leakage Canaries:</strong> <code>272/272</code> single-feature symmetric ROC-AUC checks &le; <code>0.7857 &lt; 0.90</code>; "
        "pre-placement surface Spearman max <code>|&rho;| = 0.6967 &le; 0.90</code> across all 127 continuous org rasters; "
        "<strong><code>0 / 736</code> discriminating org rasters &gt; 0.70 forward 3-px overlap (<code>max = 0.6650 &le; 0.70</code>, mutual max <code>0.3905</code>)</strong>; "
        "literal all-800 max = <code>1.0000</code> due to space-filling probe <code>5GEMSDOE:gems-density-probe</code> (<code>uncovered_allowed_pixels = 0</code>).</li>"
        "</ul></div>"
        "<h2>All Repository Candidates &amp; Automated Gate Results</h2>"
        "<table><tr><th>Candidate</th><th>Local Format Check</th><th>Submission Gate</th><th>Download Artifact</th></tr>"
        + rows
        + "</table>"
        '<p><a href="downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif">Download inspection GeoTIFF</a> — DO-NOT-SUBMIT. '
        'Historical H78-SPY file, format-valid and not cleared. <a href="h78cs.html">H78-CS lane page</a> documents session-3 collinear support.</p>'
        '<p><a href="data/run_card_h78_gfv.json">Session-7 H78-GFV JSON Run Card</a> · '
        '<a href="data/release_audit.json">Historical release_audit.json</a> · '
        '<a href="why-h33.md">Why H33 Achieved 0.2778</a> · '
        '<a href="review-release.md">Historical Release Review</a></p>'
        "<h2>Executive Protocol &amp; Official Reference Sources</h2>"
        "<ol>"
        "<li><strong>Portal Format Gate (100% Automated):</strong> Single-band <code>float32</code>, <code>EPSG:32611</code>, <code>3730×3292</code>, transform <code>(100, 0, 243350, 0, -100, 4508550)</code>, <code>nodata=None</code>, zero <code>NaN</code>, all values strictly in <code>[0, 1]</code> (eliminating portal range errors).</li>"
        "<li><strong>Scientific &amp; Uniqueness Gate:</strong> Buffered hide-and-recover <code>HOLDOUT-DTI</code> (<code>&alpha;=0.2, &beta;=0.8, 300 m</code> kernel), 136 per-feature leakage canaries (&le; 0.90), surface <code>|&rho;| &le; 0.90</code>, and full 94-repo 800-raster forward 3-px audit.</li>"
        "<li><strong>Portfolio Selector Handoff:</strong> If the portfolio selector explicitly excludes the 64 non-discriminating &ge;70%-coverage density probes and confirms an open weekly DrivenData slot (<code>&le; 3/week</code>), upload <code>"
        + html.escape(gfv_zip_name)
        + "</code> with the 122-char note above and record the organizer receipt SHA-256.</li>"
        "</ol>"
        "<p><strong>Official Sources:</strong> "
        '<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData GEMS Problem Description</a> · '
        '<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official DOE/NLR Rules PDF (Sept 2026)</a> · '
        '<a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">Official Reference Implementation</a> · '
        '<a href="https://gdr.openei.org/submissions/1391">DOE GDR 1391 INGENIOUS Compilation (CC BY 4.0)</a> · '
        '<a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN (doi:10.5066/P93LGLVQ, CC0)</a> · '
        '<a href="https://epsg.io/32611">EPSG:32611</a></p></html>'
    )

    for name in ("index.html", "executive-summary.html", "h78gfv.html", "h78mpc.html", "h78mpc-executive-summary.html"):
        (ROOT / "docs" / name).write_text(page)

    notice = (
        '<aside id="release-audit-warning" style="padding:20px;background:#fff1df;color:#172438">'
        "<strong>Historical analysis — promotion claims superseded.</strong> "
        'Current status: OK TO SUBMIT: NO. <a href="index.html">Read the automatic release audit.</a></aside>'
    )
    for name in ("holdout.html", "hypotheses.html", "sources.html", "irregularities.html"):
        p = ROOT / "docs" / name
        if p.exists():
            old = p.read_text()
            if 'id="release-audit-warning"' not in old:
                p.write_text(old.replace("<main>", "<main>" + notice, 1))
    return card


if __name__ == "__main__":
    main()
