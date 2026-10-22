#!/usr/bin/env bash
# Reproducible competition & external geophysical dataset fetcher.
# Streams hash-pinned tarballs from codeload.github.com (immune to gh REST API 403 rate limits)
# into snapshot-excluded .cache/ directories behind data/ symlinks and verifies every 64-hex SHA-256.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$ROOT/scripts/restore_data.sh" "$@"
