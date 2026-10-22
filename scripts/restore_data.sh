#!/usr/bin/env bash
# Restore every input from its SHA-256-pinned GitHub mirror (registry/data_manifest.json)
# using zero-rate-limit streaming tarballs from codeload.github.com first (with gh api fallback)
# and verify all 64-hex SHA-256 hashes before exit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/data"
mkdir -p bridge registry external raw

PYTHON="${ROOT}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

"$PYTHON" - <<'PY'
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request

manifest = json.loads(Path("../registry/data_manifest.json").read_text())

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

batches = defaultdict(dict)
missing = set()
for entry in manifest["files"]:
    dest = Path(entry["dest"])
    if dest.exists() and sha256(dest) == entry["sha256"]:
        continue
    missing.add(entry["id"])
    key = (entry["repo"], entry["ref"])
    if "parts" in entry:
        for part in entry["parts"]:
            batches[key][part] = Path("raw") / Path(part).name
    else:
        batches[key][entry["path"]] = dest

for (repo, ref), wanted in batches.items():
    extracted = set()
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "gemsdoe78-restore/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                for member in tf:
                    if not member.isfile():
                        continue
                    rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
                    if rel in wanted:
                        out_p = wanted[rel]
                        out_p.parent.mkdir(parents=True, exist_ok=True)
                        tmp = out_p.with_suffix(out_p.suffix + ".partial")
                        fh = tf.extractfile(member)
                        if fh is not None:
                            with tmp.open("wb") as out_f:
                                shutil.copyfileobj(fh, out_f, 1 << 20)
                            tmp.replace(out_p)
                            extracted.add(rel)
                            print(f"streamed {out_p}", flush=True)
                        if len(extracted) == len(wanted):
                            break
    except Exception as exc:
        print(f"codeload warning ({repo}@{ref[:8]}): {exc}", file=sys.stderr)

    for rel, out_p in wanted.items():
        if rel not in extracted and not out_p.exists():
            out_p.parent.mkdir(parents=True, exist_ok=True)
            tmp = out_p.with_suffix(out_p.suffix + ".partial")
            with tmp.open("wb") as out_f:
                subprocess.run(
                    ["gh", "api", f"repos/{repo}/contents/{rel}?ref={ref}", "-H", "Accept: application/vnd.github.raw"],
                    stdout=out_f,
                    check=True,
                    timeout=180,
                )
            tmp.replace(out_p)
            print(f"fetched {out_p}", flush=True)

ok = True
for entry in manifest["files"]:
    dest = Path(entry["dest"])
    if "parts" in entry and entry["id"] in missing:
        tmp = dest.with_suffix(".assembling")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("wb") as out_f:
            for part in entry["parts"]:
                part_p = Path("raw") / Path(part).name
                with part_p.open("rb") as in_f:
                    shutil.copyfileobj(in_f, out_f, 1 << 20)
                part_p.unlink(missing_ok=True)
        tmp.replace(dest)
    got = sha256(dest)
    print(("OK  " if got == entry["sha256"] else "FAIL"), entry["dest"], got, flush=True)
    ok &= got == entry["sha256"]

sys.exit(0 if ok else 1)
PY
echo RESTORE_VERIFIED
