"""Gate expensive or side-effecting agentic operations behind explicit opt-in."""

from __future__ import annotations

import os
from typing import Any

from agentic.registry import load_agent_registry

DEFAULT_ENV_VAR = "META_AGENTIC_LIVE_ENABLED"


class LiveCallBlocked(PermissionError):
    """Raised when a live agentic tool runs without the env gate."""


def live_env_var(root=None) -> str:
    registry = load_agent_registry(root)
    guardrails = registry.get("cost_guardrails") or {}
    return str(guardrails.get("live_calls_env_gate") or DEFAULT_ENV_VAR)


def is_live_enabled(root=None) -> bool:
    return os.environ.get(live_env_var(root)) == "1"


def require_live_enabled(tool_name: str = "", root=None) -> None:
    if is_live_enabled(root):
        return
    env_var = live_env_var(root)
    label = f" for tool '{tool_name}'" if tool_name else ""
    raise LiveCallBlocked(
        f"Live agentic calls blocked{label}. Set {env_var}=1 to opt in to expensive or external operations."
    )


def tool_requires_live(registry: dict[str, Any], tool_name: str) -> bool:
    cfg = (registry.get("tools") or {}).get(tool_name) or {}
    return bool(cfg.get("requires_live"))


def check_turn_budget(agent_id: str, turns: int, root=None) -> None:
    registry = load_agent_registry(root)
    guardrails = registry.get("cost_guardrails") or {}
    per_agent = (guardrails.get("per_agent") or {}).get(agent_id) or {}
    max_turns = int(per_agent.get("max_turns", 0))
    if max_turns and turns > max_turns:
        raise LiveCallBlocked(
            f"Agent '{agent_id}' exceeded max_turns ({turns} > {max_turns}). Escalate to human."
        )
