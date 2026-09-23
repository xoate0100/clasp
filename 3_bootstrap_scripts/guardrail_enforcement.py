#!/usr/bin/env python3
"""
Guardrail enforcement module.
Implements all guardrails defined in feature_flags.yml ai_guardrails section.
"""
import sys
import subprocess
import pathlib
import json
from typing import List, Optional, Set

try:
    import yaml
except ImportError:
    print("[guardrail] Warning: PyYAML not installed. Install with: pip install PyYAML")
    sys.exit(0)

# Import standardized feedback reporting
try:
    from standardized_feedback import report_guardrail_violation, report_feedback
except ImportError:
    # Fallback if standardized_feedback not available
    try:
        from feedback_logger import log_feedback
        def report_guardrail_violation(guardrail_name, component="shared", files=None, context="", details="", requires_intervention=True):
            log_feedback(
                issue=f"Guardrail violation: {guardrail_name} - {details}",
                category="GUARDRAIL_VIOLATION",
                context=context,
                files=files,
                requires_human_intervention=requires_intervention,
            )
        def report_feedback(feedback_type, **kwargs):
            log_feedback(
                issue=kwargs.get("issue", "Unknown"),
                category=feedback_type,
                context=kwargs.get("context", ""),
                files=kwargs.get("files"),
                requires_human_intervention=kwargs.get("requires_human_intervention", False),
            )
    except ImportError:
        # No feedback system available
        def report_guardrail_violation(*args, **kwargs):
            pass
        def report_feedback(*args, **kwargs):
            pass


