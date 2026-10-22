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


def test_old_unversioned_cache_is_rebuilt_and_all_invalid_band_rejected(tmp_path, monkeypatch):
    import json
    import pytest
    raw = tmp_path / "raw.tif"
    stack = tmp_path / "stack.npy"
    good = np.arange(30, dtype="float32").reshape(5, 6) + 5
    def write(a):
        with rasterio.open(raw, "w", driver="GTiff", count=1, height=5, width=6,
                           dtype="float32", transform=rasterio.transform.from_origin(1, 5, 1, 1)) as ds:
            ds.write(a, 1)
    write(good)
    monkeypatch.setattr(data, "RAW", raw)
    monkeypatch.setattr(data, "PROC", tmp_path)
    monkeypatch.setattr(data, "STACK", stack)
    monkeypatch.setattr(data, "LOG_BANDS", set())
    np.save(stack, np.zeros((1, 5, 6), dtype="float32"))  # no v2 receipt
    np.testing.assert_array_equal(np.load(data.build_stack())[0], good)
    receipt = json.loads((tmp_path / "stack19_cache.json").read_text())
    assert receipt["fill_algorithm"] == "nearest-exact-mask-v2"
    assert receipt["stack_sha256"] == data.sha256(stack)
    # Corrupt cache bytes while keeping the valid v2 receipt: must rebuild.
    np.save(stack, np.zeros((1, 5, 6), dtype="float32"))
    np.testing.assert_array_equal(np.load(data.build_stack())[0], good)
    before = stack.read_bytes()
    write(np.full((5, 6), -3.4e38, dtype="float32"))
    with pytest.raises(ValueError, match="no valid cells"):
        data.build_stack(force=True)
    assert stack.read_bytes() == before  # failed temporary build never replaces cache
