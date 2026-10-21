"""Regional structural-strike field derived from the *visible* fault catalogue only.

Hypothesis H78 (see research/h78_hypotheses.md): Basin-and-Range / Walker Lane
faults occur in sub-parallel arrays, so an unmapped strand is most likely to share
the strike of its mapped neighbours. We estimate the dominant strike of the mapped
catalogue in a ~4 km neighbourhood by the classical doubled-angle (structure
tensor) average, then use that angle only to *steer* derivative filters on the
geophysical / topographic bands. The catalogue location itself (distance,
density, coherence) is deliberately NOT exposed to the learner, so the model is
not rewarded for crowding the mapped traces (the H33 live lesson).

Leakage rule (parallel-run protocol #2): in a hide-and-recover fold this must be
called with the fold's ``visible`` catalogue (withheld components and their
3-px collar removed), never with the full catalogue.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def strike_field(visible: np.ndarray, sigma_line: float = 1.5, sigma_region: float = 40.0):
    """Return (phi, coherence, energy).

    ``phi`` is the angle (radians, image x/y convention) of the *normal* to the
    dominant mapped-fault strike in each cell; ``coherence`` in [0,1] measures
    how unimodal the local strike distribution is; ``energy`` is the smoothed
    gradient energy (diagnostic only; not a learner feature).
    """
    m = ndi.gaussian_filter(np.asarray(visible, np.float32), sigma_line)
    gx = ndi.gaussian_filter(m, sigma_line, order=(0, 1))
    gy = ndi.gaussian_filter(m, sigma_line, order=(1, 0))
    jxx = ndi.gaussian_filter(gx * gx, sigma_region)
    jyy = ndi.gaussian_filter(gy * gy, sigma_region)
    jxy = ndi.gaussian_filter(gx * gy, sigma_region)
    del m, gx, gy
    # doubled-angle average: dominant gradient (= strike-normal) direction
    phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    energy = jxx + jyy
    coh = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2) / (energy + 1e-12)
    return phi.astype(np.float32), coh.astype(np.float32), energy.astype(np.float32)
