"""Naql core package public interface (S6: export via __all__ only)."""

from __future__ import annotations

from naql_core.models import (
    Chunk,
    ClaimCheckResult,
    ClaimVerdict,
    Confidence,
    DiffOp,
    DiffOpKind,
    DocumentInfo,
    IngestProgress,
    MatchCandidate,
    NormalizedText,
    PageRecord,
    PageVerdict,
    QaResult,
    QaSentence,
    QaStatus,
    QuoteCheckResult,
    RetrievedChunk,
    TextSource,
    Verdict,
)

__all__ = [
    "Chunk",
    "ClaimCheckResult",
    "ClaimVerdict",
    "Confidence",
    "DiffOp",
    "DiffOpKind",
    "DocumentInfo",
    "IngestProgress",
    "MatchCandidate",
    "NormalizedText",
    "PageRecord",
    "PageVerdict",
    "QaResult",
    "QaSentence",
    "QaStatus",
    "QuoteCheckResult",
    "RetrievedChunk",
    "TextSource",
    "Verdict",
]
