#!/usr/bin/env python3
"""Validate WORKSPACE_SPINE_REGISTRY.yaml — meta-registry paths and validator refs."""

from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

try:
    import yaml
    import jsonschema
except ImportError:
    print("[workspace-spine] ERROR: PyYAML and jsonschema required")
    sys.exit(1)

REGISTRY_PATH = REPO_ROOT / "5_reference_architectures" / "WORKSPACE_SPINE_REGISTRY.yaml"
SCHEMA_PATH = REPO_ROOT / "7_schemas" / "workspace_spine.schema.json"


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"[workspace-spine] FAIL: missing {REGISTRY_PATH}")
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
    for reg in data.get("registries") or []:
        if not isinstance(reg, dict):
            continue
        rid = reg.get("id", "")
        if rid in seen:
            errors.append(f"duplicate registry id: {rid}")
        seen.add(rid)

        rel_path = reg.get("path", "")
        if rel_path and not (REPO_ROOT / rel_path).exists():
            errors.append(f"{rid}: registry path missing: {rel_path}")

        for key in ("validator", "indexer"):
            script = reg.get(key)
            if script:
                script_path = REPO_ROOT / script
                if not script_path.exists():
                    errors.append(f"{rid}: {key} script missing: {script}")

        schema_rel = reg.get("schema")
        if schema_rel and not (REPO_ROOT / schema_rel).exists():
            errors.append(f"{rid}: schema missing: {schema_rel}")

    if errors:
        print("[workspace-spine] FAIL:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"[workspace-spine] OK: {len(data.get('registries') or [])} registry(ies) cataloged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
