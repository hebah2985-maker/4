"""Document ingestion: PyMuPDF text layer, OCR fallback, chunking (M1, §16.1).

All file/OCR IO lives here (F5). Pages with a usable text layer skip OCR;
scanned pages are rendered to images and OCR'd with Tesseract (ara).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from naql_core import db, thresholds
from naql_core.errors import IngestError, OcrFailedError
from naql_core.models import IngestProgress, TextSource
from naql_core.normalize import normalize_for_match

logger = logging.getLogger(__name__)

_MIN_TEXT_LAYER_CHARS = 20  # below this a page is treated as scanned
_IMAGE_DPI = 200

ProgressCallback = Callable[[IngestProgress], None]


def ingest_pdf(
    conn,
    pdf_path: Path,
    *,
    title: str,
    volume_label: str | None,
    data_dir: Path,
    on_progress: ProgressCallback | None = None,
) -> int:
    """Ingest one PDF: extract text per page, OCR when needed, chunk+index.

    Args:
        conn: Open SQLite connection.
        pdf_path: Path to the uploaded PDF.
        title: Document title.
        volume_label: Optional volume/part label (e.g. "ج 2").
        data_dir: Local storage root for page images.
        on_progress: Optional callback receiving IngestProgress (FR-05).

    Returns:
        The new document id.

    Raises:
        IngestError: If the PDF cannot be opened or has no pages.
    """
    import fitz  # PyMuPDF

    try:
        doc = fitz.open(pdf_path)
    except (fitz.FileDataError, RuntimeError) as exc:
        raise IngestError(f"cannot open PDF: {pdf_path.name}") from exc
    if doc.page_count == 0:
        raise IngestError("PDF has no pages")

    doc_id = db.insert_document(
        conn,
        title=title,
        file_path=str(pdf_path),
        volume_label=volume_label,
        n_pages=doc.page_count,
    )
    low_quality: list[int] = []
    images_dir = data_dir / f"doc_{doc_id}"
    images_dir.mkdir(parents=True, exist_ok=True)

    from naql_core import index  # local import to keep module graph acyclic

    for i in range(doc.page_count):
        pdf_page = i + 1
        page = doc.load_page(i)
        text_raw, source, confidence, image_path = _extract_page(page, pdf_page, images_dir)
        text_norm = normalize_for_match(text_raw).text_norm
        if confidence is not None and confidence < thresholds.OCR_LOW_QUALITY_THRESHOLD:
            low_quality.append(pdf_page)  # FR-06
        db.insert_page(
            conn,
            doc_id=doc_id,
            pdf_page=pdf_page,
            printed_page=pdf_page,
            text_raw=text_raw,
            text_norm=text_norm,
            text_source=source,
            ocr_confidence=confidence,
            image_path=image_path,
        )
        for chunk in _chunk_page(doc_id, pdf_page, pdf_page, text_raw, text_norm):
            index.insert_chunk(conn, chunk)
        if on_progress is not None:
            on_progress(
                IngestProgress(
                    total_pages=doc.page_count,
                    done_pages=pdf_page,
                    low_quality_pdf_pages=tuple(low_quality),
                )
            )
    n_pages = doc.page_count
    doc.close()
    logger.info("ingested doc_id=%d pages=%d low_quality=%d", doc_id, n_pages, len(low_quality))
    return doc_id


def _extract_page(
    page, pdf_page: int, images_dir: Path
) -> tuple[str, TextSource, float | None, str | None]:
    """Extract one page's text; render+OCR if the text layer is unusable (FR-02)."""
    text = _extract_text_rtl(page)
    if len(text) >= _MIN_TEXT_LAYER_CHARS:
        return text, TextSource.TEXT_LAYER, None, None
    image_path = images_dir / f"page_{pdf_page:04d}.png"
    pixmap = page.get_pixmap(dpi=_IMAGE_DPI)
    pixmap.save(image_path)
    ocr_text, confidence = _ocr_image(image_path)
    return ocr_text, TextSource.OCR, confidence, str(image_path)


def _extract_text_rtl(page) -> str:
    """Rebuild Arabic text from word boxes in RTL reading order.

    PyMuPDF's plain text extraction returns Arabic lines in visual
    (reversed) order; sorting each line's words by x descending restores
    the logical order deterministically.
    """
    words = page.get_text("words")
    if not words:
        return ""
    lines: dict[tuple[int, int], list[tuple[float, str]]] = {}
    for x0, _y0, _x1, _y1, word, block_no, line_no, _word_no in words:
        lines.setdefault((block_no, line_no), []).append((x0, word))
    out_lines = []
    for _key, line_words in sorted(lines.items()):
        out_lines.append(" ".join(w for _x, w in sorted(line_words, key=lambda t: -t[0])))
    return "\n".join(out_lines).strip()


def _ocr_image(image_path: Path) -> tuple[str, float]:
    """Run Tesseract (lang=ara) on one page image (M1).

    Raises:
        OcrFailedError: If the OCR engine fails.
    """
    try:
        import pytesseract
        from PIL import Image

        data = pytesseract.image_to_data(
            Image.open(image_path), lang="ara", output_type=pytesseract.Output.DICT
        )
    except Exception as exc:  # engine boundary: convert to dedicated error (E3)
        raise OcrFailedError(f"OCR failed for {image_path.name}") from exc
    words = [w for w in data["text"] if w.strip()]
    pairs = zip(data["conf"], data["text"], strict=False)
    confidences = [float(c) for c, w in pairs if w.strip() and float(c) >= 0]
    mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return " ".join(words), mean_conf


def _chunk_page(
    doc_id: int, pdf_page: int, printed_page: int, text_raw: str, text_norm: str
) -> list[tuple]:
    """Split one page into mid-length chunks with light overlap (§16.1)."""
    words = text_norm.split(" ")
    if not words or not words[0]:
        return []
    chunks: list[tuple] = []
    step = thresholds.CHUNK_TARGET_WORDS - thresholds.CHUNK_OVERLAP_WORDS
    # word offsets within text_norm
    offsets: list[int] = []
    pos = 0
    for w in words:
        offsets.append(pos)
        pos += len(w) + 1
    for start in range(0, len(words), step):
        end = min(start + thresholds.CHUNK_TARGET_WORDS, len(words))
        char_start = offsets[start]
        char_end = offsets[end - 1] + len(words[end - 1])
        chunks.append(
            (
                doc_id,
                pdf_page,
                printed_page,
                char_start,
                char_end,
                _raw_slice(text_raw, text_norm, char_start, char_end),
                text_norm[char_start:char_end],
            )
        )
        if end == len(words):
            break
    return chunks


def _raw_slice(text_raw: str, text_norm: str, char_start: int, char_end: int) -> str:
    """Best-effort raw slice for a chunk (display aid, not position-exact)."""
    del text_norm
    return text_raw[char_start:char_end] if char_end <= len(text_raw) else text_raw
