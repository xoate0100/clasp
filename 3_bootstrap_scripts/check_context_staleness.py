#!/usr/bin/env python3
"""
Pre-commit hook: Check if AI_CONTEXT.md is stale relative to source files.

Warns (non-blocking) if generated context is older than source files.
Auto-regenerates if stale.
"""

import subprocess
import sys
import pathlib
import os

REPO_ROOT = pathlib.Path(".").resolve()
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    no_stage = "--no-stage" in sys.argv or os.environ.get("CONTEXT_STALENESS_NO_STAGE") == "1"
    context_file = REPO_ROOT / "6_ai_runtime_context" / "AI_CONTEXT.md"
    if not context_file.exists():
        print("[context-staleness] INFO: AI_CONTEXT.md not found, will be generated on next commit")
        return 0

    try:
        from agentic.optional_tools import is_tool_enabled

        if is_tool_enabled("janitor", REPO_ROOT):
            from agentic.janitor import is_context_stale, regenerate_context

            stale, reason = is_context_stale(REPO_ROOT)
            if not stale:
                return 0
            print(f"[context-staleness] WARN: AI_CONTEXT.md is stale ({reason})")
            print("[context-staleness] Regenerating...")
            if regenerate_context(REPO_ROOT) == 0:
                print("[context-staleness] OK: Regenerated AI_CONTEXT.md")
                if not no_stage:
                    subprocess.run(["git", "add", str(context_file)], capture_output=True, timeout=30)
                return 0
            return 1
    except ImportError:
        pass

    # Fallback: mtime-based check
    source_files = [
        REPO_ROOT / "0_phase0_bootstrap" / "AI_SANDBOX_RULES.md",
        REPO_ROOT / "0_phase0_bootstrap" / "feature_flags.yml",
        REPO_ROOT / "6_ai_runtime_context" / "ACTIVE_PLAN.yaml",
        REPO_ROOT / "6_ai_runtime_context" / "ACTIVE_TASK_POINTER.yaml",
        REPO_ROOT / "5_reference_architectures" / "LAYER_RULES.yaml",
        REPO_ROOT / "5_reference_architectures" / "DECISION_REGISTRY.yaml",
    ]
    context_mtime = context_file.stat().st_mtime
    stale = any(p.exists() and p.stat().st_mtime > context_mtime for p in source_files)
    if not stale:
        return 0

    print("[context-staleness] WARN: AI_CONTEXT.md is stale")
    result = subprocess.run(
        [sys.executable, "3_bootstrap_scripts/generate_ai_context.py"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode == 0:
        if not no_stage:
            subprocess.run(["git", "add", str(context_file)], capture_output=True, timeout=30)
        return 0
    print(f"[context-staleness] ERROR: {result.stderr}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
