#!/usr/bin/env python3
"""Query the local knowledge index — RAG retrieval for agent sessions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.knowledge.retriever import hits_to_dict, query  # noqa: E402
from agentic.optional_tools import is_tool_enabled  # noqa: E402


def main() -> int:
    if not is_tool_enabled("knowledge_index"):
        print("[knowledge-query] SKIP: optional tool disabled")
        return 0

    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="+", help="Natural language query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    question = " ".join(args.question)
    hits = query(question, top_k=args.top_k, root=REPO_ROOT)

    if args.as_json:
        print(json.dumps(hits_to_dict(hits), indent=2))
        return 0

    if not hits:
        print("[knowledge-query] no hits (run knowledge_index_build.py first)")
        return 0

    print(f"[knowledge-query] top {len(hits)} hit(s) for: {question!r}\n")
    for i, hit in enumerate(hits, 1):
        print(f"{i}. [{hit.score}] {hit.path} ({hit.source_id})")
        excerpt = hit.text.replace("\n", " ")[:240]
        print(f"   {excerpt}...\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
