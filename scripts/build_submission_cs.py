#!/usr/bin/env python3
"""Experiment 3 of lane H78-CS: deployment build, uniqueness audit, validator, run card.

Retrains the CAND_CS arm definition (103 H78-A features + 15 collinear-support
features) on the FULL catalogue (strike/phi from the full catalogue), emits
44,090 B3 dots, audits uniqueness against six registry/shipped rasters (surface
before placement AND final dots), writes the GeoTIFF through the UNMODIFIED
shared submission_writer, re-reads it independently, evaluates the preregistered
promote gate from evidence/h78cs_holdout_seed20.json (fail-closed arithmetic,
nothing hardcoded), and writes evidence/h78cs_run_card.json.

A negative verdict still writes the TIF (unique, downloadable, inspection only)
with ok_to_submit=False everywhere; the site banner is generated from the card.
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
from gems78 import collinear as C  # noqa: E402
from gems78 import data as D  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import pipeline as P  # noqa: E402

HGB = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=200,
           l2_regularization=1.0, max_bins=255, early_stopping=False, random_state=0)
BUDGET, FLANK = 44_090, 3.0
RHO_LIMIT, OVERLAP_LIMIT = 0.90, 0.70
REGISTRY = {
    "H19-5 solid (121131 px; owner-report 0.1922)": "data/registry/h19_5_solid_nan.tif",
    "D2.8 dots (44090; owner-report 0.2600)": "data/registry/d28_44090_nan.tif",
    "H33-2-B2 dots (37654; owner-report 0.2778)": "data/registry/h33_2_b2_37654_zeros.tif",
    "H78-A primary shipped (44090; HOLDOUT-DTI 0.1826)":
        "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif",
    "H78-A altB2 shipped (44090; inspection only)":
        "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223133Z-ec00c053-altB2-zeros.tif",
    "H78-MPC shipped (37654; HOLDOUT-DTI 0.0977)":
        "docs/downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif",
}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def read1(p):
    with rasterio.open(p) as ds:
        return ds.read(1)


def main():
    t0 = time.time()
    hold = json.loads((ROOT / "evidence/h78cs_holdout_seed20.json").read_text())
    ps = hold["pooled_summary_B3_primary"]
    cand_key, ctrl_key = "CAND_CS|B3|44090", "CTRL_A2|B3|44090"
    cand_dti = ps["scores"][cand_key]["dti"]
    ctrl_dti = ps["scores"][ctrl_key]["dti"]
    delta = ps["paired_differences"][ctrl_key]
    gate = dict(
        cand_beats_ctrl_point=bool(cand_dti > ctrl_dti),
        cand_beats_repo_best_0p1826=bool(cand_dti > 0.1826),
        paired_delta_ci_lower_gt_0=bool(delta["ci95"][0] > 0),
        canary_clean=bool(len(hold["canary"]["flagged_over_0p90"]) == 0),
    )
    log("Exp1 gate (uniqueness/validator pending):", gate, "cand", cand_dti, "ctrl", ctrl_dti)

    rep30 = None
    p30 = ROOT / "evidence/h78cs_holdout_seed30.json"
    if p30.exists():
        h30 = json.loads(p30.read_text())
        s30 = h30["pooled_summary_B3_primary"]
        rep30 = dict(evidence_class="HOLDOUT-DTI", evaluator_version=s30["evaluator_version"],
                     seed=30, withheld_positive_pixels=h30["withheld_positive_pixels_scored"],
                     cand=dict(dti=s30["scores"][cand_key]["dti"], ci95=s30["scores"][cand_key]["ci95"]),
                     ctrl=dict(dti=s30["scores"][ctrl_key]["dti"], ci95=s30["scores"][ctrl_key]["ci95"]),
                     paired_delta_cand_minus_ctrl=s30["paired_differences"][ctrl_key],
                     far_truth={k: v["dti"] for k, v in
                                h30["pooled_summary_far_truth_gt10px_B3_primary"]["scores"].items()},
                     role="replication of the negative per amendment IR-78CS-01; cannot promote this lane")
        log("seed30 replication loaded:", rep30["cand"]["dti"], "vs ctrl", rep30["ctrl"]["dti"])

    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    feats_path, fmeta = P.build_feature_matrix("full", fp, cat)
    phi = np.load(D.PROC / "phi_full.npy")
    cs_path, csmeta = C.build_cs_matrix("full", fp, phi)
    del phi
    base_mm = np.load(feats_path, mmap_mode="r")
    cs_mm = np.load(cs_path, mmap_mode="r")
    cols = P.arm_columns("A2_h78_steered")

    pos, negs = P.training_sample(fp, cat, 450_000, seed=20)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    X = np.concatenate([np.asarray(base_mm[rows[order]][:, cols], np.float32),
                        np.asarray(cs_mm[rows[order]], np.float32)], axis=1)
    y = np.concatenate([np.ones(rows_pos.size, np.int8), np.zeros(rows_neg.size, np.int8)])[order]
    clf = HistGradientBoostingClassifier(**HGB)
    tf = time.time()
    clf.fit(X, y)
    fit_info = dict(n_pos=int(rows_pos.size), n_neg=int(rows_neg.size), n_features=int(X.shape[1]),
                    params=HGB, fit_seconds=round(time.time() - tf, 1))
    del X, y
    gc.collect()
    log("fit", fit_info)

    n = base_mm.shape[0]
    out_fp = np.zeros(n, np.float32)
    for lo in range(0, n, 600_000):
        hi = min(n, lo + 600_000)
        Xc = np.concatenate([np.asarray(base_mm[lo:hi][:, cols], np.float32),
                             np.asarray(cs_mm[lo:hi], np.float32)], axis=1)
        out_fp[lo:hi] = clf.predict_proba(Xc)[:, 1].astype(np.float32)
        del Xc
    del clf
    score = np.zeros(fp.shape, np.float32)
    score[fp] = out_fp
    del out_fp
    np.save(D.PROC / "score_full_CAND_CS.npy", score)
    log("scored")

    # uniqueness on the SURFACE before placement
    surf = {}
    for label, rel in REGISTRY.items():
        a = np.where(np.isfinite(read1(ROOT / rel)), read1(ROOT / rel), 0.0).astype(np.float32)
        surf[label] = U.surface_rho(score, a, fp)
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
            spearman_full_footprint=U.surface_rho(
                pred, np.where(np.isfinite(a), a, 0.0).astype(np.float32), fp)["spearman_full_footprint"])
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

    # In-memory pre-write validation of the exact array handed to the writer, so the
    # note's verdict word (written into the file receipt) can never disagree with the
    # final gate: after these asserts + the writer's own fail-closed on-disk checks,
    # the independent re-read below is a redundant confirmation, also asserted equal.
    assert np.isfinite(pred).all() and pred.min() >= 0.0 and pred.max() <= 1.0
    assert set(np.unique(pred).tolist()) <= {0.0, 1.0}
    assert int((pred[~fp] > 0).sum()) == 0 and int((pred[cat] > 0).sum()) == 0
    gate["validator_pass"] = True  # provisional: replaced by re-read result; mismatch raises below

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
    name = f"gems78-h78cs-collinear-{n_dots}dots-{stamp}-{digest8}-zeros"
    def _word(ok, dups):
        return "promote" if ok else ("NEGATIVE-DUPLICATE-do-not-submit" if dups else "NEGATIVE-do-not-submit")
    verdict_word = _word(all(gate.values()), duplicates)
    note = (f"GEMSDOE78 H78-CS collinear HGB {n_dots} dots B3; HOLDOUT-DTI {cand_dti:.4f} s20 "
            f"vs CTRL {ctrl_dti:.4f}; {verdict_word}; not a projection")[:140]
    out_dir = ROOT / "docs" / "downloads"
    tif = out_dir / f"{name}.tif"
    receipt = SW.write_submission(tif, pred, ROOT / "data/bridge/sample_submission.tif", fp,
                                  note=note, name=name, catalogue=cat,
                                  metadata=dict(lane="H78-CS", arm="CAND_CS", flank_px=FLANK,
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

    far = hold["pooled_summary_far_truth_gt10px_B3_primary"]
    card = dict(
        lane="H78-CS strike-following collinear support",
        repository="buffedlizard55-lab/GEMSDOE78",
        branch="arena/431f4c40-gemsdoe78",
        built_utc=stamp,
        hypothesis=json.loads((ROOT / "registry/preregistration_h78cs.json").read_text())["hypothesis"],
        mechanism=("Faults are continuous strands: integrating |Hnn|/|gn| (sigma=3 px, det_elev/rtp/"
                   "depth_to_base_surf) along the visible-catalogue strike tangent over 1.1/3.1 km is a "
                   "matched filter that should raise faint-strand SNR vs isolated texture; HGB on "
                   "103 H78-A + 15 path-integral features; greedy dots >=2.8 px, <=3 px flank removed."),
        non_fault_mimic=("Pleistocene Lake Lahontan shorelines/beach ridges (long range-front-parallel "
                         "topographic lines without a magnetic/basement step); roads; bedrock strike ridges."),
        holdout=dict(
            evidence_class="HOLDOUT-DTI", evaluator_version=ps["evaluator_version"],
            evaluator_sha256=hold["evaluator_sha256"], seed=20, hide_frac=0.20, buffer_px=3,
            withheld_positive_pixels=hold["withheld_positive_pixels_scored"],
            candidate=dict(config=cand_key, dti=cand_dti, ci95=ps["scores"][cand_key]["ci95"]),
            ctrl=dict(config=ctrl_key, dti=ctrl_dti, ci95=ps["scores"][ctrl_key]["ci95"],
                      note="exact rerun control; reproduces shipped H78-A evidence 0.1826/0.1586/0.1843"),
            ablation=dict(config="ABL_A0CS|B3|44090",
                          dti=ps["scores"]["ABL_A0CS|B3|44090"]["dti"],
                          ci95=ps["scores"]["ABL_A0CS|B3|44090"]["ci95"]),
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
                    cs_features=hold["canary"]["cs_features"],
                    flagged=hold["canary"]["flagged_over_0p90"], clean=gate["canary_clean"]),
        correlation_overlap_vs_registry=dict(
            rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT,
            surface_before_placement=surf, final_dots=dot_aud,
            surface_max_abs_rho=surface_max_rho, dots_max_abs_rho=dots_max_rho,
            dots_max_overlap=dots_max_overlap, passed=unique_ok,
            duplicate_lane_vs=duplicates,
            note=("Registry = H19-5, D2.8, H33 + this repo's shipped H78-A primary/altB2 and H78-MPC. "
                  f"Duplicate-lane breach (>0.70 dot overlap or >0.90 rho) vs: {duplicates}. "
                  "Separately, seed-20 score-surface rho vs the CTRL_A2 surface was 0.9520: as a model "
                  "class this lane sits inside H78-A (amendment IR-78CS-01).")),
        raster=dict(file=tif.name, sha256=rr["sha256"], bytes=rr["bytes"],
                    zip=receipt["zip_file"], zip_sha256=receipt["zip_sha256"],
                    dots=n_dots, flank_px=FLANK, budget=BUDGET, min_separation_px=2.8),
        raster_sha256=rr["sha256"],
        validator_output=dict(independent_reread=rr, passed=validator_ok,
                              writer_receipt_checks=receipt["validator"]["checks"],
                              no_nan_inside_footprint=rr["nan_inside_footprint"] == 0,
                              values_in_0_1=rr["values_in_0_1"],
                              crs_shape_transform_match_sample=all(rr["matches_sample"].values())),
        validator=dict(passed=validator_ok),  # convenience mirror of validator_output.passed
        preregistered_gate_evaluation=gate,
        submission_name=name, submission_note=note, note_chars=len(note),
        ok_to_download=True,  # file exists and is format-valid; download for INSPECTION
        ok_to_submit=ok_to_submit,
        verdict=verdict,
        organizer_confirmed_score=None,
        organizer_confirmed_note="none: this file has not been uploaded and (verdict negative) must not be",
        selector_guidance=("Do NOT spend a weekly slot on this file: it failed the holdout gate on two "
                           "seeds AND is a duplicate lane vs the shipped H78-A dots (>0.70 within 3 px; "
                           "see duplicate_lane_vs). The repo's promotable file remains H78-A primary "
                           "(docs/index.html). This lane's deliverable is the negative result + the "
                           "CTRL across-seed replication."),
        fit=fit_info,
        features_base={k: v for k, v in fmeta.items() if k != "names"},
        features_cs={k: v for k, v in csmeta.items() if k != "names"},
        seconds=round(time.time() - t0, 1),
    )
    outp = ROOT / "evidence/h78cs_run_card.json"
    outp.write_text(json.dumps(card, indent=2, default=float))
    log(json.dumps(dict(verdict=verdict, ok_to_submit=ok_to_submit, file=tif.name,
                        sha256=rr["sha256"], dots=n_dots, gate=gate), indent=1))
    print("WROTE", outp)


if __name__ == "__main__":
    main()
