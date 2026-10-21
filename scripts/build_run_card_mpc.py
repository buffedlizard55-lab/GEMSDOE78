#!/usr/bin/env python3
"""Assemble the H78-MPC run card from measured evidence.
Publish both emission readings and preserve the original preregistered-gate
result. Apply the literal PROMPT.md forward-overlap and current-best rules as
additional binding eligibility gates; a duplicate fails closed, with the TIFF
retained only as a research artifact. IR-78-EMIT-01 remains disclosed."""
from __future__ import annotations
import json, re, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
exp = json.loads((EV / "h78mpc_experiments.json").read_text())
exp2 = json.loads((EV / "h78mpc_experiments_pass2_spaced.json").read_text())
prod = json.loads((EV / "h78mpc_production.json").read_text())
uq = json.loads((EV / "h78mpc_uniqueness.json").read_text())
can = json.loads((EV / "h78mpc_canaries.json").read_text())
receipt = json.loads((ROOT / "docs/downloads" / f"{prod['final_stem']}.json").read_text())
sc = exp2["summaries"]["E2_MPC_SPACED"]["scores"]
pd_ = exp2["summaries"]["E2_MPC_SPACED"]["paired_differences"]
sc0 = exp["summaries"]["E2_MPC"]["scores"]
informative = [r for r in uq["dot_rows"] if r.get("their_3px_halo_fp_fraction", 0) < 0.70]
worst_mut = max(informative, key=lambda r: r["mutual"])

# Compare against the highest already-recorded HOLDOUT-DTI in this checkout.
# Require the same evaluator, preregistered hide seed, and withheld-positive
# count. This remains a descriptive point-estimate comparison, not a paired test.
prereg = json.loads((ROOT / "registry/preregistration_h78_mpc.json").read_text())
seed_match = re.search(r"seed\s*=\s*(\d+)", prereg["instrument"])
if seed_match is None:
  raise SystemExit("Could not read preregistered holdout seed; fail closed")
candidate_seed = int(seed_match.group(1))
expected_withheld = int(exp["withheld_positive_pixels"])
repo_hold = json.loads((EV / "h78_holdout_seed20.json").read_text())
if repo_hold.get("seed") != candidate_seed or repo_hold.get("withheld_positive_pixels_scored") != expected_withheld:
  raise SystemExit("Repository-best comparator seed/withheld count does not match candidate; fail closed")
repo_scores = repo_hold["pooled_summary"]["scores"]
comparable = {
  k: v for k, v in repo_scores.items()
  if v.get("evidence_class") == "HOLDOUT-DTI"
  and v.get("evaluator_version") == exp["evaluator_version"]
  and v.get("withheld_positive_pixels") == expected_withheld
}
if not comparable:
  raise SystemExit("No same-instrument repository HOLDOUT-DTI comparator; fail closed")
repo_best_name, repo_best = max(comparable.items(), key=lambda item: item[1]["dti"])
worst_mutual = float(uq.get("worst_mutual_informative", uq.get("worst_mutual_informative_diagnostic_only", 1.0)))

candidate_dti = float(sc["E2_MPC_SPACED"]["dti"])
max_forward_literal = float(uq["worst_forward_literal_all_rasters"])
max_forward_informative = float(uq["worst_forward_informative"])
forward_limit = 0.70
control_delta = pd_["h33_analogue_foldfair"]
validator_passed = bool(prod["validator_all_passed"])

# Preserve the original preregistration result as history. Its mutual-overlap
# and point-estimate tests are not sufficient for the stricter session protocol.
original_preregistered_gate = {
  "E2_gt_E1_paired_ci_lower_gt_0": bool(pd_["E1_BASE_SPACED"]["ci95"][0] > 0),
  "E2_gt_0.0939_control_point_estimate": bool(candidate_dti > 0.0939),
  "surface_rho_le_0.90": bool(uq["preplacement_max_abs_sampled_rho"] <= 0.90),
  "mutual_3px_overlap_le_0.70": bool(worst_mutual <= 0.70),
  "validator_all_passed": validator_passed,
}

