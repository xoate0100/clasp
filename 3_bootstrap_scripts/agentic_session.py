#!/usr/bin/env python3
"""
Agentic session harness — entry gate + reviewer/validator pipelines.

Cursor (or any agent harness) should call `session-start` at the beginning of work
and `pre-commit-review` before committing.

Usage:
    python 3_bootstrap_scripts/agentic_session.py session-start
    python 3_bootstrap_scripts/agentic_session.py pre-commit-review
    python 3_bootstrap_scripts/agentic_session.py validate
    python 3_bootstrap_scripts/agentic_session.py tool resurrection_scan
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.graph_executor import playbook, start_run, transition  # noqa: E402
from agentic.harness import run_reviewer_pipeline, run_tool  # noqa: E402
from agentic.run_log import append_agent_run, finalize_run  # noqa: E402
from agentic.schemas import AgentRunRecord  # noqa: E402


def _log_step(run_id: str, agent: str, ok: bool, error: str = "") -> None:
    append_agent_run(
        AgentRunRecord(
            agent=agent,
            ok=ok,
            error=error or None,
            finished_at=datetime.now(timezone.utc),
        ),
        run_id=run_id,
        log_path=REPO_ROOT / "6_ai_runtime_context" / "AGENTIC_RUN_LOG.yaml",
    )


def cmd_session_start(_: argparse.Namespace) -> int:
    run_id = str(uuid.uuid4())
    start_run()

    from agentic.optional_tools import is_tool_enabled  # noqa: E402

    if is_tool_enabled("janitor", REPO_ROOT):
        code = subprocess.call(
            [sys.executable, "3_bootstrap_scripts/agentic_janitor.py"],
            cwd=REPO_ROOT,
        )
        _log_step(run_id, "janitor", code == 0, "" if code == 0 else "janitor failed")
    else:
        code = subprocess.call(
            [sys.executable, "3_bootstrap_scripts/generate_ai_context.py"],
            cwd=REPO_ROOT,
        )
        _log_step(run_id, "context_regenerate", code == 0, "" if code == 0 else "context generation failed")

    gate = subprocess.call(
        [sys.executable, "3_bootstrap_scripts/phase_gate.py", "--status"],
        cwd=REPO_ROOT,
    )
    _log_step(run_id, "phase_gate", gate == 0)
    finalize_run(run_id, "clean" if code == 0 and gate == 0 else "fail")
    return code


def cmd_pre_commit_review(_: argparse.Namespace) -> int:
    run_id = str(uuid.uuid4())
    code = run_reviewer_pipeline(REPO_ROOT)
    _log_step(run_id, "reviewer", code == 0, "" if code == 0 else "reviewer pipeline failed")
    finalize_run(run_id, "clean" if code == 0 else "findings")
    return code


def cmd_validate(_: argparse.Namespace) -> int:
    return subprocess.call(
        [sys.executable, "3_bootstrap_scripts/agentic_coordinate_validate.py"],
        cwd=REPO_ROOT,
    )


def cmd_tool(args: argparse.Namespace) -> int:
    return run_tool(args.name, args.extra_args or [], root=REPO_ROOT)


def cmd_graph_playbook(_: argparse.Namespace) -> int:
    print(playbook())
    return 0


def cmd_graph_advance(args: argparse.Namespace) -> int:
    state = transition(args.outcome)
    print(f"[graph] now at: {state.get('current_agent')} ({state.get('last_transition')})")
    print(playbook(state))
    return 0


def cmd_graph_status(_: argparse.Namespace) -> int:
    from agentic.graph_executor import load_state

    state = load_state()
    print(
        f"[graph] agent={state.get('current_agent')} loops={state.get('review_loops')} "
        f"transition={state.get('last_transition')}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="agentic_session")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("session-start", help="Regenerate context + print phase gate status")
    sub.add_parser("pre-commit-review", help="Run resurrection + drift + phase gate on staged changes")
    sub.add_parser("validate", help="Run all agentic registry validators")

    tool_p = sub.add_parser("tool", help="Run a single AGENT_REGISTRY tool by name")
    tool_p.add_argument("name", help="Tool id from AGENT_REGISTRY.yaml")
    tool_p.add_argument("extra_args", nargs="*", help="Extra CLI args for script tools")

    graph = sub.add_parser("graph", help="Agent graph state machine")
    graph_sub = graph.add_subparsers(dest="graph_cmd", required=True)
    graph_sub.add_parser("playbook", help="Print current role playbook")
    graph_sub.add_parser("status", help="Print graph state")
    adv = graph_sub.add_parser("advance", help="Transition graph by outcome")
    adv.add_argument(
        "--outcome",
        required=True,
        choices=["ok", "fail", "clean", "findings", "needs_decision"],
    )

    args = parser.parse_args()
    handlers = {
        "session-start": cmd_session_start,
        "pre-commit-review": cmd_pre_commit_review,
        "validate": cmd_validate,
        "tool": cmd_tool,
    }
    if args.cmd == "graph":
        graph_handlers = {
            "playbook": cmd_graph_playbook,
            "status": cmd_graph_status,
            "advance": cmd_graph_advance,
        }
        return graph_handlers[args.graph_cmd](args)
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
