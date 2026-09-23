"""Build and query the local knowledge index from KNOWLEDGE_SOURCES.yaml."""

from __future__ import annotations

import pathlib
from typing import Any

from agentic.knowledge.bm25_index import BM25Index, KnowledgeChunk, SearchHit, chunk_text
from agentic.registry import load_knowledge_sources

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def build_index(root: pathlib.Path | None = None) -> BM25Index:
    root = root or REPO_ROOT
    sources_cfg = load_knowledge_sources(root)
    index_cfg = sources_cfg.get("index") or {}
    max_chars = int(index_cfg.get("chunk_max_chars", 1200))
    overlap = int(index_cfg.get("chunk_overlap", 150))

    index = BM25Index()
    chunk_num = 0

    for source in sources_cfg.get("sources") or []:
        if not isinstance(source, dict):
            continue
        if source.get("enabled") is False:
            continue

        rel_path = source.get("path", "")
        file_path = root / rel_path
        if not file_path.exists():
            continue

        text = file_path.read_text(encoding="utf-8", errors="replace")
        source_id = str(source.get("id", rel_path))
        tags = list(source.get("tags") or [])
        priority = int(source.get("priority", 3))

        for piece in chunk_text(text, max_chars=max_chars, overlap=overlap):
            chunk_num += 1
            index.add(
                KnowledgeChunk(
                    chunk_id=f"{source_id}::{chunk_num}",
                    source_id=source_id,
                    path=rel_path,
                    text=piece,
                    tags=tags,
                    priority=priority,
                )
            )

    return index


def default_index_path(root: pathlib.Path | None = None) -> pathlib.Path:
    root = root or REPO_ROOT
    sources_cfg = load_knowledge_sources(root)
    rel = (sources_cfg.get("index") or {}).get("output_dir", "6_ai_runtime_context/knowledge_index")
    return root / rel / "index.json"


def query(
    question: str,
    *,
    top_k: int = 5,
    root: pathlib.Path | None = None,
    rebuild_if_missing: bool = True,
) -> list[SearchHit]:
    root = root or REPO_ROOT
    path = default_index_path(root)
    if not path.exists():
        if not rebuild_if_missing:
            return []
        index = build_index(root)
        index.save(path)
    else:
        index = BM25Index.load(path)

    return index.search(question, top_k=top_k)


def hits_to_dict(hits: list[SearchHit]) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": h.chunk_id,
            "source_id": h.source_id,
            "path": h.path,
            "score": h.score,
            "tags": h.tags,
            "excerpt": h.text[:500] + ("..." if len(h.text) > 500 else ""),
        }
        for h in hits
    ]
