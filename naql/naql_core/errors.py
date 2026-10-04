"""Project-specific exceptions (E1)."""

from __future__ import annotations


class NaqlError(Exception):
    """Base class for all Naql errors."""


class SourceNotFoundError(NaqlError):
    """Referenced document does not exist."""


class OcrFailedError(NaqlError):
    """OCR engine failed on a page."""


class LlmOutputInvalidError(NaqlError):
    """LLM output failed schema validation."""


class LlmUnavailableError(NaqlError):
    """LLM provider is disabled or unreachable."""


class IngestError(NaqlError):
    """The uploaded file could not be processed."""
