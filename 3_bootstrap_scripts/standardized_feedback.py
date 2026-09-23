#!/usr/bin/env python3
"""
Standardized Feedback Reporting Module
Pre-configured, templated issue reporting for child projects.
This module is inherited from project_initializer template and provides
standardized feedback submission to the hub (template repository).
"""

import json
import pathlib
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from feedback_logger import log_feedback
except ImportError:
    # Fallback if imported directly
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from feedback_logger import log_feedback

# Import real-time learning components (Tasks 6-8)
try:
    from match_issue import IssueMatcher
    from apply_proposed_fix import FixApplicator
    REAL_TIME_LEARNING_AVAILABLE = True
except ImportError:
    # Real-time learning not available (graceful degradation)
    IssueMatcher = None
    FixApplicator = None
    REAL_TIME_LEARNING_AVAILABLE = False

# Feedback templates for common error types
FEEDBACK_TEMPLATES = {
    "GUARDRAIL_VIOLATION": {
        "category": "GUARDRAIL_VIOLATION",
        "title_template": "[Guardrail] {guardrail_name} violation in {component}",
        "body_template": """## Guardrail Violation

**Guardrail**: {guardrail_name}
**Component**: {component}
**Files Affected**: {files}
**Context**: {context}

**Details**:
{details}

**Requires Human Intervention**: {requires_intervention}
""",
    },
    "ARCHITECTURE_VIOLATION": {
        "category": "ARCHITECTURE_VIOLATION",
        "title_template": "[Architecture] {violation_type} violation in {component}",
        "body_template": """## Architecture Violation

**Type**: {violation_type}
**Component**: {component}
**Principle**: {principle}
**Files Affected**: {files}

**Details**:
{details}

**Expected Behavior**: {expected}
**Actual Behavior**: {actual}
""",
    },
    "TEMPLATE_DRIFT": {
        "category": "TEMPLATE_DRIFT",
        "title_template": "[Drift] {drift_type} mismatch detected",
        "body_template": """## Template Drift Detected

**Type**: {drift_type}
**Location**: {location}
**Expected**: {expected}
**Actual**: {actual}

**Impact**: {impact}

**Recommendation**: {recommendation}
""",
    },
    "UPDATE_ISSUE": {
        "category": "UPDATE_ISSUE",
        "title_template": "[Update] {issue_type} during template update",
        "body_template": """## Template Update Issue

**Type**: {issue_type}
**From Version**: {from_version}
**To Version**: {to_version}
**Migration Applied**: {migration_applied}

**Details**:
{details}

**Error**: {error}

**Resolution**: {resolution}
""",
    },
    "PERFORMANCE_ISSUE": {
        "category": "PERFORMANCE_ISSUE",
        "title_template": "[Performance] {metric} exceeds threshold in {component}",
        "body_template": """## Performance Issue

**Metric**: {metric}
**Component**: {component}
**Threshold**: {threshold}
**Actual**: {actual}
**Files**: {files}

**Impact**: {impact}

**Recommendation**: {recommendation}
""",
    },
    "SCHEMA_MISMATCH": {
        "category": "SCHEMA_MISMATCH",
        "title_template": "[Schema] Validation failed for {schema_file}",
        "body_template": """## Schema Validation Failure

**Schema File**: {schema_file}
**Validated File**: {validated_file}
**Errors**: {errors}

**Details**:
{details}

**Fix Required**: {fix_required}
""",
    },
    "DOCUMENTATION_GAP": {
        "category": "DOCUMENTATION_GAP",
        "title_template": "[Docs] Missing documentation for {component}",
        "body_template": """## Documentation Gap

**Component**: {component}
**Missing**: {missing}
**Files**: {files}

**Impact**: {impact}

**Recommendation**: {recommendation}
""",
    },
    "OPERATIONAL_ERROR": {
        "category": "OPERATIONAL_ERROR",
        "title_template": "[Operational] {error_type} in {component}",
        "body_template": """## Operational Error

**Type**: {error_type}
**Component**: {component}
**Timestamp**: {timestamp}
**Error**: {error}

**Context**: {context}
**Files**: {files}

**Resolution**: {resolution}
""",
    },
    "STACK_COUPLING": {
        "category": "STACK_COUPLING",
        "title_template": "[Stack Coupling] {assumed_runtime} required for {lifecycle_verb}",
        "body_template": """## Stack Coupling / Portability Issue

**Assumed runtime**: {assumed_runtime}
**Lifecycle verb**: {lifecycle_verb}
**Affected OS**: {affected_os}
**Component**: {component}
**Files**: {files}

**Details**:
{details}

**Workaround**: {workaround}
""",
    },
    "PORTABILITY": {
        "category": "PORTABILITY",
        "title_template": "[Portability] {assumed_runtime} / OS issue in {lifecycle_verb}",
        "body_template": """## Portability Issue

**Assumed runtime**: {assumed_runtime}
**Lifecycle verb**: {lifecycle_verb}
**Affected OS**: {affected_os}
**Component**: {component}
**Files**: {files}

**Details**:
{details}

**Workaround**: {workaround}
""",
    },
}


