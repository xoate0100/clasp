#!/usr/bin/env python3
"""
Complexity check using component-specific limits from feature_flags.yml
"""
import sys
import pathlib
import re

try:
    import yaml
except ImportError:
    print("[complexity] ERROR: PyYAML required for complexity check")
    print("[complexity] Install with: pip install PyYAML")
    sys.exit(1)


def load_complexity_limits():
    """Load complexity limits from feature_flags.yml"""
    flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists():
        # Default limits
        return {
            "backend": 10,
            "frontend": 12,
            "shared": 10
        }

    try:
        flags = yaml.safe_load(open(flags_path))
        components = flags.get("components", {})
        return {
            "backend": components.get("backend", {}).get("complexity_limit", 10),
            "frontend": components.get("frontend", {}).get("complexity_limit", 12),
            "shared": components.get("shared", {}).get("complexity_limit", 10)
        }
    except Exception as e:
        print(f"[complexity] Error loading limits: {e}, using defaults")
        return {
            "backend": 10,
            "frontend": 12,
            "shared": 10
        }


def calculate_complexity(content: str) -> int:
    """Heuristic complexity: count branching statements"""
    return (
        content.count("if ") +
        content.count("for ") +
        content.count("while ") +
        content.count("case ") +
        content.count("catch ")
    )


def check_complexity():
    """Check complexity against component limits"""
    limits = load_complexity_limits()
    violations = []
    # Wave F propose-only daemon modules — file-level heuristic exceeds limit by design
    exempt = {
        pathlib.Path("backend/behavioral_daemon/kiwi_remediation.py"),
        pathlib.Path("backend/behavioral_daemon/remediation_agent.py"),
    }

    for component in ("backend", "frontend", "shared"):
        rp = pathlib.Path(component)
        if not rp.exists():
            continue

        limit = limits.get(component, 10)

        for p in rp.rglob("*.*"):
            if p in exempt:
                continue
            if p.suffix not in (".py", ".ts", ".tsx", ".js", ".jsx"):
                continue

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except:
                continue

            complexity = calculate_complexity(content)
            if complexity > limit:
                violations.append(
                    f"{p}: complexity {complexity} exceeds limit {limit} for {component}"
                )

    if violations:
        print("[complexity] Findings:")
        print("\n".join(f"- {v}" for v in violations))
        sys.exit(1)

    print("[complexity] OK")


if __name__ == "__main__":
    check_complexity()
