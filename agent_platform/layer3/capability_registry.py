"""Layer 3B — capability registry loader."""

from __future__ import annotations

import pathlib
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


def load_capability_registry(root: pathlib.Path) -> dict[str, Any]:
    path = root / "5_reference_architectures" / "CAPABILITY_REGISTRY.yaml"
    if not path.exists() or yaml is None:
        return {"version": "1.0.0", "capabilities": []}
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def capability_by_id(root: pathlib.Path) -> dict[str, dict[str, Any]]:
    registry = load_capability_registry(root)
    return {
        cap["id"]: cap
        for cap in (registry.get("capabilities") or [])
        if isinstance(cap, dict) and cap.get("id")
    }


def validate_registry(root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    registry = load_capability_registry(root)
    seen: set[str] = set()
    for cap in registry.get("capabilities") or []:
        if not isinstance(cap, dict):
            errors.append("capability entry is not a mapping")
            continue
        cap_id = cap.get("id")
        if not cap_id:
            errors.append("capability missing id")
            continue
        if cap_id in seen:
            errors.append(f"duplicate capability id: {cap_id}")
        seen.add(cap_id)
        if not cap.get("implementation_ref"):
            errors.append(f"{cap_id}: missing implementation_ref")
        if not cap.get("maturity"):
            errors.append(f"{cap_id}: missing maturity")
    return errors
