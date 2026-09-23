"""Layer 3D — structured memory with provenance."""

from __future__ import annotations

import json
import pathlib
import uuid
from typing import Any

from agent_platform.models import utc_now
from agent_platform.release import MEMORY_SCHEMA_VERSION
from agent_platform.security import sanitize_log_text


class MemoryStore:
    """File-backed multi-class memory."""

    def __init__(self, root: pathlib.Path):
        self.root = root.resolve()
        self.base = self.root / "6_ai_runtime_context" / "platform_memory"
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, memory_class: str) -> pathlib.Path:
        return self.base / f"{memory_class}.jsonl"

    def append(self, memory_class: str, record: dict[str, Any]) -> str:
        record_id = record.get("id") or str(uuid.uuid4())
        payload = {
            "id": record_id,
            "memory_class": memory_class,
            "schema_version": MEMORY_SCHEMA_VERSION,
            "created_at": utc_now(),
            **{
                k: sanitize_log_text(str(v)) if isinstance(v, str) else v
                for k, v in record.items()
            },
        }
        with open(self._path(memory_class), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return record_id

    def query(
        self,
        memory_class: str,
        *,
        repository_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        path = self._path(memory_class)
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if repository_id and row.get("repository_id") != repository_id:
                continue
            rows.append(row)
        return rows[-limit:]
