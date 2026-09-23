#!/usr/bin/env python3
"""
Feedback Collector
Collects AI feedback from projects and sends it to the template repository.
Anonymizes project-specific data and aggregates patterns.
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

try:
    import requests
except ImportError:
    requests = None


FEEDBACK_LOG = pathlib.Path("6_ai_runtime_context/ai_feedback_log.json")
FEATURE_FLAGS = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
VERSION_MANIFEST = pathlib.Path("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")


def load_feature_flags() -> Dict[str, Any]:
    """Load feature flags to check feedback collection settings."""
    if not FEATURE_FLAGS.exists():
        return {}
    try:
        with open(FEATURE_FLAGS, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def is_feedback_enabled() -> bool:
    """Check if feedback collection is enabled."""
    flags = load_feature_flags()
    feedback_config = flags.get("feedback_collection", {})
    # Default to enabled if not specified
    return feedback_config.get("enabled", True)


def get_template_repo() -> Optional[str]:
    """Get template repository URL from version manifest."""
    if not VERSION_MANIFEST.exists():
        return None
    try:
        with open(VERSION_MANIFEST, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
            return manifest.get("template_repo")
    except Exception:
        return None


def anonymize_path(path: str, project_root: str = "[PROJECT_ROOT]") -> str:
    """Anonymize project-specific paths."""
    # Replace absolute paths with placeholders
    path = re.sub(r"/[^/]+/[^/]+/", f"{project_root}/", path)
    path = re.sub(r"[a-zA-Z]:\\[^\\]+\\[^\\]+\\", f"{project_root}/", path)
    # Replace common project directories
    path = re.sub(r"\b(frontend|backend|shared|apps|packages)/[^/]+", r"\1/[COMPONENT]", path)
    return path


def anonymize_text(text: str) -> str:
    """Anonymize sensitive information in text."""
    # Remove URLs (except template repo)
    text = re.sub(r"https?://[^\s]+", "[URL]", text)
    # Remove email addresses
    text = re.sub(r"\b[\w.-]+@[\w.-]+\.\w+\b", "[EMAIL]", text)
    # Remove API keys, tokens
    text = re.sub(r"\b(api[_-]?key|token|secret|password)\s*[:=]\s*[\w-]+\b", r"\1=[REDACTED]", text, flags=re.IGNORECASE)
    # Remove file paths (anonymize)
    text = anonymize_path(text)
    return text


def hash_project_id() -> str:
    """Generate a hash of project identifier (for tracking without exposing identity)."""
    try:
        # Use git remote URL if available
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            remote = result.stdout.strip()
            return hashlib.sha256(remote.encode()).hexdigest()[:8]
    except Exception:
        pass
    # Fallback: use current directory name hash
    cwd = str(pathlib.Path.cwd())
    return hashlib.sha256(cwd.encode()).hexdigest()[:8]


def load_feedback_log() -> List[Dict[str, Any]]:
    """Load AI feedback log."""
    if not FEEDBACK_LOG.exists():
        return []
    try:
        with open(FEEDBACK_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("entries", [])
    except Exception:
        return []


def entry_hash(entry: Dict[str, Any]) -> str:
    """Stable hash for dedupe/submission tracking."""
    payload = {
        "category": entry.get("category", ""),
        "issue": entry.get("issue", ""),
        "context": entry.get("context", ""),
        "files": entry.get("files", []),
        "timestamp": entry.get("timestamp", ""),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_submitted_hashes() -> set[str]:
    """Load hashes of entries already submitted upstream."""
    if not FEEDBACK_LOG.exists():
        return set()
    try:
        with open(FEEDBACK_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
        hashes = data.get("submitted_entry_hashes", [])
        return set(hashes) if isinstance(hashes, list) else set()
    except Exception:
        return set()


def save_submitted_hashes(new_hashes: set[str]) -> None:
    """Persist submitted entry hashes to avoid duplicate submissions."""
    if not FEEDBACK_LOG.exists():
        return
    try:
        with open(FEEDBACK_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"entries": []}

    existing = data.get("submitted_entry_hashes", [])
    if not isinstance(existing, list):
        existing = []
    data["submitted_entry_hashes"] = sorted(set(existing) | new_hashes)

    with open(FEEDBACK_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def categorize_feedback(entry: Dict[str, Any]) -> str:
    """Categorize feedback entry."""
    category = entry.get("category", "UNKNOWN")
    issue = entry.get("issue", "").lower()

    # Map to feedback categories
    if "guardrail" in issue or "permission" in issue:
        return "GUARDRAIL_VIOLATION"
    if "architecture" in issue or "solid" in issue or "layer" in issue:
        return "ARCHITECTURE_VIOLATION"
    if "stack coupling" in issue or "stack_coupling" in issue or category in ("STACK_COUPLING", "PORTABILITY"):
        return "STACK_COUPLING" if "portability" not in issue else "PORTABILITY"
    if "portability" in issue or "windows" in issue and "bash" in issue:
        return "PORTABILITY"
    if "drift" in issue or "mismatch" in issue:
        return "TEMPLATE_DRIFT"
    if "update" in issue or "migration" in issue:
        return "UPDATE_ISSUE"
    if "schema" in issue or "validation" in issue:
        return "SCHEMA_MISMATCH"
    if "performance" in issue or "slow" in issue:
        return "PERFORMANCE_ISSUE"
    if "documentation" in issue or "doc" in issue or "missing" in issue:
        return "DOCUMENTATION_GAP"
    if category == "ANOMALY":
        return "AI_ANOMALY"

    return "PATTERN_DETECTED"


def aggregate_feedback(entries: List[Dict[str, Any]], submitted_hashes: Optional[set[str]] = None) -> List[Dict[str, Any]]:
    """Aggregate and anonymize feedback entries."""
    aggregated = []
    project_id = hash_project_id()

    already_submitted = submitted_hashes or set()
    for entry in entries:
        h = entry_hash(entry)
        if h in already_submitted:
            continue
        # Skip if too old (optional: only recent feedback)
        timestamp = entry.get("timestamp", "")
        if timestamp:
            try:
                entry_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                # Only include feedback from last 90 days
                age_days = (datetime.now(entry_time.tzinfo) - entry_time).days
                if age_days > 90:
                    continue
            except Exception:
                pass

        # Anonymize entry
        anonymized = {
            "category": categorize_feedback(entry),
            "issue": anonymize_text(entry.get("issue", "")),
            "context": anonymize_text(entry.get("context", "")),
            "timestamp": entry.get("timestamp", ""),
            "entry_hash": h,
            "requires_human_intervention": entry.get("requires_human_intervention", False),
            "attempt_count": entry.get("attempt_count", 1),
            "project_id_hash": project_id,  # For tracking patterns without exposing identity
        }

        # Anonymize files
        files = entry.get("files", [])
        if files:
            anonymized["files"] = [anonymize_path(f) for f in files]

        # Anonymize traceability
        trace = entry.get("traceability", {})
        if trace:
            anonymized["traceability"] = {
                k: anonymize_text(str(v)) if v else "" for k, v in trace.items()
            }

        aggregated.append(anonymized)

    return aggregated


def create_github_issue(
    template_repo: str,
    title: str,
    body: str,
    labels: List[str],
    token: Optional[str] = None,
) -> bool:
    """Create a GitHub issue via API."""
    if not requests:
        print("WARN: requests library not available. Install with: pip install requests")
        return False

    # Extract owner/repo from URL
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", template_repo)
    if not match:
        print(f"ERROR: Could not parse template repo URL: {template_repo}")
        return False

    owner, repo = match.groups()
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    if token:
        headers["Authorization"] = f"token {token}"

    payload = {
        "title": title,
        "body": body,
        "labels": labels,
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            issue_url = response.json().get("html_url", "")
            print(f"OK: Feedback submitted as issue: {issue_url}")
            return True
        elif response.status_code == 401:
            print("ERROR: Authentication failed. Check your GitHub token:")
            print("  - Token may be expired or invalid")
            print("  - Token may not have required permissions (public_repo or repo scope)")
            print("  - For private repos, token needs 'repo' scope")
            print("  - For public repos, token needs 'public_repo' scope")
            return False
        elif response.status_code == 403:
            print("ERROR: Permission denied. Your token may not have permission to create issues.")
            print("  - Check token has 'public_repo' scope (public repos) or 'repo' scope (private repos)")
            print("  - Verify you have write access to the template repository")
            return False
        elif response.status_code == 404:
            print("ERROR: Template repository not found or not accessible.")
            print(f"  - Check template_repo URL: {template_repo}")
            print("  - Verify repository exists and is accessible")
            return False
        else:
            error_msg = response.text[:200] if response.text else "Unknown error"
            print(f"ERROR: Failed to create issue: {response.status_code}")
            print(f"  Response: {error_msg}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Network error submitting feedback: {e}")
        print("  - Check internet connectivity")
        print("  - Verify GitHub API is accessible")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False


def group_feedback_by_category(feedback: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group feedback entries by category."""
    grouped = {}
    for entry in feedback:
        category = entry.get("category", "UNKNOWN")
        grouped.setdefault(category, []).append(entry)
    return grouped


