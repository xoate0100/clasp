"""
Migration to version 1.0.0: Initial template versioning system
This migration initializes version tracking for pre-versioned projects.
"""

import pathlib
from typing import Dict, Any, Tuple


def migrate_to_1_0_0(project_root: pathlib.Path) -> Tuple[bool, str]:
    """
    Migrate to version 1.0.0.
    Returns (success, notes).
    """
    notes = []

    # Ensure version file exists (should be created by template_update.py)
    version_file = project_root / "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml"
    if not version_file.exists():
        notes.append("Version manifest will be created during update")

    # Check for deprecated files or patterns
    # Example: If there were old config files, migrate them here

    # Update feature flags if needed
    feature_flags_file = project_root / "0_phase0_bootstrap/feature_flags.yml"
    if feature_flags_file.exists():
        # Could add feature flag migrations here if needed
        pass

    return True, "; ".join(notes) if notes else "No migrations required for 1.0.0"


# Migration registry
MIGRATIONS = {
    "1.0.0": migrate_to_1_0_0,
}


def get_migration(version: str):
    """Get migration function for a version."""
    return MIGRATIONS.get(version)


def list_available_migrations() -> list[str]:
    """List all available migration versions."""
    return sorted(MIGRATIONS.keys())

