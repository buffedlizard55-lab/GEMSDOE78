#!/usr/bin/env python3
"""Verify all core & external SHA-256 hashes and materialize nearest-exact-mask-v2 stack19.npy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems78 import data, mghd


def main() -> None:
    core = data.verify_inputs()
    ext = mghd.verify_external_inputs()
    stack_path = data.build_stack()
    receipt = json.loads((data._ensure_proc_dir() / "stack19_cache.json").read_text())
    print(
        json.dumps(
            {
                "core_inputs_verified": len(core),
                "external_inputs_verified": len(ext),
                "stack_path": str(stack_path),
                "fill_algorithm": receipt["fill_algorithm"],
                "stack_sha256": receipt["stack_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
