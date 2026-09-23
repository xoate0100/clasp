#!/usr/bin/env python3
"""
Legacy Project Upgrade System
Upgrades existing projects (with no AI structure) to project_initializer format.
Designed to be AI-agent friendly, robust, and handle edge cases.
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)


UPGRADE_LOG = pathlib.Path("6_ai_runtime_context/LEGACY_UPGRADE_LOG.yaml")
BACKUP_BRANCH = "backup-before-upgrade"


def analyze_project() -> Dict[str, Any]:
    """
    Phase 1: Analyze project structure, framework, and dependencies.
    Returns analysis report.
    """
    analysis = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "is_legacy": False,
        "has_meta_framework": False,
        "framework": {},
        "structure": {},
        "dependencies": {},
        "conflicts": [],
        "edge_cases": [],
    }

    root = pathlib.Path(".")

    # Check for meta-framework structure
    meta_framework_indicators = [
        "0_phase0_bootstrap",
        "META_FRAMEWORK_VERSION.yaml",
        "feature_flags.yml",
        "AI_SANDBOX_RULES.md",
    ]

    has_meta = any((root / indicator).exists() for indicator in meta_framework_indicators)
    analysis["has_meta_framework"] = has_meta
    analysis["is_legacy"] = not has_meta

    if not analysis["is_legacy"]:
        return analysis

    # Detect framework
    analysis["framework"] = detect_framework(root)

    # Analyze structure
    analysis["structure"] = analyze_structure(root, analysis["framework"])

    # Analyze dependencies
    analysis["dependencies"] = analyze_dependencies(root, analysis["framework"])

    # Detect edge cases
    analysis["edge_cases"] = detect_edge_cases(root, analysis)

    # Detect conflicts
    analysis["conflicts"] = detect_conflicts(root, analysis)

    return analysis


def detect_framework(root: pathlib.Path) -> Dict[str, Any]:
    """Detect project framework and architecture."""
    framework = {
        "type": "unknown",
        "languages": [],
        "build_system": "unknown",
        "package_manager": "unknown",
        "indicators": [],
    }

    # Node.js/TypeScript detection
    if (root / "package.json").exists():
        try:
            with open(root / "package.json", "r", encoding="utf-8") as f:
                pkg = json.load(f)
                framework["package_manager"] = detect_package_manager(root)
                framework["languages"].append("javascript")
                if (root / "tsconfig.json").exists():
                    framework["languages"].append("typescript")
                
                # Framework detection
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    framework["type"] = "nextjs"
                    framework["indicators"].append("Next.js framework")
                elif "react" in deps:
                    framework["type"] = "react"
                    framework["indicators"].append("React framework")
                elif "vue" in deps:
                    framework["type"] = "vue"
                    framework["indicators"].append("Vue framework")
                elif "angular" in deps:
                    framework["type"] = "angular"
                    framework["indicators"].append("Angular framework")
                else:
                    framework["type"] = "nodejs"
                    framework["indicators"].append("Node.js project")
        except Exception:
            pass

    # Python detection
    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        framework["languages"].append("python")
        if (root / "requirements.txt").exists():
            framework["indicators"].append("Python (requirements.txt)")
        if (root / "pyproject.toml").exists():
            framework["indicators"].append("Python (pyproject.toml)")
        
        # Framework detection
        if (root / "fastapi").exists() or any("fastapi" in str(f) for f in root.rglob("*.py")):
            framework["type"] = "fastapi" if framework["type"] == "unknown" else "mixed"
            framework["indicators"].append("FastAPI backend")
        elif (root / "django").exists() or (root / "manage.py").exists():
            framework["type"] = "django" if framework["type"] == "unknown" else "mixed"
            framework["indicators"].append("Django backend")
        elif framework["type"] == "unknown":
            framework["type"] = "python"
            framework["indicators"].append("Python project")

    # Build system detection
    if (root / "vite.config.js").exists() or (root / "vite.config.ts").exists():
        framework["build_system"] = "vite"
    elif (root / "webpack.config.js").exists():
        framework["build_system"] = "webpack"
    elif (root / "next.config.js").exists() or (root / "next.config.ts").exists():
        framework["build_system"] = "nextjs"
    elif (root / "Makefile").exists():
        framework["build_system"] = "make"
    elif (root / "setup.py").exists() or (root / "pyproject.toml").exists():
        framework["build_system"] = "python"

    return framework


def detect_package_manager(root: pathlib.Path) -> str:
    """Detect package manager (npm, yarn, pnpm)."""
    if (root / "yarn.lock").exists():
        return "yarn"
    elif (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    elif (root / "package-lock.json").exists():
        return "npm"
    return "npm"  # Default


def analyze_structure(root: pathlib.Path, framework: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze project directory structure."""
    structure = {
        "type": "unknown",  # monorepo, standard, custom
        "directories": {},
        "entry_points": [],
        "config_files": [],
    }

    # Common directory patterns
    dirs = [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]

    # Monorepo detection
    if "apps" in dirs or "packages" in dirs or "workspaces" in dirs:
        structure["type"] = "monorepo"
        structure["directories"]["apps"] = [d for d in dirs if d == "apps" or d.startswith("app-")]
        structure["directories"]["packages"] = [d for d in dirs if d == "packages" or d.startswith("pkg-")]
    elif "src" in dirs:
        structure["type"] = "standard"
        structure["directories"]["src"] = "src"
    elif "app" in dirs and framework.get("type") == "nextjs":
        structure["type"] = "nextjs_app_router"
        structure["directories"]["app"] = "app"
    elif "pages" in dirs and framework.get("type") == "nextjs":
        structure["type"] = "nextjs_pages_router"
        structure["directories"]["pages"] = "pages"
    else:
        structure["type"] = "custom"
        structure["directories"] = {d: d for d in dirs if not d.startswith(".")}

    # Find entry points
    entry_patterns = ["index.js", "index.ts", "index.tsx", "main.py", "app.py", "__main__.py"]
    for pattern in entry_patterns:
        for entry in root.rglob(pattern):
            if "node_modules" not in str(entry) and ".git" not in str(entry):
                structure["entry_points"].append(str(entry.relative_to(root)))

    # Find config files
    config_patterns = [
        "*.config.js", "*.config.ts", "*.config.json",
        "tsconfig.json", "jsconfig.json",
        ".env*", "docker-compose.yml", "Dockerfile",
    ]
    for pattern in config_patterns:
        for config in root.glob(pattern):
            if config.is_file():
                structure["config_files"].append(str(config.relative_to(root)))

    return structure


