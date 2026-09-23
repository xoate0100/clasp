"""Layer 3G — active learning queue."""

from __future__ import annotations

import pathlib
from typing import Any

from agent_platform.layer3.memory.store import MemoryStore
from agent_platform.models import SemanticClassification


def enqueue_feedback(
    store: MemoryStore,
    classification: SemanticClassification,
    *,
    reason: str,
    repository_id: str,
) -> str:
    low_conf = [label for label, score in classification.confidence_by_label.items() if score < 0.7]
    if not classification.abstained and not low_conf:
        return ""
    record: dict[str, Any] = {
        "repository_id": repository_id,
        "reason": reason,
        "labels": classification.labels,
        "low_confidence": low_conf,
        "abstained": classification.abstained,
        "status": "queued",
    }
    return store.append("active_learning", record)
