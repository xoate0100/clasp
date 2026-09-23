#!/usr/bin/env python3
"""
Cross-check governance sources: feature_flags permissions vs AI_SANDBOX_RULES.

Fails when write_to prefixes overlap readonly prefixes, or when write_to
conflicts with sandbox forbidden prefixes.
"""

from __future__ import annotations

import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.optional_tools import is_tool_enabled  # noqa: E402

try:
    import yaml
except ImportError:
    print("[governance-drift] ERROR: PyYAML required")
    sys.exit(1)

FLAGS_PATH = REPO_ROOT / "0_phase0_bootstrap" / "feature_flags.yml"
SANDBOX_PATH = REPO_ROOT / "0_phase0_bootstrap" / "AI_SANDBOX_RULES.md"


def _norm_dir(prefix: str) -> str:
    return prefix.replace("\\", "/").rstrip("/") + "/"


def load_permissions() -> tuple[set[str], set[str], set[str]]:
    with open(FLAGS_PATH, encoding="utf-8") as handle:
        flags = yaml.safe_load(handle) or {}
    perms = flags.get("permissions") or {}
    write_to = {_norm_dir(p) for p in (perms.get("write_to") or []) if isinstance(p, str)}
    readonly = {_norm_dir(p) for p in (perms.get("readonly") or []) if isinstance(p, str)}
    elevated = {_norm_dir(p) for p in (perms.get("elevated_write_to") or []) if isinstance(p, str)}
    return write_to, readonly, elevated


def parse_sandbox_forbidden() -> set[str]:
    if not SANDBOX_PATH.exists():
        return set()
    text = SANDBOX_PATH.read_text(encoding="utf-8")
    forbidden: set[str] = set()
    in_forbidden = False
    for line in text.splitlines():
        if line.strip().startswith("## Forbidden"):
            in_forbidden = True
            continue
        if in_forbidden and line.startswith("## "):
            break
        if not in_forbidden:
            continue
        for match in re.findall(r"`([^`]+/)`", line):
            forbidden.add(_norm_dir(match))
    return forbidden


def overlaps(prefix_a: str, prefix_b: str) -> bool:
    return prefix_a.startswith(prefix_b) or prefix_b.startswith(prefix_a)


def main() -> int:
    if not is_tool_enabled("governance_drift_validator"):
        print("[governance-drift] SKIP: optional tool disabled")
        return 0

    if not FLAGS_PATH.exists():
        print("[governance-drift] SKIP: feature_flags.yml missing")
        return 0

    write_to, readonly, elevated = load_permissions()
    forbidden = parse_sandbox_forbidden()
    errors: list[str] = []

    for w in write_to:
        for r in readonly:
            if overlaps(w, r):
                errors.append(
                    f"write_to/readonly overlap: {w.rstrip('/')} also under readonly {r.rstrip('/')}"
                )

    for w in write_to:
        for f in forbidden:
            if overlaps(w, f):
                errors.append(
                    f"sandbox vs write_to conflict: write_to {w.rstrip('/')} "
                    f"under sandbox-forbidden {f.rstrip('/')}"
                )

    # elevated_write_to is the intentional hub-maint carve-out for Forbidden paths.
    # Every elevated path must be Forbidden (or else it belongs in write_to).
    for e in elevated:
        if not any(overlaps(e, f) for f in forbidden):
            errors.append(
                f"elevated_write_to {e.rstrip('/')} is not under any sandbox Forbidden path "
                f"(move it to write_to if agents may edit it)"
            )
        if any(overlaps(e, w) for w in write_to):
            errors.append(
                f"elevated_write_to/write_to overlap: {e.rstrip('/')} also listed in write_to"
            )

    if errors:
        print("[governance-drift] FAIL: governance path contradictions:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(
        "[governance-drift] OK: write_to, readonly, elevated_write_to, "
        "and sandbox forbidden paths are consistent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
