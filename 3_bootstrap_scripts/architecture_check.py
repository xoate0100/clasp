#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import pathlib

try:
    import yaml
except ImportError:
    print("[architecture] Error: PyYAML not installed. Install with: pip install PyYAML")
    sys.exit(1)

EXCLUDE_DIR_NAMES = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "htmlcov", ".coverage",
}

# Template / governance trees are never product frontend|backend for cross-import.
# Spokes sometimes set components.frontend.directories: ['./'] which would otherwise
# false-positive on hub-synced 3_bootstrap_scripts mentioning the word "backend".
TEMPLATE_PATH_PREFIXES = (
    "0_phase0_bootstrap/",
    "1_global_standards/",
    "2_framework_templates/",
    "3_bootstrap_scripts/",
    "5_reference_architectures/",
    "7_schemas/",
    "8_ci/",
    "adapters/",
    "agentic/",
    "agent_platform/",
    "templates/",
    ".cursor/",
)

FULL_SCAN_ENV = "ARCHITECTURE_CHECK_ALL_FILES"


def _normalize_path(path: str) -> str:
    return pathlib.Path(path).as_posix()


def _is_excluded(path: pathlib.Path) -> bool:
    return any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def _is_template_path(path: pathlib.Path) -> bool:
    rel = _normalize_path(str(path))
    return any(rel == p.rstrip("/") or rel.startswith(p) for p in TEMPLATE_PATH_PREFIXES)


def get_staged_files() -> list[str] | None:
    """Return staged file paths during pre-commit, or None for full-repo scan."""
    if os.environ.get(FULL_SCAN_ENV, "").lower() in ("1", "true", "yes"):
        return None
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        files = [_normalize_path(f.strip()) for f in output.splitlines() if f.strip()]
        return files if files else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def iter_files_in_roots(roots: list[pathlib.Path], extensions: list[str], staged: list[str] | None):
    """Yield code files under roots, scoped to staged files when available."""
    ext_set = set(extensions)
    if staged is not None:
        for rel in staged:
            path = pathlib.Path(rel)
            if _is_excluded(path) or path.suffix not in ext_set:
                continue
            for root in roots:
                try:
                    path.relative_to(root)
                    if path.exists():
                        yield path
                    break
                except ValueError:
                    continue
        return

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix in ext_set and not _is_excluded(path):
                yield path


STAGED_FILES = get_staged_files()

# Load rules and feature flags
rules_path = pathlib.Path("5_reference_architectures/LAYER_RULES.yaml")
if rules_path.exists():
    RULES = yaml.safe_load(open(rules_path))
else:
    RULES = {"components": {}, "rules": {}, "layers": []}

flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
enforce_solid = False
FEATURE_FLAGS = {}
if flags_path.exists():
    try:
        FEATURE_FLAGS = yaml.safe_load(open(flags_path)) or {}
        enforce_solid = FEATURE_FLAGS.get("ai_guardrails", {}).get("enforce_solid_principles", False)
    except:
        pass

violations = []


def _get_component_roots() -> dict:
    """
    Read component directory roots from feature_flags.yml.
    Falls back to conventional defaults if missing.
    """
    comps = (FEATURE_FLAGS.get("components") or {}) if isinstance(FEATURE_FLAGS, dict) else {}
    out = {}
    if isinstance(comps, dict):
        for name, cfg in comps.items():
            if not isinstance(cfg, dict):
                continue
            dirs = cfg.get("directories")
            if isinstance(dirs, list) and dirs:
                out[name] = [pathlib.Path(str(d).strip()) for d in dirs if str(d).strip()]
    if not out:
        out = {"frontend": [pathlib.Path("frontend")], "backend": [pathlib.Path("backend")], "shared": [pathlib.Path("shared")]}
    return out

def check_cross_component_imports():
    # Simple heuristic: forbid strings like "from backend" inside frontend, etc.
    component_roots = _get_component_roots()
    for comp, cfg in RULES["components"].items():
        forbid = cfg.get("forbid_import", [])
        roots = component_roots.get(comp, [])
        roots = [r for r in roots if r and r.exists()]
        if not roots:
            continue
        extensions = [".ts", ".tsx", ".js", ".py", ".java", ".cs"]
        for root in roots:
            for p in iter_files_in_roots([root], extensions, STAGED_FILES):
                if _is_template_path(p):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except:
                    continue
                for bad in forbid:
                    if re.search(rf'\bfrom\s+{bad}\b|\brequire\(["\']{bad}', text):
                        violations.append(f"{p}: illegal import of {bad} in {comp}")

