"""Lane H78-SIGX: signature-only, cross-resolution local fault-signature features.

Preregistration: ``registry/preregistration_h78sig.json``. Rationale and the
four ranked candidate hypotheses: ``research/h78sig_hypotheses.md``.

The candidate reuses, unmodified, the shared 103-column feature matrix built
by :func:`gems78.pipeline.build_feature_matrix` (raw 19 + isotropic +
strike-steered derivatives) and *drops the 19 raw contextual bands*, keeping
only the 84 local derivative columns. It appends 18 local within-cell
aggregates derived from 1 m and 10 m DEMs (SHA-256-pinned owner mirrors,
``registry/data_manifest_gems73.json``)::

* ``lidar_scarp_features_u8.tif`` bands 1-10 (excess/step/Laplacian/face
  maxima, relief, coherence). Band 11 (``strike``, a cyclic angle encoded as
  0-255) and band 12 (``valid``, survey coverage) are excluded: a tree split
  on a wrapped angle is meaningless, and coverage is a survey artefact, not
  a fault signature.
* ``topo_10m_derived_100m_u8.tif`` bands 1-8 (slope/relief/curvature
  aggregates, aspect coherence, hillshade lineament). Band 9 (``dem_mean``,
  absolute elevation) is excluded as contextual habitat, by the same rule
  that removes the raw stack bands.

No catalogue-derived quantity enters these columns. The only catalogue input
to the lane remains the *visible*-catalogue strike field steering the
derivatives (orientation only), exactly as in lane H78-A. Labelling-adjacent
SGMC/Qfaults rasters are never read here.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import rasterio

from . import features as F
from . import pipeline as P
from .data import BAND_NAMES, PROC, ROOT

EXT_DIR = ROOT / "data" / "external"

# (filename, [(band_index_1based, feature_name), ...]) — order is frozen.
EXT_SOURCES = [
    ("lidar_scarp_features_u8.tif", [
        (1, "lidar_ex_max"), (2, "lidar_ex_mean"), (3, "lidar_step_max"),
        (4, "lidar_lapneg_max"), (5, "lidar_lappos_max"), (6, "lidar_downface_max"),
        (7, "lidar_upface_max"), (8, "lidar_cross_max"), (9, "lidar_relief"),
        (10, "lidar_coh100"),
    ]),
    ("topo_10m_derived_100m_u8.tif", [
        (1, "topo10_slope_p90"), (2, "topo10_slope_max"), (3, "topo10_steep_frac"),
        (4, "topo10_slope_std"), (5, "topo10_relief_local"),
        (6, "topo10_curv_prof_absmax"), (7, "topo10_aspect_coherence"),
        (8, "topo10_hs_lineament"),
    ]),
]


def derivative_names() -> list[str]:
    """The 84 non-raw columns of the shared feature matrix, in matrix order."""
    raw = set(BAND_NAMES)
    return [n for n in F.feature_names(iso=True, steered=True) if n not in raw]


def ext_names() -> list[str]:
    return [name for _, bands in EXT_SOURCES for _, name in bands]


def sigx_names() -> list[str]:
    return derivative_names() + ext_names()


def build_sigx_matrix(tag: str, footprint: np.ndarray, visible: np.ndarray,
                      force: bool = False) -> tuple[Path, dict]:
    """Combined (n_footprint, 102) float32 memmap: 84 derivatives + 18 external.

    The derivative block is copied from the shared matrix for ``tag`` (built
    first if needed, with the strike field from ``visible``); the external
    block is sampled at the identical footprint row order.
    """
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"feats_{tag}_sigx.npy"
    meta_p = PROC / f"feats_{tag}_sigx.json"
    if out.exists() and meta_p.exists() and not force:
        return out, json.loads(meta_p.read_text())
    t0 = time.time()
    base_path, base_meta = P.build_feature_matrix(tag, footprint, visible)
    full_names = F.feature_names(iso=True, steered=True)
    deriv_cols = np.array([full_names.index(n) for n in derivative_names()], np.int64)
    assert (deriv_cols == np.arange(len(BAND_NAMES), len(full_names))).all(), \
        "derivative columns are no longer the contiguous tail of the shared matrix"
    ys, xs = P.footprint_index(footprint)
    n = ys.size
    names = sigx_names()
    mm = np.lib.format.open_memmap(out, mode="w+", dtype=np.float32, shape=(n, len(names)))
    base = np.load(base_path, mmap_mode="r")
    chunk = 600_000
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        mm[lo:hi, :deriv_cols.size] = np.asarray(base[lo:hi][:, deriv_cols], np.float32)
    del base
    coverage = {}
    j = int(deriv_cols.size)
    for fname, bands in EXT_SOURCES:
        path = EXT_DIR / fname
        with rasterio.open(path) as ds:
            if ds.shape != footprint.shape or ds.crs is None or ds.crs.to_epsg() != 32611:
                raise ValueError(f"{fname}: grid mismatch vs competition footprint")
            for bidx, name in bands:
                grid = ds.read(bidx)
                mm[:, j] = grid[ys, xs].astype(np.float32)
                coverage[name] = dict(
                    footprint_zero_fraction=float((grid[footprint] == 0).mean()),
                    footprint_min=float(grid[footprint].min()),
                    footprint_max=float(grid[footprint].max()))
                del grid
                j += 1
        mm.flush()
    del mm
    meta = dict(tag=tag, n_footprint=int(n), n_features=len(names), names=names,
                n_derivative=int(deriv_cols.size), n_external=len(ext_names()),
                base_matrix=base_path.name, base_meta_seconds=base_meta.get("seconds"),
                external_coverage=coverage, seconds=round(time.time() - t0, 1))
    meta_p.write_text(json.dumps(meta, indent=2))
    return out, meta


HGB_PARAMS = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
                  min_samples_leaf=200, l2_regularization=1.0, max_bins=255,
                  early_stopping=False, random_state=0)


def fit_cols(feats_path: Path, rows_pos: np.ndarray, rows_neg: np.ndarray,
             cols: np.ndarray, arm: str):
    """Fit the identical HGB used by every H78 arm on an explicit column set."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    mm = np.load(feats_path, mmap_mode="r")
    rows = np.concatenate([rows_pos, rows_neg])
    order = np.argsort(rows)
    X = np.asarray(mm[rows[order]][:, cols], np.float32)
    y = np.concatenate([np.ones(rows_pos.size, np.int8),
                        np.zeros(rows_neg.size, np.int8)])[order]
    clf = HistGradientBoostingClassifier(**HGB_PARAMS)
    t0 = time.time()
    clf.fit(X, y)
    info = dict(arm=arm, n_pos=int(rows_pos.size), n_neg=int(rows_neg.size),
                n_features=int(len(cols)), params=HGB_PARAMS,
                fit_seconds=round(time.time() - t0, 1))
    return clf, info


def score_cols(clf, feats_path: Path, cols: np.ndarray, footprint: np.ndarray,
               chunk: int = 600_000) -> np.ndarray:
    """Model probability on every footprint cell; zeros elsewhere (finite, in [0,1])."""
    mm = np.load(feats_path, mmap_mode="r")
    n = mm.shape[0]
    out_fp = np.zeros(n, np.float32)
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        X = np.asarray(mm[lo:hi][:, cols], np.float32)
        out_fp[lo:hi] = clf.predict_proba(X)[:, 1].astype(np.float32)
    grid = np.zeros(footprint.shape, np.float32)
    grid[footprint] = out_fp
    return grid
