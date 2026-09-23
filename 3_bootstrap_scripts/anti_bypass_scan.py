#!/usr/bin/env python3
"""Scan for governance bypass patterns (--no-verify, hub hooks on spokes)."""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BYPASS_RE = re.compile(r"--no-verify|--no-gpg-sign", re.IGNORECASE)
SKIP_DIRS = {".git", "_recon_scratch", "node_modules", ".venv", "venv"}


def scan_no_verify() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in {".py", ".sh", ".ps1", ".yml", ".yaml", ".md"}:
            continue
        if "PLUMBING_CLASS.md" in str(path) or "DRIFT_VECTORS" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if BYPASS_RE.search(line) and "do not use" not in line.lower():
                rel = path.relative_to(ROOT)
                findings.append(f"{rel}:{i}: {line.strip()[:120]}")
    return findings


def scan_hooks_missing_scope() -> list[str]:
    findings: list[str] = []
    gate = ROOT / "3_bootstrap_scripts" / "task_completion_gate.py"
    if gate.exists():
        text = gate.read_text(encoding="utf-8")
        if "hub_task_gates_apply" not in text:
            findings.append("task_completion_gate.py missing hub_task_gates_apply guard")
    guard = ROOT / "3_bootstrap_scripts" / "guardrail_enforcement.py"
    if guard.exists():
        text = guard.read_text(encoding="utf-8")
        if "_hub_gates_apply" not in text:
            findings.append("guardrail_enforcement.py missing _hub_gates_apply guard")
    return findings


def main() -> int:
    violations = scan_hooks_missing_scope()
    bypass_hits = scan_no_verify()

    if violations:
        print("[anti-bypass] FAIL — missing scope guards:")
        for v in violations:
            print(f"  - {v}")
    else:
        print("[anti-bypass] OK: hub task gates scoped")

    # Documented references are informational, not blocking
    if bypass_hits:
        print(f"[anti-bypass] INFO: {len(bypass_hits)} --no-verify references (review PLUMBING_AUDIT_INVENTORY)")
        for hit in bypass_hits[:20]:
            print(f"  - {hit}")
        if len(bypass_hits) > 20:
            print(f"  ... and {len(bypass_hits) - 20} more")

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
