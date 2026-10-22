"""Lane H78-SIGX unit tests: feature hygiene and registry-gate primitives.

These tests use synthetic arrays only (no restored data), so they run in a
bare checkout. They pin the lane's defining constraints:
- no raw contextual/habitat band is a SIGX feature;
- no label-adjacent (SGMC/Qfaults) input is ever read;
- dense-vs-sparse classification and top-K support behave as documented;
- forward overlap is the fraction of my dots within radius of their support.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems78 import registry_check as RC  # noqa: E402
from gems78 import sigx as SX  # noqa: E402
from gems78.data import BAND_NAMES  # noqa: E402


def test_sigx_excludes_raw_context_bands():
    names = SX.sigx_names()
    assert len(names) == 102 and len(set(names)) == 102
    assert not any(n in BAND_NAMES for n in names), "raw habitat band leaked into SIGX"
    assert len(SX.derivative_names()) == 84
    assert len(SX.ext_names()) == 18


def test_sigx_external_sources_have_no_label_adjacent_inputs():
    files = {f for f, _ in SX.EXT_SOURCES}
    assert files == {"lidar_scarp_features_u8.tif", "topo_10m_derived_100m_u8.tif"}
    banned = ("sgmc", "qfault", "fault")
    assert not any(b in f.lower() for f in files for b in banned)
    # contextual / cyclic / coverage bands are excluded by name
    assert "dem_mean" not in " ".join(SX.ext_names())
    assert "strike" not in SX.ext_names() and "valid" not in " ".join(SX.ext_names())


def test_dense_sparse_classification_and_topk():
    fp = np.ones((30, 30), bool)
    cat = np.zeros((30, 30), bool)
    dense = np.full((30, 30), 0.5, np.float32)
    sparse = np.zeros((30, 30), np.float32)
    sparse[0, :5] = 1.0
    # full-coverage support -> space_filling (halo = 1.0); 5 px -> discriminating
    assert RC.representation(dense > 0, fp, cat)["kind"] == "space_filling"
    assert RC.representation(sparse > 0, fp, cat)["kind"] == "discriminating"
    vals = np.arange(900, dtype=np.float32).reshape(30, 30)
    support = RC.topk_support(vals, fp, 7)
    assert support.sum() == 7 and support[29, 29]
    # a 5 px-spaced binary lattice is space_filling despite small support
    lattice = np.zeros((30, 30), bool)
    lattice[::5, ::5] = True
    rep = RC.representation(lattice, fp, cat)
    assert rep["kind"] == "space_filling" and rep["halo_coverage"] >= RC.DENSE_HALO_FRACTION


def test_forward_overlap_exact_cases():
    mine = np.zeros((11, 11), bool)
    mine[5, 5] = mine[0, 0] = True
    theirs = np.zeros((11, 11), bool)
    theirs[5, 7] = True  # 2 px from (5,5) -> inside radius 3; far from (0,0)
    assert RC.forward_overlap(mine, theirs) == 0.5
    assert RC.forward_overlap(mine, mine) == 1.0


def test_gate_limits_match_protocol():
    assert RC.RHO_LIMIT == 0.90 and RC.OVERLAP_LIMIT == 0.70
