"""SQLite access layer: connection, schema, named queries (D1..D5).

All SQLite access goes through the named functions here and in index.py
(D3). Statements always use bound parameters (D2).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from naql_core.errors import SourceNotFoundError
from naql_core.models import DocumentInfo, PageRecord, TextSource

_SCHEMA_VERSION = 1
_SCHEMA_FILE = Path(__file__).with_name("schema.sql")


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection with FK enforcement; committed on exit (F8)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    """Create schema if absent and record schema version (D1)."""
    schema_sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    with connect(db_path) as conn:
        conn.executescript(schema_sql)
        row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
        if row["v"] is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (_SCHEMA_VERSION,))


def insert_document(
    conn: sqlite3.Connection,
    *,
    title: str,
    file_path: str,
    volume_label: str | None,
    n_pages: int,
) -> int:
    """Insert a document row and return its id."""
    cur = conn.execute(
        "INSERT INTO documents (title, file_path, volume_label, n_pages) VALUES (?, ?, ?, ?)",
        (title, file_path, volume_label, n_pages),
    )
    return int(cur.lastrowid)


def insert_page(
    conn: sqlite3.Connection,
    *,
    doc_id: int,
    pdf_page: int,
    printed_page: int,
    text_raw: str,
    text_norm: str,
    text_source: TextSource,
    ocr_confidence: float | None,
    image_path: str | None,
) -> int:
    """Insert one page row (D4: text_raw is immutable afterwards)."""
    cur = conn.execute(
        "INSERT INTO pages (doc_id, pdf_page, printed_page, text_raw, text_norm,"
        " text_source, ocr_confidence, image_path)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            doc_id,
            pdf_page,
            printed_page,
            text_raw,
            text_norm,
            text_source.value,
            ocr_confidence,
            image_path,
        ),
    )
    return int(cur.lastrowid)


def get_document(conn: sqlite3.Connection, doc_id: int) -> DocumentInfo:
    """Fetch a document or raise SourceNotFoundError."""
    row = conn.execute(
        "SELECT id, title, file_path, volume_label, page_offset, n_pages, created_at"
        " FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()
    if row is None:
        raise SourceNotFoundError(f"document {doc_id} not found")
    return DocumentInfo(**dict(row))


def list_documents(conn: sqlite3.Connection) -> list[DocumentInfo]:
    """List all documents, newest first."""
    rows = conn.execute(
        "SELECT id, title, file_path, volume_label, page_offset, n_pages, created_at"
        " FROM documents ORDER BY id DESC"
    ).fetchall()
    return [DocumentInfo(**dict(r)) for r in rows]


def get_pages(conn: sqlite3.Connection, doc_id: int) -> list[PageRecord]:
    """Return all pages of a document ordered by pdf_page."""
    rows = conn.execute(
        "SELECT id, doc_id, pdf_page, printed_page, text_raw, text_norm,"
        " text_source, ocr_confidence, image_path"
        " FROM pages WHERE doc_id = ? ORDER BY pdf_page",
        (doc_id,),
    ).fetchall()
    return [PageRecord(**{**dict(r), "text_source": TextSource(r["text_source"])}) for r in rows]


def set_page_offset(conn: sqlite3.Connection, doc_id: int, offset: int) -> None:
    """Update the print-numbering offset and recompute printed_page (FR-04)."""
    conn.execute("UPDATE documents SET page_offset = ? WHERE id = ?", (offset, doc_id))
    conn.execute(
        "UPDATE pages SET printed_page = pdf_page - ? WHERE doc_id = ?",
        (offset, doc_id),
    )
    conn.execute(
        "UPDATE chunks SET printed_page = pdf_page - ? WHERE doc_id = ?",
        (offset, doc_id),
    )


def insert_check_run(
    conn: sqlite3.Connection,
    *,
    doc_id: int,
    quote: str,
    claimed_page: int | None,
    page_basis: str | None,
    claim: str | None,
    verdict: str,
    page_verdict: str,
    matched_page: int | None,
    confidence: str,
    diff_json: str,
) -> int:
    """Persist a citation-check run (FR-40)."""
    cur = conn.execute(
        "INSERT INTO check_runs (doc_id, quote, claimed_page, page_basis, claim,"
        " verdict, page_verdict, matched_page, confidence, diff_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            doc_id,
            quote,
            claimed_page,
            page_basis,
            claim,
            verdict,
            page_verdict,
            matched_page,
            confidence,
            diff_json,
        ),
    )
    return int(cur.lastrowid)


def insert_qa_run(
    conn: sqlite3.Connection,
    *,
    doc_id: int,
    question: str,
    answer_json: str | None,
    status: str,
    retrieval_scores: str,
    model_id: str,
    prompt_version: str,
) -> int:
    """Persist a Q&A run (FR-40)."""
    cur = conn.execute(
        "INSERT INTO qa_runs (doc_id, question, answer_json, status,"
        " retrieval_scores, model_id, prompt_version)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_id, question, answer_json, status, retrieval_scores, model_id, prompt_version),
    )
    return int(cur.lastrowid)


def insert_feedback(
    conn: sqlite3.Connection, *, run_id: int, run_type: str, is_correct: bool, note: str
) -> None:
    """Persist user feedback on a result (FR-42)."""
    conn.execute(
        "INSERT INTO feedback (run_id, run_type, is_correct, note) VALUES (?, ?, ?, ?)",
        (run_id, run_type, int(is_correct), note),
    )


def delete_document(conn: sqlite3.Connection, doc_id: int) -> list[str]:
    """Delete a document and ALL related rows (D5, FR-41).

    Returns:
        File paths (PDF/images) that the caller must remove from disk.
    """
    doc = get_document(conn, doc_id)
    image_rows = conn.execute(
        "SELECT image_path FROM pages WHERE doc_id = ? AND image_path IS NOT NULL",
        (doc_id,),
    ).fetchall()
    files = [doc.file_path] + [r["image_path"] for r in image_rows]
    conn.execute(
        "DELETE FROM feedback WHERE run_id IN (SELECT id FROM check_runs WHERE doc_id = ?)",
        (doc_id,),
    )
    conn.execute(
        "DELETE FROM feedback WHERE run_id IN (SELECT id FROM qa_runs WHERE doc_id = ?)", (doc_id,)
    )
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return files


def encode_scores(scores: list[tuple[int, float]]) -> str:
    """Serialize retrieval scores for qa_runs.retrieval_scores."""
    return json.dumps(scores, ensure_ascii=False)
