#!/usr/bin/env python3
"""
Master agentic coordination validator — runs all registry validators and scans.

Used by CI, init self-checks, and `cli.py agentic validate`.

Usage:
    python 3_bootstrap_scripts/agentic_coordinate_validate.py
    python 3_bootstrap_scripts/agentic_coordinate_validate.py --skip-scan
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CORE_VALIDATORS = [
    "decision_registry_validate.py",
    "agent_registry_validate.py",
    "drift_vectors_validate.py",
    "workspace_spine_validate.py",
]

OPTIONAL_VALIDATORS = [
    ("knowledge_index", "knowledge_sources_validate.py"),
    ("governance_drift_validator", "governance_drift_validate.py"),
    ("reference_validator", "reference_validate.py"),
    ("doc_lifecycle", "docs_archive.py"),
]

SCANS = [
    ("resurrection_scan.py", []),
    ("drift_vector_check.py", []),
]


def run_script(name: str, extra: list[str] | None = None) -> int:
    script = REPO_ROOT / "3_bootstrap_scripts" / name
    if not script.exists():
        print(f"[agentic-validate] FAIL: missing {script}")
        return 1
    cmd = [sys.executable, str(script), *(extra or [])]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-scan", action="store_true", help="Skip diff scans (validators only)")
    # Deprecated: older spoke CI workflows still pass this after hub CLI rename.
    # Kept as a no-op so ratchet PRs do not fail on unrecognized arguments.
    parser.add_argument(
        "--core-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    if args.core_only:
        print("[agentic-validate] WARN: --core-only is deprecated and ignored")

    exit_code = 0
    for validator in CORE_VALIDATORS:
        code = run_script(validator)
        if code != 0:
            exit_code = code

    try:
        sys.path.insert(0, str(REPO_ROOT))
        from agentic.optional_tools import is_tool_enabled

        for tool_id, script in OPTIONAL_VALIDATORS:
            if not is_tool_enabled(tool_id, REPO_ROOT):
                print(f"[agentic-validate] SKIP optional: {tool_id}")
                continue
            extra = ["validate"] if script == "docs_archive.py" else []
            code = run_script(script, extra)
            if code != 0:
                exit_code = code
    except ImportError:
        pass

    if not args.skip_scan:
        for scan, extra in SCANS:
            code = run_script(scan, extra)
            if code != 0:
                exit_code = code

    if exit_code == 0:
        print("[agentic-validate] OK: all agentic validators passed")
    else:
        print("[agentic-validate] FAIL: one or more agentic checks failed")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