def analyze_dependencies(root: pathlib.Path, framework: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze project dependencies."""
    deps = {
        "node": {},
        "python": {},
        "other": [],
    }

    # Node.js dependencies
    if (root / "package.json").exists():
        try:
            with open(root / "package.json", "r", encoding="utf-8") as f:
                pkg = json.load(f)
                deps["node"] = {
                    "dependencies": pkg.get("dependencies", {}),
                    "devDependencies": pkg.get("devDependencies", {}),
                    "scripts": pkg.get("scripts", {}),
                }
        except Exception:
            pass

    # Python dependencies
    if (root / "requirements.txt").exists():
        try:
            with open(root / "requirements.txt", "r", encoding="utf-8") as f:
                deps["python"]["requirements"] = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception:
            pass

    if (root / "pyproject.toml").exists():
        deps["python"]["pyproject"] = True

    return deps


def detect_edge_cases(root: pathlib.Path, analysis: Dict[str, Any]) -> List[str]:
    """Detect edge cases that need special handling."""
    edge_cases = []

    # Monorepo
    if analysis["structure"].get("type") == "monorepo":
        edge_cases.append("MONOREPO: Multiple apps/packages structure")

    # Mixed languages
    if len(analysis["framework"].get("languages", [])) > 1:
        edge_cases.append("MIXED_LANGUAGES: Multiple languages detected")

    # Custom build system
    if analysis["framework"].get("build_system") == "make":
        edge_cases.append("CUSTOM_BUILD: Makefile-based build system")

    # Existing CI/CD
    if (root / ".github" / "workflows").exists() or (root / ".gitlab-ci.yml").exists():
        edge_cases.append("EXISTING_CI: CI/CD workflows already present")

    # Database migrations
    if any("migration" in str(p) for p in root.rglob("*")):
        edge_cases.append("DATABASE_MIGRATIONS: Migration files detected")

    # Environment configs
    if any(".env" in str(p.name) for p in root.glob(".env*")):
        edge_cases.append("ENV_CONFIGS: Environment configuration files")

    # Documentation structure
    if (root / "docs").exists() and (root / "docs").is_dir():
        edge_cases.append("EXISTING_DOCS: Documentation directory present")

    return edge_cases


def detect_conflicts(root: pathlib.Path, analysis: Dict[str, Any]) -> List[str]:
    """Detect potential conflicts with template structure."""
    conflicts = []

    template_dirs = [
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

    for template_dir in template_dirs:
        if (root / template_dir).exists():
            conflicts.append(f"CONFLICT: {template_dir}/ already exists")

    return conflicts


def generate_upgrade_plan(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 2: Generate upgrade plan based on analysis.
    """
    plan = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "analysis": analysis,
        "steps": [],
        "mappings": {},
        "preserved": [],
        "created": [],
        "migrated": [],
        "rollback_info": {},
    }

    if not analysis["is_legacy"]:
        plan["steps"].append({
            "action": "skip",
            "reason": "Project already has meta-framework structure",
        })
        return plan

    # Step 1: Create backup
    plan["steps"].append({
        "action": "backup",
        "description": "Create backup branch before upgrade",
        "command": f"git checkout -b {BACKUP_BRANCH}",
    })

    # Step 2: Map structure
    mappings = map_structure(analysis)
    plan["mappings"] = mappings

    # Step 3: Create meta-framework directories
    plan["steps"].append({
        "action": "create_directories",
        "description": "Create meta-framework directory structure",
        "directories": [
            "0_phase0_bootstrap",
            "1_global_standards",
            "2_framework_templates",
            "3_bootstrap_scripts",
            "4_docs_index",
            "5_reference_architectures",
            "6_ai_runtime_context",
            "7_schemas",
            "8_ci",
        ],
    })

    # Step 4: Generate MVP_SPECIFICATION.yaml
    plan["steps"].append({
        "action": "generate_mvp_spec",
        "description": "Generate MVP_SPECIFICATION.yaml from analysis",
        "based_on": analysis,
    })

    # Step 5: Initialize version tracking
    plan["steps"].append({
        "action": "init_versioning",
        "description": "Initialize version manifest",
    })

    # Step 6: Copy template files (if template repo available)
    plan["steps"].append({
        "action": "copy_template_files",
        "description": "Copy meta-framework files from template",
        "note": "Requires template repository URL",
    })

    # Step 7: Preserve existing structure
    plan["preserved"] = get_preserved_items(analysis)

    # Step 8: Handle edge cases
    for edge_case in analysis.get("edge_cases", []):
        plan["steps"].append({
            "action": "handle_edge_case",
            "edge_case": edge_case,
            "description": f"Handle edge case: {edge_case}",
        })

    return plan


