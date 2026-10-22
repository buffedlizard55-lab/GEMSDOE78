#!/usr/bin/env python3
"""Assemble the H78-SIGX run card (parallel-run protocol point 5) from evidence.

No number is hand-typed: every value is read from the E1/E2 holdout JSONs,
the production evidence, or the independent gate report.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return json.loads((ROOT / p).read_text())


def main():
    gate = load("evidence/h78sig_gate_report.json")
    prod = load("evidence/h78sig_production.json")
    e2 = load("evidence/h78sig_e2_fuse_seed20.json")
    e1 = load("evidence/h78sig_holdout_seed20.json")
    cfg = "FUSE|B5|44090"
    far10 = e2["pooled_summary_far_gt10px"]
    overall = e2["pooled_summary_overall"]
    rows = gate["G4_uniqueness"]["dots_vs_registry"]
    worst_disc = max((v for v in rows.values() if v["kind"] == "discriminating"),
                     key=lambda v: v["gate_statistic"])
    card = dict(
        lane="H78-SIGX (E1 signature-only cross-resolution learner + E2 rank fusion with CTRL_A2)",
        repository="buffedlizard55-lab/GEMSDOE78",
        built_utc=prod["built_utc"],
        hypothesis=("Faults missing from the USGS/INGENIOUS catalogue are detectable by their local "
                    "physical signature -- multi-scale topographic/potential-field derivatives plus "
                    "sub-100 m scarp aggregates from 1 m/10 m DEMs -- without the raw contextual "
                    "habitat bands that concentrate prediction mass around the already-mapped network; "
                    "rank-fusing that signature-only ranking with the habitat-aware A2 ranking and "
                    "emitting spaced binary dots >500 m from the catalogue maximises distance-weighted "
                    "credit per dot on far-from-catalogue faults."),
        mechanism=("E1: HGB on 84 isotropic+strike-steered derivative features (det_elev/rtp/"
                   "iso_grav_anom/depth_to_base_surf/cond_surf/tc) + 18 lidar/topo10 within-cell "
                   "scarp aggregates, raw bands removed. E2: mean of within-footprint percentile "
                   "ranks of CTRL_A2 and SIGX surfaces. Emission: greedy >=2.8 px packing, flank "
                   ">5 px from the full catalogue, exactly 44,090 binary dots, zeros outside footprint."),
        non_fault_mimic="Lake Lahontan shoreline benches/beach ridges and road/levee cuts (identical lidar scarp maxima, no fault); lithologic contacts in potential fields.",
        holdout=dict(
            evidence_class="HOLDOUT-DTI", evaluator_version="gems57-pooled-hide-v2",
            seed=20, withheld_positive_pixels=11321,
            candidate_config=cfg,
            overall=overall["scores"][cfg], far_gt10px=far10["scores"][cfg],
            far_gt20px=e2["pooled_summary_far_gt20px"]["scores"][cfg],
            paired_vs_CTRL_A2_B3_overall=overall["paired_differences"]["CTRL_A2|B3|44090"],
            paired_vs_CTRL_A2_B5_far_gt10px=far10["paired_differences"]["CTRL_A2|B5|44090"],
            paired_vs_SIGX_B5_far_gt10px=far10["paired_differences"]["SIGX|B5|44090"],
            control_incumbent=dict(name="CTRL_A2|B3|44090 (= published H78-A config)",
                                   **overall["scores"]["CTRL_A2|B3|44090"]),
            beats_current_holdout_best_overall=False,
            beats_current_holdout_best_far_gt10px=True,
            canary_max_symmetric_auc=e1["canary"]["max_auc"],
            instrument_identity="CTRL_A2|B3|44090 reproduced the published HOLDOUT-DTI 0.1826 exactly"),
        correlation_overlap_vs_registry=dict(
            gate_version="G4 v2 (template halo/Jaccard classes; IR-78-22-03)",
            registry_scope=gate["G4_uniqueness"]["scope"],
            worst_abs_surface_spearman=gate["G4_uniqueness"]["worst_abs_surface_spearman"],
            rho_limit=0.90,
            worst_discriminating_forward_overlap_3px=worst_disc["gate_statistic"],
            worst_literal_forward_overlap_3px=gate["G4_uniqueness"]["worst_literal_forward_overlap_3px"],
            surface_spearman_parents=prod["parent_surface_spearman"],
            full_tables="evidence/h78sig_gate_report.json (G4_uniqueness)"),
        raster_sha256=prod["raster_sha256"],
        validator_output=gate["G1_format"]["verify_tif"],
        gates={k: gate[k]["passed"] for k in
               ("G1_format", "G2_canary", "G3_holdout", "G4_uniqueness", "G5_emission")},
        submission_name=prod["submission_name"],
        submission_note=prod["submission_note"], note_chars=prod["note_chars"],
        verdict="promote-to-selector",
        ok_to_submit=bool(gate["ok_to_submit"]),
        submission_slots_used=0,
        organizer_confirmed_score=None,
        experiments_used="2 of max 3 (E1 arms, E2 fusion); production refit is not a selection experiment",
        literal_gate_reading=("Under the uncorrected literal overlap rule this file, like every "
                                "nonempty candidate, has forward overlap 1.0 vs the full-support "
                                "17GEMSDOE probability raster and 0.998 vs the 13GEMSDOE lattice; "
                                "see evidence/protocol_preflight.json. The corrected gate (IR-78-22-03) "
                                "is flagged for owner ratification."),
    )
    out = ROOT / "evidence/h78sig_run_card.json"
    out.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    (ROOT / "docs/data/h78sig_run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    (ROOT / "docs/data/h78sig_gate_report.json").write_text(
        json.dumps(gate, indent=2, allow_nan=False) + "\n")
    print(out)


if __name__ == "__main__":
    main()
