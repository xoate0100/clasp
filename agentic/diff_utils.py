"""Utilities for scanning only newly added diff lines."""

from __future__ import annotations

GUARDRAIL_CATALOG_PREFIXES = (
    "5_reference_architectures/",
    "7_schemas/",
    "docs/",
    "proposals/",
    "4_docs_index/",
    "3_bootstrap_scripts/phase_gate.py",
    "3_bootstrap_scripts/resurrection_scan.py",
    "3_bootstrap_scripts/drift_vector_check.py",
    "3_bootstrap_scripts/anti_bypass_scan.py",
    "3_bootstrap_scripts/plumbing_fleet_scan.py",
    "3_bootstrap_scripts/decision_registry_validate.py",
    "3_bootstrap_scripts/generate_ai_context.py",
    "3_bootstrap_scripts/agentic_coordinate_validate.py",
    "6_ai_runtime_context/AI_CONTEXT.md",
    "6_ai_runtime_context/AGENTIC_RUN_LOG.yaml",
    "6_ai_runtime_context/ACTIVE_PLAN.yaml",
    "6_ai_runtime_context/INTENT_DECLARATION.json",
    "6_ai_runtime_context/TASK_COMPLETION_REPORTS/",
    "6_ai_runtime_context/ai_feedback_log.json",
    "agentic/",
    "tests/",
    ".cursor/",
)


def is_guardrail_catalog_path(rel_path: str) -> bool:
    norm = rel_path.replace("\\", "/")
    for prefix in GUARDRAIL_CATALOG_PREFIXES:
        base = prefix.rstrip("/")
        if norm == base or norm.startswith(base + "/"):
            return True
    return False


def extract_added_lines(diff_text: str, *, exclude_catalog_paths: bool = True) -> str:
    """Return added diff lines, optionally skipping guardrail catalog paths."""
    added: list[str] = []
    current_file: str | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current_file = line[4:].strip()
            if current_file.startswith("b/"):
                current_file = current_file[2:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if exclude_catalog_paths and current_file and is_guardrail_catalog_path(current_file):
            continue
        added.append(line[1:])

    return "\n".join(added)
