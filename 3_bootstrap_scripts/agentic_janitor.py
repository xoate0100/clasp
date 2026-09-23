#!/usr/bin/env python3
"""
Agentic session janitor — refresh stale trackers, rebuild RAG index, trim run log.

Usage:
    python 3_bootstrap_scripts/agentic_janitor.py
    python 3_bootstrap_scripts/agentic_janitor.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.janitor import (  # noqa: E402
    is_context_stale,
    is_knowledge_index_stale,
    janitor_guard_enter,
    janitor_guard_exit,
    rebuild_knowledge_index,
    regenerate_context,
    trim_run_log,
)
from agentic.optional_tools import is_tool_enabled  # noqa: E402
from agentic.run_log import append_agent_run  # noqa: E402
from agentic.schemas import AgentRunRecord  # noqa: E402


def main() -> int:
    if not is_tool_enabled("janitor"):
        print("[agentic-janitor] SKIP: optional tool disabled")
        return 0

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report actions without executing")
    args = parser.parse_args()

    if not janitor_guard_enter():
        print("[agentic-janitor] SKIP: already running (recursion guard)")
        return 0

    actions: list[str] = []
    exit_code = 0

    try:
        stale_ctx, ctx_reason = is_context_stale(REPO_ROOT)
        if stale_ctx:
            actions.append(f"regenerate AI_CONTEXT.md (stale vs {ctx_reason})")
            if not args.dry_run and regenerate_context(REPO_ROOT) != 0:
                exit_code = 1

        if is_tool_enabled("knowledge_index"):
            stale_idx, idx_reason = is_knowledge_index_stale(REPO_ROOT)
            if stale_idx:
                actions.append(f"rebuild knowledge index (stale vs {idx_reason})")
                if not args.dry_run and rebuild_knowledge_index(REPO_ROOT) != 0:
                    exit_code = 1

        if trim_run_log(root=REPO_ROOT):
            actions.append("trimmed AGENTIC_RUN_LOG.yaml")

        if is_tool_enabled("doc_lifecycle"):
            from agentic.docs_lifecycle import refresh_human_docs  # noqa: E402
            from agentic.doc_governance import sync_archive_readme, sync_documentation_index  # noqa: E402

            for doc_action in refresh_human_docs(REPO_ROOT):
                actions.append(doc_action)
            if sync_documentation_index(REPO_ROOT):
                actions.append("synced DOCUMENTATION_INDEX active/archive tables")
            if sync_archive_readme(REPO_ROOT):
                actions.append("synced archive README table")

        if not args.dry_run:
            append_agent_run(
                AgentRunRecord(
                    agent="janitor",
                    ok=exit_code == 0,
                    metadata={"actions": actions, "dry_run": args.dry_run},
                    finished_at=datetime.now(timezone.utc),
                ),
                run_id=str(uuid.uuid4()),
                log_path=REPO_ROOT / "6_ai_runtime_context" / "AGENTIC_RUN_LOG.yaml",
            )

        if actions:
            print("[agentic-janitor] actions:")
            for action in actions:
                print(f"  - {action}")
        else:
            print("[agentic-janitor] OK: nothing stale")
    finally:
        janitor_guard_exit()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