# Real-time learning integration functions
def _check_for_similar_issues(issue_description: str, category: str) -> Optional[Dict]:
    """
    Check knowledge base for similar issues with proposed fixes.
    
    Args:
        issue_description: Description of the issue
        category: Issue category
    
    Returns:
        Matched issue dict if found, None otherwise
    """
    if not REAL_TIME_LEARNING_AVAILABLE:
        return None
    
    try:
        matcher = IssueMatcher()
        match = matcher.find_similar_issue(issue_description, category, threshold=0.7)
        return match
    except Exception:
        # Fail silently to not break feedback reporting
        return None


def _suggest_fix_if_available(match: Dict, category: str) -> None:
    """
    Log fix suggestion if available from matched issue.
    
    Args:
        match: Matched issue dictionary
        category: Issue category
    """
    if not match or not match.get("proposed_fixes"):
        return
    
    proposed_fixes = match.get("proposed_fixes", [])
    if not proposed_fixes:
        return
    
    # Use first proposed fix
    fix = proposed_fixes[0]
    issue_number = match.get("number", "unknown")
    issue_url = match.get("html_url", "")
    
    suggestion = f"""Similar issue found (#{issue_number}) with proposed fix:
    
Issue: {match.get('title', 'Unknown')}
URL: {issue_url if issue_url else 'N/A'}

Proposed Fix:
{fix.get('body', '')[:500]}{'...' if len(fix.get('body', '')) > 500 else ''}

To apply this fix automatically, use:
  python 3_bootstrap_scripts/apply_proposed_fix.py "{match.get('title', '')}" --category {category}
"""
    
    log_feedback(
        issue=suggestion,
        category=f"{category}_FIX_SUGGESTION",
        context=f"Auto-detected from knowledge base (issue #{issue_number})",
        requires_human_intervention=False,
    )


def report_guardrail_violation(
    guardrail_name: str,
    component: str = "shared",
    files: Optional[List[str]] = None,
    context: str = "",
    details: str = "",
    requires_intervention: bool = True,
) -> None:
    """Report a guardrail violation using standardized template with real-time learning."""
    # Check for similar issues before reporting
    issue_description = f"Guardrail violation: {guardrail_name} in {component}"
    if details:
        issue_description += f" - {details}"
    
    match = _check_for_similar_issues(issue_description, "GUARDRAIL_VIOLATION")
    if match:
        _suggest_fix_if_available(match, "GUARDRAIL_VIOLATION")
    
    template = FEEDBACK_TEMPLATES["GUARDRAIL_VIOLATION"]
    
    issue = template["body_template"].format(
        guardrail_name=guardrail_name,
        component=component,
        files=", ".join(files) if files else "N/A",
        context=context or "Guardrail check failed during pre-commit validation",
        details=details or "No additional details provided",
        requires_intervention="Yes" if requires_intervention else "No",
    )
    
    log_feedback(
        issue=issue,
        category=template["category"],
        context=context,
        files=files,
        requires_human_intervention=requires_intervention,
    )


def report_architecture_violation(
    violation_type: str,
    component: str = "shared",
    principle: str = "SOLID",
    files: Optional[List[str]] = None,
    details: str = "",
    expected: str = "",
    actual: str = "",
) -> None:
    """Report an architecture violation using standardized template with real-time learning."""
    # Check for similar issues before reporting
    issue_description = f"Architecture violation: {violation_type} in {component}"
    if details:
        issue_description += f" - {details}"
    
    match = _check_for_similar_issues(issue_description, "ARCHITECTURE_VIOLATION")
    if match:
        _suggest_fix_if_available(match, "ARCHITECTURE_VIOLATION")
    
    template = FEEDBACK_TEMPLATES["ARCHITECTURE_VIOLATION"]
    
    issue = template["body_template"].format(
        violation_type=violation_type,
        component=component,
        principle=principle,
        files=", ".join(files) if files else "N/A",
        details=details or "Architecture boundary or principle violation detected",
        expected=expected or "N/A",
        actual=actual or "N/A",
    )
    
    log_feedback(
        issue=issue,
        category=template["category"],
        context=f"{violation_type} violation in {component}",
        files=files,
        requires_human_intervention=True,
    )


