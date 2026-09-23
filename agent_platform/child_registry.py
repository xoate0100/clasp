"""Child repository registry."""

from __future__ import annotations

import json
import pathlib
import uuid
from typing import Any

from agent_platform.models import ChildRepositoryRecord, utc_now
from agent_platform.release import read_template_version

REGISTRY_PATH = "5_reference_architectures/CHILD_REPOSITORY_REGISTRY.yaml"


def registry_file(root: pathlib.Path) -> pathlib.Path:
    return root / REGISTRY_PATH


def load_registry(root: pathlib.Path) -> dict[str, Any]:
    path = registry_file(root)
    if not path.exists():
        return {"version": "1.0.0", "children": []}
    try:
        import yaml

        with open(path, encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {"version": "1.0.0", "children": []}
    except Exception:
        return {"version": "1.0.0", "children": []}


def save_registry(root: pathlib.Path, data: dict[str, Any]) -> None:
    import yaml

    path = registry_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def register_child(root: pathlib.Path, record: ChildRepositoryRecord) -> ChildRepositoryRecord:
    data = load_registry(root)
    children = [c for c in (data.get("children") or []) if c.get("repository_id") != record.repository_id]
    children.append(record.to_dict())
    data["children"] = children
    data["updated_at"] = utc_now()
    save_registry(root, data)
    return record


def list_children(root: pathlib.Path) -> list[dict[str, Any]]:
    return list(load_registry(root).get("children") or [])


def child_status(root: pathlib.Path, repository_id: str) -> dict[str, Any]:
    for child in list_children(root):
        if child.get("repository_id") == repository_id:
            target = pathlib.Path(child.get("repository_location", ""))
            status = dict(child)
            status["exists"] = target.exists()
            status["declared_initializer_version"] = child.get("initializer_version", "")
            status["hub_initializer_version"] = read_template_version(root)
            status["compatible"] = (
                status["declared_initializer_version"] == status["hub_initializer_version"]
                if status["declared_initializer_version"] and status["hub_initializer_version"]
                else None
            )
            return status
    return {"error": "not_found", "repository_id": repository_id}
