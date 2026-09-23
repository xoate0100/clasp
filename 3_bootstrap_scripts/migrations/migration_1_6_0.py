"""
Migration to version 1.6.0: DSKB + Intent Declaration Contracts Installation
This migration installs governance enforcement and intent declaration contracts.
"""

import pathlib
import json
import shutil
from typing import Dict, Any, Tuple

try:
    import yaml
except ImportError:
    yaml = None


def migrate_to_1_6_0(project_root: pathlib.Path) -> Tuple[bool, str]:
    """
    Migrate to version 1.6.0.
    Installs:
    - Governance section in AI_CONTEXT.md generation
    - Governance presence check
    - Intent declaration contract schema and template
    - Intent enforcement guardrail
    Returns (success, notes).
    """
    notes = []
    errors = []

    # 1. Ensure constitution file exists
    constitution_path = project_root / "1_global_standards" / "AI_OPERATING_CONSTITUTION.md"
    if not constitution_path.exists():
        errors.append(f"AI_OPERATING_CONSTITUTION.md missing at {constitution_path}")
        notes.append("WARN: Constitution file not found - may need manual installation")
    else:
        notes.append("Constitution file verified")

    # 2. Ensure intent declaration schema exists
    schema_path = project_root / "7_schemas" / "intent_declaration.schema.json"
    if not schema_path.exists():
        # Create schema directory if needed
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        # Schema should be copied by template_update.py, but we verify it exists
        notes.append("Intent declaration schema will be installed by template update")
    else:
        notes.append("Intent declaration schema verified")

    # 3. Ensure intent declaration template exists (only if absent - protected)
    intent_template_path = project_root / "6_ai_runtime_context" / "INTENT_DECLARATION.json"
    if not intent_template_path.exists():
        # Create runtime context directory if needed
        intent_template_path.parent.mkdir(parents=True, exist_ok=True)
        # Create template (only if absent - this is a runtime file)
        template_content = {
            "intent_id": "template-placeholder",
            "timestamp": "2026-01-08T00:00:00Z",
            "actor": "cursor_ai",
            "plan_id": "",
            "component": "",
            "task_id": 0,
            "intended_changes": [
                {
                    "path": "example/path/to/file.ext",
                    "change_type": "create",
                    "notes": "Example change - replace with actual intent"
                }
            ],
            "expected_outputs": [],
            "permissions_checked": False,
            "state_files_read": [
                "6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml",
                "6_ai_runtime_context/ACTIVE_PLAN.yaml"
            ],
            "notes": "This is a template. Replace with actual intent declaration before committing changes."
        }
        try:
            with open(intent_template_path, "w", encoding="utf-8") as f:
                json.dump(template_content, f, indent=2)
            notes.append("Intent declaration template created")
        except Exception as e:
            errors.append(f"Failed to create intent template: {e}")
    else:
        notes.append("Intent declaration template already exists (preserved)")

    # 4. Update feature flags to enable intent declaration guardrail
    feature_flags_path = project_root / "0_phase0_bootstrap" / "feature_flags.yml"
    if feature_flags_path.exists() and yaml:
        try:
            with open(feature_flags_path, "r", encoding="utf-8") as f:
                flags = yaml.safe_load(f) or {}
            
            # Ensure ai_guardrails section exists
            if "ai_guardrails" not in flags:
                flags["ai_guardrails"] = {}
            
            # Enable intent declaration guardrail if not already set
            if "enforce_intent_declaration" not in flags["ai_guardrails"]:
                flags["ai_guardrails"]["enforce_intent_declaration"] = True
                notes.append("Enabled enforce_intent_declaration guardrail")
            else:
                notes.append("Intent declaration guardrail already configured")
            
            # Write back (only if we made changes)
            with open(feature_flags_path, "w", encoding="utf-8") as f:
                yaml.dump(flags, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            errors.append(f"Failed to update feature flags: {e}")
    else:
        notes.append("Feature flags file not found or YAML not available - manual update may be needed")

    # 5. Regenerate AI_CONTEXT.md to include Governance section
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
            notes.append("AI_CONTEXT.md regenerated with Governance section")
        else:
            notes.append(f"WARN: Failed to regenerate context: {result.stderr}")
    else:
        notes.append("WARN: Context generator script not found")

    # 6. Verify pre-commit config includes governance check (template should handle this)
    precommit_path = project_root / ".pre-commit-config.yaml"
    if precommit_path.exists():
        precommit_content = precommit_path.read_text(encoding="utf-8")
        if "check-governance-install" not in precommit_content:
            notes.append("WARN: Pre-commit config may need manual update for governance check")
        else:
            notes.append("Pre-commit config verified")

    if errors:
        return False, "; ".join(errors)
    
    return True, "; ".join(notes)


# Migration registry
MIGRATIONS = {
    "1.6.0": migrate_to_1_6_0,
}


def get_migration(version: str):
    """Get migration function for a version."""
    return MIGRATIONS.get(version)


def list_available_migrations() -> list[str]:
    """List all available migration versions."""
    return sorted(MIGRATIONS.keys())

