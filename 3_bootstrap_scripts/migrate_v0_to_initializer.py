#!/usr/bin/env python3
"""
v0 → project_initializer Migration Tool
Migrates a v0.dev project to project_initializer structure.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)


def detect_v0_project(project_path: Path) -> bool:
    """Detect if a project is a v0 project."""
    indicators = [
        project_path / "app",
        project_path / "components",
        project_path / "package.json",
        project_path / "next.config.js",
    ]
    
    # Check for v0-specific patterns
    has_app_dir = (project_path / "app").exists()
    has_components = (project_path / "components").exists()
    
    # Check package.json for v0 patterns
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                package_data = json.load(f)
                # v0 projects often have specific dependencies
                deps = package_data.get("dependencies", {})
                if "next" in deps and "react" in deps:
                    return True
        except Exception:
            pass
    
    return has_app_dir and has_components


def read_v0_project_info(project_path: Path) -> Dict[str, Any]:
    """Extract information from v0 project."""
    info = {
        "name": project_path.name,
        "has_app_dir": (project_path / "app").exists(),
        "has_components": (project_path / "components").exists(),
        "has_lib": (project_path / "lib").exists(),
        "has_public": (project_path / "public").exists(),
        "framework": "Next.js",
        "language": "TypeScript",
    }
    
    # Read package.json
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                package_data = json.load(f)
                info["package_json"] = package_data
                info["dependencies"] = package_data.get("dependencies", {})
        except Exception:
            pass
    
    # Check for Vercel config
    vercel_json = project_path / "vercel.json"
    if vercel_json.exists():
        try:
            with open(vercel_json, "r", encoding="utf-8") as f:
                info["vercel_config"] = json.load(f)
        except Exception:
            pass
    
    return info


def create_initializer_structure(project_path: Path, v0_info: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Create project_initializer structure in v0 project."""
    changes = {
        "created": [],
        "modified": [],
        "skipped": [],
    }
    
    # Create directory structure
    directories = [
        "0_phase0_bootstrap",
        "1_global_standards",
        "2_framework_templates",
        "3_bootstrap_scripts",
        "4_docs_index",
        "5_reference_architectures",
        "6_ai_runtime_context",
        "7_schemas",
        "8_ci",
    ]
    
    for dir_name in directories:
        dir_path = project_path / dir_name
        if not dir_path.exists():
            if not dry_run:
                dir_path.mkdir(parents=True, exist_ok=True)
            changes["created"].append(str(dir_path))
        else:
            changes["skipped"].append(str(dir_path))
    
    # Create MVP_SPECIFICATION.yaml from v0 info
    mvp_spec_path = project_path / "0_phase0_bootstrap" / "MVP_SPECIFICATION.yaml"
    if not mvp_spec_path.exists():
        mvp_spec = generate_mvp_spec(v0_info)
        if not dry_run:
            with open(mvp_spec_path, "w", encoding="utf-8") as f:
                yaml.dump(mvp_spec, f, default_flow_style=False, sort_keys=False)
        changes["created"].append(str(mvp_spec_path))
    
    # Create META_FRAMEWORK_VERSION.yaml
    version_path = project_path / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    if not version_path.exists():
        version_manifest = {
            "template_version": "1.5.0",
            "template_repo": "https://github.com/xoate0100/project_initializer.git",
            "installed_at": datetime.utcnow().isoformat() + "Z",
            "last_updated_at": None,
            "update_history": [],
            "features": {
                "v0_integration": True,
                "vercel_deployment": True,
            },
        }
        if not dry_run:
            with open(version_path, "w", encoding="utf-8") as f:
                yaml.dump(version_manifest, f, default_flow_style=False)
        changes["created"].append(str(version_path))
    
    # Create .gitignore additions
    gitignore_path = project_path / ".gitignore"
    gitignore_additions = [
        "",
        "# project_initializer",
        ".vercel",
        "vercel_deployments.json",
        "6_ai_runtime_context/ai_feedback_log.json",
    ]
    
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing = f.read()
        
        needs_update = any(addition not in existing for addition in gitignore_additions[1:])
        if needs_update:
            if not dry_run:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\n" + "\n".join(gitignore_additions))
            changes["modified"].append(str(gitignore_path))
    
    return changes


