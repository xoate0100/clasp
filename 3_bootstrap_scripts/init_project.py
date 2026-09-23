#!/usr/bin/env python3
"""
Project initialization script.
Implements the full initialization flow as described in expected_flow.md
"""
import sys
import os
import subprocess
import json
import pathlib
from datetime import datetime
from typing import Optional

try:
    import yaml
    import jsonschema
    from jsonschema import validate
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)


def detect_initial_state():
    """STEP 1: Check if already initialized"""
    if pathlib.Path(".initialized").exists():
        print("OK: Repository already initialized.")
        print("   To re-initialize, remove .initialized file first.")
        sys.exit(0)
    print("First-time setup detected.")


def load_meta_framework():
    """STEP 2: Load meta-framework configuration"""
    meta_dir = pathlib.Path("0_phase0_bootstrap")
    required_files = [
        "feature_flags.yml",
        "AI_SANDBOX_RULES.md",
        "AI_EXECUTION_CONSTRAINTS.md",
        "MVP_SPECIFICATION.yaml"
    ]

    missing = []
    for f in required_files:
        if not (meta_dir / f).exists():
            missing.append(f)

    if missing:
        print(f"ERROR: Missing meta-framework files: {', '.join(missing)}")
        sys.exit(1)

    try:
        with open(meta_dir / "feature_flags.yml", "r") as f:
            feature_flags = yaml.safe_load(f)
        with open(meta_dir / "MVP_SPECIFICATION.yaml", "r") as f:
            mvp_spec = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Error loading meta-framework: {e}")
        sys.exit(1)

    print("OK: Loaded framework configuration and MVP spec.")
    return feature_flags, mvp_spec


def validate_schema(feature_flags, mvp_spec):
    """STEP 3: Validate schema compliance"""
    schema_dir = pathlib.Path("7_schemas")

    # Validate feature_flags.yml
    flags_schema_path = schema_dir / "feature_flags.schema.json"
    if flags_schema_path.exists():
        with open(flags_schema_path, "r") as f:
            flags_schema = json.load(f)
        try:
            validate(instance=feature_flags, schema=flags_schema)
        except jsonschema.ValidationError as e:
            print(f"ERROR: feature_flags.yml validation failed: {e.message}")
            sys.exit(1)

    # Validate MVP_SPECIFICATION.yaml (use full schema)
    mvp_schema_path = schema_dir / "mvp_specification.schema.json"
    if not mvp_schema_path.exists():
        # Fallback to template schema if full schema doesn't exist
        mvp_schema_path = schema_dir / "mvp_specification_template.schema.json"

    if mvp_schema_path.exists():
        with open(mvp_schema_path, "r") as f:
            mvp_schema = json.load(f)
        try:
            validate(instance=mvp_spec, schema=mvp_schema)
        except jsonschema.ValidationError as e:
            print(f"ERROR: MVP_SPECIFICATION.yaml validation failed: {e.message}")
            print(f"   Path: {'.'.join(str(p) for p in e.absolute_path)}")
            if e.absolute_path:
                print(f"   Missing required field at: {list(e.absolute_path)}")
            sys.exit(1)
    else:
        print("WARN: No schema found for MVP_SPECIFICATION.yaml")

    print("OK: Schema validation complete.")