def map_structure(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Map existing structure to template structure."""
    mappings = {
        "frontend": None,
        "backend": None,
        "shared": None,
        "apps": None,
        "packages": None,
    }

    structure = analysis.get("structure", {})
    framework = analysis.get("framework", {})
    structure_type = structure.get("type", "unknown")

    # Next.js App Router
    if structure_type == "nextjs_app_router":
        mappings["frontend"] = "app"  # Next.js app directory
        if (pathlib.Path(".") / "components").exists():
            mappings["frontend"] = "."

    # Next.js Pages Router
    elif structure_type == "nextjs_pages_router":
        mappings["frontend"] = "pages"
        if (pathlib.Path(".") / "components").exists():
            mappings["frontend"] = "."

    # Standard src structure
    elif structure_type == "standard":
        src_dir = structure.get("directories", {}).get("src")
        if src_dir:
            # Try to detect frontend/backend
            src_path = pathlib.Path(src_dir)
            if (src_path / "components").exists() or (src_path / "pages").exists():
                mappings["frontend"] = src_dir
            elif (src_path / "api").exists() or (src_path / "server").exists():
                mappings["backend"] = src_dir
            else:
                mappings["frontend"] = src_dir  # Default to frontend

    # Monorepo
    elif structure_type == "monorepo":
        mappings["apps"] = structure.get("directories", {}).get("apps", [])
        mappings["packages"] = structure.get("directories", {}).get("packages", [])

    # Python project
    elif framework.get("type") in ["python", "fastapi", "django"]:
        mappings["backend"] = "."

    # Custom - preserve as-is
    else:
        # Map common directories
        dirs = structure.get("directories", {})
        if "components" in dirs or "src" in dirs:
            mappings["frontend"] = dirs.get("components") or dirs.get("src")
        if "api" in dirs or "server" in dirs:
            mappings["backend"] = dirs.get("api") or dirs.get("server")

    return mappings


def get_preserved_items(analysis: Dict[str, Any]) -> List[str]:
    """Get list of items to preserve (never modify/delete)."""
    preserved = []

    # Preserve all existing code directories
    structure = analysis.get("structure", {})
    dirs = structure.get("directories", {})
    for dir_name in dirs.values():
        if isinstance(dir_name, str):
            preserved.append(dir_name)
        elif isinstance(dir_name, list):
            preserved.extend(dir_name)

    # Preserve config files
    config_files = structure.get("config_files", [])
    preserved.extend(config_files)

    # Preserve entry points
    entry_points = structure.get("entry_points", [])
    preserved.extend(entry_points)

    return preserved


def save_analysis(analysis: Dict[str, Any], filepath: pathlib.Path) -> bool:
    """Save analysis to file."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(analysis, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save analysis: {e}")
        return False


