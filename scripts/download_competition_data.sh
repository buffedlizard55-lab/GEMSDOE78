#!/usr/bin/env bash
# Reproducible zero-credential restoration of SHA-256-pinned competition inputs,
# external geodetic/geothermal/LiDAR physics rasters, and cached v2 stack19 memmap.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/restore_data.sh"
if [ -x "$ROOT/.venv/bin/python" ]; then
  "$ROOT/.venv/bin/python" "$ROOT/scripts/prepare_data.py"
else
  python3 "$ROOT/scripts/prepare_data.py"
fi
