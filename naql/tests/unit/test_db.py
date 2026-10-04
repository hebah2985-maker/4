"""Tests for db.py and index/retrieve (D5 delete, FTS5, hybrid retrieval)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from naql_core import db, index, retrieve
from naql_core.models import TextSource


@pytest.fixture()
def conn(tmp_path: Path):
    """Fresh in-file database per test."""
    db_path = tmp_path / "test.sqlite"
    db.init_db(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    yield connection
    connection.close()


def _seed_document(conn) -> int:
    doc_id = db.insert_document(
        conn, title="كتاب اختبار", file_path="/tmp/x.pdf", volume_label=None, n_pages=2
    )
    for pdf_page, text in (
        (1, "قال الله تعالى في كتابه العزيز آيات بينات لكل مسلم"),
        (2, "ثم قال المؤلف رحمه الله في باب الصلاة ما نصه هنا"),
    ):
        from naql_core.normalize import normalize_for_match

        norm = normalize_for_match(text).text_norm
        db.insert_page(
            conn,
            doc_id=doc_id,
            pdf_page=pdf_page,
            printed_page=pdf_page,
            text_raw=text,
            text_norm=norm,
            text_source=TextSource.TEXT_LAYER,
            ocr_confidence=None,
            image_path=None,
        )
        index.insert_chunk(conn, (doc_id, pdf_page, pdf_page, 0, len(norm), text, norm))
    return doc_id


def test_insert_and_get_pages(conn) -> None:
    doc_id = _seed_document(conn)
    pages = db.get_pages(conn, doc_id)
    assert len(pages) == 2
    assert pages[0].pdf_page == 1


def test_fts_search_finds_keyword(conn) -> None:
    from naql_core.normalize import normalize_for_match

    doc_id = _seed_document(conn)
    hits = index.search_fts(conn, doc_id, normalize_for_match("الصلاة").text_norm, 5)
    assert hits and hits[0].pdf_page == 2


def test_retrieve_returns_ranked_chunks(conn) -> None:
    doc_id = _seed_document(conn)
    results = retrieve.retrieve(conn, doc_id, "ماذا قال المؤلف عن الصلاة؟")
    assert results
    assert results[0].score >= results[-1].score


def test_should_abstain_on_empty_results(conn) -> None:
    assert retrieve.should_abstain(()) is True


def test_delete_document_removes_everything(conn, tmp_path: Path) -> None:
    doc_id = _seed_document(conn)
    db.insert_check_run(
        conn,
        doc_id=doc_id,
        quote="q",
        claimed_page=None,
        page_basis=None,
        claim=None,
        verdict="EXACT",
        page_verdict="PAGE_OK",
        matched_page=1,
        confidence="high",
        diff_json="[]",
    )
    files = db.delete_document(conn, doc_id)
    assert files
    for table in ("documents", "pages", "chunks", "check_runs", "qa_runs"):
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE "  # noqa: S608 — test table name
            + ("id = ?" if table == "documents" else "doc_id = ?"),
            (doc_id,),
        ).fetchone()
        assert row["n"] == 0


def test_set_page_offset_recomputes_printed_pages(conn) -> None:
    doc_id = _seed_document(conn)
    db.set_page_offset(conn, doc_id, 3)
    pages = db.get_pages(conn, doc_id)
    assert pages[0].printed_page == -2 or pages[0].printed_page == pages[0].pdf_page - 3
