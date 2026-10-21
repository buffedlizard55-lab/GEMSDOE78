#!/usr/bin/env python3
"""Experiment 3 of lane H78: deployment build, uniqueness audit, validator, run card.

Reads the emission configuration selected by the preregistered rule from the
holdout evidence (best A2 config), retrains the candidate arm on the FULL
catalogue (strike field from the full catalogue -- deployment-faithful), emits
the dots, audits uniqueness against the registry rasters, writes the GeoTIFF
through the UNMODIFIED shared ``submission_writer`` (fail-closed), re-reads the
file independently, and writes ``evidence/h78_run_card.json`` plus
``docs/data/submission.json`` for the site.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import grid as G, uniqueness as U, submission_writer as SW, validate as V  # noqa: E402
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems78 import pipeline as P, emit as E  # noqa: E402

REGISTRY = {
    "H19-5 solid (121,131 px; owner-report 0.1922)": "data/registry/h19_5_solid_nan.tif",
    "D2.8 dots (44,090; owner-report 0.2600)": "data/registry/d28_44090_nan.tif",
    "H33-2-B2 dots (37,654; owner-report 0.2778)": "data/registry/h33_2_b2_37654_zeros.tif",
}
RHO_LIMIT, OVERLAP_LIMIT = 0.90, 0.70


def read(p):
    with rasterio.open(p) as ds:
        return ds.read(1)


CONFIGS = [  # (label, variant, budget) -- see registry/preregistration.json amendments IR-78-01 / IR-78-01b
    ("primary", "nms0_B3", 44_090),
    ("alternative_B2_preregistered_default", "nms0_B2", 44_090),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", default="evidence/h78_holdout_seed20.json")
    ap.add_argument("--ci", default="evidence/h78_pooled_ci_seed20.json")
    ap.add_argument("--arm", default="A2_h78_steered")
    args = ap.parse_args()
    t0 = time.time()
    hold = json.loads((ROOT / args.holdout).read_text())
    ci = json.loads((ROOT / args.ci).read_text())

    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    feats_path, fmeta = P.build_feature_matrix("full", fp, cat)
    pos, negs = P.training_sample(fp, cat, 450_000, seed=20)
    clf, info = P.fit_arm(feats_path, P.flat_to_rows(pos, fp), P.flat_to_rows(negs, fp), args.arm, seed=0)
    print("fit", info)
    score = P.score_grid(clf, feats_path, args.arm, fp)
    np.save(ROOT / "data/processed" / f"score_full_{args.arm}.npy", score)

    # --- uniqueness on the SURFACE before placement ---
    surf = {}
    for label, rel in REGISTRY.items():
        a = read(ROOT / rel)
        a = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
        surf[label] = U.surface_rho(score, a, fp)
    surface_max_rho = max(abs(v["spearman_full_footprint"]) for v in surf.values())
    print("surface rho", {k: round(v["spearman_full_footprint"], 4) for k, v in surf.items()})

    # --- emission ---
    cards = {}
    for label, vname, n_sel in CONFIGS:
        use_nms = vname.startswith("nms1")
        bpx = float(vname.split("_B")[1])
        allowed = fp & ~E.flank_mask(cat, bpx)
        if use_nms:
            allowed &= E.ridge_nms(score, 1.0)
        rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=max(n_sel, 60_000), pool=1_500_000)
        dots = E.prefix(rank, n_sel)
        n_dots = int(dots.sum())
        pred = dots.astype(np.float32)  # binary, zeros outside footprint

        dot_aud = {}
        for rlabel, rel in REGISTRY.items():
            a = read(ROOT / rel)
            dot_aud[rlabel] = dict(fraction_of_my_dots_within_3px_of_theirs=U.dot_overlap(pred, a, 3.0),
                                   fraction_of_their_dots_within_3px_of_mine=U.dot_overlap(a, pred, 3.0),
                                   spearman_full_footprint=U.surface_rho(pred, np.where(np.isfinite(a), a, 0), fp)["spearman_full_footprint"])
        dots_max_overlap = max(v["fraction_of_my_dots_within_3px_of_theirs"] for v in dot_aud.values())
        dots_max_rho = max(abs(v["spearman_full_footprint"]) for v in dot_aud.values())
        unique_ok = surface_max_rho <= RHO_LIMIT and dots_max_rho <= RHO_LIMIT and dots_max_overlap <= OVERLAP_LIMIT
        print(label, "dot overlap", {k: round(v["fraction_of_my_dots_within_3px_of_theirs"], 4) for k, v in dot_aud.items()}, "unique_ok", unique_ok)

        # --- decision per preregistration (+ amendment IR-78-01) ---
        key = f"{args.arm}|{vname}|{n_sel}"
        ps = ci["alternative_B3_summary"] if vname == "nms0_B3" else ci["pooled_summary"]
        assert key in ps["scores"], key
        diffs = ps["paired_differences"]
        a0_key = next((k for k in diffs if k.startswith("A0_std19|")), None)
        a1_key = next((k for k in diffs if k.startswith("A1_iso|")), None)
        beats_a0 = bool(a0_key and diffs[a0_key]["ci95"][0] > 0)
        beats_a1 = bool(a1_key and diffs[a1_key]["ci95"][0] > 0)
        canary_clean = len(hold["canary"]["flagged_over_0p90"]) == 0

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        digest8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
        suffix = "" if label == "primary" else "-altB2"
        name = f"gems78-h78a-strike-steered-{n_dots}dots-{stamp}-{digest8}{suffix}-zeros"
        note = (f"GEMSDOE78 H78-A strike-steered HGB, {n_dots} dots >=283m apart, flank<={int(bpx)}px pruned; "
                f"HOLDOUT-DTI {ps['scores'][key]['dti']:.4f} s20; not a projection")[:140]
        out_dir = ROOT / "docs" / "downloads"
        out_dir.mkdir(parents=True, exist_ok=True)
        tif = out_dir / f"{name}.tif"
        receipt = SW.write_submission(tif, pred, ROOT / "data/bridge/sample_submission.tif", fp,
                                      note=note, name=name, catalogue=cat,
                                      metadata=dict(lane="H78-A", arm=args.arm, variant=vname, budget=n_sel, label=label))

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
                  positives_outside_footprint=int((a[~fp] > 0).sum()), distinct_values=[float(v) for v in np.unique(a)],
                  sha256=V.sha256(tif), bytes=tif.stat().st_size)
        validator_ok = all([rr["count"] == 1, rr["dtype"] == "float32", all(rr["matches_sample"].values()),
                            rr["all_finite"], rr["nan_inside_footprint"] == 0, rr["values_in_0_1"],
                            rr["positives_on_catalogue"] == 0, rr["positives_outside_footprint"] == 0,
                            rr["positive_pixels"] == n_dots])
        ok_to_submit = bool(beats_a0 and canary_clean and unique_ok and validator_ok and label == "primary")
        verdict = "promote" if ok_to_submit else ("negative" if not (beats_a0 and canary_clean and unique_ok and validator_ok)
                                                  else "alternative (preregistered 2-px flank default; -0.024 HOLDOUT-DTI vs primary; inspection only)")

        cards[label] = dict(
            lane="H78-A strike-steered lineament learning", repository="buffedlizard55-lab/GEMSDOE78",
            label=label, built_utc=stamp,
            hypothesis=json.loads((ROOT / "registry/preregistration.json").read_text())["hypothesis"],
            mechanism="Sub-parallel normal-fault arrays: unmapped strands share the regional strike of mapped neighbours; "
                      "derivative filters steered into the visible-catalogue strike frame separate structurally aligned "
                      "lineaments from oblique ones; HGB learner; sparse dots at >= sqrt(8) px with the catalogue flank removed.",
            non_fault_mimic="Bedding/lithologic contacts and alluvial-fan drainage aligned with range fronts; dune ridges.",
            holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=ps["evaluator_version"],
                         candidate=key, dti=ps["scores"][key]["dti"], ci95=ps["scores"][key]["ci95"],
                         withheld_positive_pixels=ps["scores"][key]["withheld_positive_pixels"],
                         controls={k: dict(dti=v["dti"], ci95=v["ci95"]) for k, v in ps["scores"].items() if k != key},
                         paired_differences=diffs, beats_A0_std19_ci=beats_a0, beats_A1_iso_ci=beats_a1,
                         seed=hold["seed"], hide_frac=hold["hide_frac"], buffer_px=hold["buffer_px"]),
            canary=dict(threshold=0.90, max_single_feature_auc=hold["canary"]["max_auc"],
                        flagged=hold["canary"]["flagged_over_0p90"], clean=canary_clean),
            uniqueness=dict(rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT, surface_before_placement=surf,
                            final_dots=dot_aud, surface_max_abs_rho=surface_max_rho, dots_max_abs_rho=dots_max_rho,
                            dots_max_overlap=dots_max_overlap, passed=unique_ok),
            raster=dict(file=tif.name, sha256=rr["sha256"], bytes=rr["bytes"], zip=receipt["zip_file"],
                        zip_sha256=receipt["zip_sha256"], dots=n_dots, variant=vname, budget=n_sel,
                        flank_px=bpx, ridge_nms=use_nms, min_separation_px=2.8),
            validator=dict(independent_reread=rr, passed=validator_ok, writer_receipt_checks=receipt["validator"]["checks"]),
            submission_name=name, submission_note=note, note_chars=len(note),
            ok_to_submit=ok_to_submit, verdict=verdict,
            organizer_confirmed_score=None,
            seconds=round(time.time() - t0, 1),
            fit=info, features={k: v for k, v in fmeta.items() if k != "names"},
        )
        print(json.dumps(dict(label=label, verdict=verdict, ok_to_submit=ok_to_submit, file=tif.name, sha256=rr["sha256"],
                              dots=n_dots, holdout_dti=cards[label]["holdout"]["dti"]), indent=1))
    card = cards["primary"]
    card["alternatives"] = {k: v for k, v in cards.items() if k != "primary"}
    (ROOT / "evidence/h78_run_card.json").write_text(json.dumps(card, indent=2, default=float))
    (ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/data/submission.json").write_text(json.dumps(card, indent=2, default=float))


if __name__ == "__main__":
    main()
