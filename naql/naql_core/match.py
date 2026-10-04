"""Deterministic quote matching, word diff, and page judgement (C2, FR-10..16).

All functions are pure (F4): no IO, no network, no global state. The LLM
is NEVER used here (C2).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from rapidfuzz import fuzz

from naql_core import thresholds
from naql_core.models import (
    Confidence,
    DiffOp,
    DiffOpKind,
    MatchCandidate,
    NormalizedText,
    PageVerdict,
    QuoteCheckResult,
    Verdict,
)
from naql_core.normalize import normalize_for_match, orig_span


@dataclass(frozen=True)
class JoinedSource:
    """One continuous normalized source with a page-position table (K2).

    Enables matching quotes that span two pages without page-by-page search.
    """

    raw: str
    norm: NormalizedText
    # page_bounds[i] = (pdf_page, printed_page, norm_start, norm_end)
    page_bounds: tuple[tuple[int, int, int, int], ...]


def build_joined_source(
    pages: list[tuple[int, int, str]],
) -> JoinedSource:
    """Join page texts into one continuous string with page bounds (K2).

    Args:
        pages: (pdf_page, printed_page, text_raw) ordered by pdf_page.

    Returns:
        JoinedSource whose page_bounds map norm ranges to pages.
    """
    raw_parts: list[str] = []
    bounds: list[tuple[int, int, int, int]] = []
    cursor = 0
    for pdf_page, printed_page, text_raw in pages:
        norm = normalize_for_match(text_raw)
        start = cursor
        cursor += len(norm.text_norm) + 1  # +1 for joining space
        bounds.append((pdf_page, printed_page, start, start + len(norm.text_norm)))
        raw_parts.append(text_raw)
    raw = "\n".join(raw_parts)
    return JoinedSource(raw=raw, norm=normalize_for_match(raw), page_bounds=tuple(bounds))


def _pages_of_span(source: JoinedSource, start: int, end: int) -> tuple[int, ...]:
    """Return pdf_pages whose bounds intersect norm span [start, end)."""
    pages: list[int] = []
    for pdf_page, _printed, b_start, b_end in source.page_bounds:
        if b_start < end and start < b_end:
            pages.append(pdf_page)
    return tuple(pages)


def find_exact(source: JoinedSource, quote_norm: str) -> MatchCandidate | None:
    """Exact substring search in normalized source text (FR-11, incl. cross-page)."""
    idx = source.norm.text_norm.find(quote_norm)
    if idx < 0:
        return None
    end = idx + len(quote_norm)
    return MatchCandidate(
        char_start=idx,
        char_end=end,
        similarity=1.0,
        pdf_pages=_pages_of_span(source, idx, end),
    )


def find_best_match(source: JoinedSource, quote_norm: str) -> MatchCandidate | None:
    """Sliding-window fuzzy match over the joined source (FR-12).

    Windows are sized around the quote's normalized length and scored with
    token-aware similarity. Returns the best candidate above
    FUZZY_CANDIDATE_THRESHOLD, else None.
    """
    quote_words = quote_norm.split()
    if not quote_words:
        return None
    source_norm = source.norm.text_norm
    source_words = source_norm.split(" ")
    if not source_words:
        return None

    # word index -> char offset in source_norm
    offsets: list[int] = []
    pos = 0
    for word in source_words:
        offsets.append(pos)
        pos += len(word) + 1

    q_len = len(quote_words)
    lo = max(1, q_len - 1)
    hi = q_len + 1
    best: MatchCandidate | None = None
    best_score = 0.0
    for win_len in range(lo, hi + 1):
        for i in range(0, max(0, len(source_words) - win_len + 1)):
            window = " ".join(source_words[i : i + win_len])
            # Coverage factor keeps shorter windows from winning by
            # truncating the quote (a removed word then looks replaced).
            coverage = min(1.0, win_len / q_len)
            score = (fuzz.ratio(quote_norm, window) / 100.0) * coverage
            if score > best_score:
                start_char = offsets[i]
                end_char = offsets[i + win_len - 1] + len(source_words[i + win_len - 1])
                best = MatchCandidate(
                    char_start=start_char,
                    char_end=end_char,
                    similarity=score,
                    pdf_pages=_pages_of_span(source, start_char, end_char),
                )
                best_score = score
    if best is None or best_score < thresholds.FUZZY_CANDIDATE_THRESHOLD:
        return None
    return best


def compute_word_diff(quote_norm: str, matched_norm: str) -> tuple[DiffOp, ...]:
    """Word-level diff between quote and matched source (FR-15).

    Returns:
        DiffOps in matched-text order; replacements pair removed/added.
    """
    matcher = difflib.SequenceMatcher(a=quote_norm.split(), b=matched_norm.split(), autojunk=False)
    ops: list[DiffOp] = []
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        q_words = quote_norm.split()[a0:a1]
        s_words = matched_norm.split()[b0:b1]
        if tag == "equal":
            ops.extend(
                DiffOp(DiffOpKind.EQUAL, q, s) for q, s in zip(q_words, s_words, strict=True)
            )
        elif tag == "replace":
            for i in range(max(len(q_words), len(s_words))):
                ops.append(
                    DiffOp(
                        DiffOpKind.REPLACED,
                        q_words[i] if i < len(q_words) else "",
                        s_words[i] if i < len(s_words) else "",
                    )
                )
        elif tag == "delete":
            ops.extend(DiffOp(DiffOpKind.REMOVED, q, "") for q in q_words)
        elif tag == "insert":
            ops.extend(DiffOp(DiffOpKind.ADDED, "", s) for s in s_words)
    return tuple(ops)


def _classify(
    candidate: MatchCandidate | None,
    diff: tuple[DiffOp, ...],
    is_exact: bool,
    ocr_low_quality: bool,
) -> Verdict:
    """Map match evidence to a Verdict (FR-13, §17.2)."""
    if ocr_low_quality and candidate is None:
        return Verdict.UNRELIABLE_OCR
    if candidate is None:
        return Verdict.NOT_FOUND
    if is_exact:
        return Verdict.EXACT
    has_word_change = any(op.kind != DiffOpKind.EQUAL for op in diff)
    if candidate.similarity >= thresholds.MINOR_DIFF_THRESHOLD and not has_word_change:
        return Verdict.MINOR_DIFF
    if candidate.similarity >= thresholds.ALTERED_THRESHOLD:
        return Verdict.ALTERED
    if candidate.similarity >= thresholds.SEMANTIC_ONLY_THRESHOLD:
        return Verdict.SEMANTIC_ONLY
    return Verdict.UNRELIABLE_OCR if ocr_low_quality else Verdict.NOT_FOUND


def judge_page(
    matched_pdf_page: int | None,
    claimed_page: int | None,
    page_basis: str,
    offset: int,
) -> tuple[PageVerdict, int | None]:
    """Compare the actual match page with the claimed page (FR-14).

    Args:
        matched_pdf_page: pdf_page where the quote was found (None if not found).
        claimed_page: Page number as the user wrote it (None if not given).
        page_basis: "pdf" or "printed" — which numbering the user used.
        offset: printed_page = pdf_page − offset (FR-04).

    Returns:
        (PageVerdict, matched_printed_page or None).
    """
    matched_printed = matched_pdf_page - offset if matched_pdf_page is not None else None
    if claimed_page is None or matched_pdf_page is None:
        return PageVerdict.PAGE_UNKNOWN, matched_printed
    actual = matched_pdf_page if page_basis == "pdf" else matched_printed
    if actual == claimed_page:
        return PageVerdict.PAGE_OK, matched_printed
    return PageVerdict.PAGE_WRONG, matched_printed


def verify_quote_exists(source: JoinedSource, quote: str) -> bool:
    """C1 gate: True iff the quote exists (exact or fuzzy) in the source.

    No quote may be shown to the user without passing this check.
    """
    quote_norm = normalize_for_match(quote).text_norm
    if not quote_norm:
        return False
    if find_exact(source, quote_norm) is not None:
        return True
    return find_best_match(source, quote_norm) is not None


def check_quote(
    source: JoinedSource,
    quote: str,
    *,
    claimed_page: int | None = None,
    page_basis: str = "pdf",
    offset: int = 0,
    ocr_low_quality: bool = False,
) -> QuoteCheckResult:
    """Full citation check pipeline (§19.3, FR-10..18).

    normalize → exact → fuzzy → word diff → page judgement → verdict.
    """
    quote_norm_obj = normalize_for_match(quote)
    quote_norm = quote_norm_obj.text_norm
    exact = find_exact(source, quote_norm) if quote_norm else None
    candidate = exact if exact is not None else find_best_match(source, quote_norm)

    diff: tuple[DiffOp, ...] = ()
    matched_raw = ""
    if candidate is not None:
        matched_norm = source.norm.text_norm[candidate.char_start : candidate.char_end]
        matched_raw = orig_span(source.norm, candidate.char_start, candidate.char_end, source.raw)
        if exact is None:
            diff = compute_word_diff(quote_norm, matched_norm)

    verdict = _classify(candidate, diff, exact is not None, ocr_low_quality)
    matched_pdf_page = candidate.pdf_pages[0] if candidate is not None else None
    page_verdict, matched_printed = judge_page(matched_pdf_page, claimed_page, page_basis, offset)
    confidence = _confidence(verdict, candidate, ocr_low_quality, quote_norm)
    return QuoteCheckResult(
        verdict=verdict,
        page_verdict=page_verdict,
        matched_pdf_page=matched_pdf_page,
        matched_printed_page=matched_printed,
        claimed_printed_page=claimed_page,
        confidence=confidence,
        similarity=candidate.similarity if candidate else 0.0,
        word_diff=diff,
        matched_text_raw=_clip_words(matched_raw),
        reason=_reason(verdict, diff),
        crossed_pages=candidate is not None and len(candidate.pdf_pages) > 1,
    )


def _confidence(
    verdict: Verdict,
    candidate: MatchCandidate | None,
    ocr_low_quality: bool,
    quote_norm: str,
) -> Confidence:
    """Map evidence to a three-level confidence (UX-06)."""
    if ocr_low_quality or len(quote_norm.split()) < thresholds.MIN_RELIABLE_QUOTE_WORDS:
        return Confidence.NEEDS_REVIEW
    if verdict in (Verdict.EXACT, Verdict.NOT_FOUND) or (
        candidate and candidate.similarity >= thresholds.MINOR_DIFF_THRESHOLD
    ):
        return Confidence.HIGH
    return Confidence.MEDIUM


def _clip_words(text: str) -> str:
    """Clip matched text for display (§17.3: short quotes only)."""
    words = text.split()
    if len(words) <= thresholds.MAX_DISPLAY_QUOTE_WORDS:
        return text
    return " ".join(words[: thresholds.MAX_DISPLAY_QUOTE_WORDS]) + " …"


def _reason(verdict: Verdict, diff: tuple[DiffOp, ...]) -> str:
    """Readable reason for the verdict (FR-18, C8: non-accusatory wording)."""
    if verdict == Verdict.EXACT:
        return "النص مطابق تماماً لما في المصدر."
    if verdict == Verdict.NOT_FOUND:
        return "لم أجد هذا النص في الملف المرفوع."
    if verdict == Verdict.UNRELIABLE_OCR:
        return "جودة النص المستخرج منخفضة، فلا يمكن الجزم بالحكم."
    changed = sum(1 for op in diff if op.kind == DiffOpKind.REPLACED)
    if changed:
        return f"وُجدت {changed} كلمة مختلفة عن المصدر."
    return "وُجد اختلاف يسير (تشكيل أو ترقيم أو تطويل)."
