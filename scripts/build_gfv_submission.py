#!/usr/bin/env python3
"""Full-Catalogue 136-Band H78-GFV Production Builder & 94-Repo Gate Validator.

Builds the production single-band float32 GeoTIFF + single-TIFF ZIP via shared
``vendor/gems57/submission_writer.py`` from the exact 136-band Dual-Head H78-GFV
architecture validated at HOLDOUT-DTI 0.2149 (seed 20) and 0.2198 (seed 30),
enforcing all automated uniqueness and portal safety checks in code.
"""
from __future__ import annotations

import datetime as dt
import gc
import json
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, label
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57 import emit as E57  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import submission_writer as SW  # noqa: E402
from gems78 import emit as E78  # noqa: E402
from gems78 import gfv  # noqa: E402
from gems78 import pipeline as P  # noqa: E402
from run_gfv_matched_global_benchmark import (  # noqa: E402
    gather_a2_plus_ext_geo,
    write_a2_bin_zero_mmap,
)
from run_gfv_tournament import (  # noqa: E402
    fit_hetero_classifier,
    fit_kernel_self_credit,
    predict_hetero_proba,
    predict_kernel_self_credit,
)


def log(*args):
    print(time.strftime("%H:%M:%S"), *args, flush=True)


def main():
    t0 = time.time()
    warnings.filterwarnings("ignore")
    DATA = ROOT / ".cache" / "gems_data"
    FEAT = ROOT / ".cache" / "features"
    WORK = ROOT / ".cache" / "work"
    REG_FULL = ROOT / ".cache" / "full_registry"
    SUB_DIR = ROOT / "submissions"
    DL_DIR = ROOT / "docs" / "downloads"
    EVID = ROOT / "evidence"
    SUB_DIR.mkdir(parents=True, exist_ok=True)
    DL_DIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    g = G.load_grid(DATA)
    fp = g.footprint
    fp_idx = np.flatnonzero(fp)
    cat = g.catalogue.astype(bool)
    allow_live = fp & (~E78.flank_mask(cat, 3.0))
    log(f"Full-catalogue grid loaded: cat={int(cat.sum()):,}, allow_live={int(allow_live.sum()):,}")

    # 1. Compute full-catalogue 136-band Dual-Head posteriors (p_full, m_full)
    p136_path = WORK / "prod136_p_gfv.npy"
    m136_path = WORK / "prod136_m_gfv.npy"
    oof_e1_p = np.load(WORK / "prod_oof_e1_p.npy").astype(np.float32)

    if p136_path.exists() and m136_path.exists():
        p_gfv = np.load(p136_path).astype(np.float32)
        m_gfv = np.load(m136_path).astype(np.float32)
        log("Loaded cached prod136_p_gfv.npy & prod136_m_gfv.npy")
    else:
        a2_bin = WORK / "a2_fp103_fullcat.bin"
        sec = write_a2_bin_zero_mmap(a2_bin, fp, cat, n_blocks=8)
        log(f"Built full-catalogue 103-band A2 matrix in {sec}s")

        p5, p995 = np.percentile(oof_e1_p[fp], [5.0, 99.5])
        weak_oof = np.clip((oof_e1_p - p5) / max(float(p995 - p5), 1e-6), 0.0, 1.0)
        strike_theta = np.load(FEAT / "gfv_phys_strike.npy").astype(np.float32)
        hydro_nodes2x = np.load(FEAT / "gfv_hydro_nodes2x.npy")

        comp_cat, n_comp = label(cat, structure=np.ones((3, 3), dtype=np.int32))
        rng_n = np.random.default_rng(7899)
        comp_fold = np.zeros(n_comp + 1, dtype=np.int32)
        comp_fold[1:] = rng_n.integers(0, 3, size=n_comp)

        X_parts, yp_parts, ym_parts, sw_parts = [], [], [], []
        for k in range(3):
            vis_ctx = cat & (comp_fold[comp_cat] != k)
            vis_tgt = cat & (comp_fold[comp_cat] == k)
            geo_k = gfv.compute_geodesic_network(
                vis_ctx, weak_oof, strike_theta, fp, hydro_nodes2x, n_color_rounds=6, seed=7400 + k
            )
            d_ctx = distance_transform_edt(~vis_ctx).astype(np.float32)
            d_tgt = distance_transform_edt(~vis_tgt).astype(np.float32)
            vp = fp & (d_ctx > 3.0)

            s0 = vp & vis_tgt
            s1 = vp & (~vis_tgt) & (d_tgt <= 3.0)
            s2 = vp & (d_tgt > 3.0) & (d_ctx <= 28.0)
            s3 = vp & (d_tgt > 3.0) & (d_ctx > 28.0)
            y0, x0 = np.nonzero(s0)
            y1, x1 = np.nonzero(s1)
            y2, x2 = np.nonzero(s2)
            y3, x3 = np.nonzero(s3)
            c1 = rng_n.choice(y1.size, size=min(19_000, y1.size), replace=False)
            c2 = rng_n.choice(y2.size, size=min(29_000, y2.size), replace=False)
            c3 = rng_n.choice(y3.size, size=min(29_000, y3.size), replace=False)

            ys_k = np.concatenate([y0, y1[c1], y2[c2], y3[c3]])
            xs_k = np.concatenate([x0, x1[c1], x2[c2], x3[c3]])
            rows_k = P.flat_to_rows(ys_k.astype(np.int64) * fp.shape[1] + xs_k.astype(np.int64), fp)
            X_parts.append(gather_a2_plus_ext_geo(a2_bin, FEAT / "fp101_f16.bin", rows_k, ys_k, xs_k, geo_k))
            yp_parts.append(np.r_[np.ones(y0.size, np.int32), np.zeros(c1.size + c2.size + c3.size, np.int32)])
            ym_parts.append(np.maximum(0.0, 1.0 - d_tgt[ys_k, xs_k] / 3.0).astype(np.float32))
            sw_parts.append(np.r_[
                np.ones(y0.size, np.float64),
                np.full(c1.size, y1.size / max(c1.size, 1), np.float64),
                np.full(c2.size, y2.size / max(c2.size, 1), np.float64),
                np.full(c3.size, y3.size / max(c3.size, 1), np.float64),
            ])
            del geo_k, d_ctx, d_tgt
            gc.collect()
            log(f"Full-cat nested split {k+1}/3 sampled")

        geo_live = gfv.compute_geodesic_network(
            cat, weak_oof, strike_theta, fp, hydro_nodes2x, n_color_rounds=8, seed=7999
        )
        X_tr = np.concatenate(X_parts, axis=0)
        yp_tr = np.concatenate(yp_parts, axis=0)
        ym_tr = np.concatenate(ym_parts, axis=0)
        sw_tr = np.concatenate(sw_parts, axis=0)
        del X_parts, yp_parts, ym_parts, sw_parts
        gc.collect()

        models_p = fit_hetero_classifier(X_tr, yp_tr, sw_tr, seed=9500)
        models_m = fit_kernel_self_credit(X_tr, ym_tr, sw_tr, seed=9600)
        del X_tr, yp_tr, ym_tr, sw_tr
        gc.collect()

        p_fp = np.empty(fp_idx.size, dtype=np.float32)
        m_fp = np.empty(fp_idx.size, dtype=np.float32)
        step = 520_000
        with a2_bin.open("rb") as fa, (FEAT / "fp101_f16.bin").open("rb") as fe:
            for r0 in range(0, fp_idx.size, step):
                r1 = min(r0 + step, fp_idx.size)
                nc = r1 - r0
                ba = np.fromfile(fa, dtype=np.float32, count=nc * 103).reshape(nc, 103)
                be = np.fromfile(fe, dtype=np.float16, count=nc * 101).reshape(nc, 101)[:, 80:101]
                fc = fp_idx[r0:r1]
                Xb = np.empty((nc, 136), dtype=np.float32)
                Xb[:, :103] = ba
                Xb[:, 103:124] = be.astype(np.float32)
                for j in range(12):
                    Xb[:, 124 + j] = geo_live[j].ravel()[fc]
                del ba, be
                p_fp[r0:r1] = predict_hetero_proba(models_p, Xb)
                m_fp[r0:r1] = predict_kernel_self_credit(models_m, Xb)
                del Xb
        del models_p, models_m, geo_live
        a2_bin.unlink(missing_ok=True)
        gc.collect()

        p_gfv = np.zeros(fp.shape, dtype=np.float32)
        m_gfv = np.zeros(fp.shape, dtype=np.float32)
        p_gfv[fp] = p_fp
        m_gfv[fp] = m_fp
        del p_fp, m_fp
        np.save(p136_path, p_gfv.astype(np.float16))
        np.save(m136_path, m_gfv.astype(np.float16))
        log(f"Saved full-catalogue 136-band Dual-Head posteriors ({time.time()-t0:.1f}s)")

    # 2. Pre-placement continuous surface Spearman check across ALL 127 continuous org rasters + local
    inv_doc = json.loads((REG_FULL / "complete_93repo_inventory.json").read_text())
    entries = inv_doc["rasters"]

    p_prod = np.clip(0.86 * p_gfv + 0.14 * oof_e1_p + 1e-5, 0.0, 1.0).astype(np.float32)
    m_prod = np.clip(m_gfv, 0.0, 1.0).astype(np.float32)
    cont_surface = (E57.expected_credit(np.where(allow_live, p_prod, 0.0)) + 0.034 * m_prod).astype(np.float32)

    allow_flat = np.flatnonzero(allow_live)
    sub_sp = np.random.default_rng(7878).choice(allow_flat, size=250_000, replace=False)
    v_self = cont_surface.ravel()[sub_sp].astype(np.float64)

    surface_corrs = {}
    for tif_p in sorted((ROOT / "data" / "registry").glob("*.tif")):
        with rasterio.open(tif_p) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sub_sp].astype(np.float64)
        rho = float(spearmanr(v_self, arr).statistic)
        if np.isfinite(rho):
            surface_corrs[f"local:{tif_p.name}"] = round(rho, 6)

    n_cont_org = 0
    for e in entries:
        if not e["is_binary"] and e["has_variation"] and Path(e["file"]).is_file():
            with rasterio.open(e["file"]) as ds:
                arr = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sub_sp].astype(np.float64)
            rho = float(spearmanr(v_self, arr).statistic)
            if np.isfinite(rho):
                surface_corrs[f"{e['repo_first']}:{e['submission']}"] = round(rho, 6)
                n_cont_org += 1

    top_surface_corrs = dict(sorted(surface_corrs.items(), key=lambda kv: -abs(kv[1]))[:20])
    max_abs_rho = max((abs(v) for v in surface_corrs.values()), default=0.0)
    max_rho_ref = max(surface_corrs.items(), key=lambda kv: abs(kv[1]))[0]
    log(f"PRE-PLACEMENT SURFACE SPEARMAN ({n_cont_org} org continuous + local): MAX |rho| = {max_abs_rho:.5f} ({max_rho_ref}) [gate <= 0.90]")
    if max_abs_rho > 0.90:
        raise RuntimeError(f"PARALLEL-RUN STOP: continuous surface |rho| = {max_abs_rho:.5f} > 0.90!")

    # 3. CELF Dinkelbach dot placement with strict <= 0.665 cap across ALL 736 discriminating rasters
    fp_to_pos = np.full(fp.size, -1, dtype=np.int32)
    fp_to_pos[fp_idx] = np.arange(fp_idx.size, dtype=np.int32)
    n_bytes = int(inv_doc["packbits_row_bytes"])

    p_eff = np.where(allow_live, p_prod, 0.0).astype(np.float32)
    cand_cap = 3_800_000
    ek_init = E57.expected_credit(p_eff)
    c_ys, c_xs = np.nonzero(allow_live & (ek_init > 0.0))
    if c_ys.size > cand_cap:
        ti = np.argpartition(-ek_init[c_ys, c_xs], cand_cap)[:cand_cap]
        c_ys, c_xs = c_ys[ti], c_xs[ti]
    oc = np.argsort(-ek_init[c_ys, c_xs], kind="stable")
    c_ys = c_ys[oc].astype(np.int32)
    c_xs = c_xs[oc].astype(np.int32)
    cand_fp_pos = fp_to_pos[c_ys.astype(np.int64) * fp.shape[1] + c_xs.astype(np.int64)]

    disc_idx = [i for i, e in enumerate(entries) if e["halo_coverage"] < 0.70]
    probe_top = cand_fp_pos[:42_000]
    active_ids = []
    with (REG_FULL / "halo_packbits.bin").open("rb") as hf:
        for i, e in enumerate(entries):
            raw = np.fromfile(hf, dtype=np.uint8, count=n_bytes)
            if e["halo_coverage"] >= 0.70:
                continue
            hb = np.unpackbits(raw)[: fp_idx.size]
            ov = float(hb[probe_top].mean())
            if ov >= 0.63:
                active_ids.append((ov, i, hb[cand_fp_pos].copy()))
    active_ids.sort(key=lambda t: -t[0])
    log(f"Unconstrained top-42k probe max overlap = {active_ids[0][0] if active_ids else 0:.4f} ({len(active_ids)} >= 0.63)")

    target_budget = 37_654
    max_allowed_fwd = 0.665  # safe margin strictly below 0.70 across all 736 discriminating rasters
    active_map = {idx_r: row_u8 for _, idx_r, row_u8 in active_ids[:48]}

    for cp_iter in range(6):
        hc_mat = np.stack(list(active_map.values()), axis=0) if active_map else None
        k_exp_live = max(float(p_eff.sum()), 12_000.0)
        alloc = E57.dinkelbach_allocate(
            p_eff,
            m_prod,
            allow_live,
            budget=target_budget,
            k_truth=k_exp_live,
            min_spacing_px=2.8,
            dinkelbach_iters=3,
            candidate_cap=cand_cap,
            halo_constraints=hc_mat,
            halo_max_hits=int(max_allowed_fwd * target_budget) if hc_mat is not None else None,
        )
        emitted_fp = alloc.emitted.ravel()[fp_idx].astype(bool)
        n_emitted = int(emitted_fp.sum())

        fwd_disc = []
        fwd_all = []
        new_violations = []
        with (REG_FULL / "halo_packbits.bin").open("rb") as hf:
            for i, e in enumerate(entries):
                h_raw = np.fromfile(hf, dtype=np.uint8, count=n_bytes)
                hb = np.unpackbits(h_raw)[: fp_idx.size].view(bool)
                fwd = float(hb[emitted_fp].sum()) / max(n_emitted, 1)
                fwd_all.append((fwd, e["repo_first"], e["submission"], e["halo_coverage"]))
                if e["halo_coverage"] < 0.70:
                    fwd_disc.append((fwd, i, e["repo_first"], e["submission"], e["halo_coverage"]))
                    if fwd > 0.680 and i not in active_map:
                        new_violations.append((fwd, i, hb[cand_fp_pos].astype(np.uint8).copy()))

        fwd_disc.sort(key=lambda t: -t[0])
        log(f"Cutting-plane pass {cp_iter+1}: n_dots={n_emitted:,}, max_disc_fwd_3px={fwd_disc[0][0]:.5f} ({fwd_disc[0][2]}:{fwd_disc[0][3]})")
        if not new_violations and fwd_disc[0][0] <= 0.70:
            break
        for _, idx_r, row_u8 in new_violations:
            active_map[idx_r] = row_u8

    self_halo_fp = (distance_transform_edt(~alloc.emitted) <= 3.0).ravel()[fp_idx]
    top_disc_records = []
    with (REG_FULL / "sup_packbits.bin").open("rb") as sf:
        sup_bytes_all = sf.read()
    for fwd_v, idx_r, repo_n, rast_n, cov_f in fwd_disc[:25]:
        off = idx_r * n_bytes
        sup_b = np.unpackbits(np.frombuffer(sup_bytes_all, dtype=np.uint8, count=n_bytes, offset=off))[: fp_idx.size].view(bool)
        rev_v = float(self_halo_fp[sup_b].sum()) / max(int(sup_b.sum()), 1)
        mut_v = min(fwd_v, rev_v)
        top_disc_records.append({
            "repo": repo_n,
            "name": rast_n,
            "forward_3px": round(fwd_v, 6),
            "reverse_3px": round(rev_v, 6),
            "mutual_3px": round(mut_v, 6),
            "halo_coverage_frac": round(cov_f, 5),
        })
    del sup_bytes_all
    gc.collect()

    n_disc_over_070 = sum(1 for x in fwd_disc if x[0] > 0.70)
    if n_disc_over_070 > 0:
        raise RuntimeError(f"PARALLEL-RUN STOP: {n_disc_over_070} discriminating rasters exceed 0.70!")

    # Remove old draft submissions before writing single authoritative candidate
    for old_f in SUB_DIR.glob("gems78-h78-gfv-*"):
        old_f.unlink()

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git_sha = subprocess.check_output(["git", "rev-parse", "--short=8", "HEAD"], cwd=ROOT, text=True).strip()
    stem = f"gems78-h78-gfv-136b-dink-{ts}-{git_sha}-zeros"
    tif_path = SUB_DIR / f"{stem}.tif"
    portal_note = (
        f"H78-GFV 136b Fermat+Hydro+3DEP Dinkelbach ({n_emitted} dots; "
        f"HOLDOUT 0.2149/0.2198; 0/736 disc dup; density-probe 1.0 disclosed)"
    )[:140]

    audit_meta = {
        "surface_spearman_pre_placement": {
            "org_continuous_surfaces_checked": n_cont_org,
            "max_abs_rho": round(max_abs_rho, 6),
            "max_abs_rho_ref": max_rho_ref,
            "gate_limit": 0.90,
            "passed": max_abs_rho <= 0.90,
            "top_20_references": top_surface_corrs,
        },
        "dot_overlap_audit_full_93_repos": {
            "total_repos_scanned": inv_doc["repos_scanned"],
            "total_blobs_inspected": inv_doc["blobs_inspected"],
            "total_unique_rasters_scanned": len(entries),
            "discriminating_rasters_count": len(disc_idx),
            "space_filler_rasters_count": len(entries) - len(disc_idx),
            "discriminating_forward_3px_over_0_70": n_disc_over_070,
            "max_forward_3px_vs_736_discriminating": round(fwd_disc[0][0], 6),
            "max_forward_3px_vs_736_ref": f"{fwd_disc[0][2]}:{fwd_disc[0][3]}",
            "max_mutual_3px_top25": round(max(r["mutual_3px"] for r in top_disc_records), 6),
            "max_forward_3px_vs_800_all_including_space_fillers": round(max(x[0] for x in fwd_all), 6),
            "space_filler_witness_note": (
                "5GEMSDOE:gems-density-probe-20261004T201937Z-b909a75f-nan.tif covers 100.00% "
                "(uncovered_allowed_pixels=0) of the allowed footprint within 3 px, forcing "
                "literal all-800 forward overlap = 1.0000 on every non-empty submission."
            ),
            "top_15_discriminating_neighbors": top_disc_records[:15],
        },
        "dinkelbach_allocation": {
            "n_dots": n_emitted,
            "surrogate_dti": round(alloc.surrogate_dti, 6),
            "expected_covered_credit": round(alloc.expected_covered_credit, 3),
            "expected_self_credit": round(alloc.expected_self_credit, 3),
        },
    }

    arr_out = np.where(alloc.emitted & allow_live, 1.0, 0.0).astype(np.float32)
    writer_receipt = SW.write_submission(
        tif_path,
        arr_out,
        DATA / "sample_submission.tif",
        fp,
        note=portal_note,
        name=stem,
        catalogue=cat,
        metadata=audit_meta,
    )

    # Mirror byte-for-byte into docs/downloads/ so GitHub Pages download links work cleanly
    for ext in (".tif", ".zip", ".json"):
        shutil.copy2(SUB_DIR / f"{stem}{ext}", DL_DIR / f"{stem}{ext}")

    verify_out = subprocess.check_output(
        [sys.executable, str(ROOT / "scripts" / "verify_tif.py"), str(tif_path)],
        cwd=ROOT,
        text=True,
    )

    full_receipt = {
        "submission_name": stem,
        "tif_path": f"submissions/{tif_path.name}",
        "docs_download_tif": f"docs/downloads/{tif_path.name}",
        "tif_sha256": writer_receipt["sha256"],
        "tif_bytes": writer_receipt["bytes"],
        "zip_path": f"submissions/{writer_receipt['zip_file']}",
        "docs_download_zip": f"docs/downloads/{writer_receipt['zip_file']}",
        "zip_sha256": writer_receipt["zip_sha256"],
        "zip_bytes": (SUB_DIR / writer_receipt["zip_file"]).stat().st_size,
        "portal_note": portal_note,
        "portal_note_chars": len(portal_note),
        "writer_receipt": writer_receipt,
        "verify_tif_cli_output": verify_out.strip(),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (EVID / "h78gfv_production_receipt.json").write_text(json.dumps(full_receipt, indent=2))
    log(f"SUCCESS! Wrote {tif_path.name} ({n_emitted:,} dots, sha256={writer_receipt['sha256'][:16]}...) in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
