#!/usr/bin/env python3
"""One preregistered experiment: independent cross-layer basement-step agreement.

Writes only a blocked inspection TIFF when a negative result or duplicate occurs.
No competition upload; see research/2026-10-22-hypotheses.md.
"""
from __future__ import annotations
import gc
import hashlib
import json
import subprocess
import sys
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

REGISTRY = [
    'data/registry/h19_5_solid_nan.tif',
    'data/registry/d28_44090_nan.tif',
    'data/registry/h33_2_b2_37654_zeros.tif',
    'data/registry/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif',
    *[str(p.relative_to(ROOT)) for p in sorted((ROOT/'docs/downloads').glob('*.tif'))],
]
BANDS = ('rtp', 'iso_grav_anom', 'depth_to_base_surf')


def rank_corr(a: np.ndarray, b: np.ndarray, footprint: np.ndarray) -> float | None:
    """Exact tied-rank Spearman on the entire footprint (shared implementation)."""
    b = np.where(np.isfinite(b), b, 0).astype(np.float32)
    result = U.surface_rho(a, b, footprint)['spearman_full_footprint']
    return None if not np.isfinite(result) else float(result)


def score_surface(stack, footprint):
    """No labels/catalogue used; gradient vectors are unoriented (sign may invert)."""
    sizes, vectors = [], []
    features = {}
    for name in BANDS:
        a = np.asarray(stack[D.BAND_NAMES.index(name)], dtype=np.float32)
        gy = ndi.gaussian_filter(a, sigma=3.0, order=(1, 0), output=np.float32)
        gx = ndi.gaussian_filter(a, sigma=3.0, order=(0, 1), output=np.float32)
        mag = np.hypot(gx, gy)
        scale = float(np.quantile(mag[footprint], .90))
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError(f'Invalid robust scale for {name}')
        sizes.append(np.minimum(mag / scale, 1.0).astype(np.float32))
        vectors.append((gx / (mag + 1e-12), gy / (mag + 1e-12)))
        features[name] = dict(p90_gradient=scale)
        del gx, gy, mag
    align = np.zeros(footprint.shape, np.float32)
    for i, j in ((0, 1), (0, 2), (1, 2)):
        align += np.abs(vectors[i][0]*vectors[j][0] + vectors[i][1]*vectors[j][1]) / 3.0
    del vectors
    score = np.cbrt(sizes[0] * sizes[1] * sizes[2]) * (.25 + .75 * align)
    score[~footprint] = 0
    if not np.isfinite(score).all() or (score < 0).any() or (score > 1.00001).any():
        raise ValueError('surface normalization failed')
    return score.astype(np.float32), dict(zip(BANDS, sizes)), align, features


def canary(features, folds, footprint):
    rng = np.random.default_rng(20)
    active = np.zeros(footprint.shape, bool)
    truth = np.zeros(footprint.shape, bool)
    for fold in folds:
        ok = footprint & fold['region'] & ~fold['masked_known']
        active |= ok
        truth |= ok & fold['truth']
    pos = np.flatnonzero(truth.ravel())
    neg = np.flatnonzero((active & ~truth).ravel())
    neg = rng.choice(neg, min(len(neg), 300_000), replace=False)
    y = np.r_[np.ones(len(pos), np.uint8), np.zeros(len(neg), np.uint8)]
    indices = np.r_[pos, neg]
    result = {}
    for name, a in features.items():
        values = a.ravel()[indices]
        auc = float(roc_auc_score(y, values))
        result[name] = max(auc, 1-auc)
    return dict(n_positive=len(pos), n_negative=len(neg), symmetric_auc=result,
                flagged_over_0p90={k:v for k,v in result.items() if v > .90})


def evaluate(dots, folds, footprint):
    terms = None
    for f in folds:
        _, t = EH.evaluate(dots.astype(np.float32), f, footprint, block_side=200,
                           origin=(0,0), global_shape=footprint.shape)
        terms = t if terms is None else terms + t
    return terms


def compare_surface(surface, footprint):
    rows = []
    for p in REGISTRY:
        with rasterio.open(ROOT / p) as ds:
            b = ds.read(1)
        rho = rank_corr(surface, b, footprint)
        rows.append(dict(file=p, sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(), rho=rho))
        print('pre-placement surface rho:', p, rho, flush=True)
    return rows


def compare_dots(dots, footprint):
    rows = []
    for p in REGISTRY:
        with rasterio.open(ROOT / p) as ds:
            a = ds.read(1)
        forward = U.dot_overlap(dots, a, 3.0)
        rho = rank_corr(dots.astype(np.float32), a, footprint)
        rows.append(dict(file=p, sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),
                         forward_3px_overlap=forward, rho=rho))
        print('final overlap:', p, forward, rho, flush=True)
    return rows


