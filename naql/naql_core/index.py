"""FTS5 index + lightweight local embeddings storage (§16.2).

Embeddings are deterministic character n-gram hashing vectors computed
locally with NumPy — no external vector DB, no network (NFR-07, §16.4).
The model choice is documented as an open decision (Needs Clarification).
"""

from __future__ import annotations

import sqlite3
import zlib

import numpy as np

from naql_core.models import Chunk

_EMBED_DIM = 512
_NGRAM = 3


def embed_text(text_norm: str) -> np.ndarray:
    """Deterministic local embedding: hashed char-ngram counts, L2-normalized.

    Args:
        text_norm: Normalized text (use normalize_for_match first).

    Returns:
        Unit-norm float32 vector of dim 512.
    """
    vec = np.zeros(_EMBED_DIM, dtype=np.float32)
    padded = f" {text_norm} "
    for i in range(len(padded) - _NGRAM + 1):
        bucket = zlib.crc32(padded[i : i + _NGRAM].encode("utf-8")) % _EMBED_DIM
        vec[bucket] += 1.0
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm > 0 else vec


def insert_chunk(conn: sqlite3.Connection, chunk_row: tuple) -> int:
    """Insert a chunk row and its embedding; FTS5 syncs via trigger (D3).

    Args:
        chunk_row: (doc_id, pdf_page, printed_page, char_start, char_end,
                    text_raw, text_norm).
    """
    embedding = embed_text(chunk_row[6])
    cur = conn.execute(
        "INSERT INTO chunks (doc_id, pdf_page, printed_page, char_start, char_end,"
        " text_raw, text_norm, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (*chunk_row, embedding.tobytes()),
    )
    return int(cur.lastrowid)


def search_fts(conn: sqlite3.Connection, doc_id: int, query_norm: str, limit: int) -> list[Chunk]:
    """BM25 keyword search over normalized chunk text (§16.2 channel 1)."""
    if not query_norm.strip():
        return []
    rows = conn.execute(
        "SELECT c.id, c.doc_id, c.pdf_page, c.printed_page, c.char_start,"
        " c.char_end, c.text_raw, c.text_norm"
        " FROM chunks_fts f JOIN chunks c ON c.id = f.rowid"
        " WHERE chunks_fts MATCH ? AND c.doc_id = ?"
        " ORDER BY rank LIMIT ?",
        (_fts_escape(query_norm), doc_id, limit),
    ).fetchall()
    return [Chunk(**dict(r)) for r in rows]


def search_semantic(
    conn: sqlite3.Connection, doc_id: int, query_norm: str, limit: int
) -> list[tuple[Chunk, float]]:
    """Cosine similarity search over stored embeddings (§16.2 channel 2)."""
    query_vec = embed_text(query_norm)
    rows = conn.execute(
        "SELECT id, doc_id, pdf_page, printed_page, char_start, char_end,"
        " text_raw, text_norm, embedding FROM chunks WHERE doc_id = ?"
        " AND embedding IS NOT NULL",
        (doc_id,),
    ).fetchall()
    scored: list[tuple[Chunk, float]] = []
    for r in rows:
        vec = np.frombuffer(r["embedding"], dtype=np.float32)
        scored.append(
            (Chunk(**{k: r[k] for k in dict(r) if k != "embedding"}), float(np.dot(query_vec, vec)))
        )
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]


def _fts_escape(query: str) -> str:
    """Quote each token so user input is never parsed as FTS5 syntax (D2)."""
    tokens = [t for t in query.split() if t]
    return " OR ".join(f'"{t}"' for t in tokens) if tokens else '""'
