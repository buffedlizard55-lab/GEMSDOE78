"""Nearest fill indices must be keyed by the mask, not merely its pixel count."""
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from gems78 import data as D


def test_equal_sized_different_invalid_masks(monkeypatch, tmp_path):
    raw = tmp_path/'raw.tif'
    a = np.arange(25, dtype=np.float32).reshape(5, 5)
    b = a.copy()
    a[0, 0] = -3.4028235e38
    b[4, 4] = -3.4028235e38
    with rasterio.open(raw,'w',driver='GTiff',height=5,width=5,count=2,
                       dtype='float32',transform=from_origin(0,5,1,1)) as ds:
        ds.write(a,1)
        ds.write(b,2)
    monkeypatch.setattr(D,'RAW',raw)
    monkeypatch.setattr(D,'PROC',tmp_path)
    monkeypatch.setattr(D,'STACK',tmp_path/'stack.npy')
    got = np.load(D.build_stack())
    assert got[0,0,0] in {1,5}
    assert got[1,4,4] in {19,23}  # not the first band\'s upper-left fill index
