"""Append-only structured run log writer."""

from __future__ import annotations

import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise ImportError("PyYAML required. Install with: pip install PyYAML") from exc

from agentic.schemas import AgentRunRecord, GraphRunRecord

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = REPO_ROOT / "6_ai_runtime_context" / "AGENTIC_RUN_LOG.yaml"


def _load_log(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "runs": []}
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        return {"version": 1, "runs": []}
    data.setdefault("version", 1)
    data.setdefault("runs", [])
    return data


def append_agent_run(
    record: AgentRunRecord,
    *,
    run_id: str | None = None,
    plan_id: str = "",
    phase_id: str = "",
    log_path: pathlib.Path | None = None,
) -> str:
    """Append an agent record under a graph run; creates run bucket if needed."""
    log_path = log_path or DEFAULT_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)

    data = _load_log(log_path)
    runs: list[dict[str, Any]] = data["runs"]

    run_id = run_id or str(uuid.uuid4())
    target = None
    for run in runs:
        if run.get("run_id") == run_id:
            target = run
            break

    if target is None:
        target = GraphRunRecord(run_id=run_id, plan_id=plan_id, phase_id=phase_id).model_dump(mode="json")
        runs.append(target)

    agents = target.setdefault("agents", [])
    payload = record.model_dump(mode="json")
    if record.finished_at is None:
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    agents.append(payload)

    data["updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with open(log_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)

    return run_id


def finalize_run(
    run_id: str,
    outcome: str,
    *,
    log_path: pathlib.Path | None = None,
) -> None:
    log_path = log_path or DEFAULT_LOG_PATH
    data = _load_log(log_path)
    for run in data.get("runs", []):
        if run.get("run_id") == run_id:
            run["outcome"] = outcome
            run["finished_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            break
    with open(log_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)
