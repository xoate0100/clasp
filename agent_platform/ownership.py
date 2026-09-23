"""File ownership classification."""

from __future__ import annotations

import pathlib
from typing import Any

from agent_platform.security import norm_path

OWNERSHIP_MODES = {
    "initializer_owned",
    "child_owned",
    "generated_extensible",
    "semantic_merge",
    "append_only",
    "manual_only",
}


def classify_path(path: str, manifest: dict[str, Any]) -> str:
    fwd = norm_path(path)
    for protected in manifest.get("protected_files") or []:
        if fwd == norm_path(protected):
            return "child_owned"
    for child_dir in manifest.get("project_directories") or []:
        if fwd.startswith(norm_path(child_dir)):
            return "child_owned"
    for init_dir in manifest.get("template_directories") or []:
        if fwd.startswith(norm_path(init_dir)):
            return "initializer_owned"
    if fwd.startswith("6_ai_runtime_context/"):
        return "generated_extensible"
    return "manual_only"


def load_manifest(root: pathlib.Path) -> dict[str, Any]:
    path = root / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    if not path.exists():
        return {}
    try:
        import yaml

        with open(path, encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception:
        return {}