def extract_write_paths_from_layout(mvp_spec):
    """
    Extract directory paths from MONOREPO_LAYOUT for permissions.write_to.
    Handles nested structures like apps/web/, apps/api/, etc.
    Returns list of paths with trailing slashes.
    """
    layout = mvp_spec.get("MONOREPO_LAYOUT", {})
    paths = []

    # Meta-framework directories that should be excluded (already in readonly)
    excluded = {
        "0_phase0_bootstrap", "1_global_standards", "2_framework_templates",
        "3_bootstrap_scripts", "4_docs_index", "5_reference_architectures",
        "6_ai_runtime_context", "7_schemas", "8_ci", ".github", "ai_reports",
        "scripts", "shared"  # scripts is for script files, shared is for shared types/utils
    }

    def extract_paths(obj, prefix="", depth=0, max_depth=3):
        """
        Recursively extract directory paths from nested structure.
        max_depth: prevent going too deep (e.g., apps/web/src/components/ is too deep)
        """
        if depth > max_depth:
            return

        if isinstance(obj, dict):
            for key, value in obj.items():
                # Skip if excluded
                if key in excluded and depth == 0:
                    continue

                # Build current path
                current_path = f"{prefix}{key}/" if prefix else f"{key}/"

                # For root-level keys, check if they contain nested apps
                if depth == 0 and key == "root":
                    # Extract paths from root (frontend/, backend/, shared/, apps/web/, etc.)
                    if isinstance(value, dict):
                        extract_paths(value, "", depth + 1, max_depth)
                elif depth == 0 and key == "apps":
                    # Extract nested app directories (apps/web/, apps/api/, etc.)
                    if isinstance(value, dict):
                        for app_name in value.keys():
                            app_path = f"apps/{app_name}/"
                            if app_path not in paths:
                                paths.append(app_path)
                elif depth == 1 and prefix == "":
                    # Direct children of root (frontend/, backend/, shared/)
                    if current_path not in paths:
                        paths.append(current_path)
                elif depth == 0:
                    # Top-level keys that aren't root or apps
                    if key not in excluded and current_path not in paths:
                        paths.append(current_path)

                # Recurse into nested structures
                if isinstance(value, dict):
                    extract_paths(value, current_path, depth + 1, max_depth)
        elif isinstance(obj, list):
            # Lists contain file paths, not directories
            pass

    if isinstance(layout, dict):
        extract_paths(layout)
    elif isinstance(layout, list):
        # Legacy format: list of directory strings
        for item in layout:
            if isinstance(item, str) and item.endswith("/"):
                if item not in paths:
                    paths.append(item)

    # Fallback to defaults if no paths found
    if not paths:
        print("WARN: No paths found in MONOREPO_LAYOUT, using defaults")
        paths = ["frontend/", "backend/", "shared/"]

    return sorted(set(paths))  # Remove duplicates and sort


def extract_component_directories(mvp_spec):
    """
    Extract component directory roots from PROJECT_LAYOUT (preferred) or MONOREPO_LAYOUT (fallback).

    Returns dict: {component_name: [dir_prefixes_with_trailing_slash]}
    """
    def norm_dir(d: str) -> str:
        d = str(d).strip().replace("\\", "/")
        if d in (".", "./"):
            return "./"
        return d if d.endswith("/") else d + "/"

    project_layout = mvp_spec.get("PROJECT_LAYOUT", {})
    comps = (project_layout.get("components") if isinstance(project_layout, dict) else None) or {}
    component_dirs = {}

    if isinstance(comps, dict) and comps:
        for comp, cfg in comps.items():
            if not isinstance(cfg, dict):
                continue
            dirs = cfg.get("directories", [])
            if isinstance(dirs, list) and dirs:
                component_dirs[comp] = [norm_dir(d) for d in dirs if str(d).strip()]
        if component_dirs:
            return component_dirs

    # Fallback: infer from MONOREPO_LAYOUT.root if present
    layout = mvp_spec.get("MONOREPO_LAYOUT", {})
    root = layout.get("root", {}) if isinstance(layout, dict) else {}
    if isinstance(root, dict):
        for comp in ("frontend", "backend", "shared"):
            if comp in root:
                component_dirs[comp] = [norm_dir(f"{comp}/")]

    return component_dirs


def derive_write_paths(mvp_spec, component_dirs):
    """
    Derive permissions.write_to.
    Priority:
      1) PROJECT_LAYOUT.write_paths (if provided)
      2) component directories (from PROJECT_LAYOUT/MONOREPO_LAYOUT)
      3) legacy extract_write_paths_from_layout fallback
    Always include safe template defaults: docs/tests/scripts/4_docs_index.
    """
    project_layout = mvp_spec.get("PROJECT_LAYOUT", {})
    if isinstance(project_layout, dict):
        wp = project_layout.get("write_paths")
        if isinstance(wp, list) and wp:
            out = []
            for p in wp:
                p = str(p).strip().replace("\\", "/")
                if not p:
                    continue
                out.append(p if p.endswith("/") else p + "/")
            return sorted(set(out))

    derived = set()
    for dirs in (component_dirs or {}).values():
        for d in dirs:
            # Avoid granting write access to repo root by default; require explicit write_paths for "./"
            if d in ("./", "/"):
                continue
            derived.add(d)

    if not derived:
        for p in extract_write_paths_from_layout(mvp_spec):
            derived.add(p)

    # Safe template defaults (documented + expected by hooks/automation)
    derived.update({"docs/", "tests/", "scripts/", "4_docs_index/"})
    return sorted(derived)


