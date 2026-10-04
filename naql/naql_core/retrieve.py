"""Hybrid retrieval with Reciprocal Rank Fusion and abstention (§16.2, §16.3)."""

from __future__ import annotations

import sqlite3

from naql_core import index, thresholds
from naql_core.models import RetrievedChunk
from naql_core.normalize import normalize_for_match


def retrieve(conn: sqlite3.Connection, doc_id: int, question: str) -> tuple[RetrievedChunk, ...]:
    """Retrieve the best chunks for a question via hybrid search (FR-20).

    Merges FTS5 keyword hits and embedding cosine hits with Reciprocal
    Rank Fusion, returning the top K chunks.

    Returns:
        RetrievedChunks ordered by fused score (may be empty).
    """
    query_norm = normalize_for_match(question).text_norm
    lexical = index.search_fts(conn, doc_id, query_norm, thresholds.RETRIEVE_TOP_K)
    semantic = index.search_semantic(conn, doc_id, query_norm, thresholds.RETRIEVE_TOP_K)

    fused: dict[int, float] = {}
    by_id: dict[int, RetrievedChunk] = {}
    for rank, chunk in enumerate(lexical):
        score = 1.0 / (thresholds.RRF_K + rank + 1)
        fused[chunk.id] = fused.get(chunk.id, 0.0) + score
        by_id[chunk.id] = RetrievedChunk(chunk=chunk, score=0.0, lexical_rank=rank + 1)
    for rank, (chunk, _cos) in enumerate(semantic):
        score = 1.0 / (thresholds.RRF_K + rank + 1)
        fused[chunk.id] = fused.get(chunk.id, 0.0) + score
        existing = by_id.get(chunk.id)
        by_id[chunk.id] = RetrievedChunk(
            chunk=chunk,
            score=0.0,
            lexical_rank=existing.lexical_rank if existing else None,
            semantic_rank=rank + 1,
        )

    ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    results: list[RetrievedChunk] = []
    for chunk_id, score in ranked[: thresholds.RETRIEVE_TOP_K]:
        base = by_id[chunk_id]
        results.append(
            RetrievedChunk(
                chunk=base.chunk,
                score=score,
                lexical_rank=base.lexical_rank,
                semantic_rank=base.semantic_rank,
            )
        )
    return tuple(results)


def should_abstain(results: tuple[RetrievedChunk, ...]) -> bool:
    """Abstention threshold (§16.3, C4): True when evidence is too weak.

    RRF best score is ~0.033 for a chunk topping both channels and ~0.016
    for a single-channel hit, so abstain when there is no keyword hit at
    all and the fused score stays in the single-channel band.
    """
    if not results:
        return True
    best = results[0]
    if best.score < thresholds.ABSTAIN_SCORE_THRESHOLD:
        return True
    return best.lexical_rank is None and best.score < thresholds.RRF_SINGLE_CHANNEL_MAX
