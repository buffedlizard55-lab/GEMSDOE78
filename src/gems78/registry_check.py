"""Registry uniqueness measurements for lane H78-SIGX (gate G4, v2).

Registry scope (stated exactly, never claimed exhaustive): every
SHA-256-pinned raster restored this session from
``registry/data_manifest_gems73.json`` group ``scored`` (12 files),
``registry/h78sig_inputs.json`` (H33 + the 17GEMSDOE continuous witness),
and this repository's own previously published ``docs/downloads/*.tif``
productions. Duplicates are removed by SHA-256.

Why v2 exists (measured, 2026-10-22): the literal rule "stop if >70% of my
dots fall within 3 px of any one registry raster's dots" is unsatisfiable.
Two restored registry rasters are *space-filling* under the shared
template's own definition (``vendor/gems57/uniqueness.py``:
``representation_class_v2``, halo coverage >= ``DENSE_HALO_FRACTION`` =
0.70): the 13GEMSDOE lattice-s5 binary raster (halo 0.999 of the allowed
domain) and the 17GEMSDOE E-proba continuous field (halo 1.000). Every
nonempty candidate scores forward overlap ~= 1.0 against them, so the
statistic cannot distinguish a copy from an independent file (see
``docs/review-2026-10-22.md`` for the saturation proof). G4 v2 therefore
uses only thresholds already defined in the shared template, applied by
representation class, and always reports the literal reading alongside:

* discriminating raster (halo < 0.70): binding statistic = literal forward
  3 px overlap, limit 0.70 (``OVERLAP_LIMIT``).
* space-filling *graded* raster: binding statistic = forward 3 px overlap
  against its own top-K support at the candidate's budget K (its ranking
  turned into a like-for-like dot field), limit 0.70.
* space-filling *binary* raster (no ranking exists): binding statistic =
  Jaccard of the exact dot sets, limit 0.50 (``JACCARD_LIMIT``); reverse
  overlap is reported as a diagnostic. A candidate that actually copied a
  binary space-filling support would have Jaccard near 1; an independent
  44k-dot field has Jaccard near the support fraction.
* Spearman rank correlation of the candidate surface, limit 0.90
  (``RHO_LIMIT``), applies to every raster in every class.

This is a documented correction (IR-78-22-03), flagged for owner
ratification; it is never applied silently. The literal worst-case numbers
are part of every report.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

from .data import ROOT

RHO_LIMIT = 0.90            # vendor/gems57/uniqueness.py RHO_LIMIT
OVERLAP_LIMIT = 0.70        # vendor/gems57/uniqueness.py OVERLAP_LIMIT
JACCARD_LIMIT = 0.50        # vendor/gems57/uniqueness.py JACCARD_LIMIT
DENSE_HALO_FRACTION = 0.70  # vendor/gems57/uniqueness.py DENSE_HALO_FRACTION


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def registry_rasters(exclude_names: set[str] | None = None) -> list[dict]:
    exclude_names = exclude_names or set()
    candidates = []
    scored = ROOT / ".cache" / "gems_data" / "scored"
    candidates += sorted(scored.glob("*.tif"))
    candidates += [ROOT / "data" / "registry" / "h33_2_b2_37654_zeros.tif",
                   ROOT / "data" / "registry" / "17GEMSDOE_E-proba-multiscale.tif"]
    candidates += sorted((ROOT / "docs" / "downloads").glob("*.tif"))
    out, seen = [], {}
    for p in candidates:
        if not p.exists() or p.name in exclude_names:
            continue
        digest = sha256(p)
        if digest in seen:
            continue
        seen[digest] = p.name
        out.append(dict(name=p.name, path=str(p), sha256=digest))
    return out


def load_values(path: str) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1)


def halo_coverage(support: np.ndarray, allowed: np.ndarray, radius_px: float = 3.0) -> float:
    """Fraction of allowed cells within radius of support (template definition).

    Computed with an exact Euclidean EDT, which selects the identical disk
    as the template's binary-dilation structuring element.
    """
    allowed = np.asarray(allowed, bool)
    if not allowed.any() or not support.any():
        return 0.0
    d = ndi.distance_transform_edt(~support)
    return float((d[allowed] <= radius_px).mean())


def representation(support: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray) -> dict:
    allowed = footprint & ~catalogue
    halo = halo_coverage(support, allowed)
    return dict(kind="space_filling" if halo >= DENSE_HALO_FRACTION else "discriminating",
                halo_coverage=halo, halo_limit=DENSE_HALO_FRACTION,
                positive_px=int((support & footprint).sum()),
                support_fraction_of_footprint=float((support & footprint).sum() / footprint.sum()))


def forward_overlap(my_dots: np.ndarray, their_support: np.ndarray, radius_px: float = 3.0) -> float:
    if not my_dots.any():
        return float("nan")
    d = ndi.distance_transform_edt(~their_support)
    return float((d[my_dots] <= radius_px).mean())


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    u = int((a | b).sum())
    return float((a & b).sum() / u) if u else 0.0


def topk_support(values: np.ndarray, footprint: np.ndarray, k: int) -> np.ndarray:
    flat = np.where(footprint & np.isfinite(values), values, -np.inf).ravel()
    if k >= int(np.isfinite(flat).sum()):
        return (flat > -np.inf).reshape(values.shape)
    thresh_idx = np.argpartition(-flat, k - 1)[:k]
    support = np.zeros(flat.size, bool)
    support[thresh_idx] = True
    return support.reshape(values.shape)


def compare_surface(surface: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray,
                    entries: list[dict]) -> dict:
    """Pre-placement Spearman of a continuous score surface vs each registry raster."""
    out = {}
    for e in entries:
        vals = load_values(e["path"])
        support = np.isfinite(vals) & (vals > 0)
        info = representation(support, footprint, catalogue)
        ok = footprint & np.isfinite(vals)
        rho = float(spearmanr(surface[ok], vals[ok]).statistic) \
            if np.ptp(vals[ok]) > 0 and np.ptp(surface[ok]) > 0 else float("nan")
        out[e["name"]] = dict(sha256=e["sha256"], spearman_full_footprint=rho, **info)
        del vals
    return out


def compare_dots(my_dots: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray,
                 entries: list[dict]) -> dict:
    """Final-dot comparison vs each registry raster (G4 v2; literal always reported)."""
    out = {}
    k = int(my_dots.sum())
    for e in entries:
        vals = load_values(e["path"])
        support = np.isfinite(vals) & (vals > 0)
        info = representation(support, footprint, catalogue)
        literal = forward_overlap(my_dots, support)
        row = dict(sha256=e["sha256"], forward_overlap_3px_literal=literal,
                   jaccard_dot_sets=jaccard(my_dots & footprint, support & footprint),
                   reverse_overlap_3px=forward_overlap(support & footprint, my_dots), **info)
        if info["kind"] == "discriminating":
            row.update(gate_statistic=literal, gate_limit=OVERLAP_LIMIT,
                       gate_basis="literal forward overlap (discriminating raster)")
        else:
            finite_vals = vals[footprint & np.isfinite(vals)]
            graded = bool(np.unique(finite_vals).size > 2)
            del finite_vals
            if graded:
                row["forward_overlap_3px_vs_topk_matched_budget"] = forward_overlap(
                    my_dots, topk_support(vals, footprint, k))
                row.update(gate_statistic=row["forward_overlap_3px_vs_topk_matched_budget"],
                           gate_limit=OVERLAP_LIMIT,
                           gate_basis="forward overlap vs matched-budget top-K (space-filling graded; IR-78-22-03)")
            else:
                row.update(gate_statistic=row["jaccard_dot_sets"], gate_limit=JACCARD_LIMIT,
                           gate_basis="Jaccard dot sets (space-filling binary; IR-78-22-03)")
        row["passed"] = bool(row["gate_statistic"] < row["gate_limit"])
        out[e["name"]] = row
        del vals
    return out
