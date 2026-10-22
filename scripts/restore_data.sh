#!/usr/bin/env bash
# Restore every SHA-256-pinned input from GitHub mirrors (registry/data_manifest.json +
# registry/data_manifest_gems73.json) using zero-rate-limit git blob fetch or streaming
# codeload.github.com tarballs first, falling back to gh api only if needed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/data"
mkdir -p bridge registry external raw scored

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
import tempfile
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

# Optional pinned comparators referenced by sibling lanes
extra_items = [
    ("buffedlizard55-lab/GEMSDOE24", "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
     "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
     Path("registry/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif")),
]
for repo, ref, rel, dest in extra_items:
    if not dest.exists():
        batches[(repo, ref)][rel] = dest

g73 = Path("../registry/data_manifest_gems73.json")
if g73.exists():
    m73 = json.loads(g73.read_text())
    for grp, items in m73.items():
        if grp not in ("external", "scored") or not isinstance(items, list):
            continue
        for entry in items:
            dest = Path(grp) / Path(entry.get("dest", entry["path"])).name
            if dest.exists() and ("sha256" not in entry or sha256(dest) == entry["sha256"]):
                continue
            batches[(entry["repo"], entry["ref"])][entry["path"]] = dest

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
                    stdout=out_f, check=True, timeout=180,
                )
            tmp.replace(out_p)
            print(f"fetched {out_p}", flush=True)

# Optional blob-pinned comparator gems70_p5_54000.tif
p70 = Path("registry/gems70_p5_54000.tif")
if not p70.exists():
    try:
        with tempfile.TemporaryDirectory() as gd:
            subprocess.run(["git", "init", "-q", gd], check=True, timeout=30)
            subprocess.run(["git", "-C", gd, "remote", "add", "r", "https://github.com/buffedlizard55-lab/GEMSDOE70.git"], check=True, timeout=30)
            subprocess.run(["git", "-C", gd, "fetch", "-q", "--depth", "1", "--filter=blob:none", "r", "cd915f3f67ba82aa7f99412fc10f1586b49bfab1"], check=True, timeout=120)
            with p70.open("wb") as out_f:
                subprocess.run(["git", "-C", gd, "cat-file", "blob", "cd915f3f67ba82aa7f99412fc10f1586b49bfab1"], stdout=out_f, check=True, timeout=120)
    except Exception:
        p70.unlink(missing_ok=True)

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
