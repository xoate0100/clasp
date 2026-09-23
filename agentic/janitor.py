"""Session janitor utilities — staleness detection without recursive side effects."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from typing import Iterable

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_JANITOR_ENV = "META_JANITOR_RUNNING"


def janitor_guard_enter() -> bool:
    if os.environ.get(_JANITOR_ENV) == "1":
        return False
    os.environ[_JANITOR_ENV] = "1"
    return True


def janitor_guard_exit() -> None:
    os.environ.pop(_JANITOR_ENV, None)


def file_mtime(path: pathlib.Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def context_source_paths(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    root = root or REPO_ROOT
    paths = [
        root / "0_phase0_bootstrap" / "AI_SANDBOX_RULES.md",
        root / "0_phase0_bootstrap" / "feature_flags.yml",
        root / "0_phase0_bootstrap" / "MVP_SPECIFICATION.yaml",
        root / "6_ai_runtime_context" / "ACTIVE_PLAN.yaml",
        root / "6_ai_runtime_context" / "ACTIVE_TASK_POINTER.yaml",
        root / "5_reference_architectures" / "LAYER_RULES.yaml",
        root / "5_reference_architectures" / "DECISION_REGISTRY.yaml",
        root / "5_reference_architectures" / "DRIFT_VECTORS.yaml",
        root / "5_reference_architectures" / "AGENT_REGISTRY.yaml",
        root / "5_reference_architectures" / "WORKSPACE_SPINE_REGISTRY.yaml",
        root / "5_reference_architectures" / "KNOWLEDGE_SOURCES.yaml",
        root / "5_reference_architectures" / "OPTIONAL_AGENTIC_TOOLS.yaml",
    ]
    try:
        from agentic.optional_tools import is_tool_enabled

        if is_tool_enabled("knowledge_index", root):
            paths.extend(knowledge_source_paths(root)[1:])
    except Exception:
        pass
    return paths


def is_context_stale(root: pathlib.Path | None = None) -> tuple[bool, str]:
    root = root or REPO_ROOT
    context_file = root / "6_ai_runtime_context" / "AI_CONTEXT.md"
    if not context_file.exists():
        return True, "AI_CONTEXT.md missing"

    try:
        from agentic.context_fingerprint import compute_context_fingerprint, parse_context_fingerprint

        text = context_file.read_text(encoding="utf-8", errors="replace")
        embedded = parse_context_fingerprint(text)
        if embedded is not None:
            current = compute_context_fingerprint(root)
            if embedded == current:
                return False, ""
            return True, "source content changed"
    except Exception:
        pass

    context_mtime = file_mtime(context_file)
    for source in context_source_paths(root):
        if not source.exists():
            continue
        mtime = file_mtime(source)
        if mtime > context_mtime:
            return True, source.name
    return False, ""


def knowledge_index_path(root: pathlib.Path | None = None) -> pathlib.Path:
    root = root or REPO_ROOT
    try:
        import yaml

        cfg_path = root / "5_reference_architectures" / "KNOWLEDGE_SOURCES.yaml"
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            rel = (data.get("index") or {}).get("output_dir", "6_ai_runtime_context/knowledge_index")
            return root / rel / "index.json"
    except Exception:
        pass
    return root / "6_ai_runtime_context" / "knowledge_index" / "index.json"


def knowledge_source_paths(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    root = root or REPO_ROOT
    paths = [root / "5_reference_architectures" / "KNOWLEDGE_SOURCES.yaml"]
    try:
        import yaml

        cfg_path = paths[0]
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            for source in data.get("sources") or []:
                if isinstance(source, dict) and source.get("enabled") is False:
                    continue
                rel = source.get("path") if isinstance(source, dict) else None
                if rel:
                    paths.append(root / rel)
    except Exception:
        pass
    return paths


def is_knowledge_index_stale(root: pathlib.Path | None = None) -> tuple[bool, str]:
    root = root or REPO_ROOT
    index_path = knowledge_index_path(root)
    if not index_path.exists():
        return True, "index missing"

    index_mtime = file_mtime(index_path)
    for source in knowledge_source_paths(root):
        if source.exists() and file_mtime(source) > index_mtime:
            return True, source.name
    return False, ""


def regenerate_context(root: pathlib.Path | None = None) -> int:
    root = root or REPO_ROOT
    env = os.environ.copy()
    env[_JANITOR_ENV] = "1"
    result = subprocess.run(
        [sys.executable, str(root / "3_bootstrap_scripts" / "generate_ai_context.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout)
    return result.returncode


def rebuild_knowledge_index(root: pathlib.Path | None = None) -> int:
    root = root or REPO_ROOT
    result = subprocess.run(
        [sys.executable, str(root / "3_bootstrap_scripts" / "knowledge_index_build.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout)
    return result.returncode


def trim_run_log(max_runs: int = 200, keep: int = 100, root: pathlib.Path | None = None) -> bool:
    root = root or REPO_ROOT
    log_path = root / "6_ai_runtime_context" / "AGENTIC_RUN_LOG.yaml"
    if not log_path.exists():
        return False

    try:
        import yaml

        with open(log_path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        runs = data.get("runs") or []
        if len(runs) <= max_runs:
            return False
        data["runs"] = runs[-keep:]
        with open(log_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)
        return True
    except Exception:
        return False
