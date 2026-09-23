"""Layer 3C — capability compiler."""

from __future__ import annotations

import pathlib
import uuid
from typing import Any

from agent_platform.layer3.capability_registry import capability_by_id
from agent_platform.layer3.classification import classify_repository
from agent_platform.models import (
    CompiledCapabilityPlan,
    EvidenceBundle,
    RepositoryProfile,
    SemanticClassification,
    SystemModel,
)


GOAL_CAPABILITY_MAP = {
    "inspect": ["CAP.repo.scan", "CAP.evidence.collect", "CAP.model.build"],
    "init": ["CAP.repo.scan", "CAP.template.apply", "CAP.validate.full"],
    "plan": ["CAP.repo.scan", "CAP.plan.compile", "CAP.risk.assess"],
    "apply": ["CAP.plan.apply", "CAP.validate.full", "CAP.rollback.prepare"],
    "validate": ["CAP.validate.full", "CAP.evaluator.run"],
    "upgrade": ["CAP.migration.plan", "CAP.migration.apply", "CAP.validate.full"],
    "release": ["CAP.release.prepare", "CAP.validate.full"],
}


def compile_plan(
    goal: str,
    profile: RepositoryProfile,
    model: SystemModel,
    evidence: EvidenceBundle,
    root: pathlib.Path,
    classification: SemanticClassification | None = None,
) -> CompiledCapabilityPlan:
    classification = classification or classify_repository(profile, model, evidence, root, goal=goal)
    caps = capability_by_id(root)
    goal_key = goal.split()[0].lower() if goal else "inspect"
    requested = GOAL_CAPABILITY_MAP.get(goal_key, ["CAP.repo.scan", "CAP.validate.full"])

    selected: list[str] = []
    graph: list[dict[str, Any]] = []
    unresolved: list[str] = []
    evaluators: list[str] = []
    approval_gates: list[str] = []

    for cap_id in requested:
        cap = caps.get(cap_id)
        if not cap:
            unresolved.append(cap_id)
            continue
        maturity = cap.get("maturity", "experimental")
        if maturity in ("disabled", "deprecated"):
            unresolved.append(f"{cap_id}:disabled")
            continue
        version = f"{cap_id}@{cap.get('version', '1.0.0')}"
        selected.append(version)
        graph.append({"capability": cap_id, "implementation_ref": cap.get("implementation_ref")})
        evaluators.extend(cap.get("evaluators") or [])
        if cap.get("risk_level") in ("high", "critical"):
            approval_gates.append(cap_id)

    risk_score = min(0.2 * len(approval_gates) + 0.1 * len(model.disconnects), 1.0)
    status = "compiled" if not unresolved else "blocked"

    return CompiledCapabilityPlan(
        plan_id=str(uuid.uuid4()),
        goal=goal,
        repository_profile_ref=profile.repository_id,
        system_model_ref=model.model_id,
        capability_versions=selected,
        execution_graph=graph,
        preconditions=["repository_profile_valid", "no_path_traversal"],
        approval_gates=approval_gates,
        validators=["schema_validation", "reference_validation"],
        evaluators=sorted(set(evaluators)),
        rollback_steps=["restore_backup_manifest"] if goal_key in ("apply", "upgrade") else [],
        risk_score=risk_score,
        blast_radius=profile.initializer_owned_paths[:5],
        unresolved_requirements=unresolved,
        compilation_status=status,
    )
