"""Equal nodata counts at different pixels must not share nearest-fill indices."""
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems78 import data


def test_distinct_equal_size_masks_fill_independently(tmp_path, monkeypatch):
    raw = tmp_path / "features.tif"
    bands = np.stack([np.arange(30).reshape(5, 6) + 100., np.arange(30).reshape(5, 6) + 200.]).astype("float32")
    bands[0, 1, 1] = -3.4e38
    bands[1, 3, 4] = -3.4e38  # same COUNT, different mask
    with rasterio.open(raw, "w", driver="GTiff", count=2, height=5, width=6,
                       dtype="float32", transform=rasterio.transform.from_origin(1, 5, 1, 1)) as ds:
        ds.write(bands)
    monkeypatch.setattr(data, "RAW", raw)
    monkeypatch.setattr(data, "PROC", tmp_path)
    monkeypatch.setattr(data, "STACK", tmp_path / "stack.npy")
    monkeypatch.setattr(data, "LOG_BANDS", set())
    result = np.load(data.build_stack())
    for i, band in enumerate(bands):
        bad = band <= data.SENTINEL
        indices = distance_transform_edt(bad, return_distances=False, return_indices=True)
        np.testing.assert_array_equal(result[i], band[indices[0], indices[1]])
    assert np.isfinite(result).all() and (result > 0).all()
