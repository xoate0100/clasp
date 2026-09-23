"""Layer 2 — structural interpretation and disconnect detection."""

from __future__ import annotations

import pathlib
import uuid
from typing import Any

from agent_platform.models import EvidenceBundle, RepositoryProfile, SystemModel
from agent_platform.security import norm_path


def build_system_model(
    profile: RepositoryProfile,
    evidence: EvidenceBundle,
    root: pathlib.Path,
) -> SystemModel:
    root = root.resolve()
    architecture_nodes: list[dict[str, Any]] = []
    feature_nodes: list[dict[str, Any]] = []
    disconnects: list[dict[str, Any]] = []

    for rel in profile.initializer_owned_paths:
        architecture_nodes.append({"type": "initializer_owned", "path": rel})

    for rel in profile.child_owned_paths:
        architecture_nodes.append({"type": "child_owned", "path": rel})

    capability_registry = root / "5_reference_architectures" / "CAPABILITY_REGISTRY.yaml"
    evaluator_registry = root / "5_reference_architectures" / "EVALUATOR_REGISTRY.yaml"
    platform_pkg = root / "agent_platform"

    if capability_registry.exists():
        feature_nodes.append({"id": "capability_registry", "path": norm_path(str(capability_registry.relative_to(root)))})
    else:
        disconnects.append({"kind": "missing_registry", "path": "5_reference_architectures/CAPABILITY_REGISTRY.yaml"})

    if evaluator_registry.exists():
        feature_nodes.append({"id": "evaluator_registry", "path": norm_path(str(evaluator_registry.relative_to(root)))})
    else:
        disconnects.append({"kind": "missing_registry", "path": "5_reference_architectures/EVALUATOR_REGISTRY.yaml"})

    if not platform_pkg.is_dir():
        disconnects.append({"kind": "missing_implementation", "path": "agent_platform/"})

    cli_path = root / "3_bootstrap_scripts" / "cli.py"
    if cli_path.exists():
        cli_text = cli_path.read_text(encoding="utf-8", errors="ignore")
        for cmd in ("inspect", "plan", "doctor", "child"):
            if cmd not in cli_text:
                disconnects.append({"kind": "cli_not_wired", "command": cmd})

    script_names = {norm_path(item.path) for item in evidence.items if item.kind == "script"}
    declared_in_registry = {n["path"] for n in feature_nodes if "path" in n}
    for item in evidence.items:
        if item.path.endswith("_validate.py") and item.path not in script_names:
            disconnects.append({"kind": "orphan_reference", "path": item.path})

    # Check agentic coordination wiring
    agentic_validate = root / "3_bootstrap_scripts" / "agentic_coordinate_validate.py"
    if agentic_validate.exists():
        feature_nodes.append({"id": "agentic_coordination", "path": "3_bootstrap_scripts/agentic_coordinate_validate.py"})
    else:
        disconnects.append({"kind": "missing_validator", "path": "3_bootstrap_scripts/agentic_coordinate_validate.py"})

    return SystemModel(
        model_id=str(uuid.uuid4()),
        repository_id=profile.repository_id,
        architecture_nodes=architecture_nodes,
        feature_nodes=feature_nodes,
        disconnects=disconnects,
    )
