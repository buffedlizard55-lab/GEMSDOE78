#!/usr/bin/env python3
"""Experiment 3 of lane H78-NET: deployment build with network context features.

This script:
1. Reads the holdout evidence
2. Retrains A3_h78_net on the FULL catalogue (deployment-faithful)
3. Emits dots with optimal geometry
4. Audits uniqueness against registry rasters
5. Writes GeoTIFF through UNMODIFIED submission_writer
6. Re-reads independently and writes run card

The key difference from H78-A: uses network context features in addition to 
steered features.
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

from gems57 import grid as G, uniqueness as U, submission_writer as SW, validate as V
from gems57 import evaluate_holdout as EH
from gems78 import pipeline_net as PN
from gems78 import emit as E

# Registry rasters for uniqueness checking
REGISTRY = {
    "H19-5 solid (121,131 px; owner-report 0.1922)": "data/registry/h19_5_solid_nan.tif",
    "D2.8 dots (44,090; owner-report 0.2600)": "data/registry/d28_44090_nan.tif",
    "H33-2-B2 dots (37,654; owner-report 0.2778)": "data/registry/h33_2_b2_37654_zeros.tif",
}

RHO_LIMIT, OVERLAP_LIMIT = 0.90, 0.70


def read(p):
    with rasterio.open(p) as ds:
        return ds.read(1)


CONFIGS = [
    ("primary", "nms0_B3", 44_090),  # Best from holdout
    ("alternative_B2", "nms0_B2", 44_090),  # Preregistered default
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", default="evidence/h78net_holdout_seed20.json")
    ap.add_argument("--ci", default="evidence/h78net_pooled_ci_seed20.json")
    ap.add_argument("--arm", default="A3_h78_net")
    args = ap.parse_args()
    
    t0 = time.time()
    
    print("=" * 80)
    print("H78-NET: Building Submission Files")
    print("=" * 80)
    
    # Load holdout evidence
    hold = json.loads((ROOT / args.holdout).read_text())
    ci = json.loads((ROOT / args.ci).read_text())
    
    # Load grid
    g = G.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    
    print(f"\nGrid loaded:")
    print(f"  Footprint: {fp.sum():,} pixels")
    print(f"  Catalogue: {cat.sum():,} pixels")
    
    # Build feature matrix with network features (using FULL catalogue for deployment)
    print(f"\nBuilding feature matrix with network context...")
    feats_path, fmeta = PN.build_feature_matrix_net("full_net", fp, cat, force=False)
    print(f"  Features: {fmeta['n_features']} total")
    print(f"  Built in {fmeta['seconds']}s")
    
    # Training sample
    pos, negs = PN.training_sample(fp, cat, 450_000, seed=20)
    rows_pos, rows_neg = PN.flat_to_rows(pos, fp), PN.flat_to_rows(negs, fp)
    
    print(f"\nTraining sample:")
    print(f"  Positives: {len(pos):,}")
    print(f"  Negatives: {len(negs):,}")
    
    # Fit model
    print(f"\nFitting {args.arm} model...")
    clf, info = PN.fit_arm_net(feats_path, rows_pos, rows_neg, args.arm, seed=0)
    print(f"  Fit time: {info['fit_seconds']}s")
    print(f"  Features used: {info['n_features']}")
    
    # Score grid
    print(f"\nScoring grid...")
    score = PN.score_grid_net(clf, feats_path, args.arm, fp)
    np.save(ROOT / "data/processed" / f"score_full_net_{args.arm}.npy", score)
    print(f"  Score range: [{score.min():.4f}, {score.max():.4f}]")
    
    # Uniqueness on surface before placement
    print(f"\nChecking uniqueness on score surface...")
    surf = {}
    for label, rel in REGISTRY.items():
        a = read(ROOT / rel)
        a = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
        surf[label] = U.surface_rho(score, a, fp)
    
    surface_max_rho = max(abs(v["spearman_full_footprint"]) for v in surf.values())
    print(f"  Surface correlations:")
    for k, v in surf.items():
        print(f"    {k}: ρ = {v['spearman_full_footprint']:.6f}")
    print(f"  Max |ρ| = {surface_max_rho:.6f} (limit: {RHO_LIMIT})")
    
    if surface_max_rho > RHO_LIMIT:
        print(f"  ⚠️  WARNING: Surface correlation exceeds limit!")
    else:
        print(f"  ✓ Surface uniqueness passed")
    
    # Emission
    print(f"\nEmitting dots...")
    cards = {}
    
    for label, vname, n_sel in CONFIGS:
        use_nms = vname.startswith("nms1")
        bpx = float(vname.split("_B")[1])
        allowed = fp & ~E.flank_mask(cat, bpx)
        if use_nms:
            allowed &= E.ridge_nms(score, 1.0)
        
        print(f"\n  Variant: {label} ({vname}, budget={n_sel}, flank={bpx}px)")
        
        rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=max(n_sel, 60_000), pool=1_500_000)
        dots = E.prefix(rank, n_sel)
        n_dots = int(dots.sum())
        pred = dots.astype(np.float32)
        
        print(f"    Dots emitted: {n_dots:,}")
        
        # Dot audit against registry
        dot_aud = {}
        for rlabel, rel in REGISTRY.items():
            a = read(ROOT / rel)
            dot_aud[rlabel] = dict(
                fraction_of_my_dots_within_3px_of_theirs=U.dot_overlap(pred, a, 3.0),
                fraction_of_their_dots_within_3px_of_mine=U.dot_overlap(a, pred, 3.0),
                spearman_full_footprint=U.surface_rho(pred, np.where(np.isfinite(a), a, 0), fp)["spearman_full_footprint"]
            )
        
        dots_max_overlap = max(v["fraction_of_my_dots_within_3px_of_theirs"] for v in dot_aud.values())
        dots_max_rho = max(abs(v["spearman_full_footprint"]) for v in dot_aud.values())
        unique_ok = surface_max_rho <= RHO_LIMIT and dots_max_rho <= RHO_LIMIT and dots_max_overlap <= OVERLAP_LIMIT
        
        print(f"    Dot overlap vs registry:")
        for k, v in dot_aud.items():
            print(f"      {k}: {v['fraction_of_my_dots_within_3px_of_theirs']*100:.2f}% within 3px")
        print(f"    Max overlap: {dots_max_overlap*100:.2f}% (limit: {OVERLAP_LIMIT*100:.0f}%)")
        print(f"    Max |ρ| on dots: {dots_max_rho:.6f} (limit: {RHO_LIMIT})")
        print(f"    Uniqueness: {'✓ PASS' if unique_ok else '✗ FAIL'}")
        
        # Decision
        key = f"{args.arm}|{vname}|{n_sel}"
        ps = ci["pooled_summary"] if vname == "nms0_B3" else ci.get("pooled_summary", {})
        
        a0_key = next((k for k in ps.get("paired_differences", {}).keys() 
                       if k.startswith("A0_std19|")), None)
        a2_key = next((k for k in ps.get("paired_differences", {}).keys() 
                       if k.startswith("A2_h78_steered|")), None)
        
        beats_a0 = bool(a0_key and ps["paired_differences"][a0_key]["ci95"][0] > 0)
        beats_a2 = bool(a2_key and ps["paired_differences"][a2_key]["ci95"][0] > 0)
        canary_clean = len(hold["canary"]["flagged_over_0p90"]) == 0
        
        # Generate submission name and note
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        digest8 = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
        suffix = "" if label == "primary" else "-altB2"
        name = f"gems78-h78net-{n_dots}dots-{stamp}-{digest8}{suffix}-zeros"
        note = (f"GEMSDOE78 H78-NET network-aware HGB, {n_dots} dots >=283m apart, "
                f"flank<={int(bpx)}px pruned; HOLDOUT-DTI {ps['scores'][key]['dti']:.4f} s20; "
                f"not a projection")[:140]
        
        print(f"    Submission name: {name}")
        print(f"    Note ({len(note)} chars): {note}")
        
        # Write TIF
        out_dir = ROOT / "docs" / "downloads"
        out_dir.mkdir(parents=True, exist_ok=True)
        tif = out_dir / f"{name}.tif"
        
        receipt = SW.write_submission(
            tif, pred, ROOT / "data/bridge/sample_submission.tif", fp,
            note=note, name=name, catalogue=cat,
            metadata=dict(lane="H78-NET", arm=args.arm, variant=vname, 
                         budget=n_sel, label=label)
        )
        
        # Validate
        with rasterio.open(tif) as ds:
            a = ds.read(1)
            rr = dict(count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs), 
                      shape=[ds.height, ds.width], transform=list(ds.transform)[:6],
                      nodata=ds.nodata)
        
        with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ref:
            rr["matches_sample"] = dict(
                crs=str(ref.crs) == rr["crs"],
                shape=[ref.height, ref.width] == rr["shape"],
                transform=list(ref.transform)[:6] == rr["transform"]
            )
        
        rr.update(
            all_finite=bool(np.isfinite(a).all()),
            nan_inside_footprint=int(np.isnan(a[fp]).sum()),
            min=float(a.min()), max=float(a.max()),
            values_in_0_1=bool(a.min() >= 0 and a.max() <= 1),
            positive_pixels=int((a > 0).sum()),
            positives_on_catalogue=int((a[cat] > 0).sum()),
            positives_outside_footprint=int((a[~fp] > 0).sum()),
            distinct_values=[float(v) for v in np.unique(a)],
            sha256=V.sha256(tif), bytes=tif.stat().st_size
        )
        
        validator_ok = all([
            rr["count"] == 1, rr["dtype"] == "float32", all(rr["matches_sample"].values()),
            rr["all_finite"], rr["nan_inside_footprint"] == 0, rr["values_in_0_1"],
            rr["positives_on_catalogue"] == 0, rr["positives_outside_footprint"] == 0,
            rr["positive_pixels"] == n_dots
        ])
        
        ok_to_submit = bool(beats_a0 and beats_a2 and canary_clean and unique_ok and 
                           validator_ok and label == "primary")
        
        if label == "primary":
            verdict = "promote" if ok_to_submit else "negative"
        else:
            verdict = "alternative (inspection only)"
        
        print(f"    Validator: {'✓ PASS' if validator_ok else '✗ FAIL'}")
        print(f"    Canary clean: {'✓ PASS' if canary_clean else '✗ FAIL'}")
        print(f"    Beats A0: {'✓' if beats_a0 else '✗'}")
        print(f"    Beats A2: {'✓' if beats_a2 else '✗'}")
        print(f"    Verdict: {verdict}")
        
        # Build run card
        cards[label] = dict(
            lane="H78-NET network-aware lineament context",
            repository="buffedlizard55-lab/GEMSDOE78",
            label=label,
            built_utc=stamp,
            hypothesis="Unmapped faults are most likely to occur in structural gaps within the visible fault network. Network-aware context features (density, junctions, gaps) raise the kernel credit per emitted dot on withheld fault segments beyond orientation-steered features alone.",
            mechanism="Network context: fault density, junction proximity, structural gaps, segment length, distance bins, strike coherence. Combined with steered derivative filters. HGB learner. Sparse dots at >=2.8px with catalogue flank removed.",
            non_fault_mimic="Drainage networks, lithologic contacts, dune ridges aligned with range fronts.",
            holdout=dict(
                evidence_class="HOLDOUT-DTI",
                evaluator_version=ps.get("evaluator_version", "gems57-pooled-hide-v2"),
                candidate=key,
                dti=ps["scores"][key]["dti"] if key in ps.get("scores", {}) else 0.0,
                ci95=ps["scores"][key]["ci95"] if key in ps.get("scores", {}) else [0.0, 0.0],
                withheld_positive_pixels=ps["scores"][key]["withheld_positive_pixels"] if key in ps.get("scores", {}) else 0,
                controls={k: dict(dti=v["dti"], ci95=v["ci95"]) 
                         for k, v in ps.get("scores", {}).items() if k != key},
                paired_differences=ps.get("paired_differences", {}),
                beats_A0_std19_ci=beats_a0,
                beats_A2_h78_steered_ci=beats_a2,
                seed=hold["seed"],
                hide_frac=hold["hide_frac"],
                buffer_px=hold["buffer_px"]
            ),
            canary=dict(
                threshold=0.90,
                max_single_feature_auc=hold["canary"]["max_auc"],
                flagged=hold["canary"]["flagged_over_0p90"],
                clean=canary_clean
            ),
            uniqueness=dict(
                rho_limit=RHO_LIMIT,
                overlap_limit=OVERLAP_LIMIT,
                surface_before_placement=surf,
                final_dots=dot_aud,
                surface_max_abs_rho=surface_max_rho,
                dots_max_abs_rho=dots_max_rho,
                dots_max_overlap=dots_max_overlap,
                passed=unique_ok
            ),
            raster=dict(
                file=tif.name,
                sha256=rr["sha256"],
                bytes=rr["bytes"],
                zip=receipt["zip_file"],
                zip_sha256=receipt["zip_sha256"],
                dots=n_dots,
                variant=vname,
                budget=n_sel,
                flank_px=bpx,
                ridge_nms=use_nms,
                min_separation_px=2.8
            ),
            validator=dict(
                independent_reread=rr,
                passed=validator_ok,
                writer_receipt_checks=receipt["validator"]["checks"]
            ),
            submission_name=name,
            submission_note=note,
            note_chars=len(note),
            ok_to_submit=ok_to_submit,
            verdict=verdict,
            organizer_confirmed_score=None,
            seconds=round(time.time() - t0, 1),
            fit=info,
            features={k: v for k, v in fmeta.items() if k != "names"},
        )
        
        print(f"\n  File: {tif.name}")
        print(f"  SHA256: {rr['sha256']}")
        print(f"  Size: {rr['bytes']:,} bytes")
    
    # Save primary card with alternatives
    card = cards["primary"]
    card["alternatives"] = {k: v for k, v in cards.items() if k != "primary"}
    
    (ROOT / "evidence/h78net_run_card.json").write_text(
        json.dumps(card, indent=2, default=float)
    )
    (ROOT / "docs/data/submission_net.json").write_text(
        json.dumps(card, indent=2, default=float)
    )
    
    print(f"\n" + "=" * 80)
    print(f"BUILD COMPLETE")
    print("=" * 80)
    print(f"\nPrimary submission:")
    print(f"  File: docs/downloads/{card['raster']['file']}")
    print(f"  SHA256: {card['raster']['sha256']}")
    print(f"  HOLDOUT-DTI: {card['holdout']['dti']:.6f} [{card['holdout']['ci95'][0]:.6f}, {card['holdout']['ci95'][1]:.6f}]")
    print(f"  Verdict: {card['verdict']}")
    print(f"  OK to submit: {card['ok_to_submit']}")
    print(f"\n  Canary: max AUC = {card['canary']['max_single_feature_auc']:.4f}, clean = {card['canary']['clean']}")
    print(f"  Uniqueness: passed = {card['uniqueness']['passed']}")
    print(f"  Validator: passed = {card['validator']['passed']}")
    
    if card['ok_to_submit']:
        print(f"\n  ✓✓✓ READY FOR ORGANIZER SUBMISSION ✓✓✓")
        print(f"\n  To submit:")
        print(f"    1. Download: docs/downloads/{card['raster']['file']}")
        print(f"    2. Go to: https://www.drivendata.org/competitions/306/competition-doe-gems/")
        print(f"    3. Click 'New submission'")
        print(f"    4. Upload the TIF file")
        print(f"    5. Paste note: '{card['submission_note']}'")
        print(f"    6. Record ORGANIZER-CONFIRMED score in registry/live_scores.csv")
    else:
        print(f"\n  ✗ NOT READY FOR SUBMISSION")
        if not beats_a0:
            print(f"    - Does not beat A0 baseline")
        if not beats_a2:
            print(f"    - Does not beat A2 steered baseline")
        if not canary_clean:
            print(f"    - Leakage canary failed")
        if not unique_ok:
            print(f"    - Uniqueness check failed")
        if not validator_ok:
            print(f"    - Validation failed")


if __name__ == "__main__":
    main()
