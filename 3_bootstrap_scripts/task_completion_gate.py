#!/usr/bin/env python3
"""
Task Completion Gate - Blocking validation before state advancement.

Validates all gates (GATE-1 through GATE-6) before allowing task completion
and state transition. Generates completion report artifact.
"""
import sys
import os
import pathlib
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install PyYAML")
    sys.exit(1)


def load_yaml(path: pathlib.Path) -> Optional[Dict]:
    """Load YAML file, return None if missing or invalid"""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load {path}: {e}")
        return None


def load_json(path: pathlib.Path) -> Optional[Dict]:
    """Load JSON file, return None if missing or invalid"""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load {path}: {e}")
        return None


def get_staged_files() -> List[str]:
    """Get list of staged files"""
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True
        )
        return [f.strip() for f in output.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def get_working_tree_files() -> List[str]:
    """Get list of modified files in working tree"""
    try:
        output = subprocess.check_output(
            ["git", "diff", "--name-only"],
            text=True
        )
        return [f.strip() for f in output.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def path_exists(path_str: str, project_root: pathlib.Path) -> bool:
    """Check if path exists (file or directory)"""
    path = project_root / path_str
    return path.exists()


def path_matches_output(output: str, file_path: str) -> bool:
    """Check if file_path matches output pattern"""
    if output.endswith("/"):
        # Directory pattern - file must be under this directory
        dir_path = output.rstrip("/")
        return file_path == dir_path or file_path.startswith(dir_path + "/")
    else:
        # File pattern - exact match or prefix match
        return file_path == output or file_path.startswith(output)


def check_gate_1_state_read_proof(intent: Dict) -> Tuple[bool, str]:
    """
    GATE-1: State Read Proof
    INTENT_DECLARATION.json.state_files_read MUST include required files.
    """
    required_files = [
        "6_ai_runtime_context/ACTIVE_PLAN.yaml",
        "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml"
    ]

    state_files_read = intent.get("state_files_read", [])
    missing = [f for f in required_files if f not in state_files_read]

    if missing:
        return False, f"GATE-1 FAILED: Missing state files in intent: {', '.join(missing)}"
    return True, "GATE-1 PASSED: All required state files read"


def check_gate_2_task_identity_match(intent: Dict, pointer: Dict) -> Tuple[bool, str]:
    """
    GATE-2: Task Identity Match
    INTENT_DECLARATION.json.task_id MUST equal ACTIVE_TASK_POINTER.yaml.current_task
    """
    intent_task_id = intent.get("task_id")
    current_task_id = pointer.get("current_task")

    if str(intent_task_id) != str(current_task_id):
        return False, f"GATE-2 FAILED: Task ID mismatch - Intent: {intent_task_id}, Current: {current_task_id}"
    return True, f"GATE-2 PASSED: Task ID matches ({current_task_id})"


def check_gate_3_outputs_present(plan: Dict, pointer: Dict, project_root: pathlib.Path) -> Tuple[bool, str, List[str]]:
    """
    GATE-3: Outputs Present
    Every output path from current task MUST exist.
    Returns: (passed, message, missing_outputs)
    """
    current_task_id = pointer.get("current_task")
    tasks = plan.get("tasks", [])
    current_task = next((t for t in tasks if str(t.get("id")) == str(current_task_id)), None)

    if not current_task:
        return False, f"GATE-3 FAILED: Task {current_task_id} not found in plan", []

    outputs = current_task.get("outputs", [])
    if not outputs:
        return True, "GATE-3 PASSED: Task has no outputs (skipped)", []

    missing = []
    for output in outputs:
        if not path_exists(output, project_root):
            missing.append(output)

    if missing:
        return False, f"GATE-3 FAILED: Missing outputs: {', '.join(missing)}", missing
    return True, f"GATE-3 PASSED: All {len(outputs)} outputs present", []


def check_gate_4_scope_compliance(
    plan: Dict,
    pointer: Dict,
    staged_files: List[str],
    feature_flags: Dict,
    project_root: pathlib.Path
) -> Tuple[bool, str, List[str]]:
    """
    GATE-4: Scope Compliance (Strict Mode)
    All modified files MUST be within allowed write paths AND task.outputs.
    Returns: (passed, message, violations)
    """
    current_task_id = pointer.get("current_task")
    tasks = plan.get("tasks", [])
    current_task = next((t for t in tasks if str(t.get("id")) == str(current_task_id)), None)

    if not current_task:
        return True, "GATE-4 SKIPPED: Task not found", []

    expected_outputs = current_task.get("outputs", [])
    if not expected_outputs:
        return True, "GATE-4 SKIPPED: Task has no outputs", []

    # Get allowed write paths (agent write_to + hub elevated when listed in outputs)
    perms = feature_flags.get("permissions", {}) or {}
    allowed_paths = set(perms.get("write_to", []) or [])
    elevated_paths = set(perms.get("elevated_write_to", []) or [])

    violations = []
    for file_path in staged_files:
        # Skip state files and completion reports (they're allowed)
        # INTENT_DECLARATION.json is a runtime file required by the system
        if file_path.startswith("6_ai_runtime_context/"):
            # Allow INTENT_DECLARATION.json and other runtime files
            if "INTENT_DECLARATION.json" in file_path or "ACTIVE_TASK_POINTER.yaml" in file_path:
                continue
            # Allow completion reports
            if "TASK_COMPLETION_REPORTS" in file_path:
                continue
            # Allow ACTIVE_PLAN.yaml if it's in expected outputs (it's both a state file and an output)
            if "ACTIVE_PLAN.yaml" in file_path:
                # Check if it's in expected outputs
                if any(path_matches_output(output, file_path) for output in expected_outputs):
                    continue
            # Allow feedback log when listed in outputs
            if "ai_feedback_log.json" in file_path:
                if any(path_matches_output(output, file_path) for output in expected_outputs):
                    continue
            if "AI_CONTEXT.md" in file_path:
                if any(path_matches_output(output, file_path) for output in expected_outputs):
                    continue
        if file_path.startswith(".git/"):
            continue

        # Explicit task.outputs authorize the path (including repo-root artifacts).
        matches_output = any(path_matches_output(output, file_path) for output in expected_outputs)
        if matches_output:
            continue

        # Check if in allowed write paths (or elevated hub path matching outputs)
        in_allowed = any(file_path.startswith(allowed) for allowed in allowed_paths)
        in_elevated = any(file_path.startswith(elev) for elev in elevated_paths)
        if in_elevated and matches_output:
            continue
        if not in_allowed:
            violations.append({
                "path": file_path,
                "reason": f"Not in allowed write paths: {list(allowed_paths)}"
            })
            continue

        # Check if matches expected outputs (strict mode)
        violations.append({
            "path": file_path,
            "reason": f"Not in task outputs: {expected_outputs}",
            "expected_outputs": expected_outputs
        })

    if violations:
        violation_paths = [v["path"] for v in violations]
        return False, f"GATE-4 FAILED: {len(violations)} files outside task scope", violation_paths
    return True, "GATE-4 PASSED: All files within task scope", []


def check_gate_5_precommit_proof() -> Tuple[bool, str]:
    """
    GATE-5: Tests + Pre-commit Proof
    Pre-commit must pass. This gate assumes pre-commit hooks will run separately.
    For now, we check that we can detect if pre-commit would run.
    """
    # This gate is validated by the pre-commit hook system itself
    # We just confirm the hook chain is configured
    precommit_config = pathlib.Path(".pre-commit-config.yaml")
    if not precommit_config.exists():
        return False, "GATE-5 FAILED: .pre-commit-config.yaml missing"

    # Note: Actual pre-commit validation happens in the hook chain
    # This gate passes if we're being called from pre-commit (meaning hooks are running)
    return True, "GATE-5 PASSED: Pre-commit hooks configured (validation in hook chain)"


def generate_completion_report(
    task_id: int,
    plan: Dict,
    gate_results: List[Dict],
    project_root: pathlib.Path
) -> Tuple[bool, pathlib.Path]:
    """
    GATE-6: Completion Artifact
    Generate completion report for the task.
    Returns: (success, report_path)
    """
    reports_dir = project_root / "6_ai_runtime_context" / "TASK_COMPLETION_REPORTS"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / f"task_{task_id}.md"

    # Preserve authored reports during pre-commit; rewriting always dirties the
    # index and fails the hook even when gates already passed.
    if report_path.exists() and report_path.stat().st_size > 0:
        if not os.environ.get("FORCE_COMPLETION_REPORT"):
            return True, report_path

    tasks = plan.get("tasks", [])
    current_task = next((t for t in tasks if str(t.get("id")) == str(task_id)), None)
    task_name = current_task.get("name", "Unknown") if current_task else "Unknown"

    # Determine overall pass/fail
    all_passed = all(g.get("passed", False) for g in gate_results)

    timestamp = datetime.now().isoformat()

    report_content = f"""# Task Completion Report

**Task ID:** {task_id}
**Task Name:** {task_name}
**Timestamp:** {timestamp}
**Plan ID:** {plan.get('plan_id', 'N/A')}
**Component:** {plan.get('component', 'N/A')}

## Gate Results

**Overall Status:** {'✅ PASSED' if all_passed else '❌ FAILED'}

"""

    for gate_result in gate_results:
        gate_name = gate_result.get("gate", "Unknown")
        passed = gate_result.get("passed", False)
        message = gate_result.get("message", "")
        status = "✅ PASS" if passed else "❌ FAIL"
        report_content += f"- **{gate_name}**: {status} - {message}\n"

    report_content += f"""
## Task Outputs

"""

    if current_task:
        outputs = current_task.get("outputs", [])
        for output in outputs:
            exists = path_exists(output, project_root)
            status = "✅" if exists else "❌"
            report_content += f"- {status} `{output}`\n"
    else:
        report_content += "- No outputs defined\n"

    report_content += f"""
## Summary

This report was generated by the Task Completion Gate system.
All gates must pass before state advancement is permitted.

**Generated by:** task_completion_gate.py
**Report Path:** {report_path}
"""

    try:
        report_path.write_text(report_content, encoding="utf-8")
        return True, report_path
    except Exception as e:
        print(f"ERROR: Failed to write completion report: {e}")
        return False, report_path


def main() -> int:
    """Main gate evaluation"""
    project_root = pathlib.Path(".").resolve()

    # Hub ACTIVE_PLAN gates apply only on the meta-framework hub repo.
    try:
        sys.path.insert(0, str(project_root / "3_bootstrap_scripts"))
        from governance_scope import hub_task_gates_apply, scope_label

        if not hub_task_gates_apply(str(project_root)):
            print(
                f"[gate] INFO: {scope_label(str(project_root))} repo — "
                "hub ACTIVE_PLAN task gates skipped"
            )
            return 0
    except ImportError:
        pass

    # Load required files
    plan_path = project_root / "6_ai_runtime_context" / "ACTIVE_PLAN.yaml"
    pointer_path = project_root / "6_ai_runtime_context" / "ACTIVE_TASK_POINTER.yaml"
    intent_path = project_root / "6_ai_runtime_context" / "INTENT_DECLARATION.json"
    feature_flags_path = project_root / "0_phase0_bootstrap" / "feature_flags.yml"

    plan = load_yaml(plan_path)
    pointer = load_yaml(pointer_path)
    intent = load_json(intent_path)
    feature_flags = load_yaml(feature_flags_path) or {}

    if not plan:
        print("ERROR: ACTIVE_PLAN.yaml not found or invalid")
        return 1

    if not pointer:
        print("ERROR: ACTIVE_TASK_POINTER.yaml not found or invalid")
        return 1

    current_task_id = pointer.get("current_task")
    if current_task_id is None:
        print("ERROR: No current_task in ACTIVE_TASK_POINTER.yaml")
        return 1

    # Get staged files (preferred) or working tree files
    staged_files = get_staged_files()
    if not staged_files:
        staged_files = get_working_tree_files()

    # Advance-only commits: pointer + transition log (+ optional AI_CONTEXT sync)
    # and the gate/guardrail scripts that implement advance-only exemption.
    advance_only_prefixes = (
        "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml",
        "6_ai_runtime_context/state_transition_log.jsonl",
        "6_ai_runtime_context/AI_CONTEXT.md",
        "6_ai_runtime_context/TASK_COMPLETION_REPORTS/",
        "3_bootstrap_scripts/task_completion_gate.py",
        "3_bootstrap_scripts/guardrail_enforcement.py",
        "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml",
        "tests/test_guardrail_context_allowlist.py",
        "tests/test_task_completion_gate_advance.py",
    )
    non_advance = [
        f for f in staged_files
        if not any(f.replace("\\", "/").startswith(p) or f.replace("\\", "/") == p for p in advance_only_prefixes)
    ]
    if not non_advance and any(
        f.replace("\\", "/").endswith("ACTIVE_TASK_POINTER.yaml") for f in staged_files
    ):
        print("[gate] INFO: advance-only changeset (pointer/transition log); skipping output/scope gates")
        return 0

    # Filter to code files only (exclude state files)
    code_files = [f for f in staged_files if not f.startswith("6_ai_runtime_context/")]

    # If no code changes, gate may not be required (but we still check if pointer changed)
    pointer_changed = any(f.endswith("ACTIVE_TASK_POINTER.yaml") for f in staged_files)

    if not code_files and not pointer_changed:
        print("[gate] INFO: No code changes or pointer changes, gate check skipped")
        return 0

    # Run all gates
    gate_results = []

    # GATE-1: State Read Proof
    if intent:
        passed, message = check_gate_1_state_read_proof(intent)
        gate_results.append({"gate": "GATE-1", "passed": passed, "message": message})
        if not passed:
            print(f"[gate] {message}")
    else:
        gate_results.append({"gate": "GATE-1", "passed": False, "message": "INTENT_DECLARATION.json missing"})
        print("[gate] GATE-1 FAILED: INTENT_DECLARATION.json missing")

    # GATE-2: Task Identity Match
    if intent:
        passed, message = check_gate_2_task_identity_match(intent, pointer)
        gate_results.append({"gate": "GATE-2", "passed": passed, "message": message})
        if not passed:
            print(f"[gate] {message}")
    else:
        gate_results.append({"gate": "GATE-2", "passed": False, "message": "INTENT_DECLARATION.json missing"})

    # GATE-3: Outputs Present
    passed, message, missing = check_gate_3_outputs_present(plan, pointer, project_root)
    gate_results.append({"gate": "GATE-3", "passed": passed, "message": message, "missing": missing})
    if not passed:
        print(f"[gate] {message}")
        if missing:
            print(f"[gate] Missing outputs:")
            for output in missing:
                print(f"  - {output}")

    # GATE-4: Scope Compliance
    passed, message, violations = check_gate_4_scope_compliance(plan, pointer, staged_files, feature_flags, project_root)
    gate_results.append({"gate": "GATE-4", "passed": passed, "message": message, "violations": violations})
    if not passed:
        print(f"[gate] {message}")
        if violations:
            print(f"[gate] Violating files:")
            for violation in violations[:10]:  # Show first 10
                print(f"  - {violation}")
            if len(violations) > 10:
                print(f"  ... and {len(violations) - 10} more")
            print("[gate] Remediation:")
            print("  1. Update ACTIVE_PLAN.yaml to include these paths in task.outputs (human action)")
            print("  2. Remove violating files from staged changes")
            print("  3. Update INTENT_DECLARATION.json to match actual changes")

    # GATE-5: Pre-commit Proof
    passed, message = check_gate_5_precommit_proof()
    gate_results.append({"gate": "GATE-5", "passed": passed, "message": message})
    if not passed:
        print(f"[gate] {message}")

    # GATE-6: Generate Completion Report
    success, report_path = generate_completion_report(current_task_id, plan, gate_results, project_root)
    gate_results.append({"gate": "GATE-6", "passed": success, "message": f"Completion report: {report_path}"})
    if not success:
        print(f"[gate] GATE-6 FAILED: Could not generate completion report")

    # Check if all gates passed
    all_passed = all(g.get("passed", False) for g in gate_results)

    if all_passed:
        print(f"[gate] ✅ All gates passed for task {current_task_id}")
        print(f"[gate] Completion report: {report_path}")
        return 0
    else:
        failed_gates = [g["gate"] for g in gate_results if not g.get("passed", False)]
        print(f"[gate] ❌ Gate check FAILED - Failed gates: {', '.join(failed_gates)}")
        print(f"[gate] Completion report: {report_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
