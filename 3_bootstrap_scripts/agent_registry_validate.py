#!/usr/bin/env python3
"""Validate AGENT_REGISTRY.yaml — graph edges, tool refs, write_policy paths."""

from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    import yaml
    import jsonschema
except ImportError:
    print("[agent-registry] ERROR: PyYAML and jsonschema required")
    sys.exit(1)

REGISTRY_PATH = REPO_ROOT / "5_reference_architectures" / "AGENT_REGISTRY.yaml"
SCHEMA_PATH = REPO_ROOT / "7_schemas" / "agent_registry.schema.json"


def load_registry() -> dict:
    with open(REGISTRY_PATH, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def tool_exists(tool_name: str, tool_cfg: dict) -> bool:
    if not isinstance(tool_cfg, dict):
        return False
    if "script" in tool_cfg:
        return (REPO_ROOT / tool_cfg["script"]).exists()
    if "path" in tool_cfg:
        return (REPO_ROOT / tool_cfg["path"]).exists()
    if "module" in tool_cfg:
        module_path = REPO_ROOT / str(tool_cfg["module"]).replace(".", "/")
        return module_path.with_suffix(".py").exists() or (module_path / "__init__.py").exists()
    return False


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    if SCHEMA_PATH.exists():
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            errors.append(f"schema: {err.message} at {list(err.path)}")

    agents = {a["id"]: a for a in (data.get("agents") or []) if isinstance(a, dict) and "id" in a}
    tools_catalog = data.get("tools") or {}
    graph = data.get("graph") or {}

    start = graph.get("start")
    if start and start not in agents:
        errors.append(f"graph.start references unknown agent '{start}'")

    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        for key in ("from", "to"):
            node = edge.get(key)
            if node and node not in agents and node not in ("done", "human_gate"):
                errors.append(f"graph edge {edge}: unknown node '{node}'")

    for agent_id, agent in agents.items():
        for tool_name in agent.get("tools") or []:
            if tool_name not in tools_catalog:
                errors.append(f"agent '{agent_id}': unknown tool '{tool_name}'")
            elif not tool_exists(tool_name, tools_catalog[tool_name]):
                errors.append(f"agent '{agent_id}': tool '{tool_name}' target missing")

    entry_gate = graph.get("entry_gate")
    if entry_gate and not (REPO_ROOT / entry_gate).exists():
        errors.append(f"entry_gate script missing: {entry_gate}")

    write_policy = data.get("write_policy") or {}
    for glob_pattern in write_policy.get("allowed_write_globs") or []:
        if not glob_pattern.strip():
            errors.append("write_policy: empty allowed_write_glob")

    return errors


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"[agent-registry] FAIL: missing {REGISTRY_PATH}")
        return 1

    errors = validate(load_registry())
    if errors:
        print("[agent-registry] FAIL:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[agent-registry] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
