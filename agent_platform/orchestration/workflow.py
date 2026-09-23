"""Explicit orchestration workflow with typed transitions."""

from __future__ import annotations

import pathlib
import uuid
from typing import Any, Callable

from agent_platform.layer0.repository_scanner import scan_repository, write_profile
from agent_platform.layer1.evidence_collector import collect_evidence
from agent_platform.layer2.system_model_builder import build_system_model
from agent_platform.layer3.active_learning import enqueue_feedback
from agent_platform.layer3.capability_compiler import compile_plan
from agent_platform.layer3.classification import classify_repository
from agent_platform.layer3.evaluators.registry import evaluators_passed, run_evaluators
from agent_platform.layer3.memory.store import MemoryStore
from agent_platform.layer3.reflection import reflect_on_run
from agent_platform.models import RunRecord, utc_now
from agent_platform.release import INITIALIZER_VERSION

WORKFLOW_NODES = [
    "intake",
    "inspect_repository",
    "collect_evidence",
    "build_model",
    "classify",
    "compile_plan",
    "evaluate",
    "complete",
]


def run_inspect_pipeline(root: pathlib.Path, goal: str = "inspect") -> dict[str, Any]:
    store = MemoryStore(root)
    run = RunRecord(
        run_id=str(uuid.uuid4()),
        run_type="inspect",
        repository_id="",
        initializer_version=INITIALIZER_VERSION,
        goal=goal,
    )

    profile = scan_repository(root)
    run.repository_id = profile.repository_id
    write_profile(profile, root)

    evidence = collect_evidence(profile, root)
    model = build_system_model(profile, evidence, root)
    classification = classify_repository(profile, model, evidence, root, goal=goal)
    plan = compile_plan(goal, profile, model, evidence, root, classification)

    evaluator_results = run_evaluators(root, plan.evaluators)
    passed = evaluators_passed(evaluator_results)

    enqueue_feedback(store, classification, reason="inspect_run", repository_id=profile.repository_id)
    run.evaluator_results = evaluator_results
    run.outcome = "success" if passed and plan.compilation_status == "compiled" else "failed"
    run.completed_at = utc_now()
    reflect_on_run(store, run, evaluator_results)

    store.append("episodic", {"run_id": run.run_id, "outcome": run.outcome, "goal": goal})

    return {
        "run": run.to_dict(),
        "profile": profile.to_dict(),
        "evidence_count": len(evidence.items),
        "model": model.to_dict(),
        "classification": classification.to_dict(),
        "plan": plan.to_dict(),
        "evaluator_results": evaluator_results,
    }