def check_layer_rules():
    # Minimal: forbid 'db' keyword in api/domain layers (heuristic)
    forbid = set(RULES.get("rules", {}).get("forbid_db_calls_from", []))
    for layer_def in RULES.get("layers", []):
        layer_name = layer_def.get("name", "") if isinstance(layer_def, dict) else layer_def
        if layer_name not in forbid:
            continue
        root = pathlib.Path(f"backend/src/{layer_name}")
        if not root.exists():
            continue
        layer_files = []
        if STAGED_FILES is not None:
            layer_files = [
                pathlib.Path(f) for f in STAGED_FILES
                if f.endswith(".py") and _normalize_path(f).startswith(_normalize_path(str(root)))
            ]
            if not layer_files:
                continue
        else:
            layer_files = list(root.rglob("*.py"))

        for p in layer_files:
            if _is_excluded(p):
                continue
            t = p.read_text(encoding="utf-8", errors="ignore")
            if re.search(r'\b(sql|cursor|Session|insert|update|delete)\b', t):
                violations.append(f"{p}: DB-like access in {layer_name} layer")

def check_srp_single_responsibility():
    """SRP: Flag functions > 50 lines"""
    if not enforce_solid:
        return

    code_extensions = [".py", ".ts", ".tsx", ".js"]
    component_roots = _get_component_roots()
    search_dirs = [p for dirs in component_roots.values() for p in dirs]

    for root_dir in search_dirs:
        if not root_dir.exists():
            continue

        for file_path in iter_files_in_roots([root_dir], code_extensions, STAGED_FILES):
            if _is_template_path(file_path):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                # Simple heuristic: count function definitions and their lengths
                in_function = False
                function_start = 0
                function_name = ""
                brace_count = 0
                paren_count = 0

                for i, line in enumerate(lines, 1):
                    # Detect function start (Python)
                    if re.match(r'^\s*(def|async def)\s+\w+', line):
                        if in_function:
                            # Previous function ended without explicit return
                            if i - function_start > 50:
                                violations.append(
                                    f"{file_path}:{function_start} SRP violation: "
                                    f"Function '{function_name}' is {i - function_start} lines (>50). "
                                    f"Refactor into smaller functions. See 1_global_standards/SOLID_PRINCIPLES.md"
                                )
                        in_function = True
                        function_start = i
                        function_name = re.search(r'(def|async def)\s+(\w+)', line).group(2)
                        brace_count = 0
                        paren_count = line.count('(') - line.count(')')

                    # Detect function start (TypeScript/JavaScript)
                    elif re.match(r'^\s*(export\s+)?(function|const|let|var)\s+\w+.*[=:]\s*\(', line):
                        if in_function and i - function_start > 50:
                            violations.append(
                                f"{file_path}:{function_start} SRP violation: "
                                f"Function '{function_name}' is {i - function_start} lines (>50). "
                                f"Refactor into smaller functions. See 1_global_standards/SOLID_PRINCIPLES.md"
                            )
                        in_function = True
                        function_start = i
                        match = re.search(r'(?:function|const|let|var)\s+(\w+)', line)
                        function_name = match.group(1) if match else "anonymous"
                        brace_count = line.count('{') - line.count('}')
                        paren_count = line.count('(') - line.count(')')

                    if in_function:
                        # Track braces and parentheses
                        brace_count += line.count('{') - line.count('}')
                        paren_count += line.count('(') - line.count(')')

                        # Function ends when braces/parentheses balance and we hit a dedent or semicolon
                        if file_path.suffix == ".py":
                            # Python: function ends at next def/class or significant dedent
                            if i > function_start and re.match(r'^\s*(def|class|async def)', line):
                                if i - 1 - function_start > 50:
                                    violations.append(
                                        f"{file_path}:{function_start} SRP violation: "
                                        f"Function '{function_name}' is {i - 1 - function_start} lines (>50). "
                                        f"Refactor into smaller functions. See 1_global_standards/SOLID_PRINCIPLES.md"
                                    )
                                in_function = False
                        else:
                            # TypeScript/JS: function ends when braces balance
                            if brace_count == 0 and paren_count == 0 and i > function_start:
                                if i - function_start > 50:
                                    violations.append(
                                        f"{file_path}:{function_start} SRP violation: "
                                        f"Function '{function_name}' is {i - function_start} lines (>50). "
                                        f"Refactor into smaller functions. See 1_global_standards/SOLID_PRINCIPLES.md"
                                    )
                                in_function = False

                # Check last function if still open
                if in_function and len(lines) - function_start > 50:
                    violations.append(
                        f"{file_path}:{function_start} SRP violation: "
                        f"Function '{function_name}' is {len(lines) - function_start} lines (>50). "
                        f"Refactor into smaller functions. See 1_global_standards/SOLID_PRINCIPLES.md"
                    )

            except Exception:
                # Skip files that can't be parsed
                continue


