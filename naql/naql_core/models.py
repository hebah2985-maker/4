"""Shared domain models: Enums and frozen dataclasses (N6, F6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Verdict(StrEnum):
    """Quote match verdict (FR-13)."""

    EXACT = "EXACT"
    MINOR_DIFF = "MINOR_DIFF"
    ALTERED = "ALTERED"
    SEMANTIC_ONLY = "SEMANTIC_ONLY"
    NOT_FOUND = "NOT_FOUND"
    UNRELIABLE_OCR = "UNRELIABLE_OCR"


class PageVerdict(StrEnum):
    """Claimed-page verdict (FR-14)."""

    PAGE_OK = "PAGE_OK"
    PAGE_WRONG = "PAGE_WRONG"
    PAGE_UNKNOWN = "PAGE_UNKNOWN"


class ClaimVerdict(StrEnum):
    """Claim-support verdict (FR-30, S1)."""

    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    EXCEEDS_TEXT = "EXCEEDS_TEXT"
    NOT_PROVEN_IN_SOURCE = "NOT_PROVEN_IN_SOURCE"
    CONTRADICTED = "CONTRADICTED"


class QaStatus(StrEnum):
    """Q&A pipeline outcome."""

    ANSWERED = "ANSWERED"
    ABSTAINED = "ABSTAINED"
    REFUSED = "REFUSED"


class TextSource(StrEnum):
    """How a page's text was obtained (FR-03)."""

    TEXT_LAYER = "text_layer"
    OCR = "ocr"


class Confidence(StrEnum):
    """Human-readable confidence level (UX-06)."""

    HIGH = "high"
    MEDIUM = "medium"
    NEEDS_REVIEW = "needs_review"


class DiffOpKind(StrEnum):
    """Word-level diff operation kinds (FR-15)."""

    EQUAL = "equal"
    ADDED = "added"
    REMOVED = "removed"
    REPLACED = "replaced"


@dataclass(frozen=True)
class DiffOp:
    """One word-level diff operation between quote and matched source."""

    kind: DiffOpKind
    quote_word: str
    source_word: str


@dataclass(frozen=True)
class NormalizedText:
    """Normalized text plus position map back to the original (K1)."""

    text_norm: str
    # norm_to_orig[i] = index in the original string of norm char i.
    norm_to_orig: tuple[int, ...]


@dataclass(frozen=True)
class MatchCandidate:
    """A fuzzy-match candidate location inside the joined source text."""

    char_start: int
    char_end: int
    similarity: float
    pdf_pages: tuple[int, ...]


@dataclass(frozen=True)
class QuoteCheckResult:
    """Full result of a citation check (FR-13, FR-14, FR-15, FR-18)."""

    verdict: Verdict
    page_verdict: PageVerdict
    matched_pdf_page: int | None
    matched_printed_page: int | None
    claimed_printed_page: int | None
    confidence: Confidence
    similarity: float
    word_diff: tuple[DiffOp, ...]
    matched_text_raw: str
    reason: str
    crossed_pages: bool = False


@dataclass(frozen=True)
class PageRecord:
    """One stored source page (FR-03)."""

    id: int
    doc_id: int
    pdf_page: int
    printed_page: int
    text_raw: str
    text_norm: str
    text_source: TextSource
    ocr_confidence: float | None
    image_path: str | None


@dataclass(frozen=True)
class Chunk:
    """One retrieval unit (§16.1)."""

    id: int
    doc_id: int
    pdf_page: int
    printed_page: int
    char_start: int
    char_end: int
    text_raw: str
    text_norm: str


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk with its hybrid retrieval score."""

    chunk: Chunk
    score: float
    lexical_rank: int | None = None
    semantic_rank: int | None = None


@dataclass(frozen=True)
class QaSentence:
    """One answer sentence with its citation (FR-22)."""

    text: str
    pdf_page: int
    printed_page: int
    quote: str


@dataclass(frozen=True)
class QaResult:
    """Q&A pipeline output (§19.4)."""

    status: QaStatus
    sentences: tuple[QaSentence, ...] = ()
    nearest_chunks: tuple[RetrievedChunk, ...] = ()
    model_id: str = ""
    prompt_version: str = ""


@dataclass(frozen=True)
class ClaimCheckResult:
    """Claim-support check output (FR-30, FR-31)."""

    verdict: ClaimVerdict
    explanation: str
    supporting_spans: tuple[str, ...] = ()
    contradicting_spans: tuple[str, ...] = ()


@dataclass(frozen=True)
class IngestProgress:
    """Ingestion progress snapshot (FR-05)."""

    total_pages: int
    done_pages: int
    low_quality_pdf_pages: tuple[int, ...] = field(default=())


@dataclass(frozen=True)
class DocumentInfo:
    """Stored document metadata."""

    id: int
    title: str
    file_path: str
    volume_label: str | None
    page_offset: int
    n_pages: int
    created_at: str
