"""Layer 3E — evaluator registry and execution."""

from __future__ import annotations

import pathlib
import subprocess
import sys
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


def load_evaluator_registry(root: pathlib.Path) -> dict[str, Any]:
    path = root / "5_reference_architectures" / "EVALUATOR_REGISTRY.yaml"
    if not path.exists() or yaml is None:
        return {"version": "1.0.0", "evaluators": []}
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def run_evaluator(evaluator: dict[str, Any], root: pathlib.Path, timeout: int = 120) -> dict[str, Any]:
    script = evaluator.get("implementation_ref", "")
    script_path = root / script
    result = {
        "evaluator_id": evaluator.get("id"),
        "passed": False,
        "score": 0.0,
        "blocking": evaluator.get("can_block", False),
        "output": "",
    }
    if not script_path.is_file():
        result["output"] = f"missing script: {script}"
        return result
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    result["output"] = (proc.stdout or proc.stderr or "")[:2000]
    result["passed"] = proc.returncode == 0
    result["score"] = 1.0 if proc.returncode == 0 else 0.0
    return result


def run_evaluators(root: pathlib.Path, evaluator_ids: list[str] | None = None) -> list[dict[str, Any]]:
    registry = load_evaluator_registry(root)
    results: list[dict[str, Any]] = []
    for ev in registry.get("evaluators") or []:
        if not isinstance(ev, dict) or not ev.get("id"):
            continue
        if evaluator_ids and ev["id"] not in evaluator_ids:
            continue
        results.append(run_evaluator(ev, root))
    return results


def evaluators_passed(results: list[dict[str, Any]]) -> bool:
    for result in results:
        if result.get("blocking") and not result.get("passed"):
            return False
    return True
