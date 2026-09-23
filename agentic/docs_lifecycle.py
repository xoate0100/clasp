"""Human documentation lifecycle — living status and staleness detection."""

from __future__ import annotations

import pathlib
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

STATUS_PATH = REPO_ROOT / "docs" / "PROJECT_STATUS.md"
POINTER_PATH = REPO_ROOT / "6_ai_runtime_context" / "ACTIVE_TASK_POINTER.yaml"
PLAN_PATH = REPO_ROOT / "6_ai_runtime_context" / "ACTIVE_PLAN.yaml"
BACKEND_DIRS = (REPO_ROOT / "backend", REPO_ROOT / "backend" / "src")
TESTS_DIR = REPO_ROOT / "tests"


@dataclass(frozen=True)
class ProjectStatus:
    generated_at: str
    git_head: str
    project_name: str
    plan_id: str
    phase_id: str
    current_task: object
    task_name: str
    task_status: str
    backend_modules: tuple[str, ...]
    test_modules: tuple[str, ...]
    test_count: int
    tasks_completed: tuple[int, ...]


def _load_yaml(path: pathlib.Path) -> dict:
    if yaml is None or not path.exists():
        return {}
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _project_name(root: pathlib.Path) -> str:
    mvp = _load_yaml(root / "0_phase0_bootstrap" / "MVP_SPECIFICATION.yaml")
    return str(mvp.get("Project") or mvp.get("project_name") or "Project")


def _git_head(root: pathlib.Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _pytest_collect_count(root: pathlib.Path) -> int:
    if not TESTS_DIR.exists():
        return 0
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        import re

        for line in reversed(result.stdout.splitlines()):
            match = re.search(r"(\d+)\s+tests?\s+collected", line)
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return 0


def _task_name(plan: dict, task_id: object) -> str:
    for task in plan.get("tasks") or []:
        if isinstance(task, dict) and task.get("id") == task_id:
            return str(task.get("name") or "")
    return ""


def _completed_tasks(pointer: dict, plan: dict) -> tuple[int, ...]:
    current = pointer.get("current_task")
    status = str(pointer.get("status") or "").lower()
    ids: list[int] = []
    for task in plan.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        if not isinstance(tid, int) or current is None:
            continue
        if tid < current or (status == "completed" and tid == current):
            ids.append(tid)
    return tuple(ids)


def _backend_modules(root: pathlib.Path) -> tuple[str, ...]:
    modules: list[str] = []
    for base in BACKEND_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            modules.append(str(path.relative_to(root)).replace("\\", "/"))
    return tuple(sorted(set(modules)))


def gather_status(root: pathlib.Path | None = None) -> ProjectStatus:
    root = root or REPO_ROOT
    plan = _load_yaml(PLAN_PATH)
    pointer = _load_yaml(POINTER_PATH)
    current = pointer.get("current_task")
    test_modules = tuple(sorted(p.name for p in TESTS_DIR.glob("test_*.py"))) if TESTS_DIR.exists() else ()
    return ProjectStatus(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        git_head=_git_head(root),
        project_name=_project_name(root),
        plan_id=str(plan.get("plan_id") or ""),
        phase_id=str(plan.get("phase_id") or ""),
        current_task=current,
        task_name=_task_name(plan, current),
        task_status=str(pointer.get("status") or ""),
        backend_modules=_backend_modules(root),
        test_modules=test_modules,
        test_count=_pytest_collect_count(root),
        tasks_completed=_completed_tasks(pointer, plan),
    )


def render_project_status(status: ProjectStatus) -> str:
    backend_lines = "\n".join(f"- `{m}`" for m in status.backend_modules) or "- _(none yet)_"
    test_lines = "\n".join(f"- `{m}`" for m in status.test_modules) or "- _(none)_"
    done = ", ".join(str(t) for t in status.tasks_completed) or "none"
    return f"""# {status.project_name} — Project Status (Living Report)

> **Auto-generated** by `agentic/docs_lifecycle.py`. Do not hand-edit the engineering snapshot.
> Regenerate via `python 3_bootstrap_scripts/agentic_janitor.py` or `docs_sync.py`.

**Generated:** {status.generated_at} · **Git:** `{status.git_head}`

---

## Engineering snapshot

| Item | Value |
|------|-------|
| **Plan** | `{status.plan_id}` |
| **Phase** | `{status.phase_id}` |
| **Active task** | **{status.current_task}** — {status.task_name} |
| **Task status** | `{status.task_status}` |
| **Tasks completed** | {done} |
| **Pytest collected** | {status.test_count} tests |
| **Backend modules** | {len(status.backend_modules)} Python file(s) |

### Backend modules

{backend_lines}

### Test modules

{test_lines}

---

## Verification commands

```bash
pip install -r requirements.txt
pre-commit run --all-files
python 3_bootstrap_scripts/agentic_coordinate_validate.py
python 3_bootstrap_scripts/cli.py agentic validate
```
"""


def write_project_status(root: pathlib.Path | None = None) -> pathlib.Path:
    root = root or REPO_ROOT
    content = render_project_status(gather_status(root))
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(content, encoding="utf-8")
    return STATUS_PATH


def status_source_paths(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    root = root or REPO_ROOT
    paths = [POINTER_PATH, PLAN_PATH]
    for base in BACKEND_DIRS:
        if base.exists():
            paths.extend(base.rglob("*.py"))
    if TESTS_DIR.exists():
        paths.extend(TESTS_DIR.glob("test_*.py"))
    return paths


def is_project_status_stale(root: pathlib.Path | None = None) -> tuple[bool, str]:
    root = root or REPO_ROOT
    if not STATUS_PATH.exists():
        return True, "PROJECT_STATUS.md missing"

    status_mtime = STATUS_PATH.stat().st_mtime
    for source in status_source_paths(root):
        if source.exists() and source.stat().st_mtime > status_mtime:
            return True, source.name
    return False, ""


def refresh_human_docs(root: pathlib.Path | None = None) -> list[str]:
    import os

    if os.environ.get("META_PYTEST") == "1":
        return []
    root = root or REPO_ROOT
    actions: list[str] = []
    stale, reason = is_project_status_stale(root)
    if stale:
        write_project_status(root)
        actions.append(f"regenerated PROJECT_STATUS.md (stale vs {reason})")
    return actions
