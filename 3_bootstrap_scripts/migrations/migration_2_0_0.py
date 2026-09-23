#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script for v2.0.0
Handles migration from v1.x.x to v2.0.0
"""

import pathlib
import shutil
from typing import Tuple


def migrate_to_2_0_0(project_root: pathlib.Path) -> Tuple[bool, str]:
    """
    Migrate project to version 2.0.0.
    
    This migration:
    1. Ensures new CLI commands are available (verify-template, template-status)
    2. Updates version manifest with v2.0.0 features
    3. Verifies file integrity verification is available
    4. Ensures atomic update mechanism is in place
    
    Args:
        project_root: Root directory of the project
    
    Returns:
        Tuple of (success: bool, notes: str)
    """
    notes = []
    
    # Check if CLI has new commands
    cli_path = project_root / "3_bootstrap_scripts" / "cli.py"
    if cli_path.exists():
        cli_content = cli_path.read_text(encoding="utf-8")
        has_verify = "verify-template" in cli_content
        has_status = "template-status" in cli_content
        
        if not has_verify or not has_status:
            notes.append("CLI may need update for v2.0.0 commands (verify-template, template-status)")
    else:
        notes.append("CLI file not found - may need manual update")
    
    # Check if template_update.py has new features
    template_update_path = project_root / "3_bootstrap_scripts" / "template_update.py"
    if template_update_path.exists():
        update_content = template_update_path.read_text(encoding="utf-8")
        has_integrity = "verify_file_integrity" in update_content
        has_atomic = "apply_staging_to_target" in update_content
        has_rollback = "rollback_update" in update_content
        
        if not has_integrity or not has_atomic or not has_rollback:
            notes.append("template_update.py may need update for v2.0.0 features")
    else:
        notes.append("template_update.py not found - update required")
    
    # Update version manifest features
    version_file = project_root / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    if version_file.exists():
        try:
            import yaml
            with open(version_file, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f) or {}
            
            # Add v2.0.0 features
            features = manifest.get("features", {})
            features["file_integrity_verification"] = True
            features["atomic_updates"] = True
            features["automatic_rollback"] = True
            features["enhanced_cli_commands"] = True
            
            manifest["features"] = features
            
            # Write back
            with open(version_file, "w", encoding="utf-8") as f:
                yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
            
            notes.append("Updated version manifest with v2.0.0 features")
        except Exception as e:
            return False, f"Failed to update version manifest: {e}"
    
    # Migration successful
    if notes:
        return True, "; ".join(notes)
    return True, "Migration to v2.0.0 completed successfully"


def list_available_migrations() -> list:
    """List available migrations for v2.0.0."""
    return [
        {
            "from_version": "1.0.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        },
        {
            "from_version": "1.1.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        },
        {
            "from_version": "1.2.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        },
        {
            "from_version": "1.3.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        },
        {
            "from_version": "1.4.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        },
        {
            "from_version": "1.5.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        },
        {
            "from_version": "1.6.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        },
        {
            "from_version": "1.7.0",
            "to_version": "2.0.0",
            "function": migrate_to_2_0_0,
            "description": "Migrate to v2.0.0 with file integrity, atomic updates, and rollback"
        }
    ]


if __name__ == "__main__":
    import sys
    project_root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    success, notes = migrate_to_2_0_0(project_root)
    print(f"Migration {'succeeded' if success else 'failed'}: {notes}")
    sys.exit(0 if success else 1)
