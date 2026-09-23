"""Layer 1 — observation and evidence collection."""

from __future__ import annotations

import hashlib
import pathlib
import uuid

from agent_platform.models import EvidenceBundle, EvidenceItem, Provenance, RepositoryProfile
from agent_platform.security import norm_path, should_skip_dir

EVIDENCE_KINDS = {
    "config": {".yml", ".yaml", ".json", ".toml"},
    "documentation": {".md"},
    "schema": {".schema.json"},
    "test": set(),
    "script": {".py", ".sh"},
}


def _kind_for(path: str) -> str:
    fwd = norm_path(path)
    if "/tests/" in fwd or fwd.startswith("tests/") or "_test." in fwd or ".test." in fwd:
        return "test"
    suffix = pathlib.Path(path).suffix.lower()
    if suffix == ".schema.json" or "/7_schemas/" in fwd:
        return "schema"
    for kind, suffixes in EVIDENCE_KINDS.items():
        if suffix in suffixes:
            return kind
    return "file"


def collect_evidence(profile: RepositoryProfile, root: pathlib.Path, max_items: int = 500) -> EvidenceBundle:
    root = root.resolve()
    items: list[EvidenceItem] = []
    priority_dirs = [
        "0_phase0_bootstrap",
        "1_global_standards",
        "3_bootstrap_scripts",
        "5_reference_architectures",
        "7_schemas",
        "agentic",
        "agent_platform",
        "docs",
        "tests",
    ]

    for rel_dir in priority_dirs:
        base = root / rel_dir
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(should_skip_dir(part) for part in path.parts):
                continue
            rel = norm_path(str(path.relative_to(root)))
            content = path.read_bytes()
            if len(content) > 1_000_000:
                continue
            digest = hashlib.sha256(content).hexdigest()[:16]
            items.append(
                EvidenceItem(
                    evidence_id=str(uuid.uuid4()),
                    kind=_kind_for(rel),
                    path=rel,
                    summary=f"{_kind_for(rel)}:{rel}",
                    provenance=Provenance(
                        source="layer1.evidence_collector",
                        path=rel,
                        content_hash=digest,
                    ),
                )
            )
            if len(items) >= max_items:
                break
        if len(items) >= max_items:
            break

    return EvidenceBundle(
        bundle_id=str(uuid.uuid4()),
        repository_id=profile.repository_id,
        items=items,
    )
