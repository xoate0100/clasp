#!/usr/bin/env python3
"""
Auto-Advance State Protocol - Governed state advancement for AI agents.

This script implements the Auto-Advance Protocol:
1. Run Task Completion Gate
2. Generate completion report
3. Append state transition event
4. Update ACTIVE_TASK_POINTER.yaml (increment by exactly +1)
5. Re-read and confirm change

AI agents should call this script to advance state, not modify pointer directly.
"""
import sys
import pathlib
import json
import subprocess
from datetime import datetime
from typing import Dict, Optional, Tuple, List

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install PyYAML")
    sys.exit(1)


def load_yaml(path: pathlib.Path) -> Optional[Dict]:
    """Load YAML file"""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load {path}: {e}")
        return None


def load_json(path: pathlib.Path) -> Optional[Dict]:
    """Load JSON file"""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load {path}: {e}")
        return None


def save_yaml(path: pathlib.Path, data: Dict) -> bool:
    """Save YAML file"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save {path}: {e}")
        return False


def run_completion_gate() -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Run task completion gate and return results.
    Returns: (success, gate_results, completion_report_path)
    """
    project_root = pathlib.Path(".").resolve()
    gate_script = project_root / "3_bootstrap_scripts" / "task_completion_gate.py"
    
    if not gate_script.exists():
        print("ERROR: task_completion_gate.py not found")
        return False, None, None
    
    # Run gate
    result = subprocess.run(
        ["python3", str(gate_script)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("ERROR: Task completion gate failed")
        print(result.stdout)
        print(result.stderr)
        return False, None, None
    
    # Extract completion report path from output
    completion_report_path = None
    for line in result.stdout.splitlines():
        if "Completion report:" in line:
            parts = line.split("Completion report:")
            if len(parts) > 1:
                completion_report_path = parts[1].strip()
            break
    
    # Load gate results from completion report if available
    gate_results = None
    if completion_report_path and pathlib.Path(completion_report_path).exists():
        # Parse gate results from report (simplified - in real implementation might store JSON)
        gate_results = []
        report_content = pathlib.Path(completion_report_path).read_text()
        # Extract gate results from markdown (simplified parsing)
        # In production, might want to store gate_results as JSON in report
        for line in report_content.splitlines():
            if line.startswith("- **GATE-"):
                gate_results.append({"gate": "GATE-X", "passed": "✅" in line, "message": line})
    
    return True, gate_results, completion_report_path


def append_transition_event(
    plan: Dict,
    from_task: int,
    to_task: int,
    actor: str,
    intent_id: Optional[str],
    completion_report_path: Optional[str],
    gate_results: Optional[list]
) -> bool:
    """Append state transition event to log"""
    transition_script = pathlib.Path("3_bootstrap_scripts/append_state_transition.py")
    
    if not transition_script.exists():
        print("ERROR: append_state_transition.py not found")
        return False
    
    # Build command
    cmd = [
        "python3", str(transition_script),
        "--plan-id", plan.get("plan_id", ""),
        "--component", plan.get("component", ""),
        "--from-task", str(from_task),
        "--to-task", str(to_task),
        "--actor", actor
    ]
    
    if intent_id:
        cmd.extend(["--intent-id", intent_id])
    if completion_report_path:
        cmd.extend(["--completion-report", completion_report_path])
    if gate_results:
        cmd.extend(["--gate-results", json.dumps(gate_results)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"ERROR: Failed to append transition: {result.stderr}")
        return False
    
    return True


def advance_pointer(pointer_path: pathlib.Path, current_task_id: int, tasks: list) -> Tuple[bool, int]:
    """
    Advance task pointer by exactly +1.
    Returns: (success, new_task_id)
    """
    # Find next task
    current_idx = None
    for idx, task in enumerate(tasks):
        if str(task.get("id")) == str(current_task_id):
            current_idx = idx
            break
    
    if current_idx is None:
        print(f"ERROR: Current task {current_task_id} not found in plan")
        return False, current_task_id
    
    if current_idx + 1 >= len(tasks):
        print(f"INFO: Task {current_task_id} is the last task. No advancement possible.")
        return False, current_task_id
    
    next_task = tasks[current_idx + 1]
    new_task_id = next_task.get("id")
    
    # Load current pointer
    pointer = load_yaml(pointer_path)
    if not pointer:
        pointer = {}
    
    # Update pointer
    pointer["current_task"] = new_task_id
    pointer["last_run"] = datetime.now().isoformat()
    pointer["status"] = "in_progress"
    
    # Save
    if not save_yaml(pointer_path, pointer):
        return False, current_task_id
    
    # Re-read and confirm
    confirmed_pointer = load_yaml(pointer_path)
    if not confirmed_pointer:
        print("ERROR: Failed to re-read pointer after update")
        return False, current_task_id
    
    confirmed_task_id = confirmed_pointer.get("current_task")
    if str(confirmed_task_id) != str(new_task_id):
        print(f"ERROR: Pointer update failed - expected {new_task_id}, got {confirmed_task_id}")
        return False, current_task_id
    
    return True, new_task_id


def main() -> int:
    """Main auto-advance protocol"""
    project_root = pathlib.Path(".").resolve()
    
    # Load required files
    plan_path = project_root / "6_ai_runtime_context" / "ACTIVE_PLAN.yaml"
    pointer_path = project_root / "6_ai_runtime_context" / "ACTIVE_TASK_POINTER.yaml"
    intent_path = project_root / "6_ai_runtime_context" / "INTENT_DECLARATION.json"
    
    plan = load_yaml(plan_path)
    pointer = load_yaml(pointer_path)
    intent = load_json(intent_path) if intent_path.exists() else None
    
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
    
    # Step 1: Run Task Completion Gate
    print(f"[auto-advance] Running completion gate for task {current_task_id}...")
    gate_success, gate_results, completion_report_path = run_completion_gate()
    
    if not gate_success:
        print("[auto-advance] ❌ Completion gate failed. State advancement blocked.")
        return 1
    
    # Step 2: Determine next task
    tasks = plan.get("tasks", [])
    current_idx = None
    for idx, task in enumerate(tasks):
        if str(task.get("id")) == str(current_task_id):
            current_idx = idx
            break
    
    if current_idx is None:
        print(f"ERROR: Task {current_task_id} not found in plan")
        return 1
    
    if current_idx + 1 >= len(tasks):
        print(f"INFO: Task {current_task_id} is the last task. Plan complete.")
        return 0
    
    next_task = tasks[current_idx + 1]
    next_task_id = next_task.get("id")
    
    # Step 3: Append state transition event
    print(f"[auto-advance] Logging transition: task {current_task_id} -> {next_task_id}...")
    intent_id = intent.get("intent_id") if intent else None
    actor = intent.get("actor", "cursor_ai") if intent else "cursor_ai"
    
    transition_success = append_transition_event(
        plan=plan,
        from_task=current_task_id,
        to_task=next_task_id,
        actor=actor,
        intent_id=intent_id,
        completion_report_path=completion_report_path,
        gate_results=gate_results
    )
    
    if not transition_success:
        print("[auto-advance] ❌ Failed to log transition. State advancement blocked.")
        return 1
    
    # Step 4: Update ACTIVE_TASK_POINTER.yaml
    print(f"[auto-advance] Updating pointer: {current_task_id} -> {next_task_id}...")
    advance_success, confirmed_task_id = advance_pointer(pointer_path, current_task_id, tasks)
    
    if not advance_success:
        print("[auto-advance] ❌ Failed to update pointer. State advancement blocked.")
        return 1
    
    print(f"[auto-advance] ✅ State advanced successfully: task {current_task_id} -> {confirmed_task_id}")
    print(f"[auto-advance] Completion report: {completion_report_path}")
    print(f"[auto-advance] Transition logged to state_transition_log.jsonl")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

