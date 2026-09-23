"""Release constants and manifest helpers."""

from __future__ import annotations

import pathlib
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

INITIALIZER_VERSION = "3.0.0"
CAPABILITY_SCHEMA_VERSION = "1.0.0"
TAXONOMY_VERSION = "1.0.0"
MEMORY_SCHEMA_VERSION = "1.0.0"
EVALUATOR_SCHEMA_VERSION = "1.0.0"
ORCHESTRATION_SCHEMA_VERSION = "1.0.0"


def read_template_version(root: pathlib.Path) -> str | None:
    manifest = root / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    if not manifest.exists() or yaml is None:
        return None
    with open(manifest, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("template_version")
