#!/usr/bin/env python3
"""Experiment 3 of lane H78-STEP: production build, uniqueness audit, validator, run card.

Retrains CAND_STEP (raw19 + 54 paired-flank STEP features) on the FULL
catalogue (strike field from the full catalogue; deployment-faithful), emits
44,090 B3 dots, audits uniqueness against the 9 preregistered comparators
(surface before placement AND final dots), writes the GeoTIFF through the
UNMODIFIED shared submission_writer, re-reads it independently plus via
scripts/verify_tif.py, evaluates the preregistered gate from the holdout
evidence (fail-closed arithmetic) and writes evidence/h78step_run_card.json.

Experiment 1 already failed the holdout gate, so the verdict is negative
before this build starts; the file is therefore named *-DO-NOT-SUBMIT and
published for inspection/reproducibility only. A negative result is a
deliverable. No competition slot is touched.
"""
from __future__ import annotations

import gc
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import grid as G, submission_writer as SW, uniqueness as U, validate as V  # noqa: E402
from gems78 import data as D  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78 import step as S  # noqa: E402
from run_holdout_step import HGB, log  # noqa: E402

BUDGET, FLANK = 44_090, 3.0
RHO_LIMIT, OVERLAP_LIMIT = 0.90, 0.70
REGISTRY = {
    "H19-5 solid (121131 px; owner-report 0.1922)": "data/registry/h19_5_solid_nan.tif",
    "D2.8 dots (44090; owner-report 0.2600)": "data/registry/d28_44090_nan.tif",
    "H33-2-B2 dots (37654; owner-report 0.2778)": "data/registry/h33_2_b2_37654_zeros.tif",
    "GEMS70-P5-54000 (owner-report 0.2478 family; blocked H78-MPC)": "data/registry/gems70_p5_54000.tif",
    "H78-A primary shipped (44090)":
        "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif",
    "H78-A altB2 shipped (44090)":
        "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223133Z-ec00c053-altB2-zeros.tif",
    "H78-MPC shipped (37654)":
        "docs/downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif",
    "H78-CS shipped (44090)":
        "docs/downloads/gems78-h78cs-collinear-44090dots-20261022T002927Z-0ca477e0-zeros.tif",
    "H78-SPY shipped (44090)":
        "docs/downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif",
}