def execute_upgrade_plan(plan: Dict[str, Any], template_repo: str = "") -> bool:
    """Phase 3: Execute upgrade plan."""
    steps = plan.get("steps", [])
    analysis = plan.get("analysis", {})
    
    # Step 1: Create backup
    print("Step 1: Creating backup branch...")
    try:
        result = subprocess.run(
            ["git", "checkout", "-b", BACKUP_BRANCH],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("OK: Backup branch created")
            # Switch back to original branch
            subprocess.run(["git", "checkout", "-"], capture_output=True)
        else:
            print(f"WARN: Could not create backup branch: {result.stderr}")
            print("      Continuing anyway (backup may already exist)")
    except Exception as e:
        print(f"WARN: Backup creation failed: {e}")
        print("      Continuing anyway")

    # Step 2: Create meta-framework directories
    print("\nStep 2: Creating meta-framework directories...")
    meta_dirs = [
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
    
    for dir_name in meta_dirs:
        dir_path = pathlib.Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            # Create .gitkeep to ensure directory is tracked
            (dir_path / ".gitkeep").touch()
            print(f"  Created: {dir_name}/")
        else:
            print(f"  Exists: {dir_name}/ (preserved)")

    # Step 3: Generate MVP_SPECIFICATION.yaml
    print("\nStep 3: Generating MVP_SPECIFICATION.yaml...")
    mvp_spec = generate_mvp_specification(analysis, plan.get("mappings", {}))
    mvp_file = pathlib.Path("0_phase0_bootstrap/MVP_SPECIFICATION.yaml")
    try:
        with open(mvp_file, "w", encoding="utf-8") as f:
            yaml.dump(mvp_spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"OK: Generated {mvp_file}")
    except Exception as e:
        print(f"ERROR: Failed to generate MVP_SPECIFICATION.yaml: {e}")
        return False

    # Step 4: Initialize version tracking
    print("\nStep 4: Initializing version tracking...")
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        from template_update import initialize_version_manifest, save_version_manifest
        
        template_repo_url = template_repo or "https://github.com/xoate0100/project_initializer.git"
        manifest = initialize_version_manifest(template_repo_url, version="1.1.0")
        if save_version_manifest(manifest):
            print("OK: Version manifest initialized")
        else:
            print("WARN: Failed to initialize version manifest")
    except Exception as e:
        print(f"WARN: Version initialization failed: {e}")

    # Step 5: Copy template files (if template repo provided)
    if template_repo:
        print("\nStep 5: Copying template files...")
        try:
            from template_update import clone_template_to_temp, copy_template_files, get_template_directories, get_protected_files, load_version_manifest
            
            manifest = load_version_manifest()
            if manifest:
                template_dir = clone_template_to_temp(template_repo)
                if template_dir:
                    template_dirs = get_template_directories(manifest)
                    protected_files = get_protected_files(manifest)
                    updated, skipped = copy_template_files(
                        template_dir,
                        pathlib.Path("."),
                        template_dirs,
                        protected_files,
                        dry_run=False,
                    )
                    print(f"OK: Copied {len(updated)} template files")
                    shutil.rmtree(template_dir, ignore_errors=True)
        except Exception as e:
            print(f"WARN: Template file copy failed: {e}")
            print("      You can copy template files manually later")

    # Step 6: Handle edge cases
    print("\nStep 6: Handling edge cases...")
    edge_cases = analysis.get("edge_cases", [])
    for edge_case in edge_cases:
        print(f"  Edge case: {edge_case}")
        # Edge case handling is documented in AI instructions
        # Actual handling depends on specific case

    print("\nOK: Upgrade execution completed")
    return True


def validate_upgrade() -> bool:
    """Phase 4: Validate upgrade success."""
    issues = []
    
    # Check meta-framework structure
    required_dirs = [
        "0_phase0_bootstrap",
        "1_global_standards",
        "3_bootstrap_scripts",
        "6_ai_runtime_context",
        "7_schemas",
    ]
    
    for dir_name in required_dirs:
        if not pathlib.Path(dir_name).exists():
            issues.append(f"Missing directory: {dir_name}/")
    
    # Check required files
    required_files = [
        "0_phase0_bootstrap/MVP_SPECIFICATION.yaml",
        "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml",
        "0_phase0_bootstrap/feature_flags.yml",
    ]
    
    for file_name in required_files:
        if not pathlib.Path(file_name).exists():
            issues.append(f"Missing file: {file_name}")
    
    # Validate MVP_SPECIFICATION.yaml
    mvp_file = pathlib.Path("0_phase0_bootstrap/MVP_SPECIFICATION.yaml")
    if mvp_file.exists():
        try:
            with open(mvp_file, "r", encoding="utf-8") as f:
                mvp_spec = yaml.safe_load(f)
                if not mvp_spec.get("Project"):
                    issues.append("MVP_SPECIFICATION.yaml missing Project field")
                if not mvp_spec.get("PROJECT_LAYOUT"):
                    issues.append("MVP_SPECIFICATION.yaml missing PROJECT_LAYOUT")
        except Exception as e:
            issues.append(f"Invalid MVP_SPECIFICATION.yaml: {e}")
    
    # Validate version manifest
    version_file = pathlib.Path("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")
    if version_file.exists():
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
                if not manifest.get("template_version"):
                    issues.append("META_FRAMEWORK_VERSION.yaml missing template_version")
                if not manifest.get("template_repo"):
                    issues.append("META_FRAMEWORK_VERSION.yaml missing template_repo")
        except Exception as e:
            issues.append(f"Invalid META_FRAMEWORK_VERSION.yaml: {e}")
    
    # Report issues
    if issues:
        print("Validation Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("All validation checks passed:")
    print("  ✓ Meta-framework structure created")
    print("  ✓ Required files present")
    print("  ✓ Configuration files valid")
    print("  ✓ Version tracking initialized")
    
    return True


def generate_mvp_specification(analysis: Dict[str, Any], mappings: Dict[str, Any]) -> Dict[str, Any]:
    """Generate MVP_SPECIFICATION.yaml from analysis."""
    framework = analysis.get("framework", {})
    structure = analysis.get("structure", {})
    
    # Detect project name from git or directory
    project_name = "legacy-project"
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract repo name from URL
            if "/" in url:
                project_name = url.split("/")[-1].replace(".git", "")
    except Exception:
        project_name = pathlib.Path(".").absolute().name

    # Build MVP spec
    mvp_spec = {
        "Project": project_name,
        "Maturity": "L2.5",
        "Architecture": structure.get("type", "custom"),
        "Repo_Type": "monorepo" if structure.get("type") == "monorepo" else "standard",
        "Execution_Mode": "Controlled Agentic Execution",
        "GOALS_AND_PRINCIPLES": {
            "goals": [
                "Upgrade to project_initializer format",
                "Preserve existing functionality",
                "Enable AI-assisted development",
            ],
            "principles": [
                "Test-driven development",
                "Code quality through automation",
                "Documentation as code",
            ],
        },
        "TECH_STACK": {},
        "PROJECT_LAYOUT": {
            "adaptation": {
                "mode": "adopt_existing",
                "auto_apply": False,
            },
            "components": {},
        },
    }

    # Add tech stack
    if framework.get("type") in ["nextjs", "react", "vue", "angular", "nodejs"]:
        mvp_spec["TECH_STACK"]["frontend"] = {
            "framework": framework.get("type", "react"),
            "language": "typescript" if "typescript" in framework.get("languages", []) else "javascript",
        }
    
    if framework.get("type") in ["python", "fastapi", "django"]:
        mvp_spec["TECH_STACK"]["backend"] = {
            "framework": framework.get("type", "python"),
            "language": "python",
        }

    # Add component mappings
    if mappings.get("frontend"):
        mvp_spec["PROJECT_LAYOUT"]["components"]["frontend"] = {
            "directories": [mappings["frontend"]] if isinstance(mappings["frontend"], str) else mappings["frontend"],
        }
    
    if mappings.get("backend"):
        mvp_spec["PROJECT_LAYOUT"]["components"]["backend"] = {
            "directories": [mappings["backend"]] if isinstance(mappings["backend"], str) else mappings["backend"],
        }

    if mappings.get("apps") or mappings.get("packages"):
        # Monorepo structure
        if mappings.get("apps"):
            mvp_spec["PROJECT_LAYOUT"]["components"]["apps"] = {
                "directories": mappings["apps"] if isinstance(mappings["apps"], list) else [mappings["apps"]],
            }
        if mappings.get("packages"):
            mvp_spec["PROJECT_LAYOUT"]["components"]["packages"] = {
                "directories": mappings["packages"] if isinstance(mappings["packages"], list) else [mappings["packages"]],
            }

    return mvp_spec


def save_plan(plan: Dict[str, Any], filepath: pathlib.Path) -> bool:
    """Save upgrade plan to file."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(plan, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save plan: {e}")
        return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="upgrade_legacy_project.py",
        description="Upgrade legacy projects to project_initializer format",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Phase 1: Analyze project structure and generate analysis report",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Phase 2: Generate upgrade plan based on analysis",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Phase 3: Execute upgrade plan (requires confirmation)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Phase 4: Validate upgrade success",
    )
    parser.add_argument(
        "--template-repo",
        default="",
        help="Template repository URL (for copying template files)",
    )

    args = parser.parse_args(argv)

    if args.analyze:
        print("Phase 1: Analyzing project structure...")
        analysis = analyze_project()
        
        analysis_file = pathlib.Path("6_ai_runtime_context/UPGRADE_ANALYSIS.yaml")
        if save_analysis(analysis, analysis_file):
            print(f"OK: Analysis saved to {analysis_file}")
            print(f"\nAnalysis Summary:")
            print(f"  Is Legacy: {analysis['is_legacy']}")
            print(f"  Framework: {analysis['framework'].get('type', 'unknown')}")
            print(f"  Structure: {analysis['structure'].get('type', 'unknown')}")
            print(f"  Edge Cases: {len(analysis.get('edge_cases', []))}")
            print(f"  Conflicts: {len(analysis.get('conflicts', []))}")
            return 0
        return 1

    if args.plan:
        print("Phase 2: Generating upgrade plan...")
        analysis_file = pathlib.Path("6_ai_runtime_context/UPGRADE_ANALYSIS.yaml")
        if not analysis_file.exists():
            print("ERROR: Analysis not found. Run --analyze first.")
            return 1

        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis = yaml.safe_load(f)

        plan = generate_upgrade_plan(analysis)
        
        plan_file = pathlib.Path("6_ai_runtime_context/UPGRADE_PLAN.yaml")
        if save_plan(plan, plan_file):
            print(f"OK: Upgrade plan saved to {plan_file}")
            print(f"\nPlan Summary:")
            print(f"  Steps: {len(plan.get('steps', []))}")
            print(f"  Preserved Items: {len(plan.get('preserved', []))}")
            print(f"  Edge Cases to Handle: {len(analysis.get('edge_cases', []))}")
            return 0
        return 1

    if args.execute:
        print("Phase 3: Executing upgrade plan...")
        print("WARN: This will modify your project structure.")
        print("      A backup branch will be created first.")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Upgrade cancelled.")
            return 0

        plan_file = pathlib.Path("6_ai_runtime_context/UPGRADE_PLAN.yaml")
        if not plan_file.exists():
            print("ERROR: Upgrade plan not found. Run --plan first.")
            return 1

        with open(plan_file, "r", encoding="utf-8") as f:
            plan = yaml.safe_load(f)

        print("Executing upgrade plan...")
        
        # Execute steps from plan
        success = execute_upgrade_plan(plan, args.template_repo)
        
        if success:
            print("OK: Upgrade execution completed")
            print("\nNext steps:")
            print("1. Review changes: git status")
            print("2. Test project: Ensure it still builds and runs")
            print("3. Validate: python3 3_bootstrap_scripts/cli.py upgrade-legacy --validate")
            print("4. Commit changes incrementally")
            return 0
        else:
            print("ERROR: Upgrade execution failed. Check logs above.")
            print("Rollback: git checkout backup-before-upgrade")
            return 1

    if args.validate:
        print("Phase 4: Validating upgrade...")
        success = validate_upgrade()
        if success:
            print("OK: Upgrade validation passed")
            return 0
        else:
            print("ERROR: Upgrade validation failed. Review errors above.")
            return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