def generate_mvp_spec(v0_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generate MVP_SPECIFICATION.yaml from v0 project info."""
    return {
        "Project": v0_info["name"],
        "Maturity": "L2.5",
        "Architecture": "Single Vercel App with App Router",
        "Repo_Type": "frontend",
        "Execution_Mode": "Controlled Agentic Execution",
        "GOALS_AND_PRINCIPLES": {
            "goals": [
                "Maintain v0.dev workflow",
                "Add project_initializer standards",
                "Enable automated updates",
            ],
            "principles": [
                "v0-first development",
                "TypeScript for type safety",
                "Component-based architecture",
            ],
        },
        "TECH_STACK": {
            "frontend": {
                "framework": "Next.js",
                "version": "14",
                "language": "TypeScript",
                "styling": ["TailwindCSS"],
                "ui_generation": "v0.dev",
            },
            "deployment": {
                "provider": "Vercel",
                "serverless": True,
            },
        },
        "MONOREPO_LAYOUT": {
            "root": {
                "files": [".env.local", "package.json", "next.config.js"],
            },
            "app": {
                "directories": ["app/", "components/", "lib/", "public/"],
            },
        },
        "DEPLOYMENT": {
            "provider": "Vercel",
            "preview": True,
        },
        "MIGRATION_PATH": {
            "from_v0": True,
            "v0_project_name": v0_info["name"],
            "migration_date": datetime.utcnow().isoformat() + "Z",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="migrate_v0_to_initializer.py",
        description="Migrate v0.dev project to project_initializer structure",
    )
    parser.add_argument(
        "project_path",
        help="Path to v0 project directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if project_initializer structure exists",
    )
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    
    if not project_path.exists():
        print(f"ERROR: Project path does not exist: {project_path}")
        return 1
    
    if not project_path.is_dir():
        print(f"ERROR: Project path is not a directory: {project_path}")
        return 1
    
    # Detect v0 project
    if not detect_v0_project(project_path):
        print(f"WARN: This doesn't appear to be a v0 project.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            return 1
    
    print(f"Migrating v0 project: {project_path.name}")
    print()
    
    # Read v0 project info
    print("Analyzing v0 project...")
    v0_info = read_v0_project_info(project_path)
    print(f"  Framework: {v0_info['framework']}")
    print(f"  Language: {v0_info['language']}")
    print(f"  Has app/ directory: {v0_info['has_app_dir']}")
    print(f"  Has components/ directory: {v0_info['has_components']}")
    print()
    
    # Check if already migrated
    if (project_path / "0_phase0_bootstrap").exists() and not args.force:
        print("ERROR: Project appears to already have project_initializer structure.")
        print("Use --force to migrate anyway.")
        return 1
    
    # Create structure
    if args.dry_run:
        print("DRY RUN: Would create the following:")
    else:
        print("Creating project_initializer structure...")
    
    changes = create_initializer_structure(project_path, v0_info, dry_run=args.dry_run)
    
    print()
    print("Changes:")
    print(f"  Created: {len(changes['created'])}")
    print(f"  Modified: {len(changes['modified'])}")
    print(f"  Skipped: {len(changes['skipped'])}")
    
    if changes["created"]:
        print()
        print("Created files/directories:")
        for item in changes["created"]:
            print(f"  - {item}")
    
    if changes["modified"]:
        print()
        print("Modified files:")
        for item in changes["modified"]:
            print(f"  - {item}")
    
    if not args.dry_run:
        print()
        print("Migration complete!")
        print("Next steps:")
        print("  1. Review MVP_SPECIFICATION.yaml")
        print("  2. Run: python3 3_bootstrap_scripts/cli.py init")
        print("  3. Configure Vercel deployment if needed")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

