#!/usr/bin/env bash
# Restore every input from its SHA-256-pinned GitHub mirror (registry/data_manifest.json)
# and verify the hashes. Needs `gh` authenticated (or edit fetch() to use raw.githubusercontent.com).
set -euo pipefail
cd "$(dirname "$0")/../data"
mkdir -p bridge registry external raw
fetch() { gh api "repos/$1/contents/$3?ref=$2" -H "Accept: application/vnd.github.raw" > "$4.partial" && mv "$4.partial" "$4"; echo "fetched $4"; }
python3 - <<'PY' | while read -r repo ref path dest; do [ -s "$dest" ] || fetch "$repo" "$ref" "$path" "$dest"; done
import json
for f in json.load(open("../registry/data_manifest.json"))["files"]:
    if "path" in f: print(f["repo"], f["ref"], f["path"], f["dest"])
PY
if [ ! -s raw/training_features.tif ]; then
  rm -f raw/training_features.tif.assembling
  for i in 0 1 2 3 4; do
    fetch buffedlizard55-lab/GEMSDOE c0c06ac82178f26b94fce3397036ef8f12a2f3a0 "data/bridge/gems-geodawn-numerical-features.tif.part-00$i" "raw/part-00$i"
    cat "raw/part-00$i" >> raw/training_features.tif.assembling && rm "raw/part-00$i"
  done
  mv raw/training_features.tif.assembling raw/training_features.tif
fi
python3 - <<'PY'
import json, hashlib, sys
ok = True
for f in json.load(open("../registry/data_manifest.json"))["files"]:
    h = hashlib.sha256(open(f["dest"], "rb").read()).hexdigest()
    print(("OK  " if h == f["sha256"] else "FAIL"), f["dest"], h)
    ok &= h == f["sha256"]
sys.exit(0 if ok else 1)
PY
echo RESTORE_VERIFIED
