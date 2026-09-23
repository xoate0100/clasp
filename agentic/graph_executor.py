"""Cursor-facing agent graph executor — role playbooks and state transitions."""

from __future__ import annotations

import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise ImportError("PyYAML required") from exc

from agentic.live_gate import check_turn_budget
from agentic.registry import load_agent_registry

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "6_ai_runtime_context" / "AGENT_GRAPH_STATE.yaml"

DEFAULT_STATE: dict[str, Any] = {
    "version": 1,
    "current_agent": "spec_reader",
    "review_loops": 0,
    "run_id": None,
    "turn_counts": {},
    "last_transition": None,
}


def load_state(path: pathlib.Path | None = None) -> dict[str, Any]:
    path = path or STATE_PATH
    if not path.exists():
        return dict(DEFAULT_STATE)
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    merged = dict(DEFAULT_STATE)
    merged.update(data if isinstance(data, dict) else {})
    return merged


def save_state(state: dict[str, Any], path: pathlib.Path | None = None) -> None:
    path = path or STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(state, handle, sort_keys=False, allow_unicode=True)


def _agent_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        a["id"]: a
        for a in (registry.get("agents") or [])
        if isinstance(a, dict) and a.get("id")
    }


def _edges_from(registry: dict[str, Any], agent_id: str) -> list[dict[str, Any]]:
    graph = registry.get("graph") or {}
    return [e for e in (graph.get("edges") or []) if e.get("from") == agent_id]


def start_run(path: pathlib.Path | None = None) -> dict[str, Any]:
    registry = load_agent_registry(REPO_ROOT)
    graph = registry.get("graph") or {}
    state = load_state(path)
    state["run_id"] = str(uuid.uuid4())
    state["current_agent"] = graph.get("start", "spec_reader")
    state["review_loops"] = 0
    state["turn_counts"] = {state["current_agent"]: 1}
    state["last_transition"] = "session_start"
    save_state(state, path)
    return state


def increment_turn(state: dict[str, Any]) -> None:
    agent = state.get("current_agent", "spec_reader")
    turns = state.setdefault("turn_counts", {})
    turns[agent] = int(turns.get(agent, 0)) + 1
    check_turn_budget(agent, turns[agent], REPO_ROOT)


def transition(outcome: str, path: pathlib.Path | None = None) -> dict[str, Any]:
    """Advance graph state using AGENT_REGISTRY.yaml edges."""
    registry = load_agent_registry(REPO_ROOT)
    state = load_state(path)
    current = state.get("current_agent", "spec_reader")
    edges = _edges_from(registry, current)

    next_agent = None
    for edge in edges:
        when = edge.get("when")
        if when is None or when == outcome:
            next_agent = edge.get("to")
            break

    if next_agent is None:
        state["last_transition"] = f"{current}:{outcome}:hold"
        save_state(state, path)
        return state

    if current == "reviewer" and next_agent == "implementer":
        state["review_loops"] = int(state.get("review_loops", 0)) + 1
        max_loops = int((registry.get("graph") or {}).get("max_review_loops", 3))
        if state["review_loops"] >= max_loops:
            next_agent = "done"
            state["last_transition"] = "escalated:max_review_loops"
            state["current_agent"] = next_agent
            save_state(state, path)
            return state

    state["current_agent"] = next_agent
    state["last_transition"] = f"{current}:{outcome}->{next_agent}"
    turns = state.setdefault("turn_counts", {})
    turns[next_agent] = int(turns.get(next_agent, 0)) + 1
    check_turn_budget(next_agent, turns[next_agent], REPO_ROOT)
    save_state(state, path)
    return state


def playbook(state: dict[str, Any] | None = None, root: pathlib.Path | None = None) -> str:
    """Markdown instructions for the current graph node."""
    root = root or REPO_ROOT
    registry = load_agent_registry(root)
    state = state or load_state()
    agent_id = state.get("current_agent", "spec_reader")
    agents = _agent_map(registry)
    agent = agents.get(agent_id, {})
    graph = registry.get("graph") or {}

    lines = [
        f"# Agent graph node: `{agent_id}`",
        "",
        f"**Role:** {agent.get('role', 'unknown')}",
        f"**Output model:** {agent.get('output_model', 'AgentRunRecord')}",
        f"**Review loops:** {state.get('review_loops', 0)} / {graph.get('max_review_loops', 3)}",
        "",
        "## Tools (run via CLI)",
    ]
    for tool in agent.get("tools") or []:
        lines.append(f"- `python 3_bootstrap_scripts/agentic_session.py tool {tool}`")

    lines.extend(
        [
            "",
            "## Handoffs",
            f"Allowed next roles: {', '.join(agent.get('handoffs') or [])}",
            "",
            "## Transition commands",
            "- After success: `python 3_bootstrap_scripts/agentic_session.py graph advance --outcome ok`",
            "- After validation fail: `graph advance --outcome fail`",
            "- Reviewer clean: `graph advance --outcome clean`",
            "- Reviewer findings: `graph advance --outcome findings`",
            "- Needs decision: `graph advance --outcome needs_decision`",
            "",
            "## Session commands",
            "- Start: `python 3_bootstrap_scripts/cli.py agentic session-start`",
            "- Pre-commit review: `python 3_bootstrap_scripts/cli.py agentic pre-commit-review`",
        ]
    )
    return "\n".join(lines)
