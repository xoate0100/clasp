#!/usr/bin/env python3
"""
Validate MODULE_REGISTRY.yaml + MODULES.lock.

- Each registry module validates against module_manifest.schema.json
- MODULES.lock validates against modules_lock.schema.json
- Lock and registry must agree on module_id, version, and governance_runtime

Usage:
    python 3_bootstrap_scripts/module_registry_validate.py
"""

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
    print("[module-registry] ERROR: PyYAML and jsonschema required")
    sys.exit(1)

REGISTRY_PATH = REPO_ROOT / "5_reference_architectures" / "MODULE_REGISTRY.yaml"
LOCK_PATH = REPO_ROOT / "MODULES.lock"
MANIFEST_SCHEMA = REPO_ROOT / "7_schemas" / "module_manifest.schema.json"
LOCK_SCHEMA = REPO_ROOT / "7_schemas" / "modules_lock.schema.json"


def _load_yaml(path: pathlib.Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _load_schema(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_errors(schema: dict, instance: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))]


def compare_registry_lock(registry_modules: list, lock_modules: list) -> list[str]:
    errors: list[str] = []
    reg_by_id = {m.get("module_id"): m for m in registry_modules if isinstance(m, dict)}
    lock_by_id = {m.get("module_id"): m for m in lock_modules if isinstance(m, dict)}

    for mid in sorted(set(reg_by_id) | set(lock_by_id)):
        if mid not in reg_by_id:
            errors.append(f"lock has module '{mid}' not present in MODULE_REGISTRY.yaml")
            continue
        if mid not in lock_by_id:
            errors.append(f"registry has module '{mid}' not present in MODULES.lock")
            continue
        reg = reg_by_id[mid]
        lock = lock_by_id[mid]
        for field in ("version", "governance_runtime"):
            if reg.get(field) != lock.get(field):
                errors.append(
                    f"{mid}: {field} mismatch registry={reg.get(field)!r} lock={lock.get(field)!r}"
                )
    return errors


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"[module-registry] FAIL: missing {REGISTRY_PATH}")
        return 1
    if not LOCK_PATH.exists():
        print(f"[module-registry] FAIL: missing {LOCK_PATH}")
        return 1

    registry = _load_yaml(REGISTRY_PATH)
    lock = _load_yaml(LOCK_PATH)
    manifest_schema = _load_schema(MANIFEST_SCHEMA)
    lock_schema = _load_schema(LOCK_SCHEMA)

    errors: list[str] = []

    modules = registry.get("modules")
    if not isinstance(modules, list):
        errors.append("MODULE_REGISTRY.yaml must contain a 'modules' array")
        modules = []

    for idx, mod in enumerate(modules):
        if not isinstance(mod, dict):
            errors.append(f"registry modules[{idx}]: not an object")
            continue
        for msg in _schema_errors(manifest_schema, mod):
            mid = mod.get("module_id", f"index-{idx}")
            errors.append(f"registry {mid}: {msg}")

    for msg in _schema_errors(lock_schema, lock):
        errors.append(f"MODULES.lock: {msg}")

    lock_modules = lock.get("modules") if isinstance(lock.get("modules"), list) else []
    errors.extend(compare_registry_lock(modules, lock_modules))

    if errors:
        print("[module-registry] FAIL:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(
        f"[module-registry] OK: {len(modules)} module(s) "
        f"registry↔lock agree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
