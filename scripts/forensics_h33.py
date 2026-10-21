#!/usr/bin/env python3
"""Independent byte-level forensics of the two top registry rasters (D2.8 -> H33-2-B2).

Every number printed here is MEASURED from the SHA-256 pinned files in data/registry.
Nothing here is a score; the owner-reported scores are 0.2600 (D2.8) and 0.2778 (H33).
"""
import json, sys, numpy as np, rasterio
from pathlib import Path
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G

g = G.load_grid(ROOT / "data" / "bridge")
fp, cat = g.footprint, g.catalogue
out = {}
def read(p):
    with rasterio.open(p) as ds:
        a = ds.read(1); meta = dict(crs=str(ds.crs), nodata=ds.nodata, dtype=ds.dtypes[0],
                                    transform=list(ds.transform)[:6], shape=[ds.height, ds.width])
    return a, meta
d28, m28 = read(ROOT/"data/registry/d28_44090_nan.tif")
h33, m33 = read(ROOT/"data/registry/h33_2_b2_37654_zeros.tif")
h195, m195 = read(ROOT/"data/registry/h19_5_solid_nan.tif")
out["grid"] = dict(footprint_px=int(fp.sum()), catalogue_px=int(cat.sum()),
                   catalogue_components_8conn=int(ndi.label(cat, np.ones((3,3)))[1]))
for name, a, m in (("d28", d28, m28), ("h33", h33, m33), ("h19_5_solid", h195, m195)):
    fin = np.isfinite(a)
    pos = fin & (a > 0)
    vals = np.unique(a[pos])
    out[name] = dict(meta=m, finite_px=int(fin.sum()), positive_px=int(pos.sum()),
                     distinct_positive_values=int(len(vals)), min_pos=float(vals.min()), max_pos=float(vals.max()),
                     positives_on_catalogue=int((pos & cat).sum()),
                     positives_outside_footprint=int((pos & ~fp).sum()))
# subset relation and distance structure
p28 = np.isfinite(d28) & (d28 > 0); p33 = h33 > 0
out["h33_subset_of_d28"] = bool(np.all(p33 <= p28))
removed = p28 & ~p33
dcat = ndi.distance_transform_edt(~cat)
out["removed_dots"] = dict(n=int(removed.sum()), dist_to_catalogue_px=dict(
    min=float(dcat[removed].min()), max=float(dcat[removed].max())))
q = [10, 25, 50, 75, 90]
out["h33_dist_to_catalogue_px_percentiles"] = dict(zip(q, [float(x) for x in np.percentile(dcat[p33], q)]))
out["h33_min_dist_to_catalogue_px"] = float(dcat[p33].min())
out["d28_dist_to_catalogue_px_percentiles"] = dict(zip(q, [float(x) for x in np.percentile(dcat[p28], q)]))
# nearest-neighbour spacing of dots
for name, p in (("d28", p28), ("h33", p33)):
    yx = np.argwhere(p); t = cKDTree(yx); d, _ = t.query(yx, k=2)
    out[f"{name}_nn_spacing_px"] = dict(min=float(d[:,1].min()), median=float(np.median(d[:,1])), mean=float(d[:,1].mean()))
# relation of dots to the solid H19-5 field
s = np.isfinite(h195) & (h195 > 0)
out["d28_dots_on_h19_5_solid"] = int((p28 & s).sum()); out["h33_dots_on_h19_5_solid"] = int((p33 & s).sum())
# catalogue segment-length structure (what a hide-and-recover holdout withholds)
lab, n = ndi.label(cat, np.ones((3,3)))
sizes = np.bincount(lab.ravel())[1:]
out["catalogue_component_px"] = dict(n=int(n), p50=float(np.median(sizes)), p90=float(np.percentile(sizes,90)), max=int(sizes.max()))
# "detachedness": fraction of catalogue components whose nearest other component is > 6 px away
print(json.dumps(out, indent=2))
(ROOT/"evidence").mkdir(exist_ok=True)
(ROOT/"evidence/forensics_h33_vs_d28.json").write_text(json.dumps(out, indent=2))
