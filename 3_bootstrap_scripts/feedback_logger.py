#!/usr/bin/env python3
"""
Feedback Logger Helper
Utility functions for logging feedback throughout the meta-framework.
"""

import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

FEEDBACK_LOG = pathlib.Path("6_ai_runtime_context/ai_feedback_log.json")


def log_feedback(
    issue: str,
    category: str = "PATTERN_DETECTED",
    context: str = "",
    files: Optional[List[str]] = None,
    requires_human_intervention: bool = False,
    traceability: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log feedback entry to ai_feedback_log.json.

    Args:
        issue: Description of the issue/pattern
        category: Feedback category (ANOMALY, GUARDRAIL_VIOLATION, etc.)
        context: Additional context
        files: List of files affected
        requires_human_intervention: Whether human intervention is needed
        traceability: Traceability information (plan_id, task_id, etc.)
    """
    if not FEEDBACK_LOG.exists():
        FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
        data = {"entries": []}
    else:
        try:
            with open(FEEDBACK_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"entries": []}

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "category": category,
        "issue": issue,
        "context": context,
        "requires_human_intervention": requires_human_intervention,
        "attempt_count": 1,
    }

    if files:
        entry["files"] = files

    if traceability:
        entry["traceability"] = traceability

    data.setdefault("entries", []).append(entry)

    # Keep only last 1000 entries to prevent log bloat
    if len(data["entries"]) > 1000:
        data["entries"] = data["entries"][-1000:]

    try:
        with open(FEEDBACK_LOG, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # Fail silently to not break workflows


def log_guardrail_violation(
    guardrail_name: str,
    violation_details: str,
    files: Optional[List[str]] = None,
) -> None:
    """Log guardrail violation feedback."""
    log_feedback(
        issue=f"Guardrail violation: {guardrail_name} - {violation_details}",
        category="GUARDRAIL_VIOLATION",
        context=f"Guardrail '{guardrail_name}' failed during pre-commit check",
        files=files,
        requires_human_intervention=True,
    )


def log_architecture_violation(
    violation_type: str,
    details: str,
    files: Optional[List[str]] = None,
) -> None:
    """Log architecture violation feedback."""
    log_feedback(
        issue=f"Architecture violation: {violation_type} - {details}",
        category="ARCHITECTURE_VIOLATION",
        context="SOLID principles or layer boundary violation detected",
        files=files,
        requires_human_intervention=True,
    )


def log_template_drift(
    drift_type: str,
    details: str,
    expected: str = "",
    actual: str = "",
) -> None:
    """Log template drift feedback."""
    log_feedback(
        issue=f"Template drift detected: {drift_type} - {details}",
        category="TEMPLATE_DRIFT",
        context=f"Expected: {expected}, Actual: {actual}",
        requires_human_intervention=False,
    )


def log_update_issue(
    issue_type: str,
    details: str,
    migration_applied: bool = False,
) -> None:
    """Log template update issue."""
    log_feedback(
        issue=f"Template update issue: {issue_type} - {details}",
        category="UPDATE_ISSUE",
        context=f"Migration applied: {migration_applied}",
        requires_human_intervention=False,
    )


def log_ai_anomaly(
    anomaly: str,
    context: str = "",
    files: Optional[List[str]] = None,
) -> None:
    """Log AI agent anomaly."""
    log_feedback(
        issue=f"AI anomaly: {anomaly}",
        category="AI_ANOMALY",
        context=context,
        files=files,
        requires_human_intervention=False,
    )


def log_schema_mismatch(
    schema_file: str,
    details: str,
    validation_errors: Optional[List[str]] = None,
) -> None:
    """Log schema validation mismatch."""
    error_summary = "; ".join(validation_errors) if validation_errors else details
    log_feedback(
        issue=f"Schema mismatch in {schema_file}: {error_summary}",
        category="SCHEMA_MISMATCH",
        context=f"Schema validation failed for {schema_file}",
        requires_human_intervention=True,
    )


def log_documentation_gap(
    gap: str,
    context: str = "",
    files: Optional[List[str]] = None,
) -> None:
    """Log documentation gap."""
    log_feedback(
        issue=f"Documentation gap: {gap}",
        category="DOCUMENTATION_GAP",
        context=context,
        files=files,
        requires_human_intervention=False,
    )

