#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script for v2.1.0
Installs agentic coordination: decision registry, drift vectors, agent graph, run log.
"""

import pathlib
import subprocess
import sys
from typing import Tuple


def migrate_to_2_1_0(project_root: pathlib.Path) -> Tuple[bool, str]:
    """Migrate project to version 2.1.0."""
    notes = []

    # Ensure runtime directories exist
    runtime_dir = project_root / "6_ai_runtime_context"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    run_log = runtime_dir / "AGENTIC_RUN_LOG.yaml"
    if not run_log.exists():
        run_log.write_text("version: 1\nruns: []\n", encoding="utf-8")
        notes.append("AGENTIC_RUN_LOG.yaml created")

    proposals_dir = project_root / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    graph_state = runtime_dir / "AGENT_GRAPH_STATE.yaml"
    if not graph_state.exists():
        notes.append("AGENT_GRAPH_STATE.yaml will be created on first session-start")

    # Verify core agentic files (copied by template_update before migration runs)
    required = [
        "5_reference_architectures/DECISION_REGISTRY.yaml",
        "5_reference_architectures/AGENT_REGISTRY.yaml",
        "5_reference_architectures/DRIFT_VECTORS.yaml",
        "5_reference_architectures/WORKSPACE_SPINE_REGISTRY.yaml",
        "3_bootstrap_scripts/resurrection_scan.py",
        "3_bootstrap_scripts/agentic_coordinate_validate.py",
        "agentic/registry.py",
    ]
    missing = [rel for rel in required if not (project_root / rel).exists()]
    if missing:
        return False, f"Missing agentic files: {', '.join(missing)}"

    # Update feature flags if agentic section missing
    flags_path = project_root / "0_phase0_bootstrap" / "feature_flags.yml"
    if flags_path.exists():
        try:
            import yaml

            with open(flags_path, "r", encoding="utf-8") as handle:
                flags = yaml.safe_load(handle) or {}

            guardrails = flags.setdefault("ai_guardrails", {})
            if not guardrails.get("enforce_agentic_coordination"):
                guardrails["enforce_agentic_coordination"] = True
                notes.append("enabled enforce_agentic_coordination guardrail")

            perms = flags.setdefault("permissions", {})
            write_to = perms.setdefault("write_to", [])
            for path in ("agentic/", "proposals/"):
                if path not in write_to:
                    write_to.append(path)
                    notes.append(f"added {path} to permissions.write_to")

            if "agentic" not in flags:
                flags["agentic"] = {
                    "enabled": True,
                    "session_start": "3_bootstrap_scripts/agentic_session.py session-start",
                    "pre_commit_review": "3_bootstrap_scripts/agentic_session.py pre-commit-review",
                }
                notes.append("agentic section added to feature_flags.yml")

            with open(flags_path, "w", encoding="utf-8") as handle:
                yaml.dump(flags, handle, default_flow_style=False, sort_keys=False)
        except Exception as exc:
            notes.append(f"WARN: could not update feature_flags.yml: {exc}")

    # Regenerate AI context
    generate_script = project_root / "3_bootstrap_scripts" / "generate_ai_context.py"
    if generate_script.exists():
        result = subprocess.run(
            [sys.executable, str(generate_script)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            notes.append("AI_CONTEXT.md regenerated with agentic coordination section")
        else:
            notes.append(f"WARN: context regeneration failed: {result.stderr}")

    # Update version manifest features
    version_file = project_root / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    if version_file.exists():
        try:
            import yaml

            with open(version_file, "r", encoding="utf-8") as handle:
                manifest = yaml.safe_load(handle) or {}

            features = manifest.setdefault("features", {})
            features["agentic_coordination"] = True
            features["decision_registry"] = True
            features["resurrection_scan"] = True
            features["agent_role_graph"] = True
            features["structured_run_log"] = True
            features["workspace_spine_registry"] = True

            template_dirs = manifest.setdefault("template_directories", [])
            if "agentic/" not in template_dirs:
                template_dirs.append("agentic/")

            with open(version_file, "w", encoding="utf-8") as handle:
                yaml.dump(manifest, handle, default_flow_style=False, sort_keys=False)

            notes.append("version manifest updated with v2.1.0 features")
        except Exception as exc:
            return False, f"Failed to update version manifest: {exc}"

    return True, "; ".join(notes) if notes else "Migration to v2.1.0 completed successfully"


MIGRATIONS = {
    "2.1.0": migrate_to_2_1_0,
}


def get_migration(version: str):
    return MIGRATIONS.get(version)


def list_available_migrations() -> list[str]:
    return sorted(MIGRATIONS.keys())
