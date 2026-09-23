"""Optional in-project agentic tools — enable/disable via feature_flags.yml."""

from __future__ import annotations

import pathlib
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise ImportError("PyYAML required. Install with: pip install PyYAML") from exc

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FLAGS_PATH = REPO_ROOT / "0_phase0_bootstrap" / "feature_flags.yml"
CATALOG_PATH = REPO_ROOT / "5_reference_architectures" / "OPTIONAL_AGENTIC_TOOLS.yaml"

TOOL_IDS = (
    "knowledge_index",
    "doc_lifecycle",
    "janitor",
    "governance_drift_validator",
    "reference_validator",
)


def load_feature_flags(root: pathlib.Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    path = root / "0_phase0_bootstrap" / "feature_flags.yml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_tool_catalog(root: pathlib.Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    path = root / "5_reference_architectures" / "OPTIONAL_AGENTIC_TOOLS.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def optional_tools_config(root: pathlib.Path | None = None) -> dict[str, Any]:
    flags = load_feature_flags(root)
    agentic = flags.get("agentic") or {}
    return agentic.get("optional_tools") or {}


def is_tool_enabled(tool_id: str, root: pathlib.Path | None = None) -> bool:
    """Return True when tool is enabled (default True if section missing)."""
    if tool_id not in TOOL_IDS:
        return False
    cfg = optional_tools_config(root)
    if not cfg:
        return True
    tool_cfg = cfg.get(tool_id)
    if tool_cfg is None:
        return True
    if isinstance(tool_cfg, bool):
        return tool_cfg
    if isinstance(tool_cfg, dict):
        return bool(tool_cfg.get("enabled", True))
    return True


def list_tools(root: pathlib.Path | None = None) -> list[dict[str, Any]]:
    catalog = load_tool_catalog(root)
    catalog_tools = {
        item.get("id"): item
        for item in (catalog.get("tools") or [])
        if isinstance(item, dict) and item.get("id")
    }
    out: list[dict[str, Any]] = []
    for tool_id in TOOL_IDS:
        meta = catalog_tools.get(tool_id, {})
        out.append(
            {
                "id": tool_id,
                "enabled": is_tool_enabled(tool_id, root),
                "description": meta.get("description", ""),
                "scripts": meta.get("scripts") or [],
            }
        )
    return out


def save_optional_tools(tools: dict[str, bool], root: pathlib.Path | None = None) -> None:
    root = root or REPO_ROOT
    path = root / "0_phase0_bootstrap" / "feature_flags.yml"
    flags = load_feature_flags(root)
    agentic = flags.setdefault("agentic", {})
    optional = agentic.setdefault("optional_tools", {})
    for tool_id, enabled in tools.items():
        if tool_id not in TOOL_IDS:
            continue
        entry = optional.get(tool_id)
        if isinstance(entry, dict):
            entry["enabled"] = enabled
        else:
            optional[tool_id] = {"enabled": enabled}
    with open(path, "w", encoding="utf-8") as handle:
        yaml.dump(flags, handle, default_flow_style=False, sort_keys=False, allow_unicode=True)
