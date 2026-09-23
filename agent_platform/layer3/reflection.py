"""Layer 3F — reflection and gated improvement proposals."""

from __future__ import annotations

from typing import Any

from agent_platform.layer3.memory.store import MemoryStore
from agent_platform.models import RunRecord


def reflect_on_run(store: MemoryStore, run: RunRecord, evaluator_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    failed = [r for r in evaluator_results if not r.get("passed")]
    if failed:
        candidates.append(
            {
                "kind": "evaluator_failure",
                "status": "candidate",
                "detail": failed[0].get("evaluator_id"),
                "repository_id": run.repository_id,
            }
        )

    if run.errors:
        candidates.append(
            {
                "kind": "execution_error",
                "status": "candidate",
                "detail": run.errors[0],
                "repository_id": run.repository_id,
            }
        )

    for candidate in candidates:
        store.append("evaluation", candidate)
        store.append("episodic", {"run_id": run.run_id, "candidate": candidate})

    return candidates
