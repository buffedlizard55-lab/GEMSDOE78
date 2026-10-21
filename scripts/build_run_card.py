#!/usr/bin/env python3
"""Assemble the protocol run card (one JSON) from measured evidence.
Publishes BOTH emission readings; verdict computed from the preregistered
gate applied to the Pass-2 corrected (spaced) emission, with the correction
disclosed as post-hoc defect fix IR-78-EMIT-01."""
from __future__ import annotations
import json, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
exp = json.loads((EV / "experiments.json").read_text())
exp2 = json.loads((EV / "experiments_pass2_spaced.json").read_text())
prod = json.loads((EV / "production.json").read_text())
uq = json.loads((EV / "uniqueness_production.json").read_text())
can = json.loads((EV / "canaries.json").read_text())
receipt = json.loads((ROOT / "docs/downloads" / f"{prod['final_stem']}.json").read_text())
sc = exp2["summaries"]["E2_MPC_SPACED"]["scores"]
pd_ = exp2["summaries"]["E2_MPC_SPACED"]["paired_differences"]
sc0 = exp["summaries"]["E2_MPC"]["scores"]
informative = [r for r in uq["dot_rows"] if r.get("their_3px_halo_fp_fraction", 0) < 0.70]
worst_mut = max(informative, key=lambda r: r["mutual"])
gate = {
  "E2_gt_E1_paired_ci_lower_gt_0": bool(pd_["E1_BASE_SPACED"]["ci95"][0] > 0),
  "E2_gt_0.0939_control_point_estimate": bool(sc["E2_MPC_SPACED"]["dti"] > 0.0939),
  "surface_rho_le_0.90": bool(uq["preplacement_max_abs_sampled_rho"] <= 0.90),
  "mutual_3px_overlap_le_0.70": bool(uq["worst_mutual_informative"] <= 0.70),
  "validator_all_passed": bool(prod["validator_all_passed"]),
}
promote = all(gate.values())
card = {
  "lane": "H78-MPC",
  "hypothesis": "Blind faults retain a contrast-invariant multi-scale local-phase step (monogenic phase congruency) even where gradient amplitude is too weak for HGM/tilt/worm detectors and for catalogue mapping.",
  "mechanism": "Riesz-transform monogenic signal on RTP / isostatic gravity / detrended elevation / depth-to-basement; DoG scales sigma=1,2,4 px; per-source phase congruency + 3 amplitudes + mean-phase cos/sin + orientation coherence (+Frangi bright/dark on RTP & det-elev) = 32 MPC-family features added to a 48-band geophysics+topo+lidar+radiometric stack (80 total); leave-one-quadrant-out HistGradientBoosting on visible catalogue only (negatives EDT>3px, 4:1); spaced greedy emission (min_dist 2.5 px) to exactly 37,654 dots at EDT(catalogue)>2.5 px (min realised 2.83 px).",
  "mimic_nonfault_process": "Lithologic contacts and aeromagnetic flight-line levelling seams are also phase-coherent step edges; they can mimic fault phase congruency with no fault present.",
  "holdout": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": exp["evaluator_version"],
    "evaluator_hashes": exp["evaluator_hashes"],
    "protocol": "shared vendor/gems57: buffered whole-component hide-and-recover, seed 20, feature buffer 3 px, boundary erosion 12 px, visible faults masked pixel-exactly, pooled DTI alpha 0.2 beta 0.8, 300 m triangular kernel; CIs = 20 km spatial-block paired bootstrap (1000 draws)",
    "withheld_positive_pixels": 11321,
    "instrument_identity_verified": "controls reproduced: h33_analogue_foldfair and random match GEMSDOE73/GEMSDOE77 published values on this instrument",
    "candidate_E2_MPC_SPACED": {"dti": sc["E2_MPC_SPACED"]["dti"], "ci95": sc["E2_MPC_SPACED"]["ci95"]},
    "E1_BASE_SPACED_ablation": {"dti": sc["E1_BASE_SPACED"]["dti"], "ci95": sc["E1_BASE_SPACED"]["ci95"]},
    "E3_MPC_ONLY_SPACED_ablation": {"dti": sc["E3_MPC_ONLY_SPACED"]["dti"], "ci95": sc["E3_MPC_ONLY_SPACED"]["ci95"]},
    "control_h33_analogue_foldfair": {"dti": sc["h33_analogue_foldfair"]["dti"], "ci95": sc["h33_analogue_foldfair"]["ci95"]},
    "random_control": {"dti": sc["random_control"]["dti"], "ci95": sc["random_control"]["ci95"]},
    "paired_deltas_candidate_minus": {k: {"delta": v["delta"], "ci95": v["ci95"]} for k, v in pd_.items()},
    "surface_auc_vs_withheld": {"E1_BASE": 0.6738, "E2_MPC": 0.6964, "E3_MPC_ONLY": 0.5092},
    "per_fold_spaced": exp2["per_fold"],
    "pass1_preregistered_emitter_reading_IR-78-EMIT-01": {
      "note": "As preregistered, vendor greedy_allocate+top-up produced contiguous dot runs (98.9% of dots with neighbour <=1.5 px, median NN 1.0 px), a defective geometry under the 300 m kernel. Those scores are retained here, not deleted: E2 0.0471 / E1 0.0366 / E3 0.0128 / control 0.0939 / random 0.0484 (evidence/experiments.json). Pass-2 re-emitted the FROZEN surfaces with the control's spaced emitter; no retraining. The MPC-vs-base paired effect is significant under BOTH emitters (+0.0105 clustered, +0.0121 spaced).",
      "scores_clustered": {k: {"dti": v["dti"], "ci95": v["ci95"]} for k, v in sc0.items()},
    },
    "caveat": "Candidate-vs-control paired delta is +0.0038 with 95% CI [-0.012, +0.020]: the point estimate beats the fold-fair H33 control but the advantage is NOT statistically significant. Holdout truth is the visible catalogue, so this instrument cannot reward genuinely new-fault geometry beyond catalogue-like structure (proxy limitation).",
  },
  "organizer_confirmed_scores": "None for any artifact in this repo. Live scores cited (H33 0.2778, leaderboard 0.4413, etc.) are user-reported submission-page receipts from sibling submissions, labelled as such wherever used. No projection is written as a score.",
  "leakage_canary": {"max_symmetric_auc": can["max_symmetric_auc"], "threshold": 0.90,
                     "passed": bool(can["max_symmetric_auc"] <= 0.90), "n_features_tested": len(can["features"]),
                     "when": "before any model fitting"},
  "correlation_overlap_vs_registry": {
    "registry_unique_rasters_compared": uq["registry_count"],
    "informative_excl_spacefilling_witnesses": uq["informative_count"],
    "preplacement_surface_max_abs_spearman_rho_sampled300k_fixedseed": uq["preplacement_max_abs_sampled_rho"],
    "rho_limit": 0.90,
    "final_dots_worst_mutual_3px_informative": uq["worst_mutual_informative"],
    "final_dots_worst_forward_3px_informative": uq["worst_forward_informative"],
    "final_dots_worst_forward_3px_literal_all_rasters": uq["worst_forward_literal_all_rasters"],
    "overlap_limit_preregistered_mutual": 0.70,
    "worst_mutual_raster": worst_mut,
    "unique_preregistered_gate": bool(gate["surface_rho_le_0.90"] and gate["mutual_3px_overlap_le_0.70"]),
    "disclosure": "Forward-only readings exceed 0.70 only against (a) the 206,895-dot r13 lattice witness whose 3-px halo covers 99.9% of the footprint (vacuous test, disclosed) and (b) one 54,000-dot raster (forward 0.73, mutual 0.42). The preregistered criterion is mutual overlap, following GEMSDOE70/73 precedent; all per-raster rows are in evidence/uniqueness_production.json.",
    "dot_spacing": prod["spacing"],
  },
  "raster_sha256": prod["sha256"],
  "superseded_defective_raster_sha256": prod["superseded_clustered"]["sha256"],
  "validator_output": {
    "all_checks_passed": receipt["validator"]["all_checks_passed"],
    "checks": receipt["validator"]["checks"],
    "no_nan_inside_footprint": receipt["validator"]["checks"]["in_footprint_all_finite"],
    "no_nan_anywhere": receipt["validator"]["checks"]["no_nan_anywhere"],
    "values_in_0_1": receipt["validator"]["checks"]["range_0_1_guaranteed"],
    "min": receipt["validator"]["min"], "max": receipt["validator"]["max"], "n_nan": receipt["validator"]["n_nan"],
    "nodata_tag": receipt["validator"]["meta"]["nodata"],
    "crs_shape_transform_match": bool(receipt["validator"]["checks"]["crs_epsg_32611"]
       and receipt["validator"]["checks"]["dimensions_3730x3292"]
       and receipt["validator"]["checks"]["transform_matches_sample_submission"]),
    "dots": receipt["validator"]["emitted_positive_pixels"],
    "on_catalogue_dots": receipt["validator"]["on_catalogue_positive_pixels"],
    "validation_class": receipt["validator"]["validation_class"],
  },
  "submission_name": prod["name"],
  "submission_note": prod["note"],
  "submission_note_chars": len(prod["note"]),
  "file": f"{prod['final_stem']}.tif",
  "zip_file": f"{prod['final_stem']}.zip",
  "ok_to_download": True,
  "ok_to_submit": bool(promote),
  "ok_to_submit_qualification": "YES for a human selector to spend one weekly slot, with stated caveats: (1) holdout advantage over the H33 fold-fair control is a non-significant +0.0038; (2) emission was corrected post-hoc (IR-78-EMIT-01), both readings published; (3) no organizer score exists for this file. The MPC-vs-base effect itself is significant and emitter-independent.",
  "weekly_slots_used_by_agent": 0,
  "experiments_used": "3 preregistered arms (E1/E2/E3) + 1 disclosed Pass-2 emission-defect correction on frozen surfaces",
  "preregistered_gate_evaluation": gate,
  "verdict": "promote" if promote else "negative",
}
assert len(prod["note"]) <= 140
(EV / "run_card.json").write_text(json.dumps(card, indent=1))
shutil.copy(EV / "run_card.json", ROOT / "docs/downloads/run_card.json")
shutil.copy(EV / "run_card.json", ROOT / "run_card.json")
print(json.dumps({"verdict": card["verdict"], "gate": gate, "sha256": card["raster_sha256"][:16],
                  "note_chars": card["submission_note_chars"]}, indent=1))
