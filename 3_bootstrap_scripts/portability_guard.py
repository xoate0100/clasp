#!/usr/bin/env python3
"""
Portability guard: flag Python-only / bash-only operational steps introduced
into neutral protocol paths (5_reference_architectures, 7_schemas, meta.*).

Exit 1 when violations found (suitable for CI / pre-commit warn or block).
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(".").resolve()
SCAN_GLOBS = [
    "5_reference_architectures/**/*.md",
    "7_schemas/**/*.json",
    "meta.ps1",
    "meta.sh",
    "adapters/*/stack_adapter.yaml",
    "adapters/*/stack_adapter.json",
]

# Patterns that re-introduce single-stack lock-in into the *neutral* surface
BANNED = [
    (re.compile(r"python3\s+3_bootstrap_scripts/", re.I), "hardcoded python3 bootstrap path"),
    (re.compile(r"\bbash\s+scripts/", re.I), "bash-only script invocation"),
    (re.compile(r"pre-commit\s+run", re.I), "pre-commit-only validate binding in protocol doc"),
]


def iter_files():
    for pattern in SCAN_GLOBS:
        yield from ROOT.glob(pattern)


def main() -> int:
    violations = []
    for path in iter_files():
        if not path.is_file():
            continue
        # Adapter manifests may legitimately mention runtimes — skip adapters/*
        if "adapters" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for cre, label in BANNED:
            if cre.search(text):
                # Allow documentation of legacy mapping tables
                if "Legacy" in text or "legacy" in text and "mapping" in text.lower():
                    continue
                violations.append(f"{path.relative_to(ROOT)}: {label}")

    if violations:
        print("[portability-guard] FAIL — neutral protocol reintroduced stack lock-in:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("[portability-guard] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
