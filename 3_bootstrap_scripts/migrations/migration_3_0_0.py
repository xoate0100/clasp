#!/usr/bin/env python3
"""Migration script for v3.0.0 — self-improving agent platform."""

import pathlib
from typing import Tuple


def migrate_to_3_0_0(project_root: pathlib.Path) -> Tuple[bool, str]:
    required = [
        "agent_platform/__init__.py",
        "agent_platform/models.py",
        "agent_platform/orchestration/workflow.py",
        "5_reference_architectures/CAPABILITY_REGISTRY.yaml",
        "5_reference_architectures/EVALUATOR_REGISTRY.yaml",
        "5_reference_architectures/SEMANTIC_TAXONOMY.yaml",
        "5_reference_architectures/CHILD_REPOSITORY_REGISTRY.yaml",
        "3_bootstrap_scripts/platform_cli.py",
        "3_bootstrap_scripts/platform_validate.py",
        "templates/catalog/TEMPLATE_CATALOG.yaml",
    ]
    missing = [rel for rel in required if not (project_root / rel).exists()]
    if missing:
        return False, f"Missing platform files: {', '.join(missing)}"

    memory_dir = project_root / "6_ai_runtime_context" / "platform_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return True, "Platform Layer 0-3 package and registries installed"


MIGRATIONS = {"3.0.0": migrate_to_3_0_0}