def format_feedback_issue(category: str, entries: List[Dict[str, Any]]) -> tuple[str, str]:
    """Format feedback as GitHub issue title and body."""
    # Title: Category and summary
    title = f"[Feedback] {category.replace('_', ' ').title()}"

    # Body: Aggregated feedback
    body_parts = [
        f"## Feedback Category: {category}",
        "",
        f"**Count**: {len(entries)} feedback entries",
        f"**Collected**: {datetime.utcnow().isoformat()}Z",
        "",
        "### Aggregated Feedback",
        "",
    ]

    if len(entries) == 1:
        only = entries[0]
        issue_text = only.get("issue", "").strip() or "Unknown issue"
        body_parts.append("### Full Feedback")
        body_parts.append("")
        body_parts.append(issue_text)
        body_parts.append("")

        context_text = only.get("context", "").strip()
        if context_text:
            body_parts.append("### Context")
            body_parts.append("")
            body_parts.append(context_text)
            body_parts.append("")

        files = only.get("files", [])
        if files:
            body_parts.append("### Related Files")
            body_parts.append("")
            for file_path in files:
                body_parts.append(f"- {file_path}")
            body_parts.append("")

        body_parts.extend([
            "---",
            "",
            "*This issue was auto-generated from anonymized project feedback.*",
            "*To disable feedback collection, set `feedback_collection.enabled: false` in feature_flags.yml*",
        ])
        return title, "\n".join(body_parts)

    # Group by issue pattern
    issue_patterns = {}
    for entry in entries:
        issue = entry.get("issue", "Unknown issue")
        # Normalize issue text for grouping
        pattern_key = issue[:100]  # Use first 100 chars as pattern key
        issue_patterns.setdefault(pattern_key, []).append(entry)

    for pattern, pattern_entries in issue_patterns.items():
        body_parts.append(f"#### Pattern: {pattern[:80]}...")
        body_parts.append(f"**Occurrences**: {len(pattern_entries)}")
        body_parts.append("")

        # Show sample entries
        for entry in pattern_entries[:3]:  # Show up to 3 examples
            body_parts.append(f"- **Issue**: {entry.get('issue', '')[:200]}")
            if entry.get("context"):
                body_parts.append(f"  - Context: {entry.get('context')[:150]}")
            if entry.get("files"):
                body_parts.append(f"  - Files: {', '.join(entry.get('files', [])[:5])}")
            body_parts.append("")

        if len(pattern_entries) > 3:
            body_parts.append(f"  - ... and {len(pattern_entries) - 3} more occurrences")
            body_parts.append("")

    body_parts.extend([
        "---",
        "",
        "*This issue was auto-generated from anonymized project feedback.*",
        "*To disable feedback collection, set `feedback_collection.enabled: false` in feature_flags.yml*",
    ])

    return title, "\n".join(body_parts)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="feedback_collector.py",
        description="Collect and submit AI feedback to template repository",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be submitted without sending",
    )
    parser.add_argument(
        "--github-token",
        default="",
        help="GitHub token for API access (or set GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--template-repo",
        default="",
        help="Template repository URL (default: from version manifest)",
    )

    args = parser.parse_args(argv)

    # Check if feedback is enabled
    if not is_feedback_enabled():
        print("INFO: Feedback collection is disabled in feature_flags.yml")
        return 0

    # Get template repo
    template_repo = args.template_repo or get_template_repo()
    if not template_repo:
        print("ERROR: Template repository URL required")
        print("Specify --template-repo or set in META_FRAMEWORK_VERSION.yaml")
        return 1

    # Load and aggregate feedback
    print("Collecting feedback...")
    entries = load_feedback_log()
    if not entries:
        print("INFO: No feedback entries found")
        return 0

    submitted_hashes = load_submitted_hashes()
    aggregated = aggregate_feedback(entries, submitted_hashes=submitted_hashes)
    if not aggregated:
        print("INFO: No recent feedback to submit")
        return 0

    # Group by category
    grouped = group_feedback_by_category(aggregated)

    print(f"Found {len(aggregated)} feedback entries in {len(grouped)} categories")

    # Get GitHub token
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN", "")

    if args.dry_run:
        print("\n=== DRY RUN: Would submit the following ===")
        for category, category_entries in grouped.items():
            title, body = format_feedback_issue(category, category_entries)
            print(f"\nCategory: {category}")
            print(f"Title: {title}")
            print(f"Body preview: {body[:200]}...")
        return 0

    if not github_token:
        print("INFO: No GitHub token provided. Feedback will be saved locally but not submitted.")
        print("")
        print("To submit feedback to the template repository, you need a GitHub Personal Access Token.")
        print("")
        print("Quick Setup:")
        print("1. Create token: GitHub Settings → Developer settings → Personal access tokens")
        print("2. Select scope: 'public_repo' (public repos) or 'repo' (private repos)")
        print("3. Set environment variable: export GITHUB_TOKEN=your_token_here")
        print("4. Re-run: python3 3_bootstrap_scripts/cli.py submit-feedback")
        print("")
        print("For detailed instructions, see: docs/FEEDBACK_AUTHENTICATION.md")
        print("")
        print("Note: Feedback collection is optional. Your project works fine without submitting feedback.")
        # Return 0 (success) since feedback is logged locally - this is graceful degradation
        return 0

    # Submit feedback for each category
    success_count = 0
    newly_submitted: set[str] = set()
    for category, category_entries in grouped.items():
        title, body = format_feedback_issue(category, category_entries)
        labels = ["feedback", "auto-generated", category.lower().replace("_", "-")]

        if create_github_issue(template_repo, title, body, labels, github_token):
            success_count += 1
            newly_submitted.update(
                entry.get("entry_hash", "") for entry in category_entries if entry.get("entry_hash")
            )

    if newly_submitted:
        save_submitted_hashes(newly_submitted)

    print(f"\nSubmitted {success_count}/{len(grouped)} feedback categories")
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

