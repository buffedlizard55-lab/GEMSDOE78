#!/usr/bin/env python3
"""Production build of lane H78-STEP: deployment, uniqueness audit, validator, run card.

Retrains the CAND_STEP arm definition (19 raw bands + 54 cross-strike STEP
features) on the FULL catalogue (strike/phi from the full catalogue), emits
44,090 B3 dots, audits uniqueness against the frozen 9-raster indexed registry
(surface before placement AND final dots, literal FORWARD 3-px overlap), writes
the GeoTIFF through the UNMODIFIED shared submission_writer, re-reads it
independently, evaluates the preregistered promote gate from
evidence/h78step_holdout_seed20.json (fail-closed arithmetic, nothing
hardcoded), and writes evidence/h78step_run_card.json.

A negative verdict still writes the TIF (new bytes, downloadable, inspection
only) with ok_to_submit=False everywhere and DO-NOT-SUBMIT in the filename;
the site banner is generated from the card. Preregistration:
registry/preregistration_h78step.json.
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import grid as G, submission_writer as SW, uniqueness as U, validate as V  # noqa: E402
from gems78 import data as D  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78 import xstep as X  # noqa: E402

HGB = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
           l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=0)
BUDGET, FLANK = 44_090, 3.0
RHO_LIMIT, OVERLAP_LIMIT = 0.90, 0.70
REGISTRY = {
    "H19-5 solid (121131 px; owner-report 0.1922)": "data/registry/h19_5_solid_nan.tif",
    "D2.8 dots (44090; owner-report 0.2600)": "data/registry/d28_44090_nan.tif",
    "H33-2-B2 dots (37654; owner-report 0.2778, source site says UNSCORED)":
        "data/registry/h33_2_b2_37654_zeros.tif",
    "GEMS70 p5 submodular 54k (sha256 00e8e1cb...)": "data/registry/gems70_p5_submod_54000.tif",
    "H78-A primary shipped (44090; HOLDOUT-DTI 0.1826)":
        "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif",
    "H78-A altB2 shipped (44090; inspection only)":
        "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223133Z-ec00c053-altB2-zeros.tif",
    "H78-MPC shipped (37654; HOLDOUT-DTI 0.0977)":
        "docs/downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif",
    "H78-SPY shipped (44090; HOLDOUT-DTI 0.1808, negative)":
        "docs/downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif",
    "H78-CS shipped (44090; HOLDOUT-DTI 0.1791, negative)":
        "docs/downloads/gems78-h78cs-collinear-44090dots-20261022T002927Z-0ca477e0-zeros.tif",
}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def read1(p):
    with rasterio.open(p) as ds:
        return ds.read(1)


def finite0(a):
    return np.where(np.isfinite(a), a, 0.0).astype(np.float32)


def main():
    t0 = time.time()
    hold = json.loads((ROOT / "evidence/h78step_holdout_seed20.json").read_text())
    ps = hold["pooled_summary_B3_primary"]
    cand_key, ctrl_key = "CAND_STEP|B3|44090", "CTRL_A2|B3|44090"
    cand_dti = ps["scores"][cand_key]["dti"]
    ctrl_dti = ps["scores"][ctrl_key]["dti"]
    delta = ps["paired_differences"][ctrl_key]
    rho_ctrl = hold["surface_rho_candidate_vs_ctrl"]["spearman_full_footprint"]
    gate = dict(
        cand_beats_ctrl_point=bool(cand_dti > ctrl_dti),
        cand_beats_repo_best_0p1826=bool(cand_dti > 0.1826),
        paired_delta_ci_lower_gt_0=bool(delta["ci95"][0] > 0),
        canary_clean=bool(len(hold["canary"]["flagged_over_0p90"]) == 0),
        surface_rho_vs_ctrl_le_0p90=bool(abs(rho_ctrl) <= RHO_LIMIT),
    )
    log("Exp1 gate (seed30/uniqueness/validator pending):", gate,
        "cand", cand_dti, "ctrl", ctrl_dti, "rho_ctrl", rho_ctrl)

    rep30 = None
    p30 = ROOT / "evidence/h78step_holdout_seed30.json"
    if p30.exists():
        h30 = json.loads(p30.read_text())
        s30 = h30["pooled_summary_B3_primary"]
        d30 = s30["paired_differences"][ctrl_key]
        rep30 = dict(evidence_class="HOLDOUT-DTI", evaluator_version=s30["evaluator_version"],
                     seed=30, withheld_positive_pixels=h30["withheld_positive_pixels_scored"],
                     cand=dict(dti=s30["scores"][cand_key]["dti"], ci95=s30["scores"][cand_key]["ci95"]),
                     ctrl=dict(dti=s30["scores"][ctrl_key]["dti"], ci95=s30["scores"][ctrl_key]["ci95"]),
                     paired_delta_cand_minus_ctrl=d30,
                     far_truth={k: v["dti"] for k, v in
                                h30["pooled_summary_far_truth_gt10px_B3_primary"]["scores"].items()},
                     surface_rho_candidate_vs_ctrl=h30["surface_rho_candidate_vs_ctrl"],
                     role="replication required positive by preregistration when run")
        gate["seed30_delta_point_gt_0"] = bool(d30["delta"] > 0)
        log("seed30 replication loaded:", rep30["cand"]["dti"], "vs ctrl", rep30["ctrl"]["dti"],
            "delta", d30["delta"])
    else:
        gate["seed30_delta_point_gt_0"] = True  # prereg: conditional on being run
        log("no seed30 replication file (conditional gate item passes vacuously; see prereg)")

    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    feats_path, fmeta = P.build_feature_matrix("full", fp, cat)
    phi = np.load(D.PROC / "phi_full.npy")
    step_path, stepmeta = X.build_step_matrix("full", fp, phi)
    del phi
    base_mm = np.load(feats_path, mmap_mode="r")
    step_mm = np.load(step_path, mmap_mode="r")
    cols = P.arm_columns("A0_std19")

    pos, negs = P.training_sample(fp, cat, 450_000, seed=20)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    Xm = np.concatenate([np.asarray(base_mm[rows[order]][:, cols], np.float32),
                         np.asarray(step_mm[rows[order]], np.float32)], axis=1)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    clf = HistGradientBoostingClassifier(**HGB)
    tf = time.time()
    clf.fit(Xm, y)
    fit_info = dict(n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), n_features=int(Xm.shape[1]),
                    params=HGB, fit_seconds=round(time.time() - tf, 1))
    del Xm, y
    gc.collect()
    log("fit", fit_info)

    n = base_mm.shape[0]
    out_fp = np.zeros(n, np.float32)
    for lo in range(0, n, 600_000):
        hi = min(n, lo + 600_000)
        Xc = np.concatenate([np.asarray(base_mm[lo:hi][:, cols], np.float32),
                             np.asarray(step_mm[lo:hi], np.float32)], axis=1)
        out_fp[lo:hi] = clf.predict_proba(Xc)[:, 1].astype(np.float32)
        del Xc
    del clf
    score = np.zeros(fp.shape, np.float32)
    score[fp] = out_fp
    del out_fp
    np.save(D.PROC / "score_full_CAND_STEP.npy", score)
    log("scored")

    # uniqueness on the SURFACE before placement
    surf = {}
    for label, rel in REGISTRY.items():
        surf[label] = U.surface_rho(score, finite0(read1(ROOT / rel)), fp)
    surface_max_rho = max(abs(v["spearman_full_footprint"]) for v in surf.values())
    log("surface rho max", surface_max_rho,
        {k: round(v["spearman_full_footprint"], 4) for k, v in surf.items()})

    allowed = fp & ~E.flank_mask(cat, FLANK)
    rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=max(BUDGET, 60_000), pool=1_500_000)
    dots = E.prefix(rank, BUDGET)
    n_dots = int(dots.sum())
    assert n_dots == BUDGET, n_dots
    pred = dots.astype(np.float32)
    del score, rank

    dot_aud = {}
    for label, rel in REGISTRY.items():
        a = read1(ROOT / rel)
        dot_aud[label] = dict(
            fraction_of_my_dots_within_3px_of_theirs=U.dot_overlap(pred, a, 3.0),
            fraction_of_their_dots_within_3px_of_mine=U.dot_overlap(a, pred, 3.0),
            spearman_full_footprint=U.surface_rho(pred, finite0(a), fp)["spearman_full_footprint"])
    dots_max_overlap = max(v["fraction_of_my_dots_within_3px_of_theirs"] for v in dot_aud.values())
    dots_max_rho = max(abs(v["spearman_full_footprint"]) for v in dot_aud.values())
    unique_ok = bool(surface_max_rho <= RHO_LIMIT and dots_max_rho <= RHO_LIMIT
                     and dots_max_overlap <= OVERLAP_LIMIT)
    log("dot overlap", {k: round(v["fraction_of_my_dots_within_3px_of_theirs"], 4)
                        for k, v in dot_aud.items()}, "unique_ok", unique_ok)
    gate["uniqueness_pass"] = unique_ok
    duplicates = [k for k, v in dot_aud.items()
                  if v["fraction_of_my_dots_within_3px_of_theirs"] > OVERLAP_LIMIT
                  or abs(v["spearman_full_footprint"]) > RHO_LIMIT]
    log("duplicate-lane vs:", duplicates)

    assert np.isfinite(pred).all() and pred.min() >= 0.0 and pred.max() <= 1.0
    assert set(np.unique(pred).tolist()) <= {0.0, 1.0}
    assert int((pred[~fp] > 0).sum()) == 0 and int((pred[cat] > 0).sum()) == 0
    gate["validator_pass"] = True  # provisional: replaced by re-read result; mismatch raises below

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]

    def _word(ok, dups):
        return "promote" if ok else ("NEGATIVE-DUPLICATE-do-not-submit" if dups else "NEGATIVE-do-not-submit")

    verdict_word = _word(all(gate.values()), duplicates)
    suffix = "zeros" if verdict_word == "promote" else "zeros-DO-NOT-SUBMIT"
    name = f"gems78-h78step-xstrike-{n_dots}dots-{stamp}-{digest8}-{suffix}"
    note = (f"GEMSDOE78 H78-STEP xstrike-step HGB {n_dots} dots B3; HOLDOUT-DTI {cand_dti:.4f} s20 "
            f"vs CTRL {ctrl_dti:.4f}; {verdict_word}; not a projection")[:140]
    out_dir = ROOT / "docs" / "downloads"
    tif = out_dir / f"{name}.tif"
    receipt = SW.write_submission(tif, pred, ROOT / "data/bridge/sample_submission.tif", fp,
                                  note=note, name=name, catalogue=cat,
                                  metadata=dict(lane="H78-STEP", arm="CAND_STEP", flank_px=FLANK,
                                                budget=BUDGET, gate_at_write=gate))

    a = read1(tif)
    with rasterio.open(tif) as ds:
        rr = dict(count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs),
                  shape=[ds.height, ds.width], transform=list(ds.transform)[:6], nodata=ds.nodata)
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ref:
        rr["matches_sample"] = dict(crs=str(ref.crs) == rr["crs"],
                                    shape=[ref.height, ref.width] == rr["shape"],
                                    transform=list(ref.transform)[:6] == rr["transform"])
    rr.update(all_finite=bool(np.isfinite(a).all()), nan_inside_footprint=int(np.isnan(a[fp]).sum()),
              min=float(a.min()), max=float(a.max()), values_in_0_1=bool(a.min() >= 0 and a.max() <= 1),
              positive_pixels=int((a > 0).sum()), positives_on_catalogue=int((a[cat] > 0).sum()),
              positives_outside_footprint=int((a[~fp] > 0).sum()),
              distinct_values=[float(v) for v in np.unique(a)],
              sha256=V.sha256(tif), bytes=tif.stat().st_size)
    validator_ok = all([rr["count"] == 1, rr["dtype"] == "float32", all(rr["matches_sample"].values()),
                        rr["all_finite"], rr["nan_inside_footprint"] == 0, rr["values_in_0_1"],
                        rr["positives_on_catalogue"] == 0, rr["positives_outside_footprint"] == 0,
                        rr["positive_pixels"] == n_dots])
    assert bool(validator_ok) == gate["validator_pass"], "pre-write vs re-read validator mismatch"
    gate["validator_pass"] = bool(validator_ok)
    ok_to_submit = bool(all(gate.values()))
    assert _word(ok_to_submit, duplicates) == verdict_word
    verdict = "promote" if ok_to_submit else "negative"

    prereg = json.loads((ROOT / "registry/preregistration_h78step.json").read_text())
    far = hold["pooled_summary_far_truth_gt10px_B3_primary"]
    if ok_to_submit:
        guidance = ("Promote to the separate selector ONLY: all preregistered gates passed within the "
                    "frozen 9-raster indexed registry scope. This session used 0 weekly slots. Before "
                    "any upload the selector must verify the weekly cap on the DrivenData submission "
                    "page and re-scan the wider family registry; global uniqueness is NOT claimed.")
    else:
        guidance = ("Do NOT spend a weekly slot on this file: it failed the preregistered gate "
                    f"({', '.join(k for k, v in gate.items() if not v)}). It is published for "
                    "inspection/reproducibility only. No file in this repo is currently cleared; "
                    "see evidence/release_audit.json for prior lanes.")
    card = dict(
        lane="H78-STEP cross-strike step-offset concordance",
        repository="buffedlizard55-lab/GEMSDOE78",
        branch="arena/faf23883-gemsdoe78",
        built_utc=stamp,
        hypothesis=prereg["hypothesis"],
        mechanism=prereg["mechanism"],
        non_fault_mimic=prereg["named_non_fault_mimic"],
        holdout=dict(
            evidence_class="HOLDOUT-DTI", evaluator_version=ps["evaluator_version"],
            evaluator_sha256=hold["evaluator_sha256"], seed=20, hide_frac=0.20, buffer_px=3,
            withheld_positive_pixels=hold["withheld_positive_pixels_scored"],
            candidate=dict(config=cand_key, dti=cand_dti, ci95=ps["scores"][cand_key]["ci95"]),
            ctrl=dict(config=ctrl_key, dti=ctrl_dti, ci95=ps["scores"][ctrl_key]["ci95"],
                      note="exact rerun control (H78-A model class)"),
            ablations={k: dict(dti=v["dti"], ci95=v["ci95"]) for k, v in ps["scores"].items()
                       if k not in (cand_key, ctrl_key)},
            paired_delta_cand_minus_ctrl=delta,
            far_truth_gt10px=dict(
                n_positives=hold["far_truth_positives_gt10px"],
                scores={k: dict(dti=v["dti"], ci95=v["ci95"]) for k, v in far["scores"].items()},
                paired_delta_cand_minus_ctrl=far["paired_differences"][ctrl_key]),
            surface_rho_candidate_vs_ctrl_seed20=hold["surface_rho_candidate_vs_ctrl"],
            budgets_B3={arm: {k: v["pooled_dti"] for k, v in hold["results"][arm]["configs"].items()}
                        for arm in hold["results"]},
        ),
        replication_seed30=rep30,
        canary=dict(threshold=0.90, max_single_feature_auc=hold["canary"]["max_auc"],
                    step_features=hold["canary"]["step_features"],
                    flagged=hold["canary"]["flagged_over_0p90"], clean=gate["canary_clean"]),
        correlation_overlap_vs_registry=dict(
            rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT,
            registry_scope="Frozen indexed registry of 9 rasters listed in registry/preregistration_h78step.json; NOT the organizer's complete submission history. Space-filling lattice rasters make the literal rule unsatisfiable by any dot set (standing irregularity, see preregistration).",
            surface_before_placement=surf, final_dots=dot_aud,
            surface_max_abs_rho=surface_max_rho, dots_max_abs_rho=dots_max_rho,
            dots_max_overlap=dots_max_overlap, passed=unique_ok,
            duplicate_lane_vs=duplicates),
        raster=dict(file=tif.name, sha256=rr["sha256"], bytes=rr["bytes"],
                    zip=receipt["zip_file"], zip_sha256=receipt["zip_sha256"],
                    dots=n_dots, flank_px=FLANK, budget=BUDGET, min_separation_px=2.8),
        raster_sha256=rr["sha256"],
        validator_output=dict(independent_reread=rr, passed=validator_ok,
                              writer_receipt_checks=receipt["validator"]["checks"],
                              no_nan_inside_footprint=rr["nan_inside_footprint"] == 0,
                              values_in_0_1=rr["values_in_0_1"],
                              crs_shape_transform_match_sample=all(rr["matches_sample"].values())),
        preregistered_gate_evaluation=gate,
        submission_name=name, submission_note=note, note_chars=len(note),
        ok_to_download=True,
        ok_to_submit=ok_to_submit,
        verdict=verdict,
        organizer_confirmed_score=None,
        organizer_confirmed_note="none: this file has not been uploaded by this session; 0 weekly slots used",
        selector_guidance=guidance,
        fit=fit_info,
        features_base={k: v for k, v in fmeta.items() if k != "names"},
        features_step={k: v for k, v in stepmeta.items() if k != "names"},
        seconds=round(time.time() - t0, 1),
    )
    outp = ROOT / "evidence/h78step_run_card.json"
    outp.write_text(json.dumps(card, indent=2, default=float))
    log(json.dumps(dict(verdict=verdict, ok_to_submit=ok_to_submit, file=tif.name,
                        sha256=rr["sha256"], dots=n_dots, gate=gate), indent=1))
    print("WROTE", outp)


if __name__ == "__main__":
    main()
