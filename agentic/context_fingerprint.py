"""Deterministic AI_CONTEXT source fingerprint — cross-platform staleness detection."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from agentic.janitor import context_source_paths

_FINGERPRINT_RE = re.compile(
    r"^\*\*Content fingerprint:\*\*\s*`?([0-9a-f]{64})`?\s*$",
    re.MULTILINE,
)


def compute_context_fingerprint(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    for source in sorted(context_source_paths(root), key=lambda p: p.as_posix()):
        try:
            rel = source.relative_to(root).as_posix()
        except ValueError:
            rel = source.name
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        if source.exists():
            digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def parse_context_fingerprint(text: str) -> str | None:
    match = _FINGERPRINT_RE.search(text)
    return match.group(1) if match else None
