"""BM25-based local retrieval for agent knowledge queries (stdlib-only)."""

from __future__ import annotations

import json
import math
import pathlib
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    if len(text) <= max_chars:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


@dataclass
class KnowledgeChunk:
    chunk_id: str
    source_id: str
    path: str
    text: str
    tags: list[str]
    priority: int


@dataclass
class SearchHit:
    chunk_id: str
    source_id: str
    path: str
    score: float
    text: str
    tags: list[str]


class BM25Index:
    """Minimal Okapi BM25 inverted index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.chunks: list[KnowledgeChunk] = []
        self.doc_tokens: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.avgdl: float = 0.0
        self.df: Counter[str] = Counter()
        self.N: int = 0

    def add(self, chunk: KnowledgeChunk) -> None:
        tokens = tokenize(chunk.text)
        self.chunks.append(chunk)
        self.doc_tokens.append(tokens)
        self.doc_lengths.append(len(tokens))
        self.N = len(self.chunks)
        seen = set(tokens)
        for term in seen:
            self.df[term] += 1
        self.avgdl = sum(self.doc_lengths) / self.N if self.N else 0.0

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5)) if self.N else 0.0

    def _score_doc(self, query_terms: list[str], doc_idx: int) -> float:
        tokens = self.doc_tokens[doc_idx]
        dl = self.doc_lengths[doc_idx]
        tf = Counter(tokens)
        score = 0.0
        for term in query_terms:
            if term not in tf:
                continue
            freq = tf[term]
            idf = self._idf(term)
            denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            score += idf * (freq * (self.k1 + 1)) / denom
        chunk = self.chunks[doc_idx]
        score *= 1.0 + (0.1 * max(0, 4 - chunk.priority))
        return score

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        terms = tokenize(query)
        if not terms or not self.chunks:
            return []

        scored: list[tuple[int, float]] = []
        for idx in range(self.N):
            s = self._score_doc(terms, idx)
            if s > 0:
                scored.append((idx, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        hits: list[SearchHit] = []
        for idx, score in scored[:top_k]:
            c = self.chunks[idx]
            hits.append(
                SearchHit(
                    chunk_id=c.chunk_id,
                    source_id=c.source_id,
                    path=c.path,
                    score=round(score, 4),
                    text=c.text,
                    tags=c.tags,
                )
            )
        return hits

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": "bm25",
            "k1": self.k1,
            "b": self.b,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "source_id": c.source_id,
                    "path": c.path,
                    "text": c.text,
                    "tags": c.tags,
                    "priority": c.priority,
                }
                for c in self.chunks
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BM25Index":
        index = cls(k1=float(data.get("k1", 1.5)), b=float(data.get("b", 0.75)))
        for item in data.get("chunks") or []:
            chunk = KnowledgeChunk(
                chunk_id=item["chunk_id"],
                source_id=item["source_id"],
                path=item["path"],
                text=item["text"],
                tags=list(item.get("tags") or []),
                priority=int(item.get("priority", 3)),
            )
            index.add(chunk)
        return index

    def save(self, path: pathlib.Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: pathlib.Path) -> "BM25Index":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
