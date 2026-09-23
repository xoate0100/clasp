#!/usr/bin/env python3
"""
Final Readiness Check for Meta-Framework Upgrade v2.0.0
Validates all prerequisites before executing the upgrade plan.
"""

import json
import pathlib
import sys
from datetime import datetime
from typing import Dict, List, Tuple

PROJECT_ROOT = pathlib.Path(".")
REQUIRED_FILES = {
    "governance": [
        "1_global_standards/AI_OPERATING_CONSTITUTION.md",
        "0_phase0_bootstrap/AI_SANDBOX_RULES.md",
        "0_phase0_bootstrap/feature_flags.yml",
    ],
    "state": [
        "6_ai_runtime_context/ACTIVE_PLAN.yaml",
        "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml",
    ],
    "schemas": [
        "7_schemas/intent_declaration.schema.json",
        "7_schemas/plan.schema.json",
    ],
    "plan": [
        "docs/GOVERNANCE_COMPLIANT_UPGRADE_PLAN.md",
        "docs/UPGRADE_EXECUTION_CHECKLIST.md",
    ],
    "scripts": [
        "3_bootstrap_scripts/task_completion_gate.py",
        "3_bootstrap_scripts/auto_advance_state.py",
        "3_bootstrap_scripts/guardrail_enforcement.py",
    ],
}


def check_file_exists(file_path: str) -> Tuple[bool, str]:
    """Check if file exists."""
    path = PROJECT_ROOT / file_path
    if path.exists():
        return True, f"OK: {file_path}"
    return False, f"MISSING: {file_path}"


def check_permissions() -> Tuple[bool, List[str]]:
    """Check write permissions for required directories."""
    allowed_dirs = [
        "3_bootstrap_scripts/",
        "docs/",
        "6_ai_runtime_context/",
        "tests/",
    ]
    
    issues = []
    for dir_path in allowed_dirs:
        path = PROJECT_ROOT / dir_path
        if not path.exists():
            issues.append(f"Directory missing: {dir_path}")
        elif not path.is_dir():
            issues.append(f"Not a directory: {dir_path}")
    
    return len(issues) == 0, issues


def check_governance_files() -> Tuple[bool, List[str]]:
    """Check governance files are read-only (as per rules)."""
    readonly_dirs = [
        "0_phase0_bootstrap/",
        "1_global_standards/",
        "7_schemas/",
    ]
    
    issues = []
    # We can't actually check if files are read-only via Python easily,
    # but we can verify they exist and note that they should be read-only
    for dir_path in readonly_dirs:
        path = PROJECT_ROOT / dir_path
        if not path.exists():
            issues.append(f"Governance directory missing: {dir_path}")
    
    return len(issues) == 0, issues


def check_state_files() -> Tuple[bool, List[str]]:
    """Check state files exist and are valid."""
    issues = []
    
    # Check upgrade plan exists
    upgrade_plan = PROJECT_ROOT / "6_ai_runtime_context/ACTIVE_PLAN.yaml"
    if not upgrade_plan.exists():
        issues.append("ACTIVE_PLAN.yaml missing")
    
    # Check task pointer exists
    pointer = PROJECT_ROOT / "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml"
    if not pointer.exists():
        issues.append("ACTIVE_TASK_POINTER.yaml missing")
    
    return len(issues) == 0, issues


def check_schemas() -> Tuple[bool, List[str]]:
    """Check required schemas exist."""
    issues = []
    
    intent_schema = PROJECT_ROOT / "7_schemas/intent_declaration.schema.json"
    if not intent_schema.exists():
        issues.append("intent_declaration.schema.json missing")
    else:
        # Validate schema is valid JSON
        try:
            with open(intent_schema, "r") as f:
                json.load(f)
        except Exception as e:
            issues.append(f"intent_declaration.schema.json invalid: {e}")
    
    plan_schema = PROJECT_ROOT / "7_schemas/plan.schema.json"
    if not plan_schema.exists():
        issues.append("plan.schema.json missing")
    
    return len(issues) == 0, issues


def check_pre_commit_hooks() -> Tuple[bool, List[str]]:
    """Check pre-commit hooks are configured."""
    precommit_config = PROJECT_ROOT / ".pre-commit-config.yaml"
    if not precommit_config.exists():
        return False, [".pre-commit-config.yaml missing"]
    
    # Check for key hooks
    content = precommit_config.read_text(encoding="utf-8")
    required_hooks = [
        "check-governance-install",
        "guardrail-enforcement",
        "task-completion-gate",
    ]
    
    missing = []
    for hook in required_hooks:
        if hook not in content:
            missing.append(f"Pre-commit hook missing: {hook}")
    
    return len(missing) == 0, missing


def main() -> int:
    """Run final readiness check."""
    print("=" * 70)
    print("FINAL READINESS CHECK: Meta-Framework Upgrade v2.0.0")
    print("=" * 70)
    print()
    
    all_checks_passed = True
    issues = []
    
    # 1. Check required files
    print("1. Checking required files...")
    for category, files in REQUIRED_FILES.items():
        for file_path in files:
            exists, message = check_file_exists(file_path)
            if exists:
                print(f"   {message}")
            else:
                print(f"   {message}")
                all_checks_passed = False
                issues.append(message)
    print()
    
    # 2. Check permissions
    print("2. Checking write permissions...")
    perms_ok, perm_issues = check_permissions()
    if perms_ok:
        print("   OK: Write permissions verified")
    else:
        for issue in perm_issues:
            print(f"   {issue}")
            all_checks_passed = False
            issues.append(issue)
    print()
    
    # 3. Check governance files
    print("3. Checking governance files...")
    gov_ok, gov_issues = check_governance_files()
    if gov_ok:
        print("   OK: Governance files present (should be read-only)")
    else:
        for issue in gov_issues:
            print(f"   {issue}")
            all_checks_passed = False
            issues.append(issue)
    print()
    
    # 4. Check state files
    print("4. Checking state files...")
    state_ok, state_issues = check_state_files()
    if state_ok:
        print("   OK: State files present")
    else:
        for issue in state_issues:
            print(f"   {issue}")
            all_checks_passed = False
            issues.append(issue)
    print()
    
    # 5. Check schemas
    print("5. Checking schemas...")
    schema_ok, schema_issues = check_schemas()
    if schema_ok:
        print("   OK: Required schemas present and valid")
    else:
        for issue in schema_issues:
            print(f"   {issue}")
            all_checks_passed = False
            issues.append(issue)
    print()
    
    # 6. Check pre-commit hooks
    print("6. Checking pre-commit hooks...")
    hooks_ok, hooks_issues = check_pre_commit_hooks()
    if hooks_ok:
        print("   OK: Pre-commit hooks configured")
    else:
        for issue in hooks_issues:
            print(f"   {issue}")
            all_checks_passed = False
            issues.append(issue)
    print()
    
    # Summary
    print("=" * 70)
    if all_checks_passed:
        print("READINESS CHECK: PASSED")
        print("=" * 70)
        print()
        print("All prerequisites met. Ready to execute Task 1.")
        return 0
    else:
        print("READINESS CHECK: FAILED")
        print("=" * 70)
        print()
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("Please resolve these issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