def main():
    # Parallel-run stop is binding. Re-running this lane after a duplicate was
    # recorded would manufacture another file and spend another experiment.
    if (ROOT/'evidence/crosslayer_run_card.json').exists():
        raise RuntimeError('cross-layer lane already evaluated and duplicate-stopped; do not rerun')
    inputs = D.verify_inputs()  # SHA-pinned bytes, owner mirror NOT organizer authentication
    g = G.load_grid(ROOT/'data/bridge')
    fp = g.footprint
    stack = D.load_stack()
    score, components, align, scales = score_surface(stack, fp)
    del stack
    gc.collect()
    # Surface audit before any dot placement; fail closed on missing comparator.
    pre = compare_surface(score, fp)
    if any(r['rho'] is not None and abs(r['rho']) > .90 for r in pre):
        raise RuntimeError('duplicate on surface: no dot placement / TIFF')
    folds, _ = HO.buffered_component_draw(g, seed=20, hide_frac=.20, buffer_px=3)
    visible = folds[0]['visible']
    n_truth = sum(int(f['truth'].sum()) for f in folds)
    checks = canary({**components, 'normal_alignment':align, 'composite':score}, folds, fp)
    del components, align
    gc.collect()
    if checks['flagged_over_0p90']:
        raise RuntimeError(f'leakage canary >0.90; no emission: {checks["flagged_over_0p90"]}')
    hold_allowed = fp & ~E.flank_mask(visible, 3.0)
    rank = E.greedy_dots(score, hold_allowed, min_dist=2.8, max_dots=44_090, pool=1_500_000)
    hold_dots = E.prefix(rank, 44_090)
    if hold_dots.sum() != 44_090:
        raise RuntimeError('insufficient emitted holdout dots')
    t = evaluate(hold_dots, folds, fp)
    summary = EH.pooled_summary({'candidate':t}, candidate='candidate', draws=1000, seed=520810)
    hold = summary['scores']['candidate']
    print('HOLDOUT-DTI', hold, flush=True)
    del hold_allowed, rank, hold_dots, t, folds, visible
    gc.collect()
    # Same score on full data; only catalogue exclusion changes.
    allowed = fp & ~E.flank_mask(g.catalogue, 3.0)
    rank = E.greedy_dots(score, allowed, min_dist=2.8, max_dots=44_090, pool=1_500_000)
    dots = E.prefix(rank, 44_090)
    if dots.sum() != 44_090: raise RuntimeError('insufficient production dots')
    del rank, score, allowed
    gc.collect()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    digest = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:10]
    name = f'gems78-crosslayer-step-{stamp}-{digest}-DO-NOT-SUBMIT'
    note = 'NOT OK TO SUBMIT: cross-layer step candidate; inspect negative/duplicate gate in run card.'
    p = ROOT/'docs/downloads'/f'{name}.tif'
    receipt = SW.write_submission(p, dots.astype(np.float32), ROOT/'data/bridge/sample_submission.tif',
                                  fp, note=note, name=name, catalogue=g.catalogue,
                                  metadata={'lane':'cross-layer step', 'holdout_only': True})
    verify = json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/verify_tif.py'),str(p)]))
    if not verify['all_passed']: raise RuntimeError('independent TIFF verification failed')
    final = compare_dots(dots, fp)
    dup = [r for r in final if r['forward_3px_overlap'] > .70 or (r['rho'] is not None and abs(r['rho']) > .90)]
    incumbent = json.loads((ROOT/'evidence/h78_holdout_seed20.json').read_text())['pooled_summary']['scores']
    incumbent_key = 'A2_h78_steered|nms0_B3|50000'
    old = incumbent[incumbent_key]
    card = dict(schema_version=1, generated_utc=stamp, hypothesis='Co-aligned magnetic, gravity and basement-depth cross-strike steps identify unmapped basement faults beneath cover.',
                mechanism='Unsigned 300 m gradient-normal concordance and geometric edge-strength agreement, no catalogue-derived surface features.',
                mimic_nonfault_process='Intrusive/lithologic contact or basin facies boundary.',
                input_sha256={k:v['sha256'] for k,v in inputs.items()},
                feature_scales=scales, canary=checks,
                holdout=dict(evidence_class='HOLDOUT-DTI', evaluator_version=EH.VERSION,
                             withheld_positive_pixels=n_truth, seed=20, score=hold['dti'], ci95=hold['ci95'],
                             control_incumbent={'name':incumbent_key, 'score':old['dti'], 'ci95':old['ci95'],
                               'evidence_class':'HOLDOUT-DTI', 'evaluator_version':EH.VERSION,
                               'withheld_positive_pixels':old['withheld_positive_pixels'],
                               'comparison':'same draw seed; different fixed dot budget; descriptive, not paired'},
                             metric={'alpha':.2,'beta':.8,'triangular_radius_m':300}),
                registry=dict(preplacement_surface=pre, final_dots=final, duplicate_witnesses=dup,
                              exhaustive_accessible_inventory=False,
                              scope='Only pinned comparators indexed here plus shipped local TIFFs. NOT all sibling submissions.'),
                raster_sha256=verify['sha256'], validator_output=verify,
                submission_name=name, submission_note=note,
                writer_receipt=p.with_suffix('.json').name,
                verdict='negative', ok_to_download=True, ok_to_submit=False,
                stop_required=bool(dup) or hold['dti'] <= old['dti'],
                submission_slots_used=0, organizer_confirmed_score=None)
    out = ROOT/'evidence/crosslayer_run_card.json'
    out.write_text(json.dumps(card, indent=2, allow_nan=False)+'\n')
    print('CARD',out,'witnesses',len(dup), 'TIFF',p,flush=True)
    # A duplicate was discovered only after this candidate was already written as
    # inspection artifact. STOP now: never promote or regenerate from this field.

if __name__ == '__main__':
    main()
