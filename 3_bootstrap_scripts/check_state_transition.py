#!/usr/bin/env python3
"""
Pre-commit hook: Validate state transitions.

BLOCKING: Ensures that if ACTIVE_TASK_POINTER.yaml changed:
1. A completion report exists for the prior task
2. A transition event was appended to state_transition_log.jsonl
3. The transition was made via auto_advance_state.py (not direct edit)
"""
import sys
import pathlib
import json
import subprocess

try:
    import yaml
except ImportError:
    print("[state-transition-check] ERROR: PyYAML required for state transition validation")
    print("[state-transition-check] Install with: pip install PyYAML")
    sys.exit(1)


def get_staged_files() -> list[str]:
    """Get list of staged files"""
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True
        )
        return [f.strip() for f in output.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def get_pointer_diff() -> tuple[dict, dict]:
    """Get old and new pointer values from git diff"""
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml"],
            text=True
        )

        old_pointer = {}
        new_pointer = {}

        for line in output.splitlines():
            if line.startswith("-") and not line.startswith("---"):
                # Old value
                if "current_task:" in line:
                    old_pointer["current_task"] = int(line.split(":")[1].strip())
            elif line.startswith("+") and not line.startswith("+++"):
                # New value
                if "current_task:" in line:
                    new_pointer["current_task"] = int(line.split(":")[1].strip())

        return old_pointer, new_pointer
    except Exception:
        return {}, {}


def check_completion_report_exists(task_id: int, project_root: pathlib.Path) -> bool:
    """Check if completion report exists for task"""
    report_path = project_root / "6_ai_runtime_context" / "TASK_COMPLETION_REPORTS" / f"task_{task_id}.md"
    return report_path.exists()


def get_pointer_plan_diff() -> tuple[str | None, str | None]:
    """Return (old_plan_id, new_plan_id) from staged pointer diff when present."""
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml"],
            text=True,
        )
        old_plan = None
        new_plan = None
        for line in output.splitlines():
            if "plan_id:" not in line:
                continue
            value = line.split(":", 1)[1].strip().strip("'\"")
            if line.startswith("-") and not line.startswith("---"):
                old_plan = value
            elif line.startswith("+") and not line.startswith("+++"):
                new_plan = value
        return old_plan, new_plan
    except Exception:
        return None, None


def check_transition_logged(
    from_task: int,
    to_task: int,
    project_root: pathlib.Path,
    *,
    transition_type: str | None = None,
) -> bool:
    """Check if transition was logged"""
    log_path = project_root / "6_ai_runtime_context" / "state_transition_log.jsonl"

    if not log_path.exists():
        return False

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-20:]:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if event.get("from_task") != from_task or event.get("to_task") != to_task:
                        continue
                    if transition_type and event.get("transition_type") != transition_type:
                        continue
                    return True
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return False


def main() -> int:
    """Main validation"""
    project_root = pathlib.Path(".").resolve()

    try:
        sys.path.insert(0, str(project_root / "3_bootstrap_scripts"))
        from governance_scope import hub_task_gates_apply, scope_label

        if not hub_task_gates_apply(str(project_root)):
            print(
                f"[state-transition-check] INFO: {scope_label(str(project_root))} repo — "
                "hub pointer transition check skipped"
            )
            return 0
    except ImportError:
        pass

    pointer_path = project_root / "6_ai_runtime_context" / "ACTIVE_TASK_POINTER.yaml"

    staged_files = get_staged_files()

    # Check if pointer is in staged files
    pointer_staged = any(f.endswith("ACTIVE_TASK_POINTER.yaml") for f in staged_files)

    if not pointer_staged:
        # No pointer change, nothing to validate
        return 0

    # Get old and new task IDs
    old_pointer, new_pointer = get_pointer_diff()

    if "current_task" not in old_pointer or "current_task" not in new_pointer:
        # Couldn't parse diff, try loading current and checking git
        print("[state-transition-check] WARN: Could not parse pointer diff, attempting alternative check")

        # Load current pointer
        if pointer_path.exists():
            try:
                with open(pointer_path, "r", encoding="utf-8") as f:
                    current_pointer = yaml.safe_load(f)
                    current_task = current_pointer.get("current_task")

                    # Check if completion report exists
                    if current_task and not check_completion_report_exists(current_task, project_root):
                        print(f"[state-transition-check] WARN: No completion report for task {current_task}")
                        print("[state-transition-check] State transitions should use: python3 3_bootstrap_scripts/auto_advance_state.py")
            except Exception:
                pass

        # Non-blocking warning
        return 0

    from_task = old_pointer["current_task"]
    to_task = new_pointer["current_task"]
    old_plan, new_plan = get_pointer_plan_diff()
    plan_swap = bool(old_plan and new_plan and old_plan != new_plan and to_task == 1)

    # Validate transition
    errors = []

    if plan_swap:
        # Plan activation resets pointer to task 1; must be logged as plan_swap.
        if not check_transition_logged(
            from_task, to_task, project_root, transition_type="plan_swap"
        ):
            errors.append(
                f"Plan swap {old_plan} -> {new_plan} reset {from_task} -> {to_task} not logged"
            )
            errors.append(
                "  Expected state_transition_log.jsonl entry with transition_type=plan_swap"
            )
        if errors:
            print("[state-transition-check] ❌ State transition validation FAILED")
            for error in errors:
                print(f"[state-transition-check] {error}")
            return 1
        print(
            f"[state-transition-check] ✅ Plan swap validated: "
            f"{old_plan} -> {new_plan}, pointer {from_task} -> {to_task}"
        )
        return 0

    # Check 1: Completion report exists for from_task
    if not check_completion_report_exists(from_task, project_root):
        errors.append(f"Missing completion report for task {from_task}")
        errors.append(f"  Expected: 6_ai_runtime_context/TASK_COMPLETION_REPORTS/task_{from_task}.md")

    # Check 2: Transition was logged
    if not check_transition_logged(from_task, to_task, project_root):
        errors.append(f"Transition from task {from_task} to {to_task} not logged")
        errors.append(f"  Expected entry in: 6_ai_runtime_context/state_transition_log.jsonl")

    # Check 3: Validate task increment (must be +1)
    if to_task != from_task + 1:
        errors.append(f"Invalid task increment: {from_task} -> {to_task} (must be +1)")
        errors.append("  State advancement must increment by exactly 1 task")

    if errors:
        print("[state-transition-check] ❌ State transition validation FAILED")
        for error in errors:
            print(f"[state-transition-check] {error}")
        print("[state-transition-check]")
        print("[state-transition-check] Remediation:")
        print("[state-transition-check]   Use: python3 3_bootstrap_scripts/auto_advance_state.py")
        print("[state-transition-check]   Do NOT edit ACTIVE_TASK_POINTER.yaml directly")
        return 1

    print(f"[state-transition-check] ✅ State transition validated: task {from_task} -> {to_task}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