def load_feature_flags():
    """Load feature flags configuration"""
    flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists():
        print("[guardrail] Warning: feature_flags.yml not found")
        return {}
    with open(flags_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_active_plan():
    """Load active plan for task scope validation"""
    plan_path = pathlib.Path("6_ai_runtime_context/ACTIVE_PLAN.yaml")
    if not plan_path.exists():
        return None
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except:
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


ADVANCE_HYGIENE_ALLOWLIST = {
    "3_bootstrap_scripts/task_completion_gate.py",
    "3_bootstrap_scripts/guardrail_enforcement.py",
    "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml",
    "tests/test_task_completion_gate_advance.py",
}

CONTEXT_ALLOWLIST = {
    "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml",
    "6_ai_runtime_context/AI_CONTEXT.md",
    "6_ai_runtime_context/ACTIVE_PLAN.yaml",
    "6_ai_runtime_context/state_transition_log.jsonl",
}


def _normalize_path(path: str) -> str:
    """Normalize path separators for cross-platform comparison."""
    return pathlib.Path(path).as_posix()


def is_context_allowlist_file(path: str) -> bool:
    """Return True if path is an AI context sync file allowed in any commit."""
    return _normalize_path(path) in CONTEXT_ALLOWLIST


def _hub_gates_apply() -> bool:
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from governance_scope import hub_task_gates_apply
        return hub_task_gates_apply()
    except ImportError:
        return True


def enforce_task_scope(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: enforce_task_scope
    Commits must modify only paths tied to current ACTIVE_TASK_POINTER.
    """
    if not guardrails.get("enforce_task_scope", False):
        return True  # Not enabled

    if not _hub_gates_apply():
        print("[guardrail] enforce_task_scope: spoke repo — hub task scope skipped")
        return True

    plan = load_active_plan()
    if not plan:
        print("[guardrail] enforce_task_scope: No active plan found, skipping")
        return True

    allow_context = guardrails.get("allow_context_files_in_any_commit", True)

    # Get current task from pointer
    pointer_path = pathlib.Path("6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml")
    if pointer_path.exists():
        try:
            with open(pointer_path, "r", encoding="utf-8") as f:
                pointer = yaml.safe_load(f)
            current_task_id = pointer.get("current_task", 0)
        except:
            current_task_id = 0
    else:
        current_task_id = 0

    # Get expected outputs for current task
    tasks = plan.get("tasks", [])
    current_task = next((t for t in tasks if t.get("id") == current_task_id), None)

    if not current_task:
        print(f"[guardrail] enforce_task_scope: Task {current_task_id} not found, allowing")
        return True

    expected_outputs = current_task.get("outputs", [])
    if not expected_outputs:
        print(f"[guardrail] enforce_task_scope: Task {current_task_id} has no outputs, allowing")
        return True

    # Check if staged files match expected outputs
    violations = []
    for file_path in staged_files:
        norm_path = _normalize_path(file_path)
        if allow_context and (is_context_allowlist_file(norm_path) or norm_path in ADVANCE_HYGIENE_ALLOWLIST):
            continue

        # Check if file matches any expected output pattern
        matches = False
        for output in expected_outputs:
            norm_output = _normalize_path(output)
            if norm_output.endswith("/"):
                # Directory pattern
                if norm_path.startswith(norm_output.rstrip("/")):
                    matches = True
                    break
            else:
                # File pattern
                if norm_path == norm_output or norm_path.startswith(norm_output):
                    matches = True
                    break

        if not matches:
            violations.append(file_path)

    if violations:
        print("[guardrail] enforce_task_scope: Files outside task scope:")
        for v in violations:
            print(f"  - {v}")
        print(f"  Expected outputs: {expected_outputs}")
        return False

    return True


def forbid_folder_creation_outside_scope(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: forbid_folder_creation_outside_scope
    New directories validated against plan context; off-scope blocked.
    """
    if not guardrails.get("forbid_folder_creation_outside_scope", False):
        return True  # Not enabled

    flags = load_feature_flags()
    perms = flags.get("permissions", {}) or {}
    allowed_paths = set(perms.get("write_to", []) or [])
    allowed_paths |= set(perms.get("elevated_write_to", []) or [])

    root_allow = {
        "README.md",
        ".pre-commit-config.yaml",
        ".gitignore",
        "requirements.txt",
        "pytest.ini",
        "config.json",
        "vercel_projects.json",
        "MODULES.lock",
        "meta.ps1",
        "meta.sh",
    }

    violations = []
    for file_path in staged_files:
        norm_path = _normalize_path(file_path)

        # Check if file is in allowed write paths
        in_allowed = any(norm_path.startswith(_normalize_path(allowed).rstrip("/"))
                         or norm_path.startswith(_normalize_path(allowed))
                         for allowed in allowed_paths)

        if not in_allowed:
            # Allow root files
            path = pathlib.Path(norm_path)
            if path.name in root_allow:
                continue
            violations.append(file_path)

    if violations:
        print("[guardrail] forbid_folder_creation_outside_scope: Files outside allowed paths:")
        for v in violations:
            print(f"  - {v}")
        print(f"  Allowed paths: {list(allowed_paths)}")
        return False

    return True


def enforce_tdd_cycle(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: enforce_tdd_cycle
    BLOCKING: Commits are blocked if code files are modified without corresponding test files.
    Enforces TDD discipline: Red -> Green -> Refactor -> Document.
    """
    if not guardrails.get("enforce_tdd_cycle", False):
        return True  # Not enabled

    def is_test_file(file_path: str) -> bool:
        """Check if file is a test file based on patterns"""
        path_lower = file_path.lower()
        # Check for test directories
        if "/test" in path_lower or "/tests" in path_lower:
            return True
        # Python test patterns
        if file_path.endswith(("_test.py", "test_.py")):
            return True
        # TypeScript/JavaScript test patterns
        if file_path.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js")):
            return True
        return False

    def is_code_file(file_path: str) -> bool:
        """Check if file is a code file (not a test file)"""
        return file_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) and not is_test_file(file_path)

    # Identify test files and code files
    test_files = [f for f in staged_files if is_test_file(f)]
    code_files = [f for f in staged_files if is_code_file(f)]

    # BLOCKING: If code files are modified without corresponding tests, block commit
    if code_files and not test_files:
        print("[guardrail] BLOCKING: TDD violation - Code modified without tests")
        print("[guardrail] Code files that need tests:")
        for cf in code_files:
            print(f"  - {cf}")
        print("[guardrail] TDD requires: Red -> Green -> Refactor -> Document")
        print("[guardrail] Please add/update test files for all code changes before committing.")
        print("[guardrail] Test file patterns: *_test.py, test_*.py, *.test.ts, *.test.tsx, *.spec.ts, *.spec.tsx, files in test/ directories")
        return False  # Block commit

    return True


def require_doc_sync(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: require_doc_sync
    Checks that updated code sections have matching doc diffs.
    """
    if not guardrails.get("require_doc_sync", False):
        return True  # Not enabled

    # Check if code files modified
    code_files = [f for f in staged_files if f.endswith((".py", ".ts", ".tsx", ".js"))]
    doc_files = [f for f in staged_files if "docs" in f.lower() or f.endswith(".md")]

    if code_files:
        # Check if any doc files are also modified
        if not doc_files:
            print("[guardrail] require_doc_sync: Code modified without documentation updates")
            print("  Modified code:", code_files)
            print("  Tip: Update documentation when code changes")
            # Warning only, not blocking
            return True

    return True


def require_commit_plan_tags(guardrails: dict, staged_files: Optional[List[str]] = None) -> bool:
    """
    Guardrail: require_commit_plan_tags
    Pre-commit hook ensures each commit message contains a plan/task tag.

    Skip when there is no staged changeset (e.g. `meta validate` / `pre-commit run
    --all-files`). Commit-message policy only applies when a commit is being formed.
    """
    if not guardrails.get("require_commit_plan_tags", False):
        return True  # Not enabled

    if not _hub_gates_apply():
        print("[guardrail] require_commit_plan_tags: spoke repo — hub plan tags skipped")
        return True

    staged = staged_files if staged_files is not None else get_staged_files()
    if not staged:
        print("[guardrail] require_commit_plan_tags: no staged files; skipping (validate mode)")
        return True

    # Check commit message
    commit_msg_file = pathlib.Path(".git/COMMIT_EDITMSG")
    if commit_msg_file.exists():
        msg = commit_msg_file.read_text(encoding="utf-8", errors="replace")
    else:
        # Try to get from git
        try:
            msg = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%B"],
                text=True
            )
        except Exception:
            return True  # Can't validate, allow

    # Stale EDITMSG from merges / prior commits during `pre-commit run --all-files`
    # is not an authored commit message. Skip when it looks like merge leftover.
    lower = msg.lower()
    if "conflicts:" in lower or msg.lstrip().startswith("Merge "):
        print("[guardrail] require_commit_plan_tags: stale/merge COMMIT_EDITMSG; skipping")
        return True

    # Check for plan/task tags
    if "plan:" not in msg.lower() and "task:" not in msg.lower():
        print("[guardrail] require_commit_plan_tags: Commit message missing plan/task tags")
        print("  Format: plan: <plan_id> | task: <task_id>")
        return False

    return True


def enforce_intent_declaration(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: enforce_intent_declaration
    BLOCKING: Requires INTENT_DECLARATION.json for commits modifying project code.
    Validates intent matches current task and allowed paths.
    """
    if not guardrails.get("enforce_intent_declaration", False):
        return True  # Not enabled

    if not _hub_gates_apply():
        print("[guardrail] enforce_intent_declaration: spoke repo — hub intent gate skipped")
        return True

    import json

    # Check if any staged files are in project code directories (not just docs)
    project_code_dirs = ["frontend/", "backend/", "shared/", "apps/", "packages/", "scripts/"]
    code_files = [f for f in staged_files if any(f.startswith(d) for d in project_code_dirs)]

    # Also check for non-doc changes (exclude pure doc changes)
    non_doc_files = [f for f in staged_files if not (f.endswith(".md") or "docs/" in f or "4_docs_index/" in f)]

    # Advance-only / context-only commits do not require a new intent
    if non_doc_files and all(
        is_context_allowlist_file(f) or _normalize_path(f) in ADVANCE_HYGIENE_ALLOWLIST
        for f in non_doc_files
    ):
        print("[guardrail] enforce_intent_declaration: context/advance-only changeset; skipping")
        return True

    # If no code files changed, intent declaration not required
    if not code_files and not non_doc_files:
        return True  # Only docs changed, intent not required

    # Intent declaration required for code changes
    intent_path = pathlib.Path("6_ai_runtime_context/INTENT_DECLARATION.json")

    if not intent_path.exists():
        print("[guardrail] BLOCKING: INTENT_DECLARATION.json missing")
        print("[guardrail] Code changes require an intent declaration.")
        print("[guardrail] Create INTENT_DECLARATION.json with:")
        print("  - intent_id: unique identifier")
        print("  - timestamp: ISO8601 timestamp")
        print("  - actor: 'cursor_ai' or 'human'")
        print("  - plan_id: from ACTIVE_PLAN.yaml")
        print("  - component: component name")
        print("  - task_id: must match ACTIVE_TASK_POINTER.current_task")
        print("  - intended_changes: array of {path, change_type}")
        print("  - expected_outputs: from current task")
        print("  - permissions_checked: true")
        print("  - state_files_read: must include ACTIVE_TASK_POINTER.yaml and ACTIVE_PLAN.yaml")
        print("[guardrail] See 6_ai_runtime_context/INTENT_DECLARATION.json for template")
        return False

    # Load and validate intent declaration
    try:
        with open(intent_path, "r", encoding="utf-8") as f:
            intent = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[guardrail] BLOCKING: INTENT_DECLARATION.json is invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"[guardrail] BLOCKING: Failed to read INTENT_DECLARATION.json: {e}")
        return False

    # Validate required fields
    required_fields = ["intent_id", "timestamp", "actor", "plan_id", "component", "task_id",
                      "intended_changes", "expected_outputs", "permissions_checked", "state_files_read"]
    missing_fields = [f for f in required_fields if f not in intent]
    if missing_fields:
        print(f"[guardrail] BLOCKING: INTENT_DECLARATION.json missing required fields: {', '.join(missing_fields)}")
        return False

    # Validate task_id matches ACTIVE_TASK_POINTER
    pointer_path = pathlib.Path("6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml")
    if pointer_path.exists():
        try:
            with open(pointer_path, "r", encoding="utf-8") as f:
                pointer = yaml.safe_load(f)
            current_task_id = pointer.get("current_task")

            # Normalize task_id for comparison (handle int/string)
            intent_task_id = intent.get("task_id")
            if str(intent_task_id) != str(current_task_id):
                print("[guardrail] BLOCKING: Intent task_id does not match ACTIVE_TASK_POINTER")
                print(f"  Intent task_id: {intent_task_id}")
                print(f"  Current task: {current_task_id}")
                print("  Remediation: Update INTENT_DECLARATION.json task_id to match current task")
                return False
        except Exception as e:
            print(f"[guardrail] WARN: Failed to read ACTIVE_TASK_POINTER.yaml: {e}")
            # Continue validation, but this is a warning

    # Validate state_files_read includes required files
    state_files_read = intent.get("state_files_read", [])
    required_state_files = [
        "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml",
        "6_ai_runtime_context/ACTIVE_PLAN.yaml"
    ]
    missing_state_files = [f for f in required_state_files if f not in state_files_read]
    if missing_state_files:
        print(f"[guardrail] BLOCKING: Intent state_files_read missing required files: {', '.join(missing_state_files)}")
        return False

    # Validate permissions_checked
    if not intent.get("permissions_checked", False):
        print("[guardrail] BLOCKING: Intent permissions_checked must be true")
        print("  Remediation: Set permissions_checked: true after verifying permissions")
        return False

    # Load active plan to get expected outputs
    plan = load_active_plan()
    if plan:
        current_task_id = intent.get("task_id")
        tasks = plan.get("tasks", [])
        current_task = next((t for t in tasks if str(t.get("id")) == str(current_task_id)), None)

        if current_task:
            expected_outputs = current_task.get("outputs", [])
            intent_expected = intent.get("expected_outputs", [])

            # Get allowed write paths (agent + elevated hub carve-out)
            flags = load_feature_flags()
            perms = flags.get("permissions", {}) or {}
            allowed_paths = set(perms.get("write_to", []) or [])
            allowed_paths |= set(perms.get("elevated_write_to", []) or [])
            root_allow = {
                "config.json",
                "vercel_projects.json",
                "MODULES.lock",
                "README.md",
                "requirements.txt",
                "pytest.ini",
            }

            # Validate each intended change
            violations = []
            intended_changes = intent.get("intended_changes", [])

            for change in intended_changes:
                change_path = change.get("path", "")
                if not change_path:
                    continue

                # Explicit task outputs authorize the path
                matches_expected = False
                for expected in expected_outputs:
                    if expected.endswith("/"):
                        if change_path.startswith(expected.rstrip("/")):
                            matches_expected = True
                            break
                    else:
                        if change_path == expected or change_path.startswith(expected):
                            matches_expected = True
                            break
                if matches_expected:
                    continue

                path_name = pathlib.Path(change_path).name
                in_allowed = any(change_path.startswith(allowed) for allowed in allowed_paths)
                if path_name in root_allow:
                    in_allowed = True
                if not in_allowed:
                    violations.append({
                        "path": change_path,
                        "reason": f"Path not in allowed write paths: {list(allowed_paths)}"
                    })
                    continue

                if not matches_expected:
                    violations.append({
                        "path": change_path,
                        "reason": f"Path not in expected outputs for task {current_task_id}",
                        "expected_outputs": expected_outputs
                    })

            if violations:
                print("[guardrail] BLOCKING: Intent declaration contains paths outside task scope")
                print("  Violating paths:")
                for v in violations:
                    print(f"    - {v['path']}: {v['reason']}")
                    if "expected_outputs" in v:
                        print(f"      Expected outputs: {v['expected_outputs']}")
                print("  Remediation options:")
                print("    1. Update ACTIVE_PLAN.yaml to include these paths in task.outputs (human action)")
                print("    2. Remove violating files from staged changes")
                print("    3. Update INTENT_DECLARATION.json to match actual changes")
                return False

    # Validate that staged files match intended changes (loose check)
    # This is a sanity check - we don't require exact match, but major discrepancies are flagged
    intended_paths = {c.get("path") for c in intent.get("intended_changes", [])}
    staged_paths = set(staged_files)

    # Allow staged files that are in intended paths or subdirectories
    mismatches = []
    for staged in staged_files:
        # Skip if it's a subdirectory of an intended path
        matches_intent = any(staged.startswith(intended) or intended.startswith(staged)
                            for intended in intended_paths)
        if not matches_intent and staged not in ["6_ai_runtime_context/INTENT_DECLARATION.json"]:
            # Allow intent declaration file itself
            mismatches.append(staged)

    if mismatches and len(mismatches) > len(staged_files) * 0.5:  # More than 50% mismatch
        print("[guardrail] WARN: Significant mismatch between staged files and intended changes")
        print(f"  Mismatched files: {mismatches[:5]}...")  # Show first 5
        print("  This is a warning; intent declaration may need updating")
        # Warning only, don't block

    return True


def enforce_agentic_coordination(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: agentic coordination on staged changes.
    Runs resurrection scan, drift vector check, and phase gate when files are staged.
    """
    if not guardrails.get("enforce_agentic_coordination", False):
        return True

    if not staged_files:
        return True

    scripts = [
        ("resurrection_scan.py", []),
        ("drift_vector_check.py", []),
        ("phase_gate.py", ["--staged"]),
    ]

    for script, extra in scripts:
        script_path = pathlib.Path("3_bootstrap_scripts") / script
        if not script_path.exists():
            print(f"[guardrail] WARN: agentic script missing: {script_path}")
            continue
        cmd = [sys.executable, str(script_path), *extra]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.rstrip())
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr.rstrip())
            print(f"[guardrail] agentic_coordination: {script} failed")
            return False

    return True


def main():
    """Main guardrail enforcement"""
    flags = load_feature_flags()
    guardrails = flags.get("ai_guardrails", {})

    if not guardrails:
        print("[guardrail] No guardrails configured")
        sys.exit(0)

    staged_files = get_staged_files()

    results = []

    # Run all enabled guardrails
    results.append(("enforce_task_scope", enforce_task_scope(guardrails, staged_files)))
    results.append(("forbid_folder_creation_outside_scope",
                   forbid_folder_creation_outside_scope(guardrails, staged_files)))
    results.append(("enforce_tdd_cycle", enforce_tdd_cycle(guardrails, staged_files)))
    results.append(("require_doc_sync", require_doc_sync(guardrails, staged_files)))
    results.append(("require_commit_plan_tags", require_commit_plan_tags(guardrails, staged_files)))
    results.append(("enforce_intent_declaration", enforce_intent_declaration(guardrails, staged_files)))
    results.append(("enforce_agentic_coordination", enforce_agentic_coordination(guardrails, staged_files)))

    # Check results
    failed = [name for name, passed in results if not passed]

    if failed:
        print(f"[guardrail] Failed checks: {', '.join(failed)}")
        # Log feedback for guardrail violations using standardized reporting
        try:
            sys.path.insert(0, str(pathlib.Path(__file__).parent))
            for guardrail_name in failed:
                report_guardrail_violation(
                    guardrail_name=guardrail_name,
                    component="shared",
                    files=staged_files,
                    context="Guardrail check failed during pre-commit",
                    details=f"Guardrail '{guardrail_name}' failed validation",
                    requires_intervention=True,
                )
        except Exception:
            pass  # Fail silently to not break guardrail enforcement
        sys.exit(1)

    print("[guardrail] All checks passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
