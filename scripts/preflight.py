#!/usr/bin/env python3
"""Hash-pinned, fail-closed protocol preflight. No training or slot selection.

Exit 2 means blocked, not a tool crash. --restore fetches only pinned small
reference inputs and the registry witness through GitHub, never DrivenData.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import saturation_certificate  # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def restore_entry(entry):
    path = ROOT / entry["local_path"]
    if path.exists() and sha256(path) == entry["sha256"]:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    import tempfile
    try:
        fetched = False
        try:
            with tempfile.TemporaryDirectory() as git_dir:
                subprocess.run(["git", "init", "-q", git_dir], check=True, timeout=30)
                subprocess.run(
                    ["git", "-C", git_dir, "remote", "add", "origin", f"https://github.com/{entry['repo']}.git"],
                    check=True, timeout=30,
                )
                subprocess.run(
                    ["git", "-C", git_dir, "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", entry["ref"]],
                    check=True, timeout=180,
                )
                with tmp.open("wb") as stream:
                    subprocess.run(
                        ["git", "-C", git_dir, "show", f"{entry['ref']}:{entry['path']}"],
                        stdout=stream, check=True, timeout=180,
                    )
                if sha256(tmp) == entry["sha256"]:
                    fetched = True
        except (OSError, subprocess.SubprocessError):
            fetched = False
        if not fetched:
            with tmp.open("wb") as stream:
                subprocess.run([
                    "gh", "api",
                    f"repos/{entry['repo']}/contents/{entry['path']}?ref={entry['ref']}",
                    "-H", "Accept: application/vnd.github.raw",
                ], stdout=stream, check=True, timeout=180)
        if sha256(tmp) != entry["sha256"]:
            raise ValueError(f"SHA256 mismatch: {entry['local_path']}")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def blocked_reasons(lane, certificate, errors):
    reasons = list(errors)
    if not isinstance(lane, str) or not lane.strip():
        reasons.append("No single method paragraph was assigned in the current request.")
    if certificate is None:
        reasons.append("No valid grid-checked registry saturation certificate is available.")
    elif certificate["universal_overlap_blocker"]:
        reasons.append("Literal forward-overlap gate is unsatisfiable for any nonempty allowed prediction: registry witness covers every allowed cell.")
    else:
        reasons.append("No universal blocker proven; a complete surface and final-dot registry audit is still required before promotion.")
    return reasons


def run(restore=False, lane=None):
    manifest = json.loads((ROOT / "registry/preflight_inputs.json").read_text())
    errors, verified = [], []
    for entry in manifest["files"]:
        try:
            if restore:
                restore_entry(entry)
            if sha256(ROOT / entry["local_path"]) != entry["sha256"]:
                raise ValueError("SHA256 mismatch")
            verified.append(entry)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            errors.append(f"{entry['id']}: {exc}")
    cert = None
    if not errors:
        paths = {e["id"]: ROOT / e["local_path"] for e in verified}
        try:
            with rasterio.open(paths["sample_submission"]) as src:
                fp = np.isfinite(src.read(1))
                grid = (src.shape, src.crs, src.transform)
            with rasterio.open(paths["existing_faults"]) as src:
                if src.count != 1 or (src.shape, src.crs, src.transform) != grid:
                    raise ValueError("catalogue grid mismatch")
                cat = src.read(1) > 0
            cert = saturation_certificate(paths["saturation_witness"], fp, cat, expected_grid=grid)
            cert["witness_file"] = str(paths["saturation_witness"].relative_to(ROOT))
        except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
            errors.append(str(exc))
    reasons = blocked_reasons(lane, cert, errors)
    card = dict(
        schema_version=1, reviewed_utc=datetime.now(timezone.utc).isoformat(),
        review_type="protocol preflight, not a model experiment", assigned_lane=lane,
        hypothesis="A full-footprint positive registry raster makes the literal 3-pixel forward-overlap gate impossible for every nonempty in-footprint candidate.",
        mechanism="Every permitted dot lies on positive witness support, hence within 3 pixels of it; forward overlap is exactly one.",
        non_fault_process="Continuous probability support is a raster representation, not evidence of a physical fault at every pixel.",
        holdout=None, holdout_note="No new HOLDOUT-DTI experiment; no organizer receipt; no score projection.",
        correlation_overlap_vs_registry=cert,
        raster_sha256=None, validator_output=None, submission_name=None,
        submission_note="DO NOT SUBMIT: literal registry gate blocks every nonempty candidate; no new raster generated.",
        verdict="negative", ok_to_download_existing_for_inspection=True, ok_to_submit=False,
        training_allowed=False, new_tif_generated=False, new_experiments=0,
        submission_slots_used=0, organizer_confirmed_score=None,
        stop_required=True, reasons=reasons, verified_inputs=verified,
        scope="One verified counterexample is enough to prove impossibility. This is NOT a complete registry inventory or a new score-surface audit.",
        required_resolution="An explicit revised registry representation policy and an assigned method lane are needed. Do not exclude continuous rasters silently. Slot selection remains separate.",
    )
    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    for rel in ("evidence/protocol_preflight.json", "docs/data/protocol_preflight.json"):
        (ROOT / rel).write_text(text)
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--lane", help="Explicit assigned method; never inferred from old run cards")
    args = parser.parse_args()
    card = run(args.restore, args.lane)
    print(json.dumps(card, indent=2, allow_nan=False))
    return 2 if card["stop_required"] else 0


if __name__ == "__main__":
    sys.exit(main())
