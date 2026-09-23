"""
Migration to version 1.7.0: Auto-Advance State with Completion Gate + Transition Log
This migration installs governed state advancement with completion gates and audit logging.
"""

import pathlib
import json
from typing import Dict, Any, Tuple

try:
    import yaml
except ImportError:
    yaml = None


def migrate_to_1_7_0(project_root: pathlib.Path) -> Tuple[bool, str]:
    """
    Migrate to version 1.7.0.
    Installs:
    - Task completion gate system
    - State transition logging
    - Auto-advance protocol
    Returns (success, notes).
    """
    notes = []
    errors = []

    # 1. Ensure completion reports directory exists
    reports_dir = project_root / "6_ai_runtime_context" / "TASK_COMPLETION_REPORTS"
    reports_dir.mkdir(parents=True, exist_ok=True)
    notes.append("TASK_COMPLETION_REPORTS directory created")

    # 2. Ensure state transition log exists (empty is OK)
    log_path = project_root / "6_ai_runtime_context" / "state_transition_log.jsonl"
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Create empty log file
        log_path.write_text("", encoding="utf-8")
        notes.append("state_transition_log.jsonl created")
    else:
        notes.append("state_transition_log.jsonl already exists")

    # 3. Verify scripts exist (should be copied by template_update.py)
    required_scripts = [
        "task_completion_gate.py",
        "append_state_transition.py",
        "auto_advance_state.py",
        "check_state_transition.py"
    ]
    
    scripts_dir = project_root / "3_bootstrap_scripts"
    for script_name in required_scripts:
        script_path = scripts_dir / script_name
        if script_path.exists():
            notes.append(f"{script_name} verified")
        else:
            errors.append(f"{script_name} missing - will be installed by template update")

    # 4. Verify schema exists
    schema_path = project_root / "7_schemas" / "state_transition_log.schema.json"
    if schema_path.exists():
        notes.append("state_transition_log.schema.json verified")
    else:
        errors.append("state_transition_log.schema.json missing - will be installed by template update")

    # 5. Update feature flags if needed (no new flags required, but verify structure)
    feature_flags_path = project_root / "0_phase0_bootstrap" / "feature_flags.yml"
    if feature_flags_path.exists() and yaml:
        try:
            with open(feature_flags_path, "r", encoding="utf-8") as f:
                flags = yaml.safe_load(f) or {}
            notes.append("Feature flags structure verified")
        except Exception as e:
            errors.append(f"Failed to read feature flags: {e}")
    else:
        notes.append("Feature flags file not found or YAML not available")

    # 6. Regenerate AI_CONTEXT.md to include auto-advance protocol
    generate_script = project_root / "3_bootstrap_scripts" / "generate_ai_context.py"
    if generate_script.exists():
        import subprocess
        result = subprocess.run(
            ["python3", str(generate_script)],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            notes.append("AI_CONTEXT.md regenerated with auto-advance protocol")
        else:
            notes.append(f"WARN: Failed to regenerate context: {result.stderr}")
    else:
        notes.append("WARN: Context generator script not found")

    # 7. Verify pre-commit config includes new hooks (template should handle this)
    precommit_path = project_root / ".pre-commit-config.yaml"
    if precommit_path.exists():
        precommit_content = precommit_path.read_text(encoding="utf-8")
        if "task-completion-gate" not in precommit_content:
            notes.append("WARN: Pre-commit config may need manual update for task-completion-gate")
        if "check-state-transition" not in precommit_content:
            notes.append("WARN: Pre-commit config may need manual update for check-state-transition")
        if "task-completion-gate" in precommit_content and "check-state-transition" in precommit_content:
            notes.append("Pre-commit config verified")

    if errors:
        return False, "; ".join(errors)
    
    return True, "; ".join(notes)


# Migration registry
MIGRATIONS = {
    "1.7.0": migrate_to_1_7_0,
}


def get_migration(version: str):
    """Get migration function for a version."""
    return MIGRATIONS.get(version)


def list_available_migrations() -> list[str]:
    """List all available migration versions."""
    return sorted(MIGRATIONS.keys())

