#!/usr/bin/env python3
"""Restore and SHA-256 verify all competition, external, and historical scored files in registry/data_manifest_gems73.json.

Uses zero-rate-limit streaming tarballs from codeload.github.com grouped by (repo, ref) first,
falling back to gh api / raw.githubusercontent.com only if needed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    """GEMSDOE78 local data root (env override, else .cache/gems_data)."""
    env = os.environ.get("GEMS_DATA_DIR")
    return Path(env).expanduser() if env else ROOT / ".cache" / "gems_data"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_stream_batch(repo: str, ref: str, wanted: dict[str, Path]) -> set[str]:
    """Stream a single GitHub codeload tarball for (repo, ref) and extract all requested paths."""
    if not wanted:
        return set()
    extracted: set[str] = set()
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    req = urllib.request.Request(url, headers={"User-Agent": "gems78-data-restore"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                for member in tf:
                    if not member.isfile():
                        continue
                    parts = member.name.split("/", 1)
                    rel = parts[1] if len(parts) > 1 else parts[0]
                    if rel in wanted:
                        dest = wanted[rel]
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        fh = tf.extractfile(member)
                        if fh is not None:
                            tmp = dest.with_suffix(dest.suffix + ".partial")
                            try:
                                with tmp.open("wb") as out:
                                    shutil.copyfileobj(fh, out, 1 << 20)
                                tmp.replace(dest)
                                extracted.add(rel)
                            finally:
                                tmp.unlink(missing_ok=True)
                        if len(extracted) == len(wanted):
                            break
    except Exception:
        return extracted
    return extracted


def fetch_single_fallback(repo: str, ref: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    try:
        # Prefer zero-rate-limit streaming tarball extraction via codeload.github.com first
        import tarfile
        import urllib.request

        tar_url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
        found_member = False
        try:
            req = urllib.request.Request(tar_url, headers={"User-Agent": "gemsdoe78-restore/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                    for m in tf:
                        rel = m.name.split("/", 1)[1] if "/" in m.name else m.name
                        if rel == path and m.isfile():
                            fobj = tf.extractfile(m)
                            if fobj is not None:
                                with tmp.open("wb") as out:
                                    shutil.copyfileobj(fobj, out, 1 << 20)
                                found_member = True
                            break
        except Exception:
            found_member = False

        if not found_member:
            if shutil.which("gh"):
                with tmp.open("wb") as out:
                    subprocess.run(
                        [
                            "gh",
                            "api",
                            f"repos/{repo}/contents/{path}?ref={ref}",
                            "-H",
                            "Accept: application/vnd.github.raw",
                        ],
                        stdout=out,
                        check=True,
                    )
            else:
                raise RuntimeError(f"Could not fetch {repo}@{ref}:{path}")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group", default="all", choices=["core", "external", "scored", "all"])
    ap.add_argument("--manifest", default=str(ROOT / "registry" / "data_manifest_gems73.json"))
    ap.add_argument("--target-dir", default=None, help="Override destination directory")
    ap.add_argument("--link-data", action="store_true", help="Also symlink restored tree into data/")
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text())
    root = Path(args.target_dir) if args.target_dir else data_dir()
    root.mkdir(parents=True, exist_ok=True)

    selected = [e for e in man["files"] if args.group in ("all", e["group"])]
    missing_entries = []
    batch_by_repo_ref: dict[tuple[str, str], dict[str, Path]] = defaultdict(dict)

    for e in selected:
        dest = root / e["dest"]
        if not (dest.exists() and sha256_file(dest) == e["sha256"]):
            missing_entries.append(e)
            key = (e["repo"], e["ref"])
            if "parts" in e:
                for part in e["parts"]:
                    batch_by_repo_ref[key][part] = root / "raw_parts" / Path(part).name
            else:
                batch_by_repo_ref[key][e["path"]] = dest

    for (repo, ref), wanted in batch_by_repo_ref.items():
        got_paths = fetch_stream_batch(repo, ref, wanted)
        for rel, dest in wanted.items():
            if rel not in got_paths and not dest.exists():
                fetch_single_fallback(repo, ref, rel, dest)

    results = []
    was_missing = {e["id"] for e in missing_entries}
    for e in selected:
        dest = root / e["dest"]
        if "parts" in e and e["id"] in was_missing:
            tmp = dest.with_suffix(".assembling")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            with tmp.open("wb") as out:
                for part in e["parts"]:
                    p = root / "raw_parts" / Path(part).name
                    with p.open("rb") as src:
                        shutil.copyfileobj(src, out, 1 << 20)
                    p.unlink(missing_ok=True)
            tmp.replace(dest)
        got = sha256_file(dest)
        if got != e["sha256"]:
            dest.unlink(missing_ok=True)
            raise SystemExit(f"HASH MISMATCH for {e['id']}: {got} != {e['sha256']}")
        st = "restored" if e["id"] in was_missing else "present"
        results.append(
            {
                "id": e["id"],
                "dest": e["dest"],
                "group": e["group"],
                "status": st,
                "bytes": dest.stat().st_size,
                "sha256": got,
            }
        )
        print(f"{st:>8}  {e['dest']:82s}  sha256={got[:12]}…")

    data_link_dir = ROOT / "data"
    data_link_dir.mkdir(parents=True, exist_ok=True)
    if args.link_data:
        for e in selected:
            src = (root / e["dest"]).resolve()
            dst = data_link_dir / e["dest"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.is_symlink() or dst.exists():
                if dst.resolve() == src:
                    continue
                dst.unlink()
            dst.symlink_to(src)

    receipt = {
        "schema_version": 1,
        "verified_files_count": len(results),
        "storage_root": str(root),
        "files": results,
    }
    (data_link_dir / "restore_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Verified {len(results)} files; receipt written to data/restore_receipt.json")


if __name__ == "__main__":
    main()