def report_template_drift(
    drift_type: str,
    location: str = "",
    expected: str = "",
    actual: str = "",
    impact: str = "",
    recommendation: str = "",
) -> None:
    """Report template drift using standardized template."""
    template = FEEDBACK_TEMPLATES["TEMPLATE_DRIFT"]
    
    issue = template["body_template"].format(
        drift_type=drift_type,
        location=location or "Unknown",
        expected=expected or "N/A",
        actual=actual or "N/A",
        impact=impact or "Potential configuration mismatch",
        recommendation=recommendation or "Review and align with template",
    )
    
    log_feedback(
        issue=issue,
        category=template["category"],
        context=f"Drift detected: {drift_type}",
        requires_human_intervention=False,
    )


def report_update_issue(
    issue_type: str,
    from_version: str = "",
    to_version: str = "",
    migration_applied: bool = False,
    details: str = "",
    error: str = "",
    resolution: str = "",
) -> None:
    """Report a template update issue using standardized template."""
    template = FEEDBACK_TEMPLATES["UPDATE_ISSUE"]
    
    issue = template["body_template"].format(
        issue_type=issue_type,
        from_version=from_version or "Unknown",
        to_version=to_version or "Unknown",
        migration_applied="Yes" if migration_applied else "No",
        details=details or "Template update encountered an issue",
        error=error or "None",
        resolution=resolution or "Manual intervention may be required",
    )
    
    log_feedback(
        issue=issue,
        category=template["category"],
        context=f"Update issue: {issue_type}",
        requires_human_intervention=bool(error),
    )


def report_performance_issue(
    metric: str,
    component: str = "shared",
    threshold: str = "",
    actual: str = "",
    files: Optional[List[str]] = None,
    impact: str = "",
    recommendation: str = "",
) -> None:
    """Report a performance issue using standardized template."""
    template = FEEDBACK_TEMPLATES["PERFORMANCE_ISSUE"]
    
    issue = template["body_template"].format(
        metric=metric,
        component=component,
        threshold=threshold or "N/A",
        actual=actual or "N/A",
        files=", ".join(files) if files else "N/A",
        impact=impact or "Performance degradation detected",
        recommendation=recommendation or "Review and optimize",
    )
    
    log_feedback(
        issue=issue,
        category=template["category"],
        context=f"Performance: {metric} in {component}",
        files=files,
        requires_human_intervention=False,
    )


def report_schema_mismatch(
    schema_file: str,
    validated_file: str = "",
    errors: Optional[List[str]] = None,
    details: str = "",
    fix_required: str = "",
) -> None:
    """Report a schema validation mismatch using standardized template."""
    template = FEEDBACK_TEMPLATES["SCHEMA_MISMATCH"]
    
    error_list = "\n".join(f"- {e}" for e in errors) if errors else "N/A"
    
    issue = template["body_template"].format(
        schema_file=schema_file,
        validated_file=validated_file or "N/A",
        errors=error_list,
        details=details or "Schema validation failed",
        fix_required=fix_required or "Update file to match schema",
    )
    
    log_feedback(
        issue=issue,
        category=template["category"],
        context=f"Schema mismatch: {schema_file}",
        requires_human_intervention=True,
    )


def report_documentation_gap(
    component: str = "shared",
    missing: str = "",
    files: Optional[List[str]] = None,
    impact: str = "",
    recommendation: str = "",
) -> None:
    """Report a documentation gap using standardized template."""
    template = FEEDBACK_TEMPLATES["DOCUMENTATION_GAP"]
    
    issue = template["body_template"].format(
        component=component,
        missing=missing or "Documentation missing",
        files=", ".join(files) if files else "N/A",
        impact=impact or "Reduced maintainability",
        recommendation=recommendation or "Add missing documentation",
    )
    
    log_feedback(
        issue=issue,
        category=template["category"],
        context=f"Documentation gap: {component}",
        files=files,
        requires_human_intervention=False,
    )


def report_operational_error(
    error_type: str,
    component: str = "shared",
    error: str = "",
    context: str = "",
    files: Optional[List[str]] = None,
    resolution: str = "",
) -> None:
    """Report an operational error using standardized template."""
    template = FEEDBACK_TEMPLATES["OPERATIONAL_ERROR"]
    
    issue = template["body_template"].format(
        error_type=error_type,
        component=component,
        timestamp=datetime.utcnow().isoformat() + "Z",
        error=error or "Unknown error",
        context=context or "Runtime error occurred",
        files=", ".join(files) if files else "N/A",
        resolution=resolution or "Review logs and fix",
    )
    
    log_feedback(
        issue=issue,
        category="OPERATIONAL_ERROR",
        context=context,
        files=files,
        requires_human_intervention=True,
    )


