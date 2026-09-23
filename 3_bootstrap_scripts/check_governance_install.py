#!/usr/bin/env python3
"""
Pre-commit hook: Check governance installation integrity.

BLOCKING: Ensures that:
- AI_OPERATING_CONSTITUTION.md exists
- AI_CONTEXT.md contains Governance section
- AI_CONTEXT.md references constitution path correctly
- AI_CONTEXT.md is not stale relative to constitution file
"""
import sys
import pathlib
import subprocess

def get_file_mtime(path: pathlib.Path) -> float:
    """Get file modification time, or 0 if doesn't exist"""
    if path.exists():
        return path.stat().st_mtime
    return 0.0

def main() -> int:
    """Check governance installation integrity"""
    root = pathlib.Path(".").resolve()
    
    # Required files
    constitution_path = root / "1_global_standards" / "AI_OPERATING_CONSTITUTION.md"
    context_path = root / "6_ai_runtime_context" / "AI_CONTEXT.md"
    
    errors = []
    
    # Check 1: Constitution file must exist
    if not constitution_path.exists():
        errors.append(f"ERROR: AI_OPERATING_CONSTITUTION.md missing at {constitution_path}")
        errors.append("  This file is required for governance installation.")
        errors.append("  Run: python3 3_bootstrap_scripts/generate_ai_context.py to regenerate context")
        return 1
    
    # Check 2: Context file must exist
    if not context_path.exists():
        errors.append(f"ERROR: AI_CONTEXT.md missing at {context_path}")
        errors.append("  Regenerating context...")
        result = subprocess.run(
            ["python3", "3_bootstrap_scripts/generate_ai_context.py"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            errors.append(f"  Failed to regenerate: {result.stderr}")
            return 1
        # Re-check after regeneration
        if not context_path.exists():
            errors.append("  Context file still missing after regeneration")
            return 1
    
    # Check 3: Read context file and validate content
    try:
        context_content = context_path.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(f"ERROR: Failed to read AI_CONTEXT.md: {e}")
        return 1
    
    # Check 4: Must contain Governance section
    if "## Governance" not in context_content:
        errors.append("ERROR: AI_CONTEXT.md missing '## Governance' section")
        errors.append("  The Governance section must be present at the top of the context document.")
        errors.append("  Regenerating context...")
        result = subprocess.run(
            ["python3", "3_bootstrap_scripts/generate_ai_context.py"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            errors.append(f"  Failed to regenerate: {result.stderr}")
            return 1
        # Re-read after regeneration
        try:
            context_content = context_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"  Failed to re-read after regeneration: {e}")
            return 1
        if "## Governance" not in context_content:
            errors.append("  Governance section still missing after regeneration")
            return 1
    
    # Check 5: Must reference constitution path exactly
    constitution_ref = "1_global_standards/AI_OPERATING_CONSTITUTION.md"
    if constitution_ref not in context_content:
        errors.append(f"ERROR: AI_CONTEXT.md missing reference to {constitution_ref}")
        errors.append("  The Governance section must include the exact path to the constitution file.")
        return 1
    
    # Check 6: Context must not be stale relative to constitution
    constitution_mtime = get_file_mtime(constitution_path)
    context_mtime = get_file_mtime(context_path)
    
    if constitution_mtime > context_mtime:
        errors.append("WARN: AI_CONTEXT.md is stale relative to AI_OPERATING_CONSTITUTION.md")
        errors.append("  Regenerating context...")
        result = subprocess.run(
            ["python3", "3_bootstrap_scripts/generate_ai_context.py"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            errors.append(f"  Failed to regenerate: {result.stderr}")
            return 1
        # Stage regenerated file
        subprocess.run(["git", "add", str(context_path)], capture_output=True)
        print("[governance-check] OK: Regenerated stale context")
    
    # Check 7: Verify core rules are restated (optional check, warns only)
    core_rules = [
        "Authority must be explicit",
        "State must be read",
        "Generated artifacts are derivative",
        "No action without explicit permission",
        "If unsure, stop",
        "AI may not modify governance"
    ]
    missing_rules = []
    for rule in core_rules:
        if rule.lower() not in context_content.lower():
            missing_rules.append(rule)
    
    if missing_rules:
        print("[governance-check] WARN: Some core rules may not be restated in context")
        print(f"  Missing: {', '.join(missing_rules)}")
        print("  This is a warning only; context will still be generated.")
    
    if errors:
        for error in errors:
            print(f"[governance-check] {error}")
        return 1
    
    print("[governance-check] OK: Governance installation verified")
    return 0

if __name__ == "__main__":
    sys.exit(main())

