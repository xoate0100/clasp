#!/usr/bin/env python3
"""Migration script for v2.2.0 — optional in-project agentic tools."""

import pathlib
import subprocess
import sys
from typing import Tuple


def migrate_to_2_2_0(project_root: pathlib.Path) -> Tuple[bool, str]:
    notes = []

    required = [
        "5_reference_architectures/OPTIONAL_AGENTIC_TOOLS.yaml",
        "5_reference_architectures/KNOWLEDGE_SOURCES.yaml",
        "3_bootstrap_scripts/agentic_tools.py",
        "3_bootstrap_scripts/governance_drift_validate.py",
        "3_bootstrap_scripts/reference_validate.py",
        "3_bootstrap_scripts/agentic_janitor.py",
        "agentic/optional_tools.py",
        "agentic/janitor.py",
        "docs/DOC_MANIFEST.yaml",
    ]
    missing = [rel for rel in required if not (project_root / rel).exists()]
    if missing:
        return False, f"Missing optional tool files: {', '.join(missing)}"

    (project_root / "docs" / "archive").mkdir(parents=True, exist_ok=True)
    archive_readme = project_root / "docs" / "archive" / "README.md"
    if not archive_readme.exists():
        archive_readme.write_text(
            "# Documentation Archive\n\n"
            "<!-- AUTO-GENERATED ARCHIVE TABLE START -->\n"
            "| Archived doc | Date | Superseded by |\n|-------------|------|----------------|\n"
            "| *(none yet)* | — | — |\n"
            "<!-- AUTO-GENERATED ARCHIVE TABLE END -->\n",
            encoding="utf-8",
        )
        notes.append("created docs/archive/README.md")

    index_dir = project_root / "6_ai_runtime_context" / "knowledge_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    flags_path = project_root / "0_phase0_bootstrap" / "feature_flags.yml"
    if flags_path.exists():
        try:
            import yaml

            with open(flags_path, "r", encoding="utf-8") as handle:
                flags = yaml.safe_load(handle) or {}
            agentic = flags.setdefault("agentic", {})
            optional = agentic.setdefault("optional_tools", {})
            defaults = {
                "knowledge_index": True,
                "doc_lifecycle": True,
                "janitor": True,
                "governance_drift_validator": True,
                "reference_validator": True,
            }
            for tool_id, enabled in defaults.items():
                if tool_id not in optional:
                    optional[tool_id] = {"enabled": enabled}
            with open(flags_path, "w", encoding="utf-8") as handle:
                yaml.dump(flags, handle, default_flow_style=False, sort_keys=False)
            notes.append("optional_tools defaults applied to feature_flags.yml")
        except Exception as exc:
            notes.append(f"WARN: feature_flags update failed: {exc}")

    generate_script = project_root / "3_bootstrap_scripts" / "generate_ai_context.py"
    if generate_script.exists():
        subprocess.run([sys.executable, str(generate_script)], cwd=str(project_root), check=False)
        notes.append("AI_CONTEXT.md regenerated with content fingerprint")

    version_file = project_root / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    if version_file.exists():
        try:
            import yaml

            with open(version_file, "r", encoding="utf-8") as handle:
                manifest = yaml.safe_load(handle) or {}
            features = manifest.setdefault("features", {})
            for key in (
                "optional_agentic_tools",
                "knowledge_index",
                "doc_lifecycle",
                "janitor",
                "governance_drift_validator",
                "reference_validator",
            ):
                features[key] = True
            with open(version_file, "w", encoding="utf-8") as handle:
                yaml.dump(manifest, handle, default_flow_style=False, sort_keys=False)
            notes.append("version manifest updated with v2.2.0 features")
        except Exception as exc:
            return False, f"Failed to update version manifest: {exc}"

    return True, "; ".join(notes) if notes else "Migration to v2.2.0 completed"


MIGRATIONS = {"2.2.0": migrate_to_2_2_0}
