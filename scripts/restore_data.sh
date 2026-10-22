#!/usr/bin/env bash
# Restore every input from its SHA-256-pinned GitHub mirror (registry/data_manifest.json)
# and verify the hashes. Uses zero-rate-limit git blob fetch over github.com first,
# falling back to gh api only if needed.
set -euo pipefail
cd "$(dirname "$0")/../data"
mkdir -p bridge registry external raw

TMP_GIT="$(mktemp -d)"
trap 'rm -rf "$TMP_GIT" ./*/*.partial ./raw/training_features.tif.assembling' EXIT

git init -q "$TMP_GIT"

fetch_git_blob() {
  local repo="$1" ref="$2" path="$3" dest="$4"
  local remote_name
  remote_name="r_$(printf '%s' "$repo" | tr '/-' '__')"
  if ! git -C "$TMP_GIT" remote get-url "$remote_name" >/dev/null 2>&1; then
    git -C "$TMP_GIT" remote add "$remote_name" "https://github.com/${repo}.git"
  fi
  if ! git -C "$TMP_GIT" cat-file -e "${ref}^{commit}" 2>/dev/null; then
    git -C "$TMP_GIT" fetch -q --depth 1 --filter=blob:none "$remote_name" "$ref"
  fi
  git -C "$TMP_GIT" show "${ref}:${path}" > "${dest}.partial"
  mv "${dest}.partial" "$dest"
}

fetch() {
  local repo="$1" ref="$2" path="$3" dest="$4"
  if fetch_git_blob "$repo" "$ref" "$path" "$dest" 2>/dev/null; then
    echo "fetched $dest (git)"
    return 0
  fi
  rm -f "${dest}.partial"
  gh api "repos/$repo/contents/$path?ref=$ref" -H "Accept: application/vnd.github.raw" > "${dest}.partial"
  mv "${dest}.partial" "$dest"
  echo "fetched $dest (gh-api)"
}

while read -r repo ref path dest; do
  [ -s "$dest" ] || fetch "$repo" "$ref" "$path" "$dest"
done < <(python3 - <<'PY'
import json
for f in json.load(open("../registry/data_manifest.json"))["files"]:
    if "path" in f:
        print(f["repo"], f["ref"], f["path"], f["dest"])
PY
)

if [ ! -s raw/training_features.tif ]; then
  rm -f raw/training_features.tif.assembling
  for i in 0 1 2 3 4; do
    fetch buffedlizard55-lab/GEMSDOE c0c06ac82178f26b94fce3397036ef8f12a2f3a0 "data/bridge/gems-geodawn-numerical-features.tif.part-00$i" "raw/part-00$i"
    [ -s "raw/part-00$i" ]
    cat "raw/part-00$i" >> raw/training_features.tif.assembling
    rm -f "raw/part-00$i"
  done
  mv raw/training_features.tif.assembling raw/training_features.tif
fi

# Also restore pinned registry comparators (13gems lattice from GEMSDOE24 & GEMSDOE70 p5)
if [ ! -s registry/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif ]; then
  fetch buffedlizard55-lab/GEMSDOE24 07345ea0604953d7efb858d9cfbc21e20c7aca0b "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif" "registry/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
fi
if [ ! -s registry/gems70_p5_54000.tif ]; then
  if ! git -C "$TMP_GIT" remote get-url r_gems70 >/dev/null 2>&1; then
    git -C "$TMP_GIT" remote add r_gems70 "https://github.com/buffedlizard55-lab/GEMSDOE70.git"
  fi
  git -C "$TMP_GIT" fetch -q --depth 1 --filter=blob:none r_gems70 cd915f3f67ba82aa7f99412fc10f1586b49bfab1
  git -C "$TMP_GIT" cat-file blob cd915f3f67ba82aa7f99412fc10f1586b49bfab1 > registry/gems70_p5_54000.tif.partial
  mv registry/gems70_p5_54000.tif.partial registry/gems70_p5_54000.tif
  echo "fetched registry/gems70_p5_54000.tif (git)"
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
