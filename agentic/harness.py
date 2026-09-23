"""Agent graph tool dispatcher — reads AGENT_REGISTRY.yaml, runs registered tools."""

from __future__ import annotations

import importlib
import pathlib
import sys
from typing import Any

from agentic.exec_guard import Limits, run_guarded
from agentic.live_gate import require_live_enabled, tool_requires_live
from agentic.registry import load_agent_registry

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _tool_config(registry: dict[str, Any], tool_name: str) -> dict[str, Any]:
    tools = registry.get("tools") or {}
    cfg = tools.get(tool_name)
    return cfg if isinstance(cfg, dict) else {}


def _exec_limits(registry: dict[str, Any]) -> Limits:
    """Resolve execution caps from registry cost_guardrails.exec_limits (or defaults)."""
    guardrails = registry.get("cost_guardrails") or {}
    ex = guardrails.get("exec_limits") or {}
    base = Limits()
    return Limits(
        wall_timeout_s=float(ex.get("wall_timeout_s", base.wall_timeout_s)),
        max_memory_mb=int(ex.get("max_memory_mb", base.max_memory_mb)),
        max_output_bytes=int(ex.get("max_output_bytes", base.max_output_bytes)),
        max_subprocesses=int(ex.get("max_subprocesses", base.max_subprocesses)),
        max_cpu_seconds=float(ex.get("max_cpu_seconds", base.max_cpu_seconds)),
    )


def run_tool(tool_name: str, extra_args: list[str] | None = None, root: pathlib.Path | None = None) -> int:
    """Execute a tool declared in AGENT_REGISTRY.yaml."""
    root = root or REPO_ROOT
    registry = load_agent_registry(root)
    cfg = _tool_config(registry, tool_name)
    extra_args = extra_args or []

    if not cfg:
        print(f"[harness] unknown tool: {tool_name}")
        return 2

    if tool_requires_live(registry, tool_name):
        try:
            require_live_enabled(tool_name, root)
        except PermissionError as exc:
            print(f"[harness] FAIL: {exc}")
            return 1

    if "script" in cfg:
        script = root / cfg["script"]
        cmd = [sys.executable, str(script), *extra_args]
        result = run_guarded(cmd, cwd=root, limits=_exec_limits(registry), label=tool_name)
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        if result.killed:
            print(f"[harness] GUARD KILLED {tool_name}: {result.reason}")
        return result.returncode

    if "module" in cfg and "fn" in cfg:
        module = importlib.import_module(str(cfg["module"]))
        fn = getattr(module, str(cfg["fn"]))
        result = fn(root)
        item_count = len(result.get("decisions", result))
        print(f"[harness] {tool_name}: loaded {item_count} item(s)")
        return 0

    if "path" in cfg:
        path = root / cfg["path"]
        if path.exists():
            print(path.read_text(encoding="utf-8", errors="replace")[:500])
            return 0
        print(f"[harness] missing path for {tool_name}: {path}")
        return 1

    print(f"[harness] tool '{tool_name}' has no runnable target")
    return 2


def run_reviewer_pipeline(root: pathlib.Path | None = None) -> int:
    """Run reviewer-role checks: resurrection, drift, phase gate on staged changes."""
    root = root or REPO_ROOT
    steps = [
        ("resurrection_scan", []),
        ("drift_vector_check", []),
        ("phase_gate_check", ["--staged"]),
    ]
    exit_code = 0
    for tool_name, args in steps:
        code = run_tool(tool_name, args, root=root)
        if code != 0:
            exit_code = code
    return exit_code


def run_validator_pipeline(root: pathlib.Path | None = None) -> int:
    """Run validator-role checks."""
    root = root or REPO_ROOT
    steps = [
        ("architecture_check", []),
        ("schema_validate", []),
    ]
    exit_code = 0
    for tool_name, args in steps:
        code = run_tool(tool_name, args, root=root)
        if code != 0:
            exit_code = code
    return exit_code