def set_coverage_thresholds(feature_flags, mvp_spec):
    """
    Enforce 100% coverage for all components regardless of language/framework.
    Rationale: 100% TDD coverage prevents unusable code, AI drift/hallucination, and massive rework.
    """
    components = feature_flags.get("components", {})
    updated = False

    for component_name, component_config in components.items():
        if isinstance(component_config, dict):
            current_threshold = component_config.get("coverage_threshold", 0)
            if current_threshold != 100:
                component_config["coverage_threshold"] = 100
                updated = True
                print(f"   Updated {component_name} coverage threshold to 100%")

    if updated:
        print("OK: Enforced 100% coverage for all components (universal requirement)")
    else:
        print("OK: All components already have 100% coverage threshold")

    return feature_flags


def update_feature_flags_from_mvp_spec(feature_flags, mvp_spec):
    """
    Update feature_flags.yml dynamically based on MVP_SPECIFICATION.yaml:
    - Update permissions.write_to from MONOREPO_LAYOUT
    - Enforce 100% coverage for all components
    - Update component languages from TECH_STACK if specified
    """
    print("Updating feature flags from MVP specification...")

    # Extract component directories and derive write paths
    component_dirs = extract_component_directories(mvp_spec)
    write_paths = derive_write_paths(mvp_spec, component_dirs)
    if write_paths:
        feature_flags.setdefault("permissions", {})["write_to"] = write_paths
        print(f"   Updated permissions.write_to: {', '.join(write_paths)}")

    # Update feature_flags component directory roots when provided (template-level portability)
    if component_dirs:
        ff_components = feature_flags.setdefault("components", {})
        for comp_name, dirs in component_dirs.items():
            if comp_name not in ff_components or not isinstance(ff_components.get(comp_name), dict):
                ff_components[comp_name] = {}
            ff_components[comp_name]["directories"] = dirs
        print("   Updated components.*.directories from PROJECT_LAYOUT / MONOREPO_LAYOUT")

    # Enforce 100% coverage for all components
    feature_flags = set_coverage_thresholds(feature_flags, mvp_spec)

    # Update component languages from TECH_STACK if available
    tech_stack = mvp_spec.get("TECH_STACK", {})
    components = feature_flags.get("components", {})

    # Map TECH_STACK component names to feature_flags component names
    tech_to_components = {
        "frontend": "frontend",
        "backend": "backend",
        "shared": "shared"
    }

    for tech_key, component_name in tech_to_components.items():
        if tech_key in tech_stack and component_name in components:
            tech_config = tech_stack[tech_key]
            if isinstance(tech_config, dict):
                language = tech_config.get("language", "")
                if language:
                    components[component_name]["language"] = language
                    print(f"   Updated {component_name} language to {language}")

    # Save updated feature flags
    feature_flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
    with open(feature_flags_path, "w") as f:
        yaml.dump(feature_flags, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print("OK: Feature flags updated and saved.")
    return feature_flags


def detect_adapter_from_tech_stack(mvp_spec: dict) -> str:
    """
    NA-01: choose adapter from TECH_STACK languages.
    Any javascript/typescript/node language → node; otherwise python.
    """
    tech_stack = mvp_spec.get("TECH_STACK") or {}
    node_tokens = ("javascript", "typescript", "node", "js", "ts")
    for _key, cfg in tech_stack.items():
        if not isinstance(cfg, dict):
            continue
        lang = str(cfg.get("language", "")).lower().strip()
        framework = str(cfg.get("framework", "")).lower().strip()
        if any(tok in lang or tok in framework for tok in node_tokens):
            return "node"
    return "python"


def write_stack_adapter_selection(mvp_spec: dict, force_adapter: Optional[str] = None) -> str:
    """Write 0_phase0_bootstrap/stack_adapter.yaml for new children (NA-01 / DEC-0003)."""
    adapter = force_adapter or detect_adapter_from_tech_stack(mvp_spec)
    if adapter not in ("python", "node"):
        # generic deferred (NA-03); fall back safely
        adapter = "python"
    path = pathlib.Path("0_phase0_bootstrap/stack_adapter.yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Active stack adapter (v4). Migrated children default to python.\n"
        f"# Selected at init from TECH_STACK → {adapter} (DEC-0003-ADAPTER-MODEL / NA-01)\n"
        f"adapter: {adapter}\n"
        f"manifest: adapters/{adapter}/stack_adapter.yaml\n",
        encoding="utf-8",
    )
    print(f"OK: stack adapter selection written → adapter: {adapter}")
    return adapter


def verify_sandbox_integrity(feature_flags):
    """STEP 4: Verify sandbox permissions"""
    mode = feature_flags.get("mode", {})
    mvp_spec = feature_flags.get("_mvp_spec", {})  # Passed from context if available

    if mode.get("cursor_agent_mode") != "sandboxed":
        print("WARN: Non-sandboxed mode detected - enable sandboxed for safe agent execution.")

    if mode.get("modify_meta_framework") is True:
        print("ERROR: Meta framework modification disabled for L2.5. Set to false.")
        sys.exit(1)

    # Log maturity and execution mode if available
    if mvp_spec:
        maturity = mvp_spec.get("Maturity", "unknown")
        exec_mode = mvp_spec.get("Execution_Mode", "unknown")
        print(f"   Maturity: {maturity}, Execution Mode: {exec_mode}")

    print("OK: Sandbox rules validated.")


def setup_environment():
    """STEP 5: Install local dependencies"""
    print("Installing dependencies...")

    # Install Python dependencies
    if pathlib.Path("requirements.txt").exists():
        try:
            subprocess.run(["pip", "install", "-r", "requirements.txt"],
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("WARN: Failed to install Python dependencies (may need virtualenv)")

    # Install Node dependencies if package.json exists
    if pathlib.Path("package.json").exists():
        try:
            # Try pnpm first, then npm
            subprocess.run(["pnpm", "install"], check=False, capture_output=True)
            subprocess.run(["npm", "install"], check=False, capture_output=True)
        except FileNotFoundError:
            pass

    # Install pre-commit
    try:
        subprocess.run(["pip", "install", "pre-commit"], check=False, capture_output=True)
    except:
        try:
            subprocess.run(["pipx", "install", "pre-commit"], check=False, capture_output=True)
        except:
            print("WARN: Could not install pre-commit automatically")

    print("OK: Dependencies installed.")


def scaffold_structure_from_mvp_spec(mvp_spec):
    """STEP 6: Create folder structure from nested MONOREPO_LAYOUT"""
    layout = mvp_spec.get("MONOREPO_LAYOUT", {})

    def create_dirs(path_obj, prefix=""):
        """Recursively create directories from nested structure"""
        if isinstance(path_obj, dict):
            for key, value in path_obj.items():
                current_path = pathlib.Path(prefix, key) if prefix else pathlib.Path(key)
                if not current_path.exists():
                    current_path.mkdir(parents=True, exist_ok=True)
                    # Add .gitkeep to empty directories
                    if not any(current_path.iterdir()):
                        (current_path / ".gitkeep").touch()
                if isinstance(value, dict):
                    create_dirs(value, str(current_path))
        elif isinstance(path_obj, list):
            # Handle scripts array - create script files
            for script_path in path_obj:
                script_file = pathlib.Path(script_path)
                if not script_file.exists():
                    script_file.parent.mkdir(parents=True, exist_ok=True)
                    script_file.touch()
                    # Make scripts executable
                    if script_file.suffix in (".sh", ".py"):
                        script_file.chmod(0o755)

    # Handle nested object structure
    if isinstance(layout, dict):
        create_dirs(layout)
    elif isinstance(layout, list):
        # Fallback: handle legacy array format
        for folder in layout:
            folder_path = pathlib.Path(folder)
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                if not any(folder_path.iterdir()):
                    (folder_path / ".gitkeep").touch()

    # Copy templates to appropriate locations
    template_dir = pathlib.Path("2_framework_templates")
    if (template_dir / "README_TEMPLATE.md").exists():
        # README will be customized by user
        pass

    if (template_dir / "COMMIT_MESSAGE_TEMPLATE.md").exists():
        github_dir = pathlib.Path(".github")
        github_dir.mkdir(exist_ok=True)
        # Copy commit template if needed
        pass

    print("OK: Folder and template structure verified.")


def generate_active_plan(mvp_spec):
    """STEP 7: Generate active plan from MVP spec"""
    plan_template = mvp_spec.get("ACTIVE_PLAN_TEMPLATE", {})

    runtime_dir = pathlib.Path("6_ai_runtime_context")
    runtime_dir.mkdir(exist_ok=True)

    # Write ACTIVE_PLAN.yaml
    with open(runtime_dir / "ACTIVE_PLAN.yaml", "w") as f:
        yaml.dump(plan_template, f, default_flow_style=False, sort_keys=False)

    # Write ACTIVE_TASK_POINTER.yaml
    task_pointer = {
        "current_task": 1,
        "status": "in_progress",
        "last_run": None
    }
    with open(runtime_dir / "ACTIVE_TASK_POINTER.yaml", "w") as f:
        yaml.dump(task_pointer, f, default_flow_style=False)

    print(f"OK: Active plan initialized (plan_id: {plan_template.get('plan_id', 'unknown')})")


def init_ai_context():
    """STEP 8: Initialize AI feedback and memory logs"""
    runtime_dir = pathlib.Path("6_ai_runtime_context")
    runtime_dir.mkdir(exist_ok=True)

    # Initialize ai_feedback_log.json
    feedback_log = {"entries": []}
    with open(runtime_dir / "ai_feedback_log.json", "w") as f:
        json.dump(feedback_log, f, indent=2)

    # Initialize MEMORY_STATE.yaml if it doesn't exist
    if not (runtime_dir / "MEMORY_STATE.yaml").exists():
        memory_state = {
            "recent_plans": [],
            "metrics": {"first_pass_commit_success_rate": 0}
        }
        with open(runtime_dir / "MEMORY_STATE.yaml", "w") as f:
            yaml.dump(memory_state, f, default_flow_style=False)

    # Initialize BOOTSTRAP_LAYOUT_GUIDANCE.md (bootstrap-time agent context)
    guidance_path = runtime_dir / "BOOTSTRAP_LAYOUT_GUIDANCE.md"
    if not guidance_path.exists():
        guidance_path.write_text(
            "# Bootstrap Layout Guidance (Generated)\n\n"
            "See this file for layout/structure guidance for AI agents.\n",
            encoding="utf-8",
        )

    # Initialize INIT_WIZARD_ANSWERS.yaml (optional answers file for guided init)
    answers_path = runtime_dir / "INIT_WIZARD_ANSWERS.yaml"
    if not answers_path.exists():
        answers_path.write_text(
            "# Guided Init - Answers File (Optional)\n"
            "# See 6_ai_runtime_context/INIT_WIZARD_ANSWERS.yaml in template for format.\n",
            encoding="utf-8",
        )

    # Generate AI context document
    try:
        subprocess.run(
            ["python3", "3_bootstrap_scripts/generate_ai_context.py"],
            check=True,
            capture_output=True
        )
        print("OK: AI context document generated.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("WARN: Could not generate AI context document (non-blocking)")

    print("OK: AI runtime context initialized.")


def install_hooks():
    """STEP 9: Install pre-commit hooks with cross-platform support"""
    try:
        # Import HookInstaller (lazy import to avoid circular dependencies)
        from install_hooks import HookInstaller
        
        installer = HookInstaller()
        success, message = installer.install_hooks(force=False)
        
        if success:
            print("OK: Pre-commit hooks installed.")
        else:
            # Handle various error cases with appropriate messages
            if "not found" in message.lower() or "not ready" in message.lower():
                print("WARN: Pre-commit not available. Install with: pip install pre-commit")
                print("   Then run: pre-commit install")
            else:
                print(f"WARN: {message}")
    except ImportError:
        # Fallback to simple installation if HookInstaller is not available
        try:
            subprocess.run(["pre-commit", "install"], check=True, capture_output=True)
            print("OK: Pre-commit hooks installed.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("WARN: Pre-commit not available. Install with: pip install pre-commit")
            print("   Then run: pre-commit install")
    except Exception as e:
        # Fallback on any unexpected error
        print(f"WARN: Hook installation failed: {e}")
        print("   You may need to install pre-commit manually: pip install pre-commit")


def run_self_checks():
    """STEP 10: Run schema enforcement and health checks"""
    scripts_dir = pathlib.Path("3_bootstrap_scripts")

    checks = [
        "schema_enforcement.py",
        "architecture_check.py",
        "ai_behavior_validation.py",
        "../scripts/meta_framework_drift_check.py"
    ]

    for script in checks:
        script_path = (scripts_dir / script).resolve()
        if script_path.exists():
            try:
                result = subprocess.run(
                    ["python3", str(script_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"WARN: {script} reported issues (non-blocking)")
            except Exception as e:
                print(f"WARN: Could not run {script}: {e}")

    print("OK: Self-checks completed.")


def generate_init_report(feature_flags):
    """STEP 11: Generate initialization report"""
    reports_dir = pathlib.Path("ai_reports")
    reports_dir.mkdir(exist_ok=True)

    try:
        with open("6_ai_runtime_context/ACTIVE_PLAN.yaml", "r") as f:
            plan = yaml.safe_load(f)
    except:
        plan = {}

    report = {
        "timestamp": datetime.now().isoformat(),
        "plan_id": plan.get("plan_id", "unknown"),
        "component": plan.get("component", "unknown"),
        "sandbox": feature_flags.get("mode", {}).get("cursor_agent_mode", "unknown"),
        "result": "success"
    }

    with open(reports_dir / "init_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Init report written to ai_reports/init_report.json")


def init_version_manifest():
    """Initialize version manifest if it doesn't exist"""
    version_file = pathlib.Path("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")
    if version_file.exists():
        return  # Already initialized

    # Try to detect template repo from git remote
    template_repo = ""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            template_repo = result.stdout.strip()
    except Exception:
        pass

    # If not detected, use default or prompt (for now, use default)
    if not template_repo:
        template_repo = "https://github.com/xoate0100/project_initializer.git"

    # Import template_update functions
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        from template_update import initialize_version_manifest, save_version_manifest

        manifest = initialize_version_manifest(template_repo, version="1.0.0")
        if save_version_manifest(manifest):
            print("OK: Version manifest initialized.")
        else:
            print("WARN: Failed to initialize version manifest (non-blocking)")
    except Exception as e:
        print(f"WARN: Could not initialize version manifest: {e} (non-blocking)")


def mark_initialized():
    """STEP 12: Create initialization marker"""
    timestamp = datetime.now().isoformat()
    with open(".initialized", "w") as f:
        f.write(f"Initialized on {timestamp}\n")
    print("OK: Initialization complete.")


def main():
    """Main initialization flow"""
    print("Starting project initialization...\n")

    try:
        detect_initial_state()
        feature_flags, mvp_spec = load_meta_framework()
        validate_schema(feature_flags, mvp_spec)

        # Phase 0/1/2: Layout adaptation
        # - Always emits a plan file: 6_ai_runtime_context/LAYOUT_REARRANGEMENT_PLAN.yaml
        # - Applies moves only when explicitly enabled in MVP spec (PROJECT_LAYOUT.adaptation)
        try:
            adaptor = pathlib.Path("3_bootstrap_scripts/layout_adaptor.py")
            if adaptor.exists():
                subprocess.run(
                    ["python3", str(adaptor), "--non_interactive"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
        except Exception as e:
            print(f"WARN: layout_adaptor failed to run: {e}")

        # Update feature flags dynamically from MVP spec
        # This adapts permissions.write_to to MONOREPO_LAYOUT and enforces 100% coverage
        feature_flags = update_feature_flags_from_mvp_spec(feature_flags, mvp_spec)
        write_stack_adapter_selection(mvp_spec)

        # Pass mvp_spec context for verification
        feature_flags["_mvp_spec"] = mvp_spec
        verify_sandbox_integrity(feature_flags)
        setup_environment()
        scaffold_structure_from_mvp_spec(mvp_spec)
        generate_active_plan(mvp_spec)
        init_ai_context()
        install_hooks()
        run_self_checks()
        generate_init_report(feature_flags)
        init_version_manifest()
        mark_initialized()

        print("\nRepository fully initialized and ready for plan execution!")
        print("\nNext steps:")
        print("1. Review and customize 0_phase0_bootstrap/MVP_SPECIFICATION.yaml")
        print("2. Review 6_ai_runtime_context/ACTIVE_PLAN.yaml")
        print("3. In Cursor, read 0_phase0_bootstrap/AI_SANDBOX_RULES.md")
        print("4. Start executing your plan!")

    except KeyboardInterrupt:
        print("\n\nERROR: Initialization cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
