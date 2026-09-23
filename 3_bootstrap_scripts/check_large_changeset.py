#!/usr/bin/env python3
"""
Pre-commit hook to warn if too many files changed since last commit.
Non-blocking warning to alert about potential large uncommitted changesets.
"""
import sys
import subprocess
import pathlib

# Threshold for warning (configurable)
WARN_THRESHOLD = 20

def get_uncommitted_file_count():
    """Get count of uncommitted files (modified + untracked)"""
    try:
        # Get modified files
        modified = subprocess.check_output(
            ["git", "diff", "--name-only"],
            text=True,
            timeout=30,
        ).strip().splitlines()
        modified = [f for f in modified if f.strip()]

        # Get untracked files
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            text=True,
            timeout=30,
        ).strip().splitlines()
        untracked = [f for f in untracked if f.strip()]

        total = len(modified) + len(untracked)
        return total, modified, untracked
    except subprocess.CalledProcessError:
        return 0, [], []

def get_files_since_last_commit():
    """Get count of files changed since last commit"""
    try:
        # Get files changed since last commit
        files = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD"],
            text=True,
            timeout=30,
        ).strip().splitlines()
        files = [f for f in files if f.strip()]

        # Get untracked files
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            text=True,
            timeout=30,
        ).strip().splitlines()
        untracked = [f for f in untracked if f.strip()]

        total = len(files) + len(untracked)
        return total, files, untracked
    except subprocess.CalledProcessError:
        # If no commits exist yet, check uncommitted files
        return get_uncommitted_file_count()

def main():
    """Check for large changeset and warn if threshold exceeded"""
    count, modified, untracked = get_files_since_last_commit()

    if count > WARN_THRESHOLD:
        print(f"[large-changeset] WARNING: {count} files changed since last commit (threshold: {WARN_THRESHOLD})")
        print(f"[large-changeset] Consider committing incrementally to avoid large uncommitted changesets.")
        print(f"[large-changeset] Modified files: {len(modified)}")
        print(f"[large-changeset] Untracked files: {len(untracked)}")
        print(f"[large-changeset] Tip: Use 'python3 3_bootstrap_scripts/cli.py commit-checkpoint' to commit with validation")
        print(f"[large-changeset] Reference: See docs/COMMIT_STRATEGY.md for commit frequency best practices")
        # Non-blocking - exit with success
        sys.exit(0)

    # All good
    sys.exit(0)

if __name__ == "__main__":
    main()
