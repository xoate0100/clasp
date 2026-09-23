#!/usr/bin/env python3
"""Validate KNOWLEDGE_SOURCES.yaml — schema, paths exist, no duplicate ids."""

from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.optional_tools import is_tool_enabled  # noqa: E402

try:
    import yaml
    import jsonschema
except ImportError:
    print("[knowledge-sources] ERROR: PyYAML and jsonschema required")
    sys.exit(1)

REGISTRY_PATH = REPO_ROOT / "5_reference_architectures" / "KNOWLEDGE_SOURCES.yaml"
SCHEMA_PATH = REPO_ROOT / "7_schemas" / "knowledge_sources.schema.json"


def main() -> int:
    if not is_tool_enabled("knowledge_index"):
        print("[knowledge-sources] SKIP: optional tool disabled")
        return 0

    if not REGISTRY_PATH.exists():
        print(f"[knowledge-sources] FAIL: missing {REGISTRY_PATH}")
        return 1

    with open(REGISTRY_PATH, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    errors: list[str] = []
    if SCHEMA_PATH.exists():
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            errors.append(f"schema: {err.message}")

    seen: set[str] = set()
    for source in data.get("sources") or []:
        if not isinstance(source, dict):
            continue
        sid = source.get("id", "")
        if sid in seen:
            errors.append(f"duplicate source id: {sid}")
        seen.add(sid)
        if source.get("enabled") is False:
            continue
        rel = source.get("path", "")
        if rel and not (REPO_ROOT / rel).exists():
            # Priority ≥3 / optional sources are advisory — hub docs like
            # docs/meta_overview.md are not required on every spoke.
            if source.get("optional") is True or int(source.get("priority") or 1) >= 3:
                print(f"[knowledge-sources] WARN: {sid}: missing path {rel} (optional)")
                continue
            errors.append(f"{sid}: missing path {rel}")

    if errors:
        print("[knowledge-sources] FAIL:")
        for err in errors:
            print(f"  - {err}")
        return 1

    enabled = sum(
        1 for s in (data.get("sources") or [])
        if isinstance(s, dict) and s.get("enabled") is not False
    )
    print(f"[knowledge-sources] OK: {enabled} enabled source(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
