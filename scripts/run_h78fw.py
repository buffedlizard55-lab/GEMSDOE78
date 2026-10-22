#!/usr/bin/env python3
"""Experiment 1 of lane H78-FW: broad flank warp + central potential-field step.

Frozen protocol: research/2026-10-22-h78fw-hypotheses.md,
registry/preregistration_h78fw.json. One candidate, one budget (44,090),
one seed (20). Catalogue-blind unsupervised surface, no learner.

Writes a blocked inspection TIFF (DO-NOT-SUBMIT) when the holdout gate or the
literal all-rasters duplicate gate fails. Never spends a weekly slot.
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
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems78 import data as D, emit as E
from gems57 import evaluate_holdout as EH, grid as G, holdout as HO, submission_writer as SW, uniqueness as U

BAND_DET_ELEV = D.BAND_NAMES.index('det_elev')
BAND_RTP = D.BAND_NAMES.index('rtp')
BAND_GRAV = D.BAND_NAMES.index('iso_grav_anom')
SIGMA_DETREND = 30.0
SIGMA_WARP = 8.0
SIGMA_CENTRAL = 3.0
BUDGET = 44_090
SEED = 20


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def registry_files() -> list[Path]:
    out: list[Path] = []
    for p in sorted((ROOT / 'data' / 'registry').glob('*.tif')):
        out.append(p)
    for p in sorted((ROOT / 'docs' / 'downloads').glob('*.tif')):
        out.append(p)
    return out


def rank_corr(a: np.ndarray, b: np.ndarray, footprint: np.ndarray):
    b0 = np.where(np.isfinite(b), b, 0).astype(np.float32)
    r = U.surface_rho(a.astype(np.float32), b0, footprint)['spearman_full_footprint']
    return None if r is None or not np.isfinite(r) else float(r)


def robust_norm(a: np.ndarray, footprint: np.ndarray, name: str):
    v = a[footprint]
    if not np.isfinite(v).all():
        raise ValueError(f'{name}: non-finite values in footprint')
    p90 = float(np.quantile(v, 0.90))
    if not np.isfinite(p90) or p90 <= 0:
        raise ValueError(f'{name}: invalid robust p90={p90}')
    n = np.minimum(a / p90, 1.0).astype(np.float32)
    n[~footprint] = 0
    return n, p90


def score_surface(stack, footprint: np.ndarray):
    """Catalogue-blind FW surface. No labels, no catalogue input."""
    t0 = time.time()
    # (a) detrend elevation
    elev = np.asarray(stack[BAND_DET_ELEV], dtype=np.float32)
    bg = ndi.gaussian_filter(elev, sigma=SIGMA_DETREND).astype(np.float32)
    resid = (elev - bg).astype(np.float32)
    del elev, bg
    # (b) wide-scale curvature magnitude
    s = np.float32(SIGMA_WARP)
    gxx = ndi.gaussian_filter(resid, s, order=(0, 2)).astype(np.float32) * (s * s)
    gyy = ndi.gaussian_filter(resid, s, order=(2, 0)).astype(np.float32) * (s * s)
    gxy = ndi.gaussian_filter(resid, s, order=(1, 1)).astype(np.float32) * (s * s)
    del resid
    half = 0.5 * (gxx + gyy)
    disc = np.sqrt((0.5 * (gxx - gyy)) ** 2 + gxy ** 2)
    l1 = half + disc
    l2 = half - disc
    warp_raw = np.maximum(np.abs(l1), np.abs(l2)).astype(np.float32)
    del gxx, gyy, gxy, half, disc, l1, l2
    gc.collect()
    warp_n, warp_p90 = robust_norm(warp_raw, footprint, 'warp')
    del warp_raw
    # (c) central 300 m potential-field steps
    comps = {}
    p90s = {'warp_p90': warp_p90}
    for key, idx in (('rtp', BAND_RTP), ('grav', BAND_GRAV)):
        a = np.ascontiguousarray(stack[idx], dtype=np.float32)
        gx = ndi.gaussian_filter(a, SIGMA_CENTRAL, order=(0, 1)).astype(np.float32) * np.float32(SIGMA_CENTRAL)
        gy = ndi.gaussian_filter(a, SIGMA_CENTRAL, order=(1, 0)).astype(np.float32) * np.float32(SIGMA_CENTRAL)
        del a
        mag = np.hypot(gx, gy).astype(np.float32)
        del gx, gy
        n, p90 = robust_norm(mag, footprint, key)
        del mag
        comps[key] = n
        p90s[f'{key}_p90'] = p90
    central = np.sqrt(comps['rtp'] * comps['grav']).astype(np.float32)
    central[~footprint] = 0
    score = np.sqrt(warp_n * central).astype(np.float32)
    score[~footprint] = 0
    if not np.isfinite(score).all() or (score < 0).any() or (score > 1.00001).any():
        raise ValueError('surface normalization failed')
    feats = {'warp_n': warp_n, 'rtp_n': comps['rtp'], 'grav_n': comps['grav'],
             'central': central, 'composite': score}
    meta = dict(sigma_detrend_px=SIGMA_DETREND, sigma_warp_px=SIGMA_WARP,
                sigma_central_px=SIGMA_CENTRAL, norm='within-footprint p90 cap 1.0',
                composite='sqrt(warp_n * sqrt(rtp_n*grav_n))', seconds=round(time.time() - t0, 1), **p90s)
    return score, feats, meta


def canary(features: dict, folds, footprint: np.ndarray):
    rng = np.random.default_rng(SEED)
    active = np.zeros(footprint.shape, bool)
    truth = np.zeros(footprint.shape, bool)
    for f in folds:
        ok = footprint & f['region'] & ~f['masked_known']
        active |= ok
        truth |= ok & f['truth']
    pos = np.flatnonzero(truth.ravel())
    neg = np.flatnonzero((active & ~truth).ravel())
    neg = rng.choice(neg, min(len(neg), 300_000), replace=False)
    y = np.r_[np.ones(len(pos), np.uint8), np.zeros(len(neg), np.uint8)]
    idx = np.r_[pos, neg]
    out = {}
    for name, a in features.items():
        v = np.asarray(a).ravel()[idx]
        auc = float(roc_auc_score(y, v))
        out[name] = max(auc, 1 - auc)
    return dict(n_positive=len(pos), n_negative=len(neg), symmetric_auc=out,
                flagged_over_0p90={k: v for k, v in out.items() if v > 0.90})


def fold_terms(dots: np.ndarray, folds, footprint: np.ndarray):
    pred = dots.astype(np.float32)
    terms = None
    per_fold = {}
    for f in folds:
        r, t = EH.evaluate(pred, f, footprint, block_side=200, origin=(0, 0),
                           global_shape=footprint.shape)
        per_fold[f['name']] = dict(dti=r['dti'], tp=r['tp'], fp=r['fp'], fn=r['fn'],
                                   n_truth=r['n_truth'], n_emitted=r['n_emitted'])
        terms = t if terms is None else terms + t
    return terms, per_fold


def compare_surface(surface: np.ndarray, footprint: np.ndarray, files: list[Path]):
    rows = []
    for p in files:
        with rasterio.open(p) as ds:
            b = ds.read(1)
            grid_ok = (ds.count == 1 and ds.shape == surface.shape
                       and ds.crs is not None and ds.crs.to_epsg() == 32611)
        rho = rank_corr(surface, b, footprint)
        rows.append(dict(file=str(p.relative_to(ROOT)), sha256=sha_file(p),
                         grid_ok=grid_ok, rho=rho))
        print('pre-placement surface rho:', p.name, rho, flush=True)
    return rows


def compare_dots(dots: np.ndarray, footprint: np.ndarray, allowed: np.ndarray, files: list[Path]):
    mine = dots.astype(np.float32)
    rows = []
    fp_cells = int(footprint.sum())
    for p in files:
        with rasterio.open(p) as ds:
            a = ds.read(1)
        fwd = U.dot_overlap(mine, a, 3.0)
        rho = rank_corr(mine, a, footprint)
        sup = (np.isfinite(a) & (a > 0) & footprint)
        rep = U.representation_class(int(sup.sum()), fp_cells)
        halo = U.halo_coverage(sup, allowed, 3.0)
        rows.append(dict(file=str(p.relative_to(ROOT)), sha256=sha_file(p),
                         their_dots=int(sup.sum()), forward_3px_overlap=fwd, rho=rho,
                         representation=rep['kind'], support_fraction=rep['support_fraction'],
                         halo_coverage=halo))
        print('final overlap:', p.name, round(fwd, 4), rho, rep['kind'], flush=True)
    return rows


def main():
    t_start = time.time()
    if (ROOT / 'evidence/h78fw_run_card.json').exists():
        raise RuntimeError('H78-FW already evaluated; do not rerun (budget/duplicate-stop)')
    inputs = D.verify_inputs()
    g = G.load_grid(ROOT / 'data' / 'bridge')
    fp = g.footprint
    stack = D.load_stack()
    score, feats, smeta = score_surface(stack, fp)
    del stack
    gc.collect()
    files = registry_files()
    print(f'registry comparators present: {len(files)}', flush=True)
    pre = compare_surface(score, fp, files)
    if any(r['rho'] is not None and abs(r['rho']) > 0.90 for r in pre):
        raise RuntimeError('duplicate on surface: no dot placement / TIFF')
    folds, _ = HO.buffered_component_draw(g, seed=SEED, hide_frac=0.20, buffer_px=3)
    n_truth = sum(int(f['truth'].sum()) for f in folds)
    print('withheld positives (scored):', n_truth, flush=True)
    if n_truth != 11321:
        print(f'WARNING: withheld {n_truth} != preregistered 11321', flush=True)
    checks = canary(feats, folds, fp)
    print('canary:', checks['symmetric_auc'], flush=True)
    if checks['flagged_over_0p90']:
        raise RuntimeError(f"leakage canary >0.90; no emission: {checks['flagged_over_0p90']}")
    # Holdout emission (visible flank) + identical-fold comparators
    visible = folds[0]['visible']
    hold_allowed = fp & ~E.flank_mask(visible, 3.0)
    rank = E.greedy_dots(score, hold_allowed, min_dist=2.8, max_dots=BUDGET, pool=1_500_000)
    hold_dots = E.prefix(rank, BUDGET)
    del rank
    if int(hold_dots.sum()) != BUDGET:
        raise RuntimeError('insufficient emitted holdout dots')
    terms_by_arm = {}
    per_fold_by_arm = {}
    t, pf = fold_terms(hold_dots, folds, fp)
    terms_by_arm['FW_candidate'] = t
    per_fold_by_arm['FW_candidate'] = pf
    print('FW raw pooled:', float(EH.from_terms(t.sum(axis=0))), flush=True)
    del hold_allowed, hold_dots, t
    gc.collect()
    for label, rel in (('registry_D2.8_44090', 'data/registry/d28_44090_nan.tif'),
                       ('registry_H33_37654', 'data/registry/h33_2_b2_37654_zeros.tif')):
        with rasterio.open(ROOT / rel) as ds:
            a = ds.read(1)
        d = np.isfinite(a) & (a > 0)
        t, pf = fold_terms(d, folds, fp)
        terms_by_arm[label] = t
        per_fold_by_arm[label] = pf
        print(label, float(EH.from_terms(t.sum(axis=0))), flush=True)
        del a, d, t
    summary = EH.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate='FW_candidate')
    hold = summary['scores']['FW_candidate']
    print('HOLDOUT-DTI FW:', hold, flush=True)
    # Stored incumbent (descriptive, same draw/seed, different budget for 50k)
    inc = json.loads((ROOT / 'evidence/h78_holdout_seed20.json').read_text())['pooled_summary']['scores']
    old50 = inc['A2_h78_steered|nms0_B3|50000']
    # B3/44090 pooled CI lives in the H78-A run card holdout (same draw/seed), not in
    # the stored pooled_summary (which kept only the 50k shortlist + comparators).
    h78a = json.loads((ROOT / 'evidence/h78_run_card.json').read_text())['holdout']
    old44 = dict(dti=h78a['dti'], ci95=h78a['ci95'],
                 withheld_positive_pixels=h78a['withheld_positive_pixels'])
    del folds, visible
    gc.collect()
    # Production (same surface; flank uses FULL catalogue)
    allowed = fp & ~E.flank_mask(g.catalogue, 3.0)
    rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=BUDGET, pool=1_500_000)
    dots = E.prefix(rank, BUDGET)
    del rank
    if int(dots.sum()) != BUDGET:
        raise RuntimeError('insufficient production dots')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    digest = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
    # Final-dot registry audit BEFORE deciding the filename suffix
    final = compare_dots(dots, fp, allowed, files)
    literal_dup = [r for r in final if r['forward_3px_overlap'] > 0.70
                   or (r['rho'] is not None and abs(r['rho']) > 0.90)]
    dotfield = [r for r in final if r['representation'] == 'dot_field']
    informative_dup = [r for r in dotfield if r['forward_3px_overlap'] > 0.70
                       or (r['rho'] is not None and abs(r['rho']) > 0.90)]
    beats_best = hold['dti'] > old50['dti']
    gated = bool(literal_dup) or not beats_best
    suffix = 'DO-NOT-SUBMIT' if gated else 'zeros'
    name = f'gems78-h78fw-flankwarp-44090dots-{stamp}-{digest}-{suffix}'
    if gated:
        note = 'NOT OK TO SUBMIT: H78-FW flank-warp inspection; see run card gates.'
    else:
        note = f"H78-FW warp+step HOLDOUT-DTI {hold['dti']:.4f} n={hold['withheld_positive_pixels']}; not a projection"
    assert len(note) <= 140 and len(name) <= 140, (len(note), len(name))
    p = ROOT / 'docs/downloads' / f'{name}.tif'
    receipt = SW.write_submission(p, dots.astype(np.float32), ROOT / 'data/bridge/sample_submission.tif',
                                  fp, note=note, name=name, catalogue=g.catalogue,
                                  metadata={'lane': 'H78-FW broad flank warp + central step',
                                            'holdout_only': True, 'surface': smeta})
    verify = json.loads(subprocess.check_output(
        [sys.executable, str(ROOT / 'scripts/verify_tif.py'), str(p)]))
    if not verify['all_passed']:
        raise RuntimeError('independent TIFF verification failed')
    # Binding literal decision via shared helper (dense binding, never exempt)
    binding = U.binding_duplicate_decision(
        [dict(file=r['file'], forward_overlap=r['forward_3px_overlap'],
              spearman_full_footprint=r['rho'], halo_coverage=r['halo_coverage']) for r in final])
    verdict = 'negative'  # promote requires beating best + literal pass + canary + validator
    if beats_best and not literal_dup and not checks['flagged_over_0p90'] and verify['all_passed']:
        verdict = 'promote'
    # Note: 'promote' here means eligible for the SEPARATE selector step, not a slot claim.
    # Under the proven saturation witness the literal gate cannot pass; expect negative.
    card = dict(
        schema_version=1, generated_utc=stamp, lane='H78-FW broad flank warp + central potential-field step',
        hypothesis='Buried normal-fault tips carry distributed monoclinal flank warping plus a central basement/magnetic step even without a narrow mapped rupture.',
        mechanism='Detrended 800 m Hessian curvature magnitude corroborated by 300 m RTP+gravity gradient geometric mean; sqrt(warp*central); unsupervised, catalogue-blind.',
        mimic_nonfault_process='Differential sediment compaction across a basin margin (broad warp + density step, no fault).',
        input_sha256={k: v['sha256'] for k, v in inputs.items()},
        surface_meta=smeta, canary=checks,
        holdout=dict(evidence_class='HOLDOUT-DTI', evaluator_version=EH.VERSION,
                     withheld_positive_pixels=hold['withheld_positive_pixels'], seed=SEED,
                     score=hold['dti'], ci95=hold['ci95'], tpw=hold['tpw'], fpw=hold['fpw'], fnw=hold['fnw'],
                     comparators_same_folds={k: dict(dti=v['dti'], ci95=v['ci95'],
                         withheld_positive_pixels=v['withheld_positive_pixels'])
                         for k, v in summary['scores'].items() if k != 'FW_candidate'},
                     paired_differences_vs_comparators=summary.get('paired_differences'),
                     stored_incumbent_B3_50000=dict(name='A2_h78_steered|nms0_B3|50000', score=old50['dti'],
                         ci95=old50['ci95'], evidence_class='HOLDOUT-DTI', evaluator_version=EH.VERSION,
                         withheld_positive_pixels=old50['withheld_positive_pixels'],
                         comparison='same draw seed; different fixed dot budget; descriptive, not paired'),
                     stored_incumbent_B3_44090=dict(name='A2_h78_steered|nms0_B3|44090', score=old44['dti'],
                         ci95=old44['ci95'], evidence_class='HOLDOUT-DTI', evaluator_version=EH.VERSION,
                         withheld_positive_pixels=old44['withheld_positive_pixels'],
                         comparison='same draw seed; same dot budget; descriptive (terms not shared), not paired'),
                     beats_stored_best_0p1843=beats_best,
                     metric=dict(alpha=0.2, beta=0.8, triangular_radius_m=300)),
        registry=dict(preplacement_surface=pre, final_dots=final,
                      literal_duplicate_witnesses=literal_dup,
                      informative_dotfield_duplicates=informative_dup,
                      binding_literal_decision=binding,
                      exhaustive_accessible_inventory=False,
                      scope='Pinned local comparators (data/registry + shipped docs/downloads at run time). NOT all sibling submissions; not the organizer registry.'),
        raster_sha256=verify['sha256'], validator_output=verify,
        submission_name=name, submission_note=note,
        writer_receipt=p.with_suffix('.json').name,
        verdict=verdict, ok_to_download=True,
        ok_to_submit=(verdict == 'promote'),
        stop_required=(verdict != 'promote'),
        submission_slots_used=0, organizer_confirmed_score=None,
        experiments_charged=1, seconds_total=round(time.time() - t_start, 1))
    out = ROOT / 'evidence/h78fw_run_card.json'
    out.write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    print('CARD', out, 'verdict', verdict, 'witnesses', len(literal_dup), 'TIFF', p, flush=True)
    print(json.dumps({k: card[k] for k in ('verdict', 'ok_to_submit', 'submission_name')}, indent=2))


if __name__ == '__main__':
    main()
