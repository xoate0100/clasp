"""BM25-based local retrieval for agent knowledge queries (no external API)."""

from agentic.knowledge.bm25_index import BM25Index, KnowledgeChunk, SearchHit, chunk_text
from agentic.knowledge.retriever import build_index, default_index_path, hits_to_dict, query

__all__ = [
    "BM25Index",
    "KnowledgeChunk",
    "SearchHit",
    "chunk_text",
    "build_index",
    "default_index_path",
    "hits_to_dict",
    "query",
]
