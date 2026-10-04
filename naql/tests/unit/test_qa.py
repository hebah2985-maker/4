"""Tests for qa.py using FakeLLMClient (T4, TC-01/02/19/20, C1 gate)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from naql_core import db, index
from naql_core.llm import FakeLLMClient
from naql_core.match import build_joined_source
from naql_core.models import QaStatus, TextSource
from naql_core.normalize import normalize_for_match
from naql_core.qa import answer_question

_TEXT = "قال الله تعالى في كتابه العزيز آيات بينات لكل مسلم مهتد"


@pytest.fixture()
def env(tmp_path: Path):
    """DB with one seeded document plus its joined source."""
    db_path = tmp_path / "qa.sqlite"
    db.init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    doc_id = db.insert_document(
        conn, title="ك", file_path="/tmp/k.pdf", volume_label=None, n_pages=1
    )
    norm = normalize_for_match(_TEXT).text_norm
    db.insert_page(
        conn,
        doc_id=doc_id,
        pdf_page=1,
        printed_page=1,
        text_raw=_TEXT,
        text_norm=norm,
        text_source=TextSource.TEXT_LAYER,
        ocr_confidence=None,
        image_path=None,
    )
    index.insert_chunk(conn, (doc_id, 1, 1, 0, len(norm), _TEXT, norm))
    conn.commit()
    source = build_joined_source([(1, 1, _TEXT)])
    yield conn, doc_id, source
    conn.close()


def test_qa_answered_with_verified_quote(env) -> None:
    conn, doc_id, source = env
    llm = FakeLLMClient(
        [
            {
                "status": "ANSWERED",
                "sentences": [
                    {
                        "text": "النص يذكر آيات بينات.",
                        "quote": "آيات بينات لكل مسلم",
                        "pdf_page": 1,
                        "printed_page": 1,
                    },
                ],
            }
        ]
    )
    result = answer_question(conn, source, llm, doc_id=doc_id, question="ماذا في الكتاب؟")  # type: ignore[arg-type]
    assert result.status == QaStatus.ANSWERED
    assert result.sentences[0].quote == "آيات بينات لكل مسلم"


def test_qa_drops_unverified_llm_quote(env) -> None:
    conn, doc_id, source = env
    llm = FakeLLMClient(
        [
            {
                "status": "ANSWERED",
                "sentences": [
                    {
                        "text": "ادعاء مختلق.",
                        "quote": "نص مختلق كلياً لا وجود له",
                        "pdf_page": 1,
                        "printed_page": 1,
                    },
                ],
            }
        ]
    )
    result = answer_question(conn, source, llm, doc_id=doc_id, question="ماذا في الكتاب؟")  # type: ignore[arg-type]
    assert result.status == QaStatus.ABSTAINED  # unverified quote never shown (C1)


def test_qa_abstains_when_llm_says_insufficient(env) -> None:
    conn, doc_id, source = env
    llm = FakeLLMClient([{"status": "INSUFFICIENT_EVIDENCE", "sentences": []}])
    result = answer_question(conn, source, llm, doc_id=doc_id, question="ماذا في الكتاب؟")  # type: ignore[arg-type]
    assert result.status == QaStatus.ABSTAINED


def test_qa_abstains_after_invalid_output_retry(env) -> None:
    conn, doc_id, source = env
    llm = FakeLLMClient([{"__invalid__": True}, {"__invalid__": True}])
    result = answer_question(conn, source, llm, doc_id=doc_id, question="ماذا في الكتاب؟")  # type: ignore[arg-type]
    assert result.status == QaStatus.ABSTAINED
    assert llm.calls == 2  # E4: exactly one retry


def test_qa_refuses_fatwa_question(env) -> None:
    conn, doc_id, source = env
    llm = FakeLLMClient([])
    result = answer_question(conn, source, llm, doc_id=doc_id, question="ما حكم كذا؟")  # type: ignore[arg-type]
    assert result.status == QaStatus.REFUSED
    assert llm.calls == 0


def test_qa_extractive_fallback_when_llm_disabled(env) -> None:
    conn, doc_id, source = env
    llm = FakeLLMClient([])  # no replies -> LlmUnavailableError
    result = answer_question(conn, source, llm, doc_id=doc_id, question="آيات بينات")  # type: ignore[arg-type]
    assert result.status in (QaStatus.ANSWERED, QaStatus.ABSTAINED)
    if result.status == QaStatus.ANSWERED:
        assert result.model_id == "extractive-fallback"
        assert result.sentences[0].quote  # quote comes verbatim from the chunk
