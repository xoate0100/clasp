#!/usr/bin/env python3
"""Validate DRIFT_VECTORS.yaml against JSON Schema and linked decisions."""

from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

try:
    import yaml
    import jsonschema
except ImportError:
    print("[drift-vectors] ERROR: PyYAML and jsonschema required")
    sys.exit(1)

REGISTRY_PATH = REPO_ROOT / "5_reference_architectures" / "DRIFT_VECTORS.yaml"
SCHEMA_PATH = REPO_ROOT / "7_schemas" / "drift_vectors.schema.json"
DECISION_PATH = REPO_ROOT / "5_reference_architectures" / "DECISION_REGISTRY.yaml"


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"[drift-vectors] FAIL: missing {REGISTRY_PATH}")
        return 1

    with open(REGISTRY_PATH, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    errors: list[str] = []
    if SCHEMA_PATH.exists():
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            errors.append(f"schema: {err.message}")

    decision_ids: set[str] = set()
    if DECISION_PATH.exists():
        with open(DECISION_PATH, encoding="utf-8") as handle:
            decisions = yaml.safe_load(handle) or {}
        for row in decisions.get("decisions") or []:
            if isinstance(row, dict) and row.get("decision_id"):
                decision_ids.add(row["decision_id"])

    seen_ids: set[str] = set()
    for vector in data.get("vectors") or []:
        if not isinstance(vector, dict):
            continue
        vid = vector.get("id", "")
        if vid in seen_ids:
            errors.append(f"duplicate vector id: {vid}")
        seen_ids.add(vid)
        linked = vector.get("linked_decision")
        if linked and linked not in decision_ids:
            errors.append(f"{vid}: linked_decision '{linked}' not in DECISION_REGISTRY")

    if errors:
        print("[drift-vectors] FAIL:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"[drift-vectors] OK: {len(data.get('vectors') or [])} vector(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
