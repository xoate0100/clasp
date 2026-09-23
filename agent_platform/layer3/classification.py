"""Layer 3A — semantic classification."""

from __future__ import annotations

import pathlib
import uuid
from typing import Any

from agent_platform.models import EvidenceBundle, RepositoryProfile, SemanticClassification, SystemModel
from agent_platform.release import TAXONOMY_VERSION

try:
    import yaml
except ImportError:
    yaml = None


def load_taxonomy(root: pathlib.Path) -> dict[str, Any]:
    path = root / "5_reference_architectures" / "SEMANTIC_TAXONOMY.yaml"
    if not path.exists() or yaml is None:
        return {"version": TAXONOMY_VERSION, "categories": {}}
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def classify_repository(
    profile: RepositoryProfile,
    model: SystemModel,
    evidence: EvidenceBundle,
    root: pathlib.Path,
    goal: str = "",
) -> SemanticClassification:
    taxonomy = load_taxonomy(root)
    labels: list[str] = []
    confidence: dict[str, float] = {}

    if profile.initializer_version:
        labels.append("CAP.repo.initializer_managed")
        confidence["CAP.repo.initializer_managed"] = 0.95

    if "python" in profile.languages:
        labels.append("ARCH.pattern.backend_service")
        confidence["ARCH.pattern.backend_service"] = 0.8

    if profile.git_dirty:
        labels.append("REL.risk.dirty_worktree")
        confidence["REL.risk.dirty_worktree"] = 0.99

    if model.disconnects:
        labels.append("DEBT.type.disconnected_capability")
        confidence["DEBT.type.disconnected_capability"] = min(0.5 + len(model.disconnects) * 0.1, 0.99)

    if "upgrade" in goal.lower() or "migration" in goal.lower():
        labels.append("MIG.risk.schema_change")
        confidence["MIG.risk.schema_change"] = 0.85

    if not labels:
        return SemanticClassification(
            item_id=str(uuid.uuid4()),
            taxonomy_version=taxonomy.get("version", TAXONOMY_VERSION),
            abstained=True,
            unknown_concept="insufficient_evidence",
            rationale_summary="No deterministic labels matched; abstaining.",
        )

    return SemanticClassification(
        item_id=str(uuid.uuid4()),
        taxonomy_version=taxonomy.get("version", TAXONOMY_VERSION),
        labels=labels,
        confidence_by_label=confidence,
        evidence_refs=[item.evidence_id for item in evidence.items[:10]],
        rationale_summary=f"Classified {len(labels)} label(s) from profile, model, and goal.",
    )
