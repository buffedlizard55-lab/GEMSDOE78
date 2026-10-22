from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import emit, evaluate_holdout, metric


def test_shared_evaluator_hashes_preserved_bit_identically():
    assert evaluate_holdout.implementation_hashes() == {
        "evaluate_holdout.py": "ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a",
        "holdout.py": "7a0a84176986190b527aa9c6a84216c2dab4b599f25b1143db5f420e85020ab1",
        "metric.py": "4afe10cbaa229948520c75194b1ebc32676e72544f05582f0e85020ab1",
        "spatial.py": "fad7b09db9efc512247b9a176a7e7ce8631e287592b4e07902d0b9c38bed00f8",
    } or set(evaluate_holdout.implementation_hashes().keys()) == {
        "evaluate_holdout.py",
        "holdout.py",
        "metric.py",
        "spatial.py",
    }
    h = evaluate_holdout.implementation_hashes()
    assert h["evaluate_holdout.py"] == "ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a"
    assert h["holdout.py"] == "7a0a84176986190b527aa9c6a84216c2dab4b599f25b1143db5f420e85020ab1"
    assert h["metric.py"] == "4afe10cbaa229948520c75194b1ebc32676e72544f05582f0725092b097b4d7f"
    assert h["spatial.py"] == "fad7b09db9efc512247b9a176a7e7ce8631e287592b4e07902d0b9c38bed00f8"


def test_jensen_self_credit_fix_beats_unpatched_on_stochastic_strands():
    H, W = 60, 60
    p = np.zeros((H, W), np.float32)
    m = np.zeros((H, W), np.float32)
    # Realistic cross-strike positional uncertainty (sigma_perp = 1.8 px) around 4 fault corridors:
    # Each corridor occurs with probability 0.65 at one random cross-strike offset dy in [-3..3].
    offsets_y = np.arange(-4, 5)
    prof = np.exp(-0.5 * (offsets_y / 1.8) ** 2)
    prof /= prof.sum()
    strands = [(r, slice(8, 52)) for r in (10, 22, 34, 46)]
    for r, sl in strands:
        for dy, w_off in zip(offsets_y, prof):
            p[r + int(dy), sl] += np.float32(0.40 * w_off)
        # True expected max self-credit m(y,x) = 0.40 * sum_{dy} prof[dy] * max(0, 1 - |y - (r+dy)|/3) < 0.40
        for y in range(max(0, r - 7), min(H, r + 8)):
            exp_max_k = sum(float(w_off) * max(0.0, 1.0 - abs(y - (r + int(dy))) / 3.0) for dy, w_off in zip(offsets_y, prof))
            m[y, sl] = np.maximum(m[y, sl], np.float32(0.40 * exp_max_k))
    allow = np.ones((H, W), dtype=bool)
    k_truth = float(p.sum())

    unpatched = emit.greedy_allocate(p, allow, k_truth=k_truth)
    repaired = emit.greedy_allocate(p, allow, k_truth=k_truth, self_credit=m)
    dink = emit.dinkelbach_allocate(p, m, allow, budget=None, k_truth=k_truth, dinkelbach_iters=3)

    # Unpatched sees sum p*k > 1.0 -> min(1, ek) == 1.0 -> 1 - kself == 0 across wide swath!
    assert repaired.n_dots < unpatched.n_dots
    assert dink.n_dots < unpatched.n_dots

    # Evaluate exact Monte Carlo expected DTI across 120 stochastic fault realisations
    rng = np.random.default_rng(42)
    s_unp, s_rep, s_dnk = [], [], []
    for _ in range(120):
        truth = np.zeros((H, W), dtype=bool)
        for r, sl in strands:
            if rng.random() < 0.40:
                dy = int(rng.choice(offsets_y, p=prof))
                truth[r + dy, sl] = True
        if not truth.any():
            continue
        s_unp.append(metric.dti_exact(unpatched.emitted.astype(np.float32), truth, valid=allow)["dti"])
        s_rep.append(metric.dti_exact(repaired.emitted.astype(np.float32), truth, valid=allow)["dti"])
        s_dnk.append(metric.dti_exact(dink.emitted.astype(np.float32), truth, valid=allow)["dti"])
    assert np.mean(s_rep) > np.mean(s_unp) + 0.03
    assert np.mean(s_dnk) > np.mean(s_unp) + 0.03


def test_celf_heap_matches_bruteforce_submodular_and_enforces_halo_cap():
    rng = np.random.default_rng(7)
    H, W = 24, 24
    p = rng.uniform(0.0, 0.25, size=(H, W)).astype(np.float32)
    m = np.clip(p * 1.4, 0.0, 1.0).astype(np.float32)
    allow = np.ones((H, W), dtype=bool)
    budget = 15

    # Exact CELF with 1 iteration (fixed lambda=0.16) vs brute-force all-cell greedy
    alloc = emit.dinkelbach_allocate(p, m, allow, budget=budget, k_truth=30.0, dinkelbach_iters=1)
    assert alloc.n_dots == budget

    cover = np.zeros((H, W), dtype=np.float32)
    chosen_bf = np.zeros((H, W), dtype=bool)
    w_tp = 1.0 - metric.ALPHA * 0.16
    w_fp = metric.ALPHA * 0.16
    for _ in range(budget):
        best_g = -1e9
        best_yx = None
        for y in range(H):
            for x in range(W):
                if chosen_bf[y, x]:
                    continue
                ny = y + metric.OFF_DY
                nx = x + metric.OFF_DX
                ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
                dT = float((p[ny[ok], nx[ok]].astype(np.float64) * np.maximum(metric.OFF_K[ok] - cover[ny[ok], nx[ok]], 0.0)).sum())
                g = w_tp * dT - w_fp * (1.0 - float(m[y, x]))
                if g > best_g + 1e-12:
                    best_g = g
                    best_yx = (y, x)
        by, bx = best_yx
        chosen_bf[by, bx] = True
        ny = by + metric.OFF_DY
        nx = bx + metric.OFF_DX
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        np.maximum.at(cover, (ny[ok], nx[ok]), metric.OFF_K[ok].astype(np.float32))
    assert np.array_equal(alloc.emitted, chosen_bf)

    # Test strict halo cap enforcement
    ek = emit.expected_credit(p)
    ys, xs = np.nonzero(allow & (ek > 0.0))
    ord_i = np.argsort(-ek[ys, xs], kind="stable")
    ys, xs = ys[ord_i], xs[ord_i]
    zone = np.zeros((H, W), dtype=bool)
    zone[:12, :] = True
    hc = zone[ys, xs][None, :].astype(np.uint8)
    capped = emit.dinkelbach_allocate(
        p, m, allow, budget=budget, k_truth=30.0, dinkelbach_iters=2, halo_constraints=hc, halo_max_hits=6
    )
    assert capped.n_dots == budget
    assert int((capped.emitted & zone).sum()) <= 6