def report_stack_coupling(
    assumed_runtime: str,
    lifecycle_verb: str = "",
    affected_os: Optional[List[str]] = None,
    component: str = "meta-framework",
    details: str = "",
    files: Optional[List[str]] = None,
    workaround: str = "",
    category: str = "STACK_COUPLING",
) -> None:
    """Report a stack-coupling / portability issue (language-neutral taxonomy)."""
    if category not in ("STACK_COUPLING", "PORTABILITY"):
        category = "STACK_COUPLING"
    template = FEEDBACK_TEMPLATES[category]
    issue = template["body_template"].format(
        assumed_runtime=assumed_runtime or "unknown",
        lifecycle_verb=lifecycle_verb or "n/a",
        affected_os=", ".join(affected_os) if affected_os else "any",
        component=component,
        files=", ".join(files) if files else "N/A",
        details=details or "Protocol step requires a foreign stack runtime",
        workaround=workaround or "Provide a native adapter command for this verb",
    )
    log_feedback(
        issue=issue,
        category=category,
        context=details,
        files=files,
        requires_human_intervention=True,
    )


def auto_report_from_exception(
    exception: Exception,
    component: str = "shared",
    context: str = "",
    files: Optional[List[str]] = None,
) -> None:
    """Automatically report an exception using standardized format."""
    error_type = type(exception).__name__
    error_msg = str(exception)
    
    report_operational_error(
        error_type=error_type,
        component=component,
        error=error_msg,
        context=context or f"Exception occurred: {error_type}",
        files=files,
        resolution="Review exception details and fix root cause",
    )


# Convenience function for AI agents
def report_feedback(
    feedback_type: str,
    **kwargs: Any,
) -> None:
    """
    Universal feedback reporting function with real-time learning integration.
    
    Args:
        feedback_type: One of the template keys (GUARDRAIL_VIOLATION, etc.)
        **kwargs: Template-specific parameters
    """
    # Extract issue description for learning system
    issue_description = kwargs.get("issue") or kwargs.get("details") or kwargs.get("context", "")
    if not issue_description:
        # Try to construct from other fields
        if feedback_type == "GUARDRAIL_VIOLATION":
            issue_description = f"Guardrail violation: {kwargs.get('guardrail_name', 'unknown')}"
        elif feedback_type == "ARCHITECTURE_VIOLATION":
            issue_description = f"Architecture violation: {kwargs.get('violation_type', 'unknown')}"
        else:
            issue_description = f"{feedback_type}: {kwargs.get('issue', 'Unknown issue')}"
    
    # Check for similar issues before reporting
    match = _check_for_similar_issues(issue_description, feedback_type)
    if match:
        _suggest_fix_if_available(match, feedback_type)
    
    if feedback_type not in FEEDBACK_TEMPLATES:
        # Fallback to generic logging
        log_feedback(
            issue=f"[{feedback_type}] {kwargs.get('issue', 'Unknown issue')}",
            category="PATTERN_DETECTED",
            context=kwargs.get("context", ""),
            files=kwargs.get("files"),
            requires_human_intervention=kwargs.get("requires_human_intervention", False),
        )
        return
    
    # Map to specific reporting function
    reporters = {
        "GUARDRAIL_VIOLATION": report_guardrail_violation,
        "ARCHITECTURE_VIOLATION": report_architecture_violation,
        "TEMPLATE_DRIFT": report_template_drift,
        "UPDATE_ISSUE": report_update_issue,
        "PERFORMANCE_ISSUE": report_performance_issue,
        "SCHEMA_MISMATCH": report_schema_mismatch,
        "DOCUMENTATION_GAP": report_documentation_gap,
        "OPERATIONAL_ERROR": report_operational_error,
        "STACK_COUPLING": report_stack_coupling,
        "PORTABILITY": report_stack_coupling,
    }
    
    reporter = reporters.get(feedback_type)
    if reporter:
        reporter(**kwargs)
    else:
        # Generic fallback
        log_feedback(
            issue=kwargs.get("issue", "Unknown issue"),
            category=feedback_type,
            context=kwargs.get("context", ""),
            files=kwargs.get("files"),
            requires_human_intervention=kwargs.get("requires_human_intervention", False),
        )

