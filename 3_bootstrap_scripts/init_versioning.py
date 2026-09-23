#!/usr/bin/env python3
"""
Standalone script to initialize versioning for pre-versioned projects.

This script solves the chicken-and-egg problem where template_update.py
doesn't exist in pre-versioned projects but is needed to initialize versioning.

Usage:
    python3 3_bootstrap_scripts/init_versioning.py [--template-repo URL]

This script:
1. Detects if project is pre-versioned (no META_FRAMEWORK_VERSION.yaml)
2. Detects or prompts for template repository URL
3. Creates initial version manifest (version 1.0.0)
4. Does NOT require template_update.py to exist
"""

import argparse
import pathlib
import subprocess
import sys
from datetime import datetime
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: Missing dependency: yaml")
    print("Install with: pip install pyyaml")
    sys.exit(1)


VERSION_FILE = pathlib.Path("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")


def detect_pre_versioned_project() -> bool:
    """Detect if this is a pre-versioned project (no META_FRAMEWORK_VERSION.yaml)."""
    return not VERSION_FILE.exists()


def detect_template_repo() -> Optional[str]:
    """Try to detect template repository URL from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def initialize_version_manifest(template_repo: str, version: str = "1.0.0") -> dict:
    """Create initial version manifest for pre-versioned projects."""
    return {
        "template_version": version,
        "template_repo": template_repo,
        "installed_at": datetime.utcnow().isoformat() + "Z",
        "last_updated_at": None,
        "update_history": [],
        "features": {
            "dynamic_layout_adaptation": pathlib.Path("3_bootstrap_scripts/layout_adaptor.py").exists(),
            "guided_initialization": pathlib.Path("3_bootstrap_scripts/init_wizard.py").exists(),
            "dynamic_ai_context": pathlib.Path("3_bootstrap_scripts/generate_ai_context.py").exists(),
            "template_versioning": True,  # Being initialized now
            "drift_detection": pathlib.Path("scripts/meta_framework_drift_check.py").exists(),
        },
        "template_directories": [
            "0_phase0_bootstrap/",
            "1_global_standards/",
            "2_framework_templates/",
            "3_bootstrap_scripts/",
            "5_reference_architectures/",
            "7_schemas/",
            "8_ci/",
        ],
        "protected_files": [
            "0_phase0_bootstrap/MVP_SPECIFICATION.yaml",
            "0_phase0_bootstrap/feature_flags.yml",
        ],
        "project_directories": [
            "4_docs_index/",
            "6_ai_runtime_context/",
            "frontend/",
            "backend/",
            "shared/",
            "apps/",
            "packages/",
            "docs/",
        ],
    }


def save_version_manifest(manifest: dict) -> bool:
    """Save the version manifest."""
    try:
        VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save version manifest: {e}")
        return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="init_versioning.py",
        description="Initialize version tracking for pre-versioned projects",
    )
    parser.add_argument(
        "--template-repo",
        default="",
        help="Template repository URL (default: detect from git remote or prompt)",
    )
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="Initial version to set (default: 1.0.0)",
    )

    args = parser.parse_args(argv)

    # Check if already versioned
    if not detect_pre_versioned_project():
        print("INFO: Project already has version tracking initialized.")
        print(f"     Version manifest: {VERSION_FILE}")
        return 0

    print("Initializing version tracking for pre-versioned project...")

    # Get template repo URL
    template_repo = args.template_repo
    if not template_repo:
        detected = detect_template_repo()
        if detected:
            print(f"Detected git remote: {detected}")
            print("If this is not your template repository, specify --template-repo")
            response = input("Use this as template repository? [Y/n]: ").strip().lower()
            if response in ("", "y", "yes"):
                template_repo = detected
            else:
                template_repo = input("Enter template repository URL: ").strip()
        else:
            template_repo = input("Enter template repository URL: ").strip()

    if not template_repo:
        print("ERROR: Template repository URL required")
        return 1

    # Create version manifest
    manifest = initialize_version_manifest(template_repo, args.version)
    if not save_version_manifest(manifest):
        return 1

    print(f"OK: Version tracking initialized (version {args.version})")
    print(f"     Template repository: {template_repo}")
    print(f"     Version manifest: {VERSION_FILE}")
    print("\nNext steps:")
    print("  1. Verify CLI has update-template command:")
    print("     python3 3_bootstrap_scripts/cli.py update-template --help")
    print("  2. Run first update (dry-run):")
    print("     python3 3_bootstrap_scripts/cli.py update-template --dry-run")
    print("  3. Apply updates:")
    print("     python3 3_bootstrap_scripts/cli.py update-template")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
