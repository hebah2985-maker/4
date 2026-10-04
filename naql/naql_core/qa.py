"""Question-answering pipeline: retrieve → LLM → verify quotes → answer/abstain (§19.4).

The LLM is used ONLY here and in claims.py (C3), only to phrase answers
from retrieved paragraphs. Every generated quote is re-verified against
the source before display (FR-23, K4). Abstention beats guessing (C4).
"""

from __future__ import annotations

import logging
import sqlite3

from naql_core import db, retrieve, safety, thresholds
from naql_core.errors import LlmOutputInvalidError, LlmUnavailableError
from naql_core.llm import LLMClient, load_prompt
from naql_core.match import JoinedSource, verify_quote_exists
from naql_core.models import QaResult, QaSentence, QaStatus, RetrievedChunk

logger = logging.getLogger(__name__)

_QA_PROMPT_VERSION = "v1"


def answer_question(
    conn: sqlite3.Connection,
    source: JoinedSource,
    llm: LLMClient,
    *,
    doc_id: int,
    question: str,
) -> QaResult:
    """Run the full Q&A pipeline (FR-20..26, TC-01/02/19/20).

    Returns:
        QaResult with status ANSWERED / ABSTAINED / REFUSED.
    """
    if safety.is_fatwa_request(question):  # C5, FR-25
        logger.info("qa refused: fatwa-pattern question doc_id=%d", doc_id)
        return _persist(conn, doc_id, question, QaResult(status=QaStatus.REFUSED))

    chunks = retrieve.retrieve(conn, doc_id, question)
    if retrieve.should_abstain(chunks):  # §16.3, FR-24
        return _persist(
            conn,
            doc_id,
            question,
            QaResult(status=QaStatus.ABSTAINED, nearest_chunks=chunks),
        )

    result = _generate(conn, source, llm, question, chunks)
    return _persist(conn, doc_id, question, result)


def _generate(
    conn: sqlite3.Connection,
    source: JoinedSource,
    llm: LLMClient,
    question: str,
    chunks: tuple[RetrievedChunk, ...],
) -> QaResult:
    """Generate an answer via LLM with one retry, else deterministic fallback."""
    try:
        return _llm_answer(source, llm, question, chunks)
    except LlmUnavailableError:
        logger.info("llm unavailable; using extractive fallback")
        return _extractive_answer(chunks)
    except LlmOutputInvalidError:
        logger.info("llm invalid output; retrying once (E4)")
        try:
            return _llm_answer(source, llm, question, chunks)
        except (LlmUnavailableError, LlmOutputInvalidError):
            return QaResult(status=QaStatus.ABSTAINED, nearest_chunks=chunks)


def _llm_answer(
    source: JoinedSource,
    llm: LLMClient,
    question: str,
    chunks: tuple[RetrievedChunk, ...],
) -> QaResult:
    """LLM phrasing path: strict prompt, schema check, per-quote re-verification."""
    prompt = load_prompt("qa_answer", _QA_PROMPT_VERSION)
    evidence = "\n\n".join(
        f"[pdf_page={c.chunk.pdf_page} printed_page={c.chunk.printed_page}]\n{c.chunk.text_raw}"
        for c in chunks
    )
    payload = llm.complete_json(prompt.text, f"السؤال: {question}\n\nالفقرات:\n{evidence}")
    if payload.get("status") != "ANSWERED" or not isinstance(payload.get("sentences"), list):
        return QaResult(
            status=QaStatus.ABSTAINED,
            nearest_chunks=chunks,
            model_id=llm.model_id,
            prompt_version=_QA_PROMPT_VERSION,
        )
    sentences: list[QaSentence] = []
    for item in payload["sentences"]:
        quote = str(item.get("quote", ""))
        if not quote or not verify_quote_exists(source, quote):  # FR-23, K4
            continue  # drop unverified quote, lowering confidence
        sentences.append(
            QaSentence(
                text=str(item.get("text", "")),
                pdf_page=int(item.get("pdf_page", chunks[0].chunk.pdf_page)),
                printed_page=int(item.get("printed_page", chunks[0].chunk.printed_page)),
                quote=quote,
            )
        )
    if not sentences:
        return QaResult(
            status=QaStatus.ABSTAINED,
            nearest_chunks=chunks,
            model_id=llm.model_id,
            prompt_version=_QA_PROMPT_VERSION,
        )
    return QaResult(
        status=QaStatus.ANSWERED,
        sentences=tuple(sentences),
        nearest_chunks=chunks,
        model_id=llm.model_id,
        prompt_version=_QA_PROMPT_VERSION,
    )


def _extractive_answer(chunks: tuple[RetrievedChunk, ...]) -> QaResult:
    """Deterministic fallback: quote the best chunk verbatim (no LLM needed)."""
    best = chunks[0].chunk
    words = best.text_raw.split()
    quote = " ".join(words[: thresholds.MAX_DISPLAY_QUOTE_WORDS])
    sentence = QaSentence(
        text="النص يقول:",
        pdf_page=best.pdf_page,
        printed_page=best.printed_page,
        quote=quote,
    )
    return QaResult(
        status=QaStatus.ANSWERED,
        sentences=(sentence,),
        nearest_chunks=chunks,
        model_id="extractive-fallback",
        prompt_version="",
    )


def _persist(conn: sqlite3.Connection, doc_id: int, question: str, result: QaResult) -> QaResult:
    """Store the run for later evaluation (FR-40); logs carry no user text (L2)."""
    import json

    answer_json = (
        json.dumps([s.__dict__ for s in result.sentences], ensure_ascii=False)
        if result.sentences
        else None
    )
    scores = db.encode_scores([(c.chunk.id, c.score) for c in result.nearest_chunks])
    db.insert_qa_run(
        conn,
        doc_id=doc_id,
        question=question,
        answer_json=answer_json,
        status=result.status.value,
        retrieval_scores=scores,
        model_id=result.model_id,
        prompt_version=result.prompt_version,
    )
    logger.info("qa run doc_id=%d status=%s", doc_id, result.status.value)
    return result
