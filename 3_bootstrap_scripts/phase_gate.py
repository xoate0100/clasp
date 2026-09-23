#!/usr/bin/env python3
"""
Phase gate — block work outside the active MVP development phase.

Keyed to MVP_SPECIFICATION.yaml DEVELOPMENT_PHASES, ACTIVE_PLAN.yaml phase_id,
and optional 5_reference_architectures/PHASE_GATE_KEYWORDS.yaml.
Override with META_PHASE_GATE_OVERRIDE=1 for explicit unlock.

Usage:
    python 3_bootstrap_scripts/phase_gate.py
    python 3_bootstrap_scripts/phase_gate.py --status
    python 3_bootstrap_scripts/phase_gate.py --check-path backend/src/example.py
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.diff_utils import extract_added_lines, is_guardrail_catalog_path  # noqa: E402

try:
    import yaml
except ImportError:
    print("[phase-gate] ERROR: PyYAML required")
    sys.exit(1)

MVP_PATH = REPO_ROOT / "0_phase0_bootstrap" / "MVP_SPECIFICATION.yaml"
PLAN_PATH = REPO_ROOT / "6_ai_runtime_context" / "ACTIVE_PLAN.yaml"
KEYWORDS_PATH = REPO_ROOT / "5_reference_architectures" / "PHASE_GATE_KEYWORDS.yaml"


def _load_yaml(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def current_phase() -> tuple[str, str]:
    plan = _load_yaml(PLAN_PATH)
    phase_id = str(plan.get("phase_id") or "phase_0")
    mvp = _load_yaml(MVP_PATH)
    phases = mvp.get("DEVELOPMENT_PHASES") or {}
    phase_info = phases.get(phase_id) or {}
    phase_name = str(phase_info.get("name") or phase_id)
    return phase_id, phase_name


def phase_order() -> list[str]:
    mvp = _load_yaml(MVP_PATH)
    phases = mvp.get("DEVELOPMENT_PHASES") or {}
    return list(phases.keys())


def load_phase_keywords() -> dict[str, list[str]]:
    data = _load_yaml(KEYWORDS_PATH)
    raw = data.get("phase_keywords") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for phase_id, keywords in raw.items():
        if isinstance(keywords, list):
            out[str(phase_id)] = [str(k) for k in keywords if str(k).strip()]
    return out


def is_future_phase_work(text: str, active_phase: str) -> list[str]:
    order = phase_order()
    if active_phase not in order:
        return []

    active_idx = order.index(active_phase)
    violations: list[str] = []
    lowered = text.lower()
    phase_keywords = load_phase_keywords()

    for phase_id, keywords in phase_keywords.items():
        if phase_id not in order:
            continue
        if order.index(phase_id) <= active_idx:
            continue
        for kw in keywords:
            if kw.lower() in lowered:
                violations.append(f"{phase_id}: matched future-phase keyword '{kw}'")
    return violations


def get_staged_paths() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    except FileNotFoundError:
        return []


def get_staged_diff() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        return result.stdout or ""
    except FileNotFoundError:
        return ""


def check_paths(paths: list[str], active_phase: str) -> list[str]:
    violations: list[str] = []
    for rel in paths:
        if is_guardrail_catalog_path(rel):
            continue
        path = REPO_ROOT / rel
        if not path.exists():
            continue
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true", help="Print active phase and exit 0")
    parser.add_argument("--staged", action="store_true", help="Check git staged paths and diff content")
    parser.add_argument("--check-path", action="append", default=[], dest="paths")
    args = parser.parse_args()

    phase_id, phase_name = current_phase()

    if args.status:
        print(f"[phase-gate] active: {phase_id} — {phase_name}")
        return 0

    if os.environ.get("META_PHASE_GATE_OVERRIDE") == "1":
        print(f"[phase-gate] OK: override enabled (active {phase_id})")
        return 0

    violations: list[str] = []
    paths = list(args.paths)
    if args.staged:
        paths.extend(get_staged_paths())

    if paths:
        violations.extend(check_paths(paths, phase_id))

    if args.staged:
        diff_text = get_staged_diff()
        if diff_text:
            violations.extend(is_future_phase_work(extract_added_lines(diff_text), phase_id))

    if violations:
        print(f"[phase-gate] FAIL: work outside active phase '{phase_id}':")
        for v in violations:
            print(f"  - {v}")
        print("  Set META_PHASE_GATE_OVERRIDE=1 to unlock explicitly.")
        return 1

    print(f"[phase-gate] OK: {phase_id} — {phase_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
