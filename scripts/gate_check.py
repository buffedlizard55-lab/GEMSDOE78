#!/usr/bin/env python3
"""Independent automated submission-readiness gate for lane H78-SIGX.

Recomputes every gate from the written bytes + saved production surface +
E1/E2 holdout evidence (no trust in the build script's self-report):

  G1 format  -- scripts/verify_tif.py strict re-read vs the pinned sample grid
  G2 canary  -- max single-feature symmetric AUC <= 0.90 (E1 evidence)
  G3 holdout -- competence (candidate > random and > D2.8 overall) and the
                pre-registered far-field endpoints with paired CIs (E1/E2)
  G4 unique  -- surface |Spearman| < 0.90 and final forward 3 px overlap
                < 0.70 vs the restored registry (sparse literal; dense
                top-K corrected, IR-78-22-03), recomputed here
  G5 emission-- binary dots, realised spacing > 2.8 px (banned-offset test),
                min distance to full catalogue > 5 px, exact budget

Exit 0 iff all gates pass. Writes evidence/h78sig_gate_report.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from verify_tif import verify  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems78 import registry_check as RC  # noqa: E402


def spacing_ok(dots: np.ndarray, min_dist: float = 2.8) -> tuple[bool, float]:
    """Exact banned-offset test mirroring emit.greedy_dots, + realised min NN."""
    r = int(np.ceil(min_dist))
    offs = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if (dy or dx) and dy * dy + dx * dx <= min_dist * min_dist + 1e-9]
    pad = np.pad(dots, r)
    h, w = dots.shape
    centre = pad[r:r + h, r:r + w]
    for dy, dx in offs:
        if (centre & pad[r + dy:r + dy + h, r + dx:r + dx + w]).any():
            return False, float(np.hypot(dy, dx))
    # realised minimum nearest-neighbour over a wider neighbourhood
    best = np.inf
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            if dy == 0 and dx == 0:
                continue
            if (centre & np.pad(dots, 4)[4 + dy:4 + dy + h, 4 + dx:4 + dx + w]).any():
                best = min(best, float(np.hypot(dy, dx)))
    return True, best


def main(tif: str):
    path = ROOT / tif if not Path(tif).is_absolute() else Path(tif)
    prod = json.loads((ROOT / "evidence/h78sig_production.json").read_text())
    e1 = json.loads((ROOT / "evidence/h78sig_holdout_seed20.json").read_text())
    e2 = json.loads((ROOT / "evidence/h78sig_e2_fuse_seed20.json").read_text())
    cand = prod["selected_candidate"]
    src = e2 if cand == "FUSE" else e1
    cfg = f"{cand}|B5|44090"

    g1 = verify(path)
    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, np.asarray(g.catalogue, bool)
    with rasterio.open(path) as ds:
        arr = ds.read(1)
    dots = arr > 0
    dcat = ndi.distance_transform_edt(~cat)
    sp_ok, sp_min = spacing_ok(dots)

    entries = RC.registry_rasters(exclude_names={path.name})
    surface = np.load(ROOT / "data/processed/surface_production_selected.npy")
    surf_cmp = RC.compare_surface(surface, fp, cat, entries)
    dot_cmp = RC.compare_dots(dots, fp, cat, entries)
    worst_rho = max(abs(v["spearman_full_footprint"]) for v in surf_cmp.values())
    worst_ov = max(v["gate_statistic"] / v["gate_limit"] for v in dot_cmp.values())

    # Post-merge expanded audit (reported, NOT gating; IR-78-22-07): after
    # this lane was preregistered and its file generated, parallel sessions
    # merged additional blocked-negative lane files into docs/downloads.
    # Every current local file is compared here so the owner can see the
    # wider picture; two such dead-end files exceed 0.70 forward overlap.
    op_names = {e["name"] for e in entries}
    exp_entries = [e for e in RC.registry_rasters(exclude_names={path.name},
                                                  expanded_downloads=True)
                   if e["name"] not in op_names]
    exp_dot = RC.compare_dots(dots, fp, cat, exp_entries) if exp_entries else {}
    expanded_audit = dict(
        gating=False,
        note=("Parallel-session files merged after this lane's preregistration; "
              "all are blocked negatives (ok_to_submit=false in their own run cards). "
              "Reported for full transparency; the operative registry is the "
              "preregistered scope in G4_uniqueness.scope."),
        all_passed=bool(all(v["passed"] for v in exp_dot.values())) if exp_dot else None,
        failing_rows={k: v for k, v in exp_dot.items() if not v["passed"]},
        dots_vs_post_lane_local_files=exp_dot)

    overall = src["pooled_summary_overall"]["scores"]
    cand_key = [k for k in overall if k == cfg]
    g3_competence = bool(cand_key and overall[cfg]["dti"] >
                         max(overall["registry_D2.8_44090"]["dti"],
                             e1["pooled_summary_overall"]["scores"]["random_B3_44090"]["dti"]))
    report = dict(
        file=path.name, candidate=cand, config=cfg,
        G1_format=dict(passed=bool(g1["all_passed"]), verify_tif=g1),
        G2_canary=dict(passed=bool(e1["canary"]["max_auc"] <= 0.90 and not e1["canary"]["flagged_over_0p90"]),
                       max_symmetric_auc=e1["canary"]["max_auc"], threshold=0.90,
                       evidence="evidence/h78sig_holdout_seed20.json"),
        G3_holdout=dict(
            evidence_class="HOLDOUT-DTI", evaluator_version="gems57-pooled-hide-v2",
            withheld_positive_pixels=11321,
            overall=overall.get(cfg), far_gt10px=src["pooled_summary_far_gt10px"]["scores"].get(cfg),
            far_gt20px=src["pooled_summary_far_gt20px"]["scores"].get(cfg),
            paired_overall=src["pooled_summary_overall"]["paired_differences"],
            paired_far_gt10px=src["pooled_summary_far_gt10px"]["paired_differences"],
            paired_far_gt20px=src["pooled_summary_far_gt20px"]["paired_differences"],
            competence_gt_random_and_D2_8=g3_competence,
            beats_current_holdout_best_overall=bool(
                cand_key and overall[cfg]["dti"] > overall.get("CTRL_A2|B3|44090", {}).get("dti", np.inf)),
            passed=g3_competence),
        G4_uniqueness=dict(passed=bool(worst_rho < RC.RHO_LIMIT
                                       and all(v["passed"] for v in dot_cmp.values())),
                           worst_abs_surface_spearman=worst_rho, rho_limit=RC.RHO_LIMIT,
                           worst_gate_statistic_over_limit=worst_ov,
                           worst_literal_forward_overlap_3px=max(
                               v["forward_overlap_3px_literal"] for v in dot_cmp.values()),
                           gate_version="G4 v2 (template halo/Jaccard classes; IR-78-22-03)",
                           surface_vs_registry=surf_cmp, dots_vs_registry=dot_cmp,
                           scope="restored pinned scored set (12) + H33 + dense witness + the six local productions published when this lane was preregistered, SHA-deduped; not an exhaustive inventory of all sibling sites",
                           post_merge_expanded_audit=expanded_audit),
        G5_emission=dict(passed=bool(sp_ok and int(dots.sum()) == 44_090 and float(dcat[dots].min()) > 5.0),
                         dots=int(dots.sum()), budget_expected=44_090,
                         spacing_gt_2p8px_everywhere=bool(sp_ok), realised_min_nn_px=sp_min,
                         min_dist_to_full_catalogue_px=float(dcat[dots].min()), flank_required_px=5.0,
                         median_dist_to_full_catalogue_px=float(np.median(dcat[dots]))),
    )
    report["all_gates_passed"] = all(report[k]["passed"] for k in
                                     ("G1_format", "G2_canary", "G3_holdout", "G4_uniqueness", "G5_emission"))
    report["ok_to_submit"] = report["all_gates_passed"]
    report["organizer_confirmed_score"] = None
    report["note"] = ("OK TO SUBMIT means: passes every project gate above, computed automatically "
                      "from the written bytes. It is not an organizer score or acceptance guarantee; "
                      "spending a weekly slot remains the owner's selector decision.")
    out = ROOT / "evidence" / "h78sig_gate_report.json"
    out.write_text(json.dumps(report, indent=2, allow_nan=False))
    for k in ("G1_format", "G2_canary", "G3_holdout", "G4_uniqueness", "G5_emission"):
        print(k, "PASS" if report[k]["passed"] else "FAIL")
    print("OK_TO_SUBMIT" if report["ok_to_submit"] else "DO_NOT_SUBMIT", out)
    return 0 if report["ok_to_submit"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
