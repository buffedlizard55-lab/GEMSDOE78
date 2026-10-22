#!/usr/bin/env bash
# Reproducible competition & external public-geoscience data bootstrap + SHA-256 verification.
# Sources:
#   1. DrivenData Competition 306 (DOE GEMS Prize Challenge):
#      https://www.drivendata.org/competitions/306/doe-gems/data/
#   2. USGS 3D Elevation Program (3DEP) 1 m LiDAR & 1/3 arc-second (10 m) seamless DEMs:
#      https://www.usgs.gov/3d-elevation-program
#   3. USGS State Geologic Map Compilation (SGMC) & GeoDAWN geophysical compilations:
#      https://doi.org/10.3133/ds1052  |  https://mrdata.usgs.gov/sgmc/
#   4. US DOE Geothermal Data Repository (GDR) Submission #1391 — Great Basin INGENIOUS dataset
#      (Faulds et al., Nevada Bureau of Mines & Geology / UNR):
#      https://gdr.openei.org/submissions/1391
#   5. Pre-verified competition cache mirror with exact SHA-256 manifests:
#      scripts/restore_data.py + scripts/restore_data.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/2] Restoring & SHA-256 verifying core competition rasters (DrivenData #306)..."
python3 scripts/restore_data.py

echo "[2/2] Restoring & SHA-256 verifying external USGS 3DEP + DOE GDR #1391 INGENIOUS layers..."
bash scripts/restore_data.sh

echo "[OK] All 33 competition, external geoscience, and control files verified by SHA-256."