# Binding rule from PROMPT.md: one-way candidate-dot overlap is measured
# literally against every raster. Mutual overlap and post-hoc exclusions are
# diagnostic only and cannot convert a duplicate into a pass.
gate = {
  "E2_gt_E1_paired_ci_lower_gt_0": bool(pd_["E1_BASE_SPACED"]["ci95"][0] > 0),
  "E2_beats_h33_control_paired_ci_lower_gt_0": bool(control_delta["ci95"][0] > 0),
  "E2_gt_current_repo_best_holdout_point_estimate": bool(candidate_dti > float(repo_best["dti"])),
  "registry_at_least_74_recorded_local_rasters": bool(uq["registry_count"] >= 74),
  "surface_rho_le_0.90": bool(uq["preplacement_max_abs_sampled_rho"] <= 0.90),
  "forward_3px_overlap_le_0.70_informative_registry": bool(max_forward_informative <= forward_limit),
  "forward_3px_overlap_le_0.70_all_registry_rasters": bool(max_forward_literal <= forward_limit),
  "validator_all_passed": validator_passed,
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
    "seed": candidate_seed,
    "protocol": f"shared vendor/gems57: buffered whole-component hide-and-recover, seed {candidate_seed}, feature buffer 3 px, boundary erosion 12 px, visible faults masked pixel-exactly, pooled DTI alpha 0.2 beta 0.8, 300 m triangular kernel; CIs = 20 km spatial-block paired bootstrap (1000 draws)",
    "withheld_positive_pixels": expected_withheld,
    "instrument_identity_verified": "controls reproduced: h33_analogue_foldfair and random match GEMSDOE73/GEMSDOE77 published values on this instrument",
    "candidate_E2_MPC_SPACED": {"dti": sc["E2_MPC_SPACED"]["dti"], "ci95": sc["E2_MPC_SPACED"]["ci95"]},
    "E1_BASE_SPACED_ablation": {"dti": sc["E1_BASE_SPACED"]["dti"], "ci95": sc["E1_BASE_SPACED"]["ci95"]},
    "E3_MPC_ONLY_SPACED_ablation": {"dti": sc["E3_MPC_ONLY_SPACED"]["dti"], "ci95": sc["E3_MPC_ONLY_SPACED"]["ci95"]},
    "control_h33_analogue_foldfair": {"dti": sc["h33_analogue_foldfair"]["dti"], "ci95": sc["h33_analogue_foldfair"]["ci95"]},
    "random_control": {"dti": sc["random_control"]["dti"], "ci95": sc["random_control"]["ci95"]},
    "paired_deltas_candidate_minus": {k: {"evidence_class": "HOLDOUT-DTI paired difference", "delta": v["delta"], "ci95": v["ci95"]} for k, v in pd_.items()},
    "current_repo_best_holdout": {
      "evidence_class": "HOLDOUT-DTI",
      "evaluator_version": repo_best["evaluator_version"],
      "seed": repo_hold["seed"],
      "withheld_positive_pixels": repo_best["withheld_positive_pixels"],
      "candidate": repo_best_name,
      "dti": repo_best["dti"],
      "ci95": repo_best["ci95"],
      "source": "evidence/h78_holdout_seed20.json",
      "comparison_to_E2_MPC_SPACED": "descriptive point estimates only; no paired difference CI computed in this review",
    },
    "surface_auc_vs_withheld": {"E1_BASE": 0.6738, "E2_MPC": 0.6964, "E3_MPC_ONLY": 0.5092},
    "per_fold_spaced": exp2["per_fold"],
    "pass1_preregistered_emitter_reading_IR-78-EMIT-01": {
      "note": "As preregistered, vendor greedy_allocate+top-up produced contiguous dot runs (98.9% of dots with neighbour <=1.5 px, median NN 1.0 px), a defective geometry under the 300 m kernel. Those scores are retained here, not deleted: E2 0.0471 / E1 0.0366 / E3 0.0128 / control 0.0939 / random 0.0484 (evidence/h78mpc_experiments.json). Pass-2 re-emitted the FROZEN surfaces with the control's spaced emitter; no retraining. The MPC-vs-base paired effect is significant under BOTH emitters (+0.0105 clustered, +0.0121 spaced).",
      "scores_clustered": {k: {"dti": v["dti"], "ci95": v["ci95"]} for k, v in sc0.items()},
    },
    "caveat": "Candidate-vs-control paired HOLDOUT-DTI difference is +0.0038 with 95% CI [-0.0120, +0.0200]: the point estimate beats the fold-fair H33 control but the advantage is NOT statistically significant. The candidate HOLDOUT-DTI is also below the highest stored same-instrument repository HOLDOUT-DTI. Holdout truth is the visible catalogue, so this instrument cannot reward genuinely new-fault geometry beyond catalogue-like structure (proxy limitation).",
  },
  "organizer_confirmed_scores": "None for any artifact in this repo. Sibling-site and user-supplied values (including H33 0.2778 and leaderboard figures) are owner/user reports or dated public-page observations; no submission-page receipt is stored here, so none is classified ORGANIZER-CONFIRMED. No projection is written as a score.",
  "current_repo_best_holdout": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": repo_best["evaluator_version"],
    "seed": repo_hold["seed"],
    "withheld_positive_pixels": repo_best["withheld_positive_pixels"],
    "candidate": repo_best_name,
    "dti": repo_best["dti"],
    "ci95": repo_best["ci95"],
    "source": "evidence/h78_holdout_seed20.json"
  },
  "candidate_beats_current_repo_best_holdout": gate["E2_gt_current_repo_best_holdout_point_estimate"],
  "leakage_canary": {"max_symmetric_auc": can["max_symmetric_auc"], "threshold": 0.90,
                     "passed": bool(can["max_symmetric_auc"] <= 0.90), "n_features_tested": len(can["features"]),
                     "when": "before any model fitting"},
  "correlation_overlap_vs_registry": {
    "registry_unique_rasters_compared": uq["registry_count"],
    "minimum_recorded_local_registry_count": 74,
    "recorded_local_registry_scope_passed": gate["registry_at_least_74_recorded_local_rasters"],
    "scope_note": "This is the 74-raster locally accessible comparison inventory recorded by the prior run, not proof of exhaustive coverage of every sibling site or organizer registry.",
    "informative_excl_spacefilling_witnesses": uq["informative_count"],
    "preplacement_surface_max_abs_spearman_rho_sampled300k_fixedseed": uq["preplacement_max_abs_sampled_rho"],
    "rho_limit": 0.90,
    "final_dots_worst_mutual_3px_informative_diagnostic_only": uq["worst_mutual_informative"],
    "final_dots_worst_forward_3px_informative": uq["worst_forward_informative"],
    "final_dots_worst_forward_3px_literal_all_rasters": uq["worst_forward_literal_all_rasters"],
    "overlap_limit_forward": forward_limit,
    "worst_mutual_raster_diagnostic_only": worst_mut,
    "strict_protocol_gate_passed": bool(gate["registry_at_least_74_recorded_local_rasters"] and gate["surface_rho_le_0.90"] and gate["forward_3px_overlap_le_0.70_informative_registry"] and gate["forward_3px_overlap_le_0.70_all_registry_rasters"]),
    "duplicate_stop": {
      "required": True,
      "reason": "The literal one-way criterion in PROMPT.md is exceeded: 73.00% of candidate dots fall within 3 px of the non-spacefilling 54,000-dot GEMSDOE70 raster; the maximum against all compared rasters is 99.14% against the r13 lattice witness.",
      "informative_witness": "gems70-p5-submodular-multiphysics-hydro-54000-20261020.tif",
      "informative_witness_forward_overlap": max_forward_informative,
      "all_rasters_witness": "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
      "all_rasters_forward_overlap": max_forward_literal,
      "action": "Reclassify H78-MPC as duplicate/negative; keep its TIF only as a downloadable research artifact and stop without a slot or replacement raster.",
    },
    "disclosure": "Earlier audit text used mutual overlap and excluded a dense lattice witness. That is not the literal one-way >0.70 stop rule in PROMPT.md. The raw forward and reverse measurements remain in evidence/h78mpc_uniqueness.json; forward overlap is binding here.",
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
  "download_purpose": "Research / education only. Local format validator passes, but this is not an eligible competition submission.",
  "ok_to_submit": bool(promote),
  "ok_to_submit_qualification": "NO. The candidate is a duplicate under PROMPT.md's literal one-way 3-px criterion (0.730 against an informative registry raster; 0.9914 against the full compared set), and its HOLDOUT-DTI point estimate is below the stored repository best. The H33-control paired 95% CI also crosses zero. No slot was spent; retain the TIF only as a research artifact.",
  "weekly_slots_used_by_agent": 0,
  "experiments_used": "Prior run: 3 preregistered arms (E1/E2/E3) + 1 disclosed Pass-2 emission-defect correction on frozen surfaces; this review ran no new experiment.",
  "preregistered_gate_evaluation": original_preregistered_gate,
  "original_preregistered_gate_passed": all(original_preregistered_gate.values()),
  "strict_eligibility_gate_evaluation": gate,
  "verdict": "promote" if promote else "negative",
}
assert len(prod["note"]) <= 140
assert card["ok_to_submit"] == (card["verdict"] == "promote")
assert card["correlation_overlap_vs_registry"]["strict_protocol_gate_passed"] == bool(
    gate["registry_at_least_74_recorded_local_rasters"]
    and gate["surface_rho_le_0.90"]
    and gate["forward_3px_overlap_le_0.70_informative_registry"]
    and gate["forward_3px_overlap_le_0.70_all_registry_rasters"]
)
(EV / "h78mpc_run_card.json").write_text(json.dumps(card, indent=1))
stop_record = {
  "lane": "H78-MPC",
  "status": "duplicate-stop",
  "evidence_class": "REGISTRY-MEASUREMENT",
  "file": card["file"],
  "raster_sha256": card["raster_sha256"],
  "preplacement_surface_max_abs_spearman_rho": uq["preplacement_max_abs_sampled_rho"],
  "preplacement_surface_limit": 0.90,
  "surface_gate_passed": gate["surface_rho_le_0.90"],
  "final_dots_max_forward_3px_overlap_informative": max_forward_informative,
  "final_dots_max_forward_3px_overlap_all_compared": max_forward_literal,
  "final_dots_limit": forward_limit,
  "final_dots_gate_passed": bool(gate["forward_3px_overlap_le_0.70_informative_registry"] and gate["forward_3px_overlap_le_0.70_all_registry_rasters"]),
  "duplicate_witness_nonspacefilling": "gems70-p5-submodular-multiphysics-hydro-54000-20261020.tif",
  "duplicate_witness_nonspacefilling_overlap": max_forward_informative,
  "duplicate_witness_all_rasters": "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
  "duplicate_witness_all_rasters_overlap": max_forward_literal,
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": card["holdout"]["evaluator_version"],
    "withheld_positive_pixels": card["holdout"]["withheld_positive_pixels"],
    **card["holdout"]["candidate_E2_MPC_SPACED"],
  },
  "current_repo_best_holdout_dti": card["current_repo_best_holdout"],
  "ok_to_download": True,
  "ok_to_submit": False,
  "weekly_slots_used": 0,
  "action": "Stop this lane. Retain the existing validated TIFF for research/education only; do not submit and do not build a replacement raster in this lane.",
}
(EV / "h78mpc_duplicate_stop.json").write_text(json.dumps(stop_record, indent=1))
shutil.copy(EV / "h78mpc_run_card.json", ROOT / "docs/downloads/run_card_h78mpc.json")
shutil.copy(EV / "h78mpc_run_card.json", ROOT / "run_card_h78mpc.json")
print(json.dumps({"verdict": card["verdict"], "gate": gate, "sha256": card["raster_sha256"][:16],
                  "note_chars": card["submission_note_chars"]}, indent=1))
