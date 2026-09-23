#!/usr/bin/env python3
"""
Check Template Updates
Checks if template updates are available and prompts for update.
Runs as pre-commit hook to ensure projects stay up-to-date.
"""

import argparse
import pathlib
import subprocess
import sys
from datetime import datetime
from typing import Optional

try:
    import yaml
    import requests
except ImportError:
    requests = None
    yaml = None

VERSION_FILE = pathlib.Path("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")


def load_version_manifest() -> Optional[dict]:
    """Load version manifest if it exists."""
    if not VERSION_FILE.exists():
        return None
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def get_latest_version_from_remote(template_repo: str) -> Optional[str]:
    """Get latest version from template repository."""
    if not requests:
        return None

    # Try to get version from remote META_FRAMEWORK_VERSION.yaml
    try:
        # Extract owner/repo from URL
        import re
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", template_repo)
        if not match:
            return None

        owner, repo = match.groups()
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml"

        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            import base64
            content = base64.b64decode(response.json()["content"]).decode("utf-8")
            manifest = yaml.safe_load(content)
            return manifest.get("template_version")
    except Exception:
        pass

    # Fallback: try git tags
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", template_repo],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            tags = []
            for line in result.stdout.splitlines():
                if "refs/tags/" in line:
                    tag = line.split("refs/tags/")[-1].split()[0]
                    # Remove 'v' prefix if present
                    if tag.startswith("v"):
                        tag = tag[1:]
                    if any(c.isdigit() for c in tag):
                        tags.append(tag)
            if tags:
                # Simple version comparison - return latest
                return sorted(tags, key=lambda v: tuple(map(int, v.split("."))))[-1]
    except Exception:
        pass

    return None


def compare_versions(current: str, latest: str) -> tuple[bool, str]:
    """Compare versions. Returns (update_available, message)."""
    def version_tuple(v: str) -> tuple[int, int, int]:
        parts = v.split("-")[0].split(".")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0, int(parts[2]) if len(parts) > 2 else 0)

    curr_v = version_tuple(current)
    latest_v = version_tuple(latest)

    if latest_v > curr_v:
        # Determine update type
        if latest_v[0] > curr_v[0]:
            update_type = "MAJOR (breaking changes possible)"
        elif latest_v[1] > curr_v[1]:
            update_type = "MINOR (new features)"
        else:
            update_type = "PATCH (bug fixes)"
        return True, f"Template update available: {current} → {latest} ({update_type})"
    return False, f"Template is up-to-date ({current})"


def check_for_updates(
    template_repo: Optional[str] = None,
    current_version: Optional[str] = None,
    auto_update: bool = False,
) -> tuple[bool, str]:
    """
    Check for template updates.
    Returns (update_available, message).
    """
    manifest = load_version_manifest()
    if not manifest:
        # Not a versioned project, skip check
        return False, "Project not versioned (no META_FRAMEWORK_VERSION.yaml)"

    template_repo = template_repo or manifest.get("template_repo")
    if not template_repo:
        return False, "Template repository URL not configured"

    current_version = current_version or manifest.get("template_version", "0.0.0")
    latest_version = get_latest_version_from_remote(template_repo)

    if not latest_version:
        return False, "Could not determine latest template version"

    update_available, message = compare_versions(current_version, latest_version)
    return update_available, message


def load_feature_flags() -> dict:
    """Load feature flags to check update settings."""
    flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists():
        return {}
    try:
        with open(flags_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def should_check_updates() -> bool:
    """Check if update checking is enabled."""
    flags = load_feature_flags()
    update_config = flags.get("template_updates", {})
    return update_config.get("check_on_commit", True)


def should_auto_update() -> bool:
    """Check if auto-update is enabled."""
    flags = load_feature_flags()
    update_config = flags.get("template_updates", {})
    return update_config.get("auto_update", False)


def is_warn_only() -> bool:
    """Check if updates should only warn (not block)."""
    flags = load_feature_flags()
    update_config = flags.get("template_updates", {})
    return update_config.get("warn_only", True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="check_template_updates.py",
        description="Check if template updates are available",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Only warn, don't block commit (for pre-commit hook)",
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Automatically update if available (idempotent)",
    )
    parser.add_argument(
        "--template-repo",
        default="",
        help="Template repository URL (default: from version manifest)",
    )
    parser.add_argument(
        "--skip-if-disabled",
        action="store_true",
        help="Skip check if disabled in feature flags",
    )

    args = parser.parse_args(argv)

    # Check if updates are enabled
    if args.skip_if_disabled and not should_check_updates():
        return 0  # Silently skip if disabled

    # Determine auto-update from args or feature flags
    auto_update = args.auto_update or (should_auto_update() and not args.warn_only)
    warn_only = args.warn_only or is_warn_only()

    update_available, message = check_for_updates(
        template_repo=args.template_repo if args.template_repo else None,
        current_version=None,  # Will be loaded from manifest
        auto_update=auto_update,
    )

    if update_available:
        print(f"WARN: {message}")
        print("")
        print("To update your project to the latest template version:")
        print("  python3 3_bootstrap_scripts/cli.py update-template")
        print("")
        print("The update process is:")
        print("  - Idempotent (safe to run multiple times)")
        print("  - Non-breaking (protected files preserved)")
        print("  - Stateful (tracks update history)")
        print("")

        if args.auto_update:
            # Trigger update
            print("Auto-updating template...")
            try:
                result = subprocess.run(
                    ["python3", "3_bootstrap_scripts/cli.py", "update-template"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print("OK: Template updated successfully")
                    return 0
                else:
                    print(f"ERROR: Update failed: {result.stderr}")
                    return 1
            except Exception as e:
                print(f"ERROR: Failed to run update: {e}")
                return 1

        if args.warn_only:
            # Pre-commit hook mode: warn but don't block
            return 0
        else:
            # Interactive mode: suggest update
            return 0
    else:
        if message and "up-to-date" in message:
            print(f"OK: {message}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

