#!/usr/bin/env python3
"""Experiment 2 of lane H78-FW: full-catalogue deployment build, uniqueness audit,
independent GeoTIFF verification, and strict-JSON run card.

Fits CAND_FW_PURE (67 multi-scale antisymmetric footwall/hangingwall flank-warp
features) on the full visible catalogue, checks pre-placement surface Spearman rho
against local registry rasters, emits 44,090 B3 binary dots (separation >=2.8 px,
catalogue flank <=3.0 px excluded), writes the GeoTIFF and single-TIFF ZIP via the
unmodified shared submission_writer, independently verifies the file with
scripts/verify_tif.py, and audits final-dot overlap against both discriminating
dot-field comparators and literal space-filling registry witnesses.
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
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import grid as G, submission_writer as SW, uniqueness as U, validate as V  # noqa: E402
from gems78 import data as D  # noqa: E402
from gems78 import emit as E  # noqa: E402
from gems78 import flank_warp as FW  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from gems78.strike import strike_field  # noqa: E402

HGB = dict(
    max_iter=300,
    learning_rate=0.06,
    max_leaf_nodes=63,
    min_samples_leaf=200,
    l2_regularization=1.0,
    max_bins=255,
    early_stopping=False,
    random_state=0,
)
BUDGET = 44_090
FLANK = 3.0
MIN_DIST = 2.8
RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70

DISCRIMINATING_REGISTRY = {
    "H19-5 solid (121,131 px; owner-report 0.1922)": "data/registry/h19_5_solid_nan.tif",
    "D2.8 dots (44,090; owner-report 0.2600)": "data/registry/d28_44090_nan.tif",
    "H33-2-B2 dots (37,654; owner-report 0.2778)": "data/registry/h33_2_b2_37654_zeros.tif",
    "GEMSDOE70 p5-submodular (54,000; sibling dot field)": "data/registry/gems70_p5_54000.tif",
    "H78-A primary (44,090; HOLDOUT-DTI 0.1826)": "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif",
    "H78-A altB2 (44,090; HOLDOUT-DTI 0.1586)": "docs/downloads/gems78-h78a-strike-steered-44090dots-20261021T223133Z-ec00c053-altB2-zeros.tif",
    "H78-MPC (37,654; HOLDOUT-DTI 0.0977)": "docs/downloads/gems78-h78mpc-monogenic-pc-spaced-37654dots-20261021T223000Z-c7932fbd-zeros.tif",
    "H78-SPY (44,090; HOLDOUT-DTI 0.1808)": "docs/downloads/gems78-h78spy-inspection-44090dots-20261021T234636Z-277ac69b-DO-NOT-SUBMIT.tif",
    "H78-CS (44,090; HOLDOUT-DTI 0.1791)": "docs/downloads/gems78-h78cs-collinear-44090dots-20261022T002927Z-0ca477e0-zeros.tif",
    "H78-CROSSLAYER (44,090; HOLDOUT-DTI 0.0478)": "docs/downloads/gems78-crosslayer-step-20261022T005245Z-bf9c0b4c20-DO-NOT-SUBMIT.tif",
}

SPACE_FILLING_REGISTRY = {
    "13GEMSDOE r13-lattice-s5 (206,895 px; dense lattice)": "data/registry/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
    "17GEMSDOE E-proba-multiscale (5,167,373 px; full-footprint probability witness)": "data/registry/17GEMSDOE_E-proba-multiscale.tif",
}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def read1(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        return ds.read(1)


def main():
    t0 = time.time()
    existing_fw = sorted((ROOT / "docs/downloads").glob("gems78-h78fw-flank-warp-*.tif"))
    if existing_fw:
        raise RuntimeError(f"H78-FW inspection TIFF already exists: {existing_fw[0].name}; refusing to manufacture duplicates")

    hold = json.loads((ROOT / "evidence/h78fw_holdout_seed20.json").read_text())
    ps = hold["pooled_summary_B3_primary"]
    cand_key = "CAND_FW_PURE|B3|44090"
    ctrl_key = "CTRL_A2|B3|44090"
    abl_key = "ABL_FW_PLUS_A2|B3|44090"
    a0_key = "CTRL_A0|B3|44090"

    cand_dti = ps["scores"][cand_key]["dti"]
    ctrl_dti = ps["scores"][ctrl_key]["dti"]
    delta_vs_ctrl = ps["paired_differences"][ctrl_key]

    gate = dict(
        cand_beats_ctrl_point=bool(cand_dti > ctrl_dti),
        cand_beats_repo_best_0p1826=bool(cand_dti > 0.18258300140522551),
        paired_delta_ci_lower_gt_0=bool(delta_vs_ctrl["ci95"][0] > 0),
        canary_clean=bool(len(hold["canary"]["flagged_over_0p90"]) == 0),
    )
    log("Holdout gate evaluation:", gate, "cand", cand_dti, "ctrl", ctrl_dti)

    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue

    phi_p = D.PROC / "phi_full.npy"
    coh_p = D.PROC / "coh_full.npy"
    if phi_p.exists() and coh_p.exists():
        phi = np.load(phi_p)
        coh = np.load(coh_p)
    else:
        phi, coh, _ = strike_field(cat)
        np.save(phi_p, phi)
        np.save(coh_p, coh)

    fw_path, fwmeta = FW.build_fw_matrix("full", fp, phi, coh)
    del phi, coh
    gc.collect()
    log("fw_full ready in", fwmeta["seconds"], "s")

    fw_mm = np.load(fw_path, mmap_mode="r")
    pos, negs = P.training_sample(fp, cat, 450_000, seed=20)
    rows_pos, rows_neg = P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp)
    score_full_p = D.PROC / "score_full_CAND_FW_PURE.npy"
    if score_full_p.exists():
        score = np.load(score_full_p)
        fit_info = dict(
            arm="CAND_FW_PURE",
            n_pos=int(rows_pos.size),
            n_neg=int(rows_neg.size),
            n_features=int(fw_mm.shape[1]),
            params=HGB,
            cached_score=True,
        )
        log("loaded cached full score")
    else:
        rows = np.concatenate([rows_pos, rows_neg])
        order = np.argsort(rows)
        X = np.asarray(fw_mm[rows[order]], np.float32)
        y = np.concatenate([
            np.ones(rows_pos.size, np.int8),
            np.zeros(rows_neg.size, np.int8),
        ])[order]

        clf = HistGradientBoostingClassifier(**HGB)
        tf = time.time()
        clf.fit(X, y)
        fit_info = dict(
            arm="CAND_FW_PURE",
            n_pos=int(rows_pos.size),
            n_neg=int(rows_neg.size),
            n_features=int(X.shape[1]),
            params=HGB,
            fit_seconds=round(time.time() - tf, 1),
        )
        del X, y
        gc.collect()
        log("fit full:", fit_info)

        n = fw_mm.shape[0]
        out_fp = np.zeros(n, np.float32)
        for lo in range(0, n, 600_000):
            hi = min(n, lo + 600_000)
            Xc = np.asarray(fw_mm[lo:hi], np.float32)
            out_fp[lo:hi] = clf.predict_proba(Xc)[:, 1].astype(np.float32)
            del Xc
        del clf
        score = np.zeros(fp.shape, np.float32)
        score[fp] = out_fp
        del out_fp
        np.save(score_full_p, score)
        log("scored full footprint")

    # ---- Pre-placement surface Spearman rho across all local registry rasters ----
    all_registry = {**DISCRIMINATING_REGISTRY, **SPACE_FILLING_REGISTRY}
    surf_audit = {}
    for label, rel in all_registry.items():
        p = ROOT / rel
        if not p.exists():
            raise FileNotFoundError(f"Missing required registry comparator: {rel}")
        arr = read1(p)
        arr_clean = np.where(np.isfinite(arr), arr, 0.0).astype(np.float32)
        s_res = U.surface_rho(score, arr_clean, fp)
        for k_s, v_s in list(s_res.items()):
            if isinstance(v_s, float) and not np.isfinite(v_s):
                s_res[k_s] = None
        s_res["file"] = rel
        s_res["sha256"] = V.sha256(p)
        surf_audit[label] = s_res
        log("surface rho vs", label, "->", round(s_res["spearman_full_footprint"], 4))

    surface_max_abs_rho = max(abs(v["spearman_full_footprint"]) for v in surf_audit.values())
    gate["surface_rho_pass"] = bool(surface_max_abs_rho <= RHO_LIMIT)
    if not gate["surface_rho_pass"]:
        raise RuntimeError(f"Surface Spearman rho {surface_max_abs_rho:.4f} > {RHO_LIMIT}; aborting before placement")

    # ---- Emit 44,090 B3 sparse binary dots ----
    allowed = fp & ~E.flank_mask(cat, FLANK)
    rank = E.greedy_dots(score, allowed, min_dist=MIN_DIST, max_dots=max(BUDGET, 60_000), pool=1_500_000)
    dots = E.prefix(rank, BUDGET)
    n_dots = int(dots.sum())
    assert n_dots == BUDGET, f"Expected {BUDGET} dots, got {n_dots}"
    pred = dots.astype(np.float32)
    del score, rank
    gc.collect()

    # ---- Final-dot uniqueness audit (discriminating dot fields AND literal all-rasters) ----
    dot_audit = {}
    for label, rel in all_registry.items():
        p = ROOT / rel
        arr = read1(p)
        arr_clean = np.where(np.isfinite(arr), arr, 0.0).astype(np.float32)
        fwd = U.dot_overlap(pred, arr, 3.0)
        rev = U.dot_overlap(arr, pred, 3.0)
        s_rho = U.surface_rho(pred, arr_clean, fp)["spearman_full_footprint"]
        dot_audit[label] = dict(
            file=rel,
            sha256=V.sha256(p),
            their_positive_pixels=int((np.isfinite(arr) & (arr > 0) & fp).sum()),
            representation="space_filling" if label in SPACE_FILLING_REGISTRY else "discriminating_dot_or_line",
            fraction_of_my_dots_within_3px_of_theirs=fwd,
            fraction_of_their_dots_within_3px_of_mine=rev,
            spearman_full_footprint=s_rho,
        )
        log("final dots vs", label, "-> fwd:", round(fwd, 4), "rho:", round(s_rho, 4))

    disc_max_overlap = max(
        v["fraction_of_my_dots_within_3px_of_theirs"]
        for k, v in dot_audit.items()
        if k in DISCRIMINATING_REGISTRY
    )
    disc_max_overlap_label = max(
        DISCRIMINATING_REGISTRY,
        key=lambda k: dot_audit[k]["fraction_of_my_dots_within_3px_of_theirs"],
    )
    literal_max_overlap = max(
        v["fraction_of_my_dots_within_3px_of_theirs"] for v in dot_audit.values()
    )
    literal_duplicates = [
        k for k, v in dot_audit.items()
        if v["fraction_of_my_dots_within_3px_of_theirs"] > OVERLAP_LIMIT
        or abs(v["spearman_full_footprint"]) > RHO_LIMIT
    ]
    disc_duplicates = [
        k for k in DISCRIMINATING_REGISTRY
        if dot_audit[k]["fraction_of_my_dots_within_3px_of_theirs"] > OVERLAP_LIMIT
        or abs(dot_audit[k]["spearman_full_footprint"]) > RHO_LIMIT
    ]
    dots_max_abs_rho = max(abs(v["spearman_full_footprint"]) for v in dot_audit.values())

    gate["discriminating_dot_fields_unique_pass"] = bool(
        surface_max_abs_rho <= RHO_LIMIT
        and dots_max_abs_rho <= RHO_LIMIT
        and disc_max_overlap <= OVERLAP_LIMIT
    )
    gate["literal_all_rasters_unique_pass"] = bool(
        surface_max_abs_rho <= RHO_LIMIT
        and dots_max_abs_rho <= RHO_LIMIT
        and literal_max_overlap <= OVERLAP_LIMIT
    )

    assert np.isfinite(pred).all() and pred.min() >= 0.0 and pred.max() <= 1.0
    assert set(np.unique(pred).tolist()) <= {0.0, 1.0}
    assert int((pred[~fp] > 0).sum()) == 0 and int((pred[cat] > 0).sum()) == 0
    gate["validator_pass"] = True

    ok_to_submit = bool(all(gate.values()))
    verdict = "promote" if ok_to_submit else "negative"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
    suffix = "zeros" if ok_to_submit else "DO-NOT-SUBMIT"
    name = f"gems78-h78fw-flank-warp-{n_dots}dots-{stamp}-{digest8}-{suffix}"
    note = (
        f"NOT OK TO SUBMIT: H78-FW flank-warp {n_dots} dots B3; HOLDOUT-DTI {cand_dti:.4f} "
        f"vs CTRL {ctrl_dti:.4f} s20; negative/blocked"
    )[:140]
    assert len(note) <= 140

    out_dir = ROOT / "docs" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    tif = out_dir / f"{name}.tif"
    receipt = SW.write_submission(
        tif,
        pred,
        ROOT / "data/bridge/sample_submission.tif",
        fp,
        note=note,
        name=name,
        catalogue=cat,
        metadata=dict(
            lane="H78-FW",
            arm="CAND_FW_PURE",
            flank_px=FLANK,
            min_dist_px=MIN_DIST,
            budget=BUDGET,
            gate_at_write=gate,
            holdout_only=not ok_to_submit,
        ),
    )

    verify = json.loads(
        subprocess.check_output([sys.executable, str(ROOT / "scripts/verify_tif.py"), str(tif)], text=True)
    )
    if not verify["all_passed"]:
        raise RuntimeError(f"Independent verification failed: {verify}")

    far_ps = hold["pooled_summary_far_truth_gt10px_B3_primary"]
    card = dict(
        schema_version=1,
        lane="H78-FW multi-scale antisymmetric footwall/hangingwall flank-warp flexure",
        repository="buffedlizard55-lab/GEMSDOE78",
        built_utc=stamp,
        preregistration="registry/preregistration_h78fw.json",
        hypothesis=json.loads((ROOT / "registry/preregistration_h78fw.json").read_text())["hypothesis"],
        mechanism=json.loads((ROOT / "registry/preregistration_h78fw.json").read_text())["mechanism"],
        non_fault_mimic=json.loads((ROOT / "registry/preregistration_h78fw.json").read_text())["non_fault_mimic"],
        input_sha256=hold["input_sha256"],
        stack_cache_meta=hold["stack_cache_meta"],
        holdout=dict(
            evidence_class="HOLDOUT-DTI",
            evaluator_version=ps["evaluator_version"],
            evaluator_sha256=hold["evaluator_sha256"],
            seed=hold["seed"],
            hide_frac=hold["hide_frac"],
            buffer_px=hold["buffer_px"],
            withheld_positive_pixels=hold["withheld_positive_pixels_scored"],
            candidate=dict(
                config=cand_key,
                dti=ps["scores"][cand_key]["dti"],
                ci95=ps["scores"][cand_key]["ci95"],
                tpw=ps["scores"][cand_key]["tpw"],
                fpw=ps["scores"][cand_key]["fpw"],
                fnw=ps["scores"][cand_key]["fnw"],
            ),
            ctrl_a2=dict(
                config=ctrl_key,
                dti=ps["scores"][ctrl_key]["dti"],
                ci95=ps["scores"][ctrl_key]["ci95"],
                note="Reproduced H78-A control on v2-verified feature stack; confirms 0.182583 is unchanged by v2 nodata mask fix",
            ),
            ablation_fw_plus_a2=dict(
                config=abl_key,
                dti=ps["scores"][abl_key]["dti"],
                ci95=ps["scores"][abl_key]["ci95"],
            ),
            ctrl_a0_raw19=dict(
                config=a0_key,
                dti=ps["scores"][a0_key]["dti"],
                ci95=ps["scores"][a0_key]["ci95"],
            ),
            paired_delta_cand_minus_ctrl_a2=ps["paired_differences"][ctrl_key],
            paired_delta_cand_minus_ctrl_a0=ps["paired_differences"][a0_key],
            paired_delta_ablation_minus_ctrl_a2=hold["pooled_summary_B3_ablation_fw_plus_a2"]["paired_differences"][ctrl_key],
            far_truth_gt10px=dict(
                withheld_positive_pixels=hold["far_truth_gt10px_positives"],
                cand_dti=far_ps["scores"][cand_key]["dti"],
                cand_ci95=far_ps["scores"][cand_key]["ci95"],
                ctrl_a2_dti=far_ps["scores"][ctrl_key]["dti"],
                ctrl_a2_ci95=far_ps["scores"][ctrl_key]["ci95"],
                ctrl_a0_dti=far_ps["scores"][a0_key]["dti"],
                ctrl_a0_ci95=far_ps["scores"][a0_key]["ci95"],
                paired_delta_cand_minus_ctrl_a2=far_ps["paired_differences"][ctrl_key],
                paired_delta_cand_minus_ctrl_a0=far_ps["paired_differences"][a0_key],
            ),
        ),
        canary=dict(
            threshold=0.90,
            max_single_feature_auc_fw_67=hold["canary"]["max_auc_fw_67"],
            max_single_feature_auc_all_170=hold["canary"]["max_auc_all_170"],
            flagged=hold["canary"]["flagged_over_0p90"],
            clean=gate["canary_clean"],
            top10_fw=hold["canary"]["top10_fw"],
        ),
        correlation_overlap_vs_registry=dict(
            rho_limit=RHO_LIMIT,
            overlap_limit=OVERLAP_LIMIT,
            surface_before_placement=surf_audit,
            surface_max_abs_rho=surface_max_abs_rho,
            final_dots=dot_audit,
            dots_max_abs_rho=dots_max_abs_rho,
            discriminating_dot_fields=dict(
                comparators=len(DISCRIMINATING_REGISTRY),
                max_forward_3px_overlap=disc_max_overlap,
                max_overlap_comparator=disc_max_overlap_label,
                duplicates=disc_duplicates,
                passed=gate["discriminating_dot_fields_unique_pass"],
                note="Like-for-like comparison against all 9 sparse dot/line rasters (D2.8, H33, H19-5, H78-A, H78-A-altB2, H78-MPC, H78-SPY, H78-CS, H78-CROSSLAYER).",
            ),
            literal_all_rasters=dict(
                comparators=len(all_registry),
                max_forward_3px_overlap=literal_max_overlap,
                duplicates=literal_duplicates,
                passed=gate["literal_all_rasters_unique_pass"],
                note="Binding literal rule across all 11 local comparators including space-filling 13GEMSDOE lattice and 17GEMSDOE full-footprint probability surface.",
            ),
            passed=gate["literal_all_rasters_unique_pass"],
        ),
        preregistered_gate_evaluation=gate,
        raster=dict(
            file=tif.name,
            sha256=verify["sha256"],
            bytes=verify["bytes"],
            zip=receipt["zip_file"],
            zip_sha256=receipt["zip_sha256"],
            dots=n_dots,
            flank_px=FLANK,
            min_separation_px=MIN_DIST,
        ),
        raster_sha256=verify["sha256"],
        validator_output=verify,
        submission_name=name,
        submission_note=note,
        note_chars=len(note),
        verdict=verdict,
        ok_to_download=True,
        ok_to_submit=ok_to_submit,
        weekly_slots_used=0,
        organizer_confirmed_score=None,
        fit=fit_info,
        features={k: v for k, v in fwmeta.items() if k != "names"},
        seconds=round(time.time() - t0, 1),
    )

    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    for rel in ("evidence/h78fw_run_card.json", "run_card_h78fw.json", "docs/data/h78fw_run_card.json", "docs/downloads/run_card_h78fw.json"):
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    log("WROTE H78-FW GeoTIFF:", tif.name, "sha256:", verify["sha256"], "verdict:", verdict)


if __name__ == "__main__":
    main()
