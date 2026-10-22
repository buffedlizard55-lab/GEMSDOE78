#!/usr/bin/env python3
"""Build a hash- and commit-pinned inventory of accessible sibling GeoTIFFs.

Streams public ``buffedlizard55-lab`` repositories over ``git ls-remote`` +
``https://codeload.github.com/<owner>/<repo>/tar.gz/<commit>`` (zero GitHub REST
API quota required), caches per-(repo, commit) scan manifests under
``data/registry/repo_manifests/`` so reruns only download new commits, validates
that every comparator is readable single-band 3730x3292 EPSG:32611 on the exact
pinned 100 m transform, excludes non-prediction input layers, computes support and
3-px halo coverage for each unique SHA-256 raster, and writes
``registry/accessible_registry_2026-10-22.json``.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.grid import TRANSFORM  # noqa: E402
from gems57.uniqueness import representation_class, representation_class_v2  # noqa: E402

OWNER = "buffedlizard55-lab"
CACHE_DIR = ROOT / "data" / "registry" / "accessible"
REPO_CACHE_DIR = ROOT / "data" / "registry" / "repo_manifests"
OUT_JSON = ROOT / "registry" / "accessible_registry_2026-10-22.json"

EXCLUDED_INPUT_SHA256 = {
    "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
    "26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c",
}

EXCLUDED_BASENAMES = {
    "existing_faults.tif",
    "labels.tif",
    "sample_submission.tif",
    "example_submission.tif",
    "training_features.tif",
    "gems-geodawn-numerical-features.tif",
    "sgmc_faults_100m.tif",
    "derived_sgmc_faults_100m_u8.tif",
    "lidar_scarp_features_u8.tif",
    "geodawn_rad_u8.tif",
    "geodawn_extensions_u8.tif",
    "topo_10m_derived_100m_u8.tif",
    "dem10_chi_100m_i16.tif",
    "dem10_chi_100m_u8.tif",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def candidate_repo_names() -> list[str]:
    names: set[str] = set()
    csv_p = ROOT / "registry" / "family_scores.csv"
    if csv_p.exists():
        with csv_p.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("site_repo"):
                    names.add(row["site_repo"].strip())
    names.add("GEMSDOE")
    for n in range(1, 86):
        names.add(f"GEMSDOE{n}")
        names.add(f"{n}GEMSDOE")
    names.discard("GEMSDOE78")
    return sorted(names)


def resolve_head(repo_name: str) -> tuple[str, str | None, str | None]:
    url = f"https://github.com/{OWNER}/{repo_name}.git"
    for attempt in range(3):
        try:
            proc = subprocess.run(
                ["git", "ls-remote", url, "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                env={"GIT_TERMINAL_PROMPT": "0"},
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return repo_name, None, None
            commit = proc.stdout.split()[0].strip()
            if len(commit) == 40:
                return repo_name, commit, None
            return repo_name, None, f"unexpected HEAD token: {commit}"
        except Exception as exc:
            if attempt == 2:
                return repo_name, None, f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return repo_name, None, None


def stream_repo_tifs(repo_name: str, commit: str) -> tuple[str, str, list[dict], list[str], list[str]]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    REPO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest_p = REPO_CACHE_DIR / f"{repo_name}_{commit}.json"
    if manifest_p.exists():
        saved = json.loads(manifest_p.read_text())
        if all((ROOT / r["cache_file"]).exists() for r in saved.get("found", [])):
            return repo_name, commit, saved["found"], [], saved.get("skipped_corrupt", [])

    url = f"https://codeload.github.com/{OWNER}/{repo_name}/tar.gz/{commit}"
    last_err: str | None = None
    for attempt in range(4):
        found: list[dict] = []
        skipped_corrupt: list[str] = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gemsdoe78-registry-scan/1.0"})
            with urllib.request.urlopen(req, timeout=240) as resp:
                with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                    for member in tf:
                        if not member.isfile():
                            continue
                        rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
                        low = rel.lower()
                        if not (low.endswith(".tif") or low.endswith(".tiff")):
                            continue
                        base = Path(rel).name
                        if base in EXCLUDED_BASENAMES or "/external/" in low or "/raw/" in low or "/bridge/" in low:
                            continue
                        if member.size > 60_000_000 or member.size < 1024:
                            continue
                        fh = tf.extractfile(member)
                        if fh is None:
                            continue
                        data = fh.read()
                        digest = sha256_bytes(data)
                        if digest in EXCLUDED_INPUT_SHA256:
                            continue
                        try:
                            with rasterio.MemoryFile(data) as mem:
                                with mem.open() as ds:
                                    if (
                                        ds.count != 1
                                        or ds.shape != (3730, 3292)
                                        or ds.crs is None
                                        or ds.crs.to_epsg() != 32611
                                        or ds.transform != TRANSFORM
                                    ):
                                        continue
                                    # Verify band payload actually decompresses without error
                                    _ = ds.read(1, window=((0, min(64, ds.height)), (0, ds.width)))
                        except Exception as exc:
                            skipped_corrupt.append(f"{OWNER}/{repo_name}@{commit}:{rel} ({type(exc).__name__})")
                            continue
                        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base)
                        dest = CACHE_DIR / f"{digest[:12]}_{safe}"
                        if not dest.exists():
                            tmp = dest.with_suffix(dest.suffix + ".partial")
                            tmp.write_bytes(data)
                            tmp.replace(dest)
                        found.append(
                            dict(
                                repo=f"{OWNER}/{repo_name}",
                                ref=commit,
                                path=rel,
                                sha256=digest,
                                bytes=len(data),
                                cache_file=str(dest.relative_to(ROOT)),
                            )
                        )
            manifest_p.write_text(
                json.dumps(dict(repo=repo_name, commit=commit, found=found, skipped_corrupt=skipped_corrupt), indent=2)
            )
            return repo_name, commit, found, [], skipped_corrupt
        except Exception as exc:
            last_err = f"{OWNER}/{repo_name}@{commit}: {type(exc).__name__}: {exc}"
            time.sleep(2.0 * (attempt + 1))
    return repo_name, commit, [], [last_err or f"{repo_name}: unknown error"], []


def main(exclude_local_names: set[str] | None = None) -> dict:
    exclude_local_names = set(exclude_local_names or ())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        catalogue = src.read(1) > 0
    allowed = footprint & ~catalogue
    fp_cells = int(footprint.sum())

    candidates = candidate_repo_names()
    print(f"Probing {len(candidates)} candidate repository names...", flush=True)
    accessible_repos: list[tuple[str, str]] = []
    probe_errors: list[str] = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(resolve_head, name) for name in candidates]
        for fut in as_completed(futs):
            name, commit, err = fut.result()
            if commit:
                accessible_repos.append((name, commit))
            elif err:
                probe_errors.append(f"{name}: {err}")
    accessible_repos.sort()
    print(f"Found {len(accessible_repos)} accessible sibling repos.", flush=True)

    raw_hits: list[dict] = []
    scan_errors: list[str] = list(probe_errors)
    skipped_corrupt_all: list[str] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(stream_repo_tifs, name, commit) for name, commit in accessible_repos]
        for idx, fut in enumerate(as_completed(futs), 1):
            name, commit, hits, errs, skipped = fut.result()
            raw_hits.extend(hits)
            scan_errors.extend(errs)
            skipped_corrupt_all.extend(skipped)
            if errs:
                print(f"[{idx}/{len(accessible_repos)}] ERROR {name}@{commit[:8]}: {errs}", flush=True)

    pre = json.loads((ROOT / "registry/preflight_inputs.json").read_text())
    for e in pre["files"]:
        if e["id"] == "saturation_witness":
            p = ROOT / e["local_path"]
            if p.exists():
                dest = CACHE_DIR / f"{e['sha256'][:12]}_{Path(e['path']).name}"
                if not dest.exists():
                    shutil.copy2(p, dest)
                raw_hits.append(
                    dict(
                        repo=e["repo"],
                        ref=e["ref"],
                        path=e["path"],
                        sha256=e["sha256"],
                        bytes=p.stat().st_size,
                        cache_file=str(dest.relative_to(ROOT)),
                    )
                )

    head_self = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        if p.name in exclude_local_names:
            continue
        digest = sha256_file(p)
        dest = CACHE_DIR / f"{digest[:12]}_{p.name}"
        if not dest.exists():
            shutil.copy2(p, dest)
        raw_hits.append(
            dict(
                repo=f"{OWNER}/GEMSDOE78",
                ref=head_self,
                path=str(p.relative_to(ROOT)),
                sha256=digest,
                bytes=p.stat().st_size,
                cache_file=str(dest.relative_to(ROOT)),
            )
        )

    by_sha: dict[str, dict] = {}
    for h in sorted(raw_hits, key=lambda r: (r["repo"], r["path"], r["sha256"])):
        d = h["sha256"]
        src_label = f"{h['repo']}@{h['ref']}:{h['path']}"
        if d not in by_sha:
            by_sha[d] = dict(
                sha256=d,
                repo_first=h["repo"],
                ref_first=h["ref"],
                path_first=h["path"],
                bytes=h["bytes"],
                cache_file=h["cache_file"],
                sources=[src_label],
            )
        else:
            if src_label not in by_sha[d]["sources"]:
                by_sha[d]["sources"].append(src_label)

    print(f"Computing support & fast exact 3-px halo coverage across {len(by_sha)} unique SHA-256 rasters...", flush=True)
    t0 = time.time()
    rasters = []
    for idx, rec in enumerate(by_sha.values(), 1):
        p = ROOT / rec["cache_file"]
        try:
            with rasterio.open(p) as ds:
                arr = ds.read(1).astype(np.float32)
        except Exception as exc:
            skipped_corrupt_all.append(f"{rec['sources'][0]} ({type(exc).__name__}: {exc})")
            continue
        pos = np.isfinite(arr) & (arr > 0) & footprint
        n_pos = int(pos.sum())
        rep1 = representation_class(n_pos, fp_cells)
        rep2 = representation_class_v2(pos, allowed)
        rec.update(
            positive_footprint_pixels=n_pos,
            representation=rep1["kind"],
            support_fraction=rep1["support_fraction"],
            halo_kind=rep2["kind"],
            halo_coverage=rep2["halo_coverage"],
        )
        rasters.append(rec)
        if idx % 200 == 0:
            print(f"  processed {idx}/{len(by_sha)} ({time.time()-t0:.1f}s)", flush=True)

    rasters.sort(key=lambda r: (r["repo_first"], r["path_first"], r["sha256"]))
    space_filling = [r for r in rasters if r["halo_kind"] == "space_filling"]
    discriminating = [r for r in rasters if r["halo_kind"] == "discriminating"]

    inventory = dict(
        schema_version=1,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        evidence_class="REGISTRY-MEASUREMENT",
        owner=OWNER,
        candidate_repo_names_probed=len(candidates),
        accessible_sibling_repos=[dict(repo=f"{OWNER}/{n}", commit=c) for n, c in accessible_repos],
        accessible_sibling_repo_count=len(accessible_repos),
        complete_accessible_scan=len(scan_errors) == 0,
        errors=scan_errors,
        skipped_corrupt_non_submission_files=skipped_corrupt_all,
        unique_raster_count=len(rasters),
        discriminating_raster_count=len(discriminating),
        space_filling_raster_count=len(space_filling),
        space_filling_witnesses=[
            dict(
                sha256=r["sha256"],
                source=r["sources"][0],
                positive_footprint_pixels=r["positive_footprint_pixels"],
                halo_coverage=r["halo_coverage"],
            )
            for r in space_filling
        ],
        scope=(
            "Complete scan of all publicly accessible buffedlizard55-lab GEMSDOE repositories at "
            "the pinned commit hashes listed in accessible_sibling_repos, plus local GEMSDOE78 "
            "downloads. Does NOT cover private repositories, unlinked external accounts, or the "
            "DrivenData organizer's private submission database."
        ),
        rasters=rasters,
    )
    OUT_JSON.write_text(json.dumps(inventory, indent=2, allow_nan=False) + "\n")
    print(
        f"DONE in {time.time()-t0:.1f}s: {len(rasters)} unique rasters "
        f"({len(discriminating)} discriminating, {len(space_filling)} space-filling) "
        f"from {len(accessible_repos)} accessible sibling repos; errors={len(scan_errors)}",
        flush=True,
    )
    return inventory


if __name__ == "__main__":
    inv = main()
    sys.exit(0 if inv["complete_accessible_scan"] else 1)
