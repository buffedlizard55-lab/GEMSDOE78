#!/usr/bin/env python3
"""Fresh, strict-JSON H33 geometry review; never infers an organizer score."""
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    entries = {e['id']: e for e in manifest['files']}
    arrays, pins = {}, {}
    grid = None
    for name in ('existing_faults', 'sample_submission', 'registry_d28', 'registry_h33'):
        entry = entries[name]
        path = ROOT / 'data' / entry['dest']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry['sha256']:
            raise ValueError(f'{name}: SHA256 mismatch')
        with rasterio.open(path) as ds:
            meta = ds.shape, ds.crs, ds.transform
            if grid is not None and meta != grid:
                raise ValueError(f'{name}: grid mismatch')
            grid = meta
            a = ds.read(1)
        arrays[name] = a
        pins[name] = {'sha256': digest, 'repo': entry['repo'], 'ref': entry['ref'], 'path': entry['path']}
    fp = np.isfinite(arrays['sample_submission'])
    cat = arrays['existing_faults'] > 0
    d28 = np.isfinite(arrays['registry_d28']) & (arrays['registry_d28'] > 0) & fp
    h33 = np.isfinite(arrays['registry_h33']) & (arrays['registry_h33'] > 0) & fp
    removed = d28 & ~h33
    distance = distance_transform_edt(~cat)
    result = dict(evidence_class='RASTER-GEOMETRY-DIAGNOSTIC, not a score',
                  inputs=pins, d28_dots=int(d28.sum()), h33_dots=int(h33.sum()),
                  h33_subset_of_d28=bool(not (h33 & ~d28).any()),
                  exact_h33_equals_d28_pruned_within_2px=bool(np.array_equal(h33, d28 & (distance > 2))),
                  removed_dots=int(removed.sum()),
                  removed_distance_to_catalogue_px=[float(distance[removed].min()), float(distance[removed].max())],
                  organizer_confirmed_score=None,
                  conclusion='H33 is exactly the D2.8 support minus dots within 2 pixels of the catalogue. This is a representation/pruning change, not evidence of new geological discovery. Causal score gain is not established without organizer receipts and a controlled comparison.')
    output = json.dumps(result, indent=2, allow_nan=False) + '\n'
    (ROOT / 'evidence/h33_geometry_review_2026-10-22.json').write_text(output)
    print(output)


if __name__ == '__main__':
    main()
