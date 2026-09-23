"""Typed contracts for the self-improving agent platform."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class Provenance:
    source: str
    path: str = ""
    collector_version: str = "1.0.0"
    collected_at: str = field(default_factory=utc_now)
    confidence: float = 1.0
    content_hash: str = ""


@dataclass
class RepositoryProfile:
    repository_id: str
    root_path: str
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    build_commands: list[str] = field(default_factory=list)
    ci_workflows: list[str] = field(default_factory=list)
    initializer_version: str | None = None
    capability_schema_version: str = "1.0.0"
    git_branch: str = ""
    git_dirty: bool = False
    protected_paths: list[str] = field(default_factory=list)
    initializer_owned_paths: list[str] = field(default_factory=list)
    child_owned_paths: list[str] = field(default_factory=list)
    profile_version: str = "1.0.0"
    scanned_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceItem:
    evidence_id: str
    kind: str
    path: str
    summary: str
    provenance: Provenance
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    bundle_id: str
    repository_id: str
    items: list[EvidenceItem] = field(default_factory=list)
    bundle_version: str = "1.0.0"
    collected_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SystemModel:
    model_id: str
    repository_id: str
    architecture_nodes: list[dict[str, Any]] = field(default_factory=list)
    feature_nodes: list[dict[str, Any]] = field(default_factory=list)
    disconnects: list[dict[str, Any]] = field(default_factory=list)
    model_version: str = "1.0.0"
    built_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticClassification:
    item_id: str
    taxonomy_version: str
    labels: list[str] = field(default_factory=list)
    confidence_by_label: dict[str, float] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    rationale_summary: str = ""
    abstained: bool = False
    unknown_concept: str = ""
    classifier_version: str = "1.0.0"
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompiledCapabilityPlan:
    plan_id: str
    goal: str
    repository_profile_ref: str
    system_model_ref: str
    capability_versions: list[str] = field(default_factory=list)
    execution_graph: list[dict[str, Any]] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    approval_gates: list[str] = field(default_factory=list)
    validators: list[str] = field(default_factory=list)
    evaluators: list[str] = field(default_factory=list)
    rollback_steps: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    blast_radius: list[str] = field(default_factory=list)
    unresolved_requirements: list[str] = field(default_factory=list)
    compilation_status: str = "pending"
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunRecord:
    run_id: str
    run_type: str
    repository_id: str
    initializer_version: str
    goal: str = ""
    compiled_plan_ref: str = ""
    capabilities_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    evaluator_results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rollback_status: str = "none"
    memory_records_created: list[str] = field(default_factory=list)
    improvement_candidates: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = "pending"
    started_at: str = field(default_factory=utc_now)
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChildRepositoryRecord:
    repository_id: str
    repository_name: str
    repository_location: str
    remote_url: str = ""
    default_branch: str = "main"
    initializer_version: str = ""
    capability_schema_version: str = "1.0.0"
    release_channel: str = "stable"
    update_policy: str = "manual_only"
    status: str = "registered"
    last_successful_sync: str = ""
    last_validation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
