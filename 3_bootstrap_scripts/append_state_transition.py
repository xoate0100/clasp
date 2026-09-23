#!/usr/bin/env python3
"""
State Transition Logger - Append-only audit trail for state transitions.

Appends JSONL events to state_transition_log.jsonl when tasks are completed
and state is advanced.
"""
import sys
import pathlib
import json
import uuid
from datetime import datetime
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


def get_commit_hash() -> Optional[str]:
    """Get current commit hash if available"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def append_transition(
    plan_id: str,
    component: str,
    from_task: int,
    to_task: int,
    actor: str,
    intent_id: Optional[str] = None,
    completion_report_path: Optional[str] = None,
    gate_results: Optional[list] = None,
    notes: Optional[str] = None
) -> bool:
    """
    Append a state transition event to the log.
    
    Args:
        plan_id: Plan ID from ACTIVE_PLAN.yaml
        component: Component name
        from_task: Task ID being completed
        to_task: Task ID being started
        actor: "cursor_ai" or "human"
        intent_id: Intent ID from INTENT_DECLARATION.json
        completion_report_path: Path to completion report
        gate_results: List of gate check results
        notes: Optional notes
    
    Returns:
        True if successful, False otherwise
    """
    project_root = pathlib.Path(".").resolve()
    log_path = project_root / "6_ai_runtime_context" / "state_transition_log.jsonl"
    
    # Ensure directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create transition event
    transition_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    commit_hash = get_commit_hash()
    
    event = {
        "transition_id": transition_id,
        "timestamp": timestamp,
        "plan_id": plan_id,
        "component": component,
        "from_task": from_task,
        "to_task": to_task,
        "actor": actor,
        "intent_id": intent_id,
        "completion_report_path": completion_report_path,
        "gate_results": gate_results or [],
        "commit_hash": commit_hash,
        "notes": notes
    }
    
    # Append to log (JSONL format - one JSON object per line)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        print(f"[transition-log] Appended transition {transition_id}: task {from_task} -> {to_task}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to append transition: {e}")
        return False


def main() -> int:
    """CLI interface for appending transitions"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Append state transition event")
    parser.add_argument("--plan-id", required=True, help="Plan ID")
    parser.add_argument("--component", required=True, help="Component name")
    parser.add_argument("--from-task", type=int, required=True, help="Task ID being completed")
    parser.add_argument("--to-task", type=int, required=True, help="Task ID being started")
    parser.add_argument("--actor", required=True, choices=["cursor_ai", "human"], help="Actor")
    parser.add_argument("--intent-id", help="Intent ID from INTENT_DECLARATION.json")
    parser.add_argument("--completion-report", help="Path to completion report")
    parser.add_argument("--gate-results", help="JSON string of gate results")
    parser.add_argument("--notes", help="Optional notes")
    
    args = parser.parse_args()
    
    gate_results = None
    if args.gate_results:
        try:
            gate_results = json.loads(args.gate_results)
        except json.JSONDecodeError:
            print("ERROR: Invalid gate_results JSON")
            return 1
    
    success = append_transition(
        plan_id=args.plan_id,
        component=args.component,
        from_task=args.from_task,
        to_task=args.to_task,
        actor=args.actor,
        intent_id=args.intent_id,
        completion_report_path=args.completion_report,
        gate_results=gate_results,
        notes=args.notes
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