def check_isp_interface_segregation():
    """ISP: Flag interfaces/types > 10 methods/properties"""
    if not enforce_solid:
        return

    ts_extensions = [".ts", ".tsx"]
    component_roots = _get_component_roots()
    search_dirs = [p for dirs in component_roots.values() for p in dirs]

    for root_dir in search_dirs:
        if not root_dir.exists():
            continue

        for file_path in iter_files_in_roots([root_dir], ts_extensions, STAGED_FILES):
            if _is_template_path(file_path):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                # Find interface and type definitions
                for i, line in enumerate(lines, 1):
                    # Match interface definitions
                    interface_match = re.search(r'interface\s+(\w+)', line)
                    if interface_match:
                        interface_name = interface_match.group(1)
                        # Count methods/properties in interface
                        brace_count = line.count('{') - line.count('}')
                        method_count = 0
                        j = i

                        while j < len(lines) and brace_count >= 0:
                            current_line = lines[j]
                            brace_count += current_line.count('{') - current_line.count('}')

                            # Count method/property definitions
                            if re.search(r'^\s*\w+.*[:?]\s*[^;]', current_line) or re.search(r'^\s*\w+\s*\(', current_line):
                                method_count += 1

                            if brace_count < 0:
                                break
                            j += 1

                        if method_count > 10:
                            violations.append(
                                f"{file_path}:{i} ISP violation: "
                                f"Interface '{interface_name}' has {method_count} methods/properties (>10). "
                                f"Split into smaller, focused interfaces. See 1_global_standards/SOLID_PRINCIPLES.md"
                            )

                    # Match type definitions (TypeScript)
                    type_match = re.search(r'type\s+(\w+)\s*=\s*\{', line)
                    if type_match:
                        type_name = type_match.group(1)
                        brace_count = line.count('{') - line.count('}')
                        method_count = 0
                        j = i

                        while j < len(lines) and brace_count >= 0:
                            current_line = lines[j]
                            brace_count += current_line.count('{') - current_line.count('}')

                            if re.search(r'^\s*\w+.*[:?]\s*[^;]', current_line):
                                method_count += 1

                            if brace_count < 0:
                                break
                            j += 1

                        if method_count > 10:
                            violations.append(
                                f"{file_path}:{i} ISP violation: "
                                f"Type '{type_name}' has {method_count} properties (>10). "
                                f"Split into smaller, focused types. See 1_global_standards/SOLID_PRINCIPLES.md"
                            )

            except Exception as e:
                # Skip files that can't be parsed
                continue


def check_dip_dependency_inversion():
    """DIP: Flag direct imports of concrete implementations"""
    if not enforce_solid:
        return

    code_extensions = [".py", ".ts", ".tsx"]
    component_roots = _get_component_roots()
    search_dirs = [p for dirs in component_roots.values() for p in dirs]

    # Patterns that suggest concrete implementation imports
    concrete_patterns = [
        (r'from\s+[\w.]+\.models\.', "models"),  # Direct model imports
        (r'from\s+[\w.]+\.services\.', "services"),  # Direct service imports
        (r'from\s+[\w.]+\.repositories\.', "repositories"),  # Direct repository imports
        (r'import\s+.*from\s+["\']([\w/]+/)?(models|services|repositories)', "concrete"),  # JS/TS imports
    ]

    for root_dir in search_dirs:
        if not root_dir.exists():
            continue

        for file_path in iter_files_in_roots([root_dir], code_extensions, STAGED_FILES):
            if _is_template_path(file_path):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                for i, line in enumerate(lines, 1):
                    # Skip if importing from interfaces/abstract
                    if re.search(r'(interfaces|abstract|interfaces/)', line, re.IGNORECASE):
                        continue

                    # Check for concrete imports
                    for pattern, pattern_type in concrete_patterns:
                        match = re.search(pattern, line)
                        if match:
                            # Extract the import path
                            import_match = re.search(r'from\s+["\']?([\w./]+)', line) or re.search(r'import\s+.*from\s+["\']([\w./]+)', line)
                            if import_match:
                                import_path = import_match.group(1)
                                violations.append(
                                    f"{file_path}:{i} DIP violation: "
                                    f"Direct import of concrete implementation '{import_path}'. "
                                    f"Depend on abstractions (interfaces/abstract classes) instead. "
                                    f"See 1_global_standards/SOLID_PRINCIPLES.md"
                                )
                                break  # Only report once per line

            except Exception as e:
                # Skip files that can't be parsed
                continue


# Run all checks
check_cross_component_imports()
check_layer_rules()

if enforce_solid:
    check_srp_single_responsibility()
    check_isp_interface_segregation()
    check_dip_dependency_inversion()

if violations:
    print("[architecture] BLOCKING: Architecture violations detected:")
    print("\n".join(f"  - {v}" for v in violations))
    print("\n[architecture] Fix violations before committing. See 1_global_standards/SOLID_PRINCIPLES.md for guidance.")
    sys.exit(1)

print("[architecture] OK: All checks passed")
