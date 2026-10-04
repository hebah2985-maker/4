"""Claim-support judgement (S1, FR-30..33).

Evaluates the relation between the student's claim and the source text
around a matched quote. LLM is used here only (besides qa.py — C3), and
its cited spans are re-verified for presence in the text (FR-33, K4).
"""

from __future__ import annotations

import logging

from naql_core.errors import LlmOutputInvalidError, LlmUnavailableError
from naql_core.llm import LLMClient, load_prompt
from naql_core.models import ClaimCheckResult, ClaimVerdict

logger = logging.getLogger(__name__)

_CLAIM_PROMPT_VERSION = "v1"

_VALID_VERDICTS = {v.value for v in ClaimVerdict}


def judge_claim(llm: LLMClient, *, claim: str, matched_text_raw: str) -> ClaimCheckResult:
    """Judge whether the matched source text supports the claim (FR-30).

    Args:
        llm: The swappable LLM client.
        claim: The student's conclusion.
        matched_text_raw: Source text matched to the quote (original form).

    Returns:
        ClaimCheckResult; NOT_PROVEN_IN_SOURCE on LLM failure (E4, C4).
    """
    prompt = load_prompt("claim_support", _CLAIM_PROMPT_VERSION)
    user = f"النص من المصدر:\n{matched_text_raw}\n\nاستنتاج الطالب:\n{claim}"
    for attempt in range(2):  # E4: one retry then abstain-equivalent
        try:
            payload = llm.complete_json(prompt.text, user)
            return _parse(payload, matched_text_raw)
        except (LlmUnavailableError, LlmOutputInvalidError):
            logger.info("claim judge failed attempt=%d", attempt + 1)
    return ClaimCheckResult(
        verdict=ClaimVerdict.NOT_PROVEN_IN_SOURCE,
        explanation="تعذّر الحكم آلياً؛ لا يثبت الملف المرفوع هذا الاستنتاج.",
    )


def _parse(payload: dict, matched_text_raw: str) -> ClaimCheckResult:
    """Schema-validate the LLM verdict and re-verify its spans (FR-33)."""
    verdict_raw = str(payload.get("verdict", ""))
    if verdict_raw not in _VALID_VERDICTS:
        raise LlmOutputInvalidError(f"invalid claim verdict: {verdict_raw!r}")
    supporting = _verified_spans(payload.get("supporting_spans"), matched_text_raw)
    contradicting = _verified_spans(payload.get("contradicting_spans"), matched_text_raw)
    return ClaimCheckResult(
        verdict=ClaimVerdict(verdict_raw),
        explanation=str(payload.get("explanation", "")),
        supporting_spans=supporting,
        contradicting_spans=contradicting,
    )


def _verified_spans(spans: object, text: str) -> tuple[str, ...]:
    """Keep only spans that literally occur in the matched text (K4)."""
    if not isinstance(spans, list):
        return ()
    return tuple(str(s) for s in spans if str(s) and str(s) in text)