def clean(x):
    """JSON-safe: NaN -> None, numpy -> python."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def read1(p):
    with rasterio.open(p) as ds:
        return ds.read(1)


def main():
    t_start = time.time()
    D.verify_inputs()
    hold = json.loads((ROOT / "evidence/h78step_holdout_seed20.json").read_text())
    diag = json.loads((ROOT / "evidence/h78step_append_diag_seed20.json").read_text())
    prereg = json.loads((ROOT / "registry/preregistration_h78step.json").read_text())

    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue

    feats_path, fmeta = P.build_feature_matrix("full", fp, cat)
    phi = np.load(D.PROC / "phi_full.npy")
    step_path, stepmeta = S.build_step_matrix("full", fp, phi)
    del phi
    gc.collect()
    log("full features ready", fmeta["seconds"], stepmeta["seconds"])

    base_mm = np.load(feats_path, mmap_mode="r")
    step_mm = np.load(step_path, mmap_mode="r")
    raw_cols = P.arm_columns("A0_std19")
    pos, negs = P.training_sample(fp, cat, 450_000, seed=20)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    X = np.concatenate([np.asarray(base_mm[rows[order]][:, raw_cols], np.float32),
                        np.asarray(step_mm[rows[order]], np.float32)], axis=1)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    assert X.shape[1] == 73 and np.isfinite(X).all()
    clf = HistGradientBoostingClassifier(**HGB)
    t0 = time.time()
    clf.fit(X, y)
    fit_info = dict(arm="CAND_STEP (full catalogue)", n_pos=int(rows_pos.size),
                    n_neg=int(rows_neg.size), n_features=int(X.shape[1]), params=HGB,
                    fit_seconds=round(time.time() - t0, 1))
    del X, y
    gc.collect()
    log("fit", fit_info)

    n = base_mm.shape[0]
    out = np.zeros(n, np.float32)
    for lo in range(0, n, 600_000):
        hi = min(n, lo + 600_000)
        Xc = np.concatenate([np.asarray(base_mm[lo:hi][:, raw_cols], np.float32),
                             np.asarray(step_mm[lo:hi], np.float32)], axis=1)
        out[lo:hi] = clf.predict_proba(Xc)[:, 1].astype(np.float32)
        del Xc
    del clf
    score = np.zeros(fp.shape, np.float32)
    score[fp] = out
    del out
    assert np.isfinite(score).all() and 0.0 <= score.min() and score.max() <= 1.0
    np.save(D.PROC / "score_full_CAND_STEP.npy", score)

    # --- uniqueness on the SURFACE before placement ---
    surf = {}
    for label, rel in REGISTRY.items():
        a = read1(ROOT / rel)
        a = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
        surf[label] = clean(U.surface_rho(score, a, fp))
    surface_max_rho = max(abs(v["spearman_full_footprint"]) for v in surf.values())
    log("surface rho max", surface_max_rho)

    # --- emission (preregistered primary; B5 rule not triggered in experiment 1) ---
    allowed = fp & ~E.flank_mask(cat, FLANK)
    rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=60_000, pool=1_500_000)
    dots = E.prefix(rank, BUDGET)
    n_dots = int(dots.sum())
    assert n_dots == BUDGET, n_dots
    pred = dots.astype(np.float32)
    del rank

    dot_aud = {}
    for label, rel in REGISTRY.items():
        a = read1(ROOT / rel)
        af = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
        dot_aud[label] = dict(
            fraction_of_my_dots_within_3px_of_theirs=float(U.dot_overlap(pred, a, 3.0)),
            fraction_of_their_dots_within_3px_of_mine=float(U.dot_overlap(a, pred, 3.0)),
            spearman_full_footprint=clean(U.surface_rho(pred, af, fp))["spearman_full_footprint"])
    dots_max_overlap = max(v["fraction_of_my_dots_within_3px_of_theirs"] for v in dot_aud.values())
    worst_overlap_label = max(dot_aud, key=lambda k: dot_aud[k]["fraction_of_my_dots_within_3px_of_theirs"])
    dots_max_rho = max(abs(v["spearman_full_footprint"]) for v in dot_aud.values()
                       if v["spearman_full_footprint"] is not None)
    unique_ok = bool(surface_max_rho <= RHO_LIMIT and dots_max_rho <= RHO_LIMIT
                     and dots_max_overlap <= OVERLAP_LIMIT)
    log("dots max forward overlap", dots_max_overlap, "vs", worst_overlap_label, "unique_ok(scoped)", unique_ok)
    fwd_h78a = dot_aud["H78-A primary shipped (44090)"]["fraction_of_my_dots_within_3px_of_theirs"]

    d_cat = ndi.distance_transform_edt(~np.asarray(cat, bool))
    dd = d_cat[dots]
    dist_stats = dict(n=n_dots, min=float(dd.min()),
                      p10=float(np.percentile(dd, 10)), p25=float(np.percentile(dd, 25)),
                      p50=float(np.percentile(dd, 50)), p75=float(np.percentile(dd, 75)),
                      p90=float(np.percentile(dd, 90)),
                      frac_le_5px=float((dd <= 5).mean()), frac_le_10px=float((dd <= 10).mean()),
                      frac_gt_30px=float((dd > 30).mean()),
                      note="diagnostic only; H33 shipped median is 19.6 px (evidence/h78_dot_distance_to_catalogue.json)")
    del d_cat, dd

    # --- write through the shared fail-closed writer ---
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
    name = f"gems78-h78step-flankstep-{n_dots}dots-{stamp}-{digest8}-DO-NOT-SUBMIT"
    note = (f"NOT OK TO SUBMIT negative: H78-STEP flank-step HOLDOUT-DTI 0.1662 vs CTRL 0.1826 s20; "
            f"inspection only")[:140]
    out_dir = ROOT / "docs" / "downloads"
    tif = out_dir / f"{name}.tif"
    receipt = SW.write_submission(tif, pred, ROOT / "data/bridge/sample_submission.tif", fp,
                                  note=note, name=name, catalogue=cat,
                                  metadata=dict(lane="H78-STEP", arm="CAND_STEP raw19+STEP54",
                                                flank_px=FLANK, budget=BUDGET, verdict="negative"))
    log("wrote", tif.name, receipt["sha256"])

    # --- independent re-read + verify_tif.py ---
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        rr = dict(count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs), shape=[ds.height, ds.width],
                  transform=list(ds.transform)[:6], nodata=ds.nodata)
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ref:
        rr["matches_sample"] = dict(crs=str(ref.crs) == rr["crs"], shape=[ref.height, ref.width] == rr["shape"],
                                    transform=list(ref.transform)[:6] == rr["transform"])
    rr.update(all_finite=bool(np.isfinite(a).all()), nan_inside_footprint=int(np.isnan(a[fp]).sum()),
              min=float(a.min()), max=float(a.max()), values_in_0_1=bool(a.min() >= 0 and a.max() <= 1),
              positive_pixels=int((a > 0).sum()), positives_on_catalogue=int((a[cat] > 0).sum()),
              positives_outside_footprint=int((a[~fp] > 0).sum()),
              distinct_values=[float(v) for v in np.unique(a)],
              sha256=V.sha256(tif), bytes=tif.stat().st_size)
    validator_ok = all([rr["count"] == 1, rr["dtype"] == "float32", all(rr["matches_sample"].values()),
                        rr["nodata"] is None, rr["all_finite"], rr["nan_inside_footprint"] == 0,
                        rr["values_in_0_1"], rr["positives_on_catalogue"] == 0,
                        rr["positives_outside_footprint"] == 0, rr["positive_pixels"] == n_dots,
                        set(rr["distinct_values"]) <= {0.0, 1.0}])
    vt = subprocess.run([sys.executable, str(ROOT / "scripts/verify_tif.py"), str(tif)],
                        capture_output=True, text=True)
    try:
        verify_report = json.loads(vt.stdout)
    except json.JSONDecodeError:
        verify_report = dict(all_passed=False, error=vt.stderr[-2000:])
    verify_ok = bool(vt.returncode == 0 and verify_report.get("all_passed"))
    log("validator_ok", validator_ok, "verify_tif_ok", verify_ok)
    (ROOT / "evidence" / f"verify_{name}.json").write_text(json.dumps(verify_report, indent=2) + "\n")

    # --- preregistered gate, fail-closed from evidence ---
    ps = hold["pooled_summary_B3_primary"]
    cand_key, ctrl_key = "CAND_STEP|B3|44090", "CTRL_A2|B3|44090"
    cand, ctrl = ps["scores"][cand_key], ps["scores"][ctrl_key]
    paired = ps["paired_differences"][ctrl_key]
    rho_holdout = hold["surface_rho_candidate_vs_ctrl"]["spearman_full_footprint"]
    gate = dict(
        cand_beats_ctrl_point=bool(cand["dti"] > ctrl["dti"]),
        cand_beats_repo_best_0p1826=bool(cand["dti"] > 0.1826),
        paired_delta_ci_lower_gt_0=bool(paired["ci95"][0] > 0),
        canary_clean=bool(len(hold["canary"]["flagged_over_0p90"]) == 0),
        surface_rho_vs_ctrl_le_0p90=bool(abs(rho_holdout) <= RHO_LIMIT),
        uniqueness_pass_scoped_9_comparators=unique_ok,
        validator_pass=bool(validator_ok and verify_ok),
        seed30_replication="not run (preregistration: only if seed-20 gates pass)",
    )
    promote = bool(gate["cand_beats_ctrl_point"] and gate["cand_beats_repo_best_0p1826"]
                   and gate["paired_delta_ci_lower_gt_0"] and gate["canary_clean"]
                   and gate["surface_rho_vs_ctrl_le_0p90"] and unique_ok and validator_ok and verify_ok)
    assert not promote, "gate unexpectedly passes but filename says DO-NOT-SUBMIT; stop and review"

    far = hold["pooled_summary_far_truth_gt10px_B3_primary"]
    b5 = hold["pooled_summary_B5_primary"]
    card = dict(
        lane="H78-STEP paired cross-strike flank step", repository="buffedlizard55-lab/GEMSDOE78",
        branch="arena/2a6915e5-gemsdoe78", built_utc=stamp,
        hypothesis=prereg["hypothesis"],
        mechanism="Strike-elongated flank patches at +-4/+-9 px across the visible-catalogue strike on "
                  "det_elev/rtp/iso_grav_anom/depth_to_base_surf/cond_surf/band6: signed step, |step|, "
                  "noise-normalised step, centre-line deviation, cross-scale sharpness (54 features) + raw 19 "
                  "bands, HGB; greedy dots >=2.8 px apart, <=3 px catalogue flank removed, 44,090 dots.",
        non_fault_mimic=prereg["non_fault_mimic"],
        holdout=dict(
            evidence_class="HOLDOUT-DTI", evaluator_version=ps["evaluator_version"],
            evaluator_sha256=hold["evaluator_sha256"], seed=20, hide_frac=0.20, buffer_px=3,
            withheld_positive_pixels=cand["withheld_positive_pixels"],
            candidate=dict(config=cand_key, dti=cand["dti"], ci95=cand["ci95"]),
            control=dict(config=ctrl_key, dti=ctrl["dti"], ci95=ctrl["ci95"]),
            a1_iso=dict(config="A1_ISO|B3|44090", **{k: ps["scores"]["A1_ISO|B3|44090"][k] for k in ("dti", "ci95")}),
            abl_steponly=dict(config="ABL_STEPONLY|B3|44090",
                              **{k: ps["scores"]["ABL_STEPONLY|B3|44090"][k] for k in ("dti", "ci95")}),
            paired_delta_cand_minus_ctrl=paired,
            paired_delta_cand_minus_a1=ps["paired_differences"]["A1_ISO|B3|44090"],
            all_budgets_B3={arm: {k: v["pooled_dti"] for k, v in hold["results"][arm]["configs"].items()}
                            for arm in hold["results"]},
            flank_B5_secondary=dict(candidate=b5["scores"]["CAND_STEP|B5|44090"],
                                    control=b5["scores"]["CTRL_A2|B5|44090"],
                                    paired=b5["paired_differences"]["CTRL_A2|B5|44090"],
                                    conclusion="B5 hurts both arms; production uses preregistered B3"),
            far_truth_gt10px=dict(n_truth=hold["far_truth_positives_gt10px"],
                                  scores={k: v["dti"] for k, v in far["scores"].items()},
                                  paired_vs_candidate=far["paired_differences"]),
            repo_best_before=hold["repo_holdout_best_before"],
            source_files=["evidence/h78step_holdout_seed20.json", "evidence/h78step_append_diag_seed20.json"],
        ),
        experiment2_append_diagnostic=dict(
            note="IR-78STEP-A1: diagnostic only, cannot promote. DIAG_A2STEP = CTRL 103 + STEP 54.",
            diag_dti=diag["pooled_summary_B3_primary"]["scores"]["DIAG_A2STEP|B3|44090"],
            paired_delta_diag_minus_ctrl=diag["pooled_summary_B3_primary"]["paired_differences"]["CTRL_A2|B3|44090"],
            surface_rho_diag_vs_ctrl=clean(diag["surface_rho_diag_vs_ctrl"]),
            forward_3px_overlap_holdout_dots=diag["forward_3px_overlap"],
            conclusion="Append adds nothing (delta CI includes 0, point negative) and duplicates the H78-A lane "
                       "(rho 0.929, forward overlap 0.842): STEP signal is largely redundant with steered "
                       "derivatives at holdout localisation precision."),
        canary=dict(threshold=0.90, max_single_feature_auc=hold["canary"]["max_auc"],
                    step_max_auc=hold["canary"]["step_max_auc"], step_features=hold["canary"]["step_features"],
                    flagged=hold["canary"]["flagged_over_0p90"], clean=gate["canary_clean"],
                    note="strongest single feature overall is step_det_elev_d4_abs (0.6027) - detection without localisation"),
        correlation_overlap_vs_registry=dict(
            rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT,
            comparators=list(REGISTRY.values()), n_comparators=len(REGISTRY),
            surface_before_placement=surf, surface_max_abs_rho=float(surface_max_rho),
            surface_rho_candidate_vs_ctrl_holdout=clean(hold["surface_rho_candidate_vs_ctrl"]),
            final_dots=dot_aud, dots_max_forward_overlap=float(dots_max_overlap),
            worst_forward_overlap_comparator=worst_overlap_label,
            forward_overlap_vs_h78a_primary=float(fwd_h78a),
            dots_max_abs_rho=float(dots_max_rho), passed_scoped=unique_ok,
            complete_registry_verified=False,
            scope_note="9 comparators: 3 restored registry rasters + GEMS70-P5 fetched this session + all 5 "
                       "previously shipped rasters of this repo. Not the organizer's complete registry."),
        production_fit=fit_info,
        dot_distance_to_catalogue_px=dist_stats,
        raster=dict(file=tif.name, sha256=rr["sha256"], bytes=rr["bytes"], zip=receipt["zip_file"],
                    zip_sha256=receipt["zip_sha256"], dots=n_dots, flank_px=FLANK, budget=BUDGET),
        raster_sha256=rr["sha256"],
        validator_output=dict(writer_receipt_checks=receipt["validator"]["checks"] if "checks" in receipt.get("validator", {}) else receipt["validator"],
                              independent_reread=rr, verify_tif=verify_report,
                              validator_ok=validator_ok, verify_tif_ok=verify_ok),
        preregistered_gate_evaluation=gate,
        submission_name=name, submission_note=note, note_chars=len(note),
        verdict="promote" if promote else "negative",
        ok_to_download=True, ok_to_submit=False,
        ok_to_submit_reason="HOLDOUT-DTI gate failed: CAND_STEP 0.1662 vs CTRL_A2 0.1826, paired delta -0.0164 "
                             "[-0.0235,-0.0090] (gems57-pooled-hide-v2, seed 20, 11,321 withheld). "
                             "See preregistered_gate_evaluation for every gate item.",
        experiments_charged=3, submission_slots_used=0, organizer_confirmed_score=None,
        seconds_total=round(time.time() - t_start, 1),
    )
    card = clean(card)
    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "evidence/h78step_run_card.json").write_text(text)
    log("wrote evidence/h78step_run_card.json verdict", card["verdict"], "unique_scoped", unique_ok)
    print(json.dumps({k: card[k] for k in ("submission_name", "raster_sha256", "verdict", "ok_to_submit")}, indent=1))


if __name__ == "__main__":
    main()
