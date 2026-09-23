#!/usr/bin/env python3
"""Platform connectivity and registry validation."""

from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(".").resolve()
sys.path.insert(0, str(REPO_ROOT))

from agent_platform.layer3.capability_registry import validate_registry


def main() -> int:
    errors = validate_registry(REPO_ROOT)
    if not (REPO_ROOT / "agent_platform" / "orchestration" / "workflow.py").is_file():
        errors.append("orchestration workflow missing")
    if not (REPO_ROOT / "5_reference_architectures" / "CAPABILITY_REGISTRY.yaml").is_file():
        errors.append("CAPABILITY_REGISTRY.yaml missing")
    if errors:
        print("[platform-validate] FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("[platform-validate] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
