#!/usr/bin/env python3
"""Build local BM25 knowledge index from KNOWLEDGE_SOURCES.yaml for agent RAG retrieval."""

from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.knowledge.retriever import build_index, default_index_path  # noqa: E402
from agentic.optional_tools import is_tool_enabled  # noqa: E402


def main() -> int:
    if not is_tool_enabled("knowledge_index"):
        print("[knowledge-index] SKIP: optional tool disabled")
        return 0

    index = build_index(REPO_ROOT)
    out_path = default_index_path(REPO_ROOT)
    index.save(out_path)
    print(f"[knowledge-index] OK: {len(index.chunks)} chunk(s) -> {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
